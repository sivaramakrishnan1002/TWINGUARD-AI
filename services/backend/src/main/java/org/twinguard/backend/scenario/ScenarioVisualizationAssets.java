package org.twinguard.backend.scenario;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.LocalDate;
import java.time.Instant;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.regex.Pattern;

/**
 * Internal read-only projection of the A20 scenario manifest.
 *
 * Controller exposure is limited to the two CR-009 read-only GET operations.
 */
public final class ScenarioVisualizationAssets {
    private static final int MAX_MANIFEST_BYTES = 256 * 1024;
    private static final int MAX_RASTER_REFERENCES = 64;
    private static final long MAX_RASTER_BYTES = 64 * 1024;
    private static final long MAX_TOTAL_RASTER_BYTES = 1024 * 1024;
    private static final Pattern SCENARIO_ID = Pattern.compile("^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$");
    private static final Pattern SHA256 = Pattern.compile("^[0-9a-f]{64}$");
    private static final List<String> CATALOG_KEYS = List.of(
            "schema_version", "artifact_version", "status", "grid", "depth_units", "nodata",
            "provenance", "context_layers", "limitations", "presentation_policy", "time_basis");
    private static final List<String> SERIES_SUMMARY_KEYS = List.of(
            "event_id", "scenario_id", "source_mode", "window_start_utc", "window_end_utc_inclusive",
            "member_count", "rainfall_semantics", "band_semantics");

    private final Path projectRoot;
    private final Path manifestPath;
    private final ObjectMapper mapper;

    public ScenarioVisualizationAssets(Path projectRoot, ObjectMapper mapper) {
        this.projectRoot = projectRoot;
        this.manifestPath = projectRoot.resolve("data/features/visualization3d/batch2_v1/manifest.json");
        this.mapper = mapper;
    }

    public ObjectNode catalog() {
        JsonNode manifest = readVerifiedManifest();
        ObjectNode result = mapper.createObjectNode();
        for (String key : CATALOG_KEYS) {
            result.set(key, manifest.path(key).deepCopy());
        }
        ArrayNode summaries = mapper.createArrayNode();
        for (JsonNode series : manifest.path("scenario_series")) {
            ObjectNode summary = mapper.createObjectNode();
            for (String key : SERIES_SUMMARY_KEYS) {
                summary.set(key, series.path(key).deepCopy());
            }
            ArrayNode savedTimes = mapper.createArrayNode();
            for (JsonNode slice : series.path("slices")) {
                savedTimes.add(slice.path("valid_time_utc").deepCopy());
            }
            summary.set("saved_times_utc", savedTimes);
            summaries.add(summary);
        }
        result.set("scenario_series", summaries);
        return result;
    }

    public ObjectNode asset(String eventId, String scenarioId) {
        validateSelector(eventId, scenarioId);
        JsonNode manifest = readVerifiedManifest();
        JsonNode selected = null;
        for (JsonNode series : manifest.path("scenario_series")) {
            if (eventId.equals(series.path("event_id").asText())
                    && scenarioId.equals(series.path("scenario_id").asText())) {
                if (selected != null) {
                    throw new ScenarioIdentityConflictException();
                }
                selected = series;
            }
        }
        if (selected == null) {
            throw new ScenarioAssetNotFoundException();
        }
        ObjectNode result = mapper.createObjectNode();
        for (String key : CATALOG_KEYS) {
            if (!"context_layers".equals(key)) {
                result.set(key, manifest.path(key).deepCopy());
            }
        }
        result.set("series", selected.deepCopy());
        return result;
    }

    private JsonNode readVerifiedManifest() {
        try {
            Path realRoot = projectRoot.toRealPath();
            Path realManifest = manifestPath.toRealPath();
            if (!realManifest.startsWith(realRoot) || !Files.isRegularFile(realManifest, LinkOption.NOFOLLOW_LINKS)) {
                throw new ScenarioAssetUnavailableException();
            }
            long size = Files.size(realManifest);
            if (size <= 0 || size > MAX_MANIFEST_BYTES) {
                throw new ScenarioAssetUnavailableException();
            }
            byte[] manifestBytes;
            try (InputStream input = Files.newInputStream(realManifest)) {
                manifestBytes = input.readNBytes(MAX_MANIFEST_BYTES + 1);
            }
            if (manifestBytes.length != size || manifestBytes.length > MAX_MANIFEST_BYTES) {
                throw new ScenarioAssetUnavailableException();
            }
            JsonNode manifest = mapper.readTree(manifestBytes);
            validateManifestShape(manifest);
            verifyRasterReferences(realRoot, manifest);
            return manifest;
        } catch (ScenarioIdentityConflictException | ScenarioAssetUnavailableException exception) {
            throw exception;
        } catch (IOException | RuntimeException exception) {
            // Keep paths and low-level filesystem diagnostics out of the service surface.
            throw new ScenarioAssetUnavailableException();
        }
    }

    private void validateManifestShape(JsonNode manifest) {
        if (!manifest.isObject()
                || !"1.0.0".equals(manifest.path("schema_version").asText())
                || !"batch2_v1".equals(manifest.path("artifact_version").asText())
                || !"DERIVED_ASSUMPTION_BASED_RESEARCH_SCENARIO".equals(manifest.path("status").asText())
                || !manifest.path("scenario_series").isArray()
                || manifest.path("scenario_series").size() > 3
                || !manifest.path("context_layers").isArray()
                || manifest.path("context_layers").size() > 4) {
            throw new ScenarioAssetUnavailableException();
        }
        HashSet<String> identities = new HashSet<>();
        for (JsonNode series : manifest.path("scenario_series")) {
            try {
                validateSelector(series.path("event_id").asText(null), series.path("scenario_id").asText(null));
            } catch (InvalidScenarioSelectorException exception) {
                throw new ScenarioAssetUnavailableException();
            }
            if (!identities.add(series.path("event_id").asText() + "\u0000" + series.path("scenario_id").asText())) {
                throw new ScenarioIdentityConflictException();
            }
            validateTimestamp(series.path("window_start_utc"));
            validateTimestamp(series.path("window_end_utc_inclusive"));
            JsonNode members = series.path("members");
            JsonNode slices = series.path("slices");
            if (!members.isArray() || members.size() != 20 || !slices.isArray() || slices.size() != 5) {
                throw new ScenarioAssetUnavailableException();
            }
            String previousTime = null;
            for (JsonNode slice : slices) {
                validateTimestamp(slice.path("valid_time_utc"));
                String currentTime = slice.path("valid_time_utc").asText();
                if (previousTime != null && previousTime.compareTo(currentTime) >= 0) {
                    throw new ScenarioAssetUnavailableException();
                }
                previousTime = currentTime;
                validateBands(slice.path("bands"), List.of("p05", "p50", "p95"));
            }
        }
        for (JsonNode context : manifest.path("context_layers")) {
            validateTimestamp(context.path("window_start_utc"));
            validateTimestamp(context.path("window_end_utc_inclusive"));
            validateBands(context.path("bands"), List.of("mean", "p05", "p95"));
            String temporalKind = context.path("temporal_kind").asText();
            if ("per_cell_event_peak".equals(temporalKind)) {
                if (!context.path("valid_time_utc").isNull()
                        || !context.path("selected_hour_index_zero_based").isNull()) {
                    throw new ScenarioAssetUnavailableException();
                }
            } else if ("selected_hour".equals(temporalKind)) {
                validateTimestamp(context.path("valid_time_utc"));
                if (!context.path("selected_hour_index_zero_based").canConvertToInt()
                        || context.path("selected_hour_index_zero_based").asInt() < 0) {
                    throw new ScenarioAssetUnavailableException();
                }
            } else {
                throw new ScenarioAssetUnavailableException();
            }
        }
    }

    private static void validateBands(JsonNode bands, List<String> expected) {
        if (!bands.isObject() || bands.size() != expected.size()) {
            throw new ScenarioAssetUnavailableException();
        }
        for (String name : expected) {
            if (!bands.has(name)) {
                throw new ScenarioAssetUnavailableException();
            }
        }
    }

    private static void validateTimestamp(JsonNode value) {
        String timestamp = value.asText("");
        try {
            if (timestamp.length() > 32 || !timestamp.endsWith("Z")) {
                throw new IllegalArgumentException("Timestamp must be an exact UTC instant.");
            }
            Instant.parse(timestamp);
        } catch (RuntimeException exception) {
            throw new ScenarioAssetUnavailableException();
        }
    }

    private void verifyRasterReferences(Path realRoot, JsonNode manifest) throws IOException {
        List<JsonNode> refs = new ArrayList<>();
        for (JsonNode series : manifest.path("scenario_series")) {
            if (!series.path("slices").isArray() || series.path("slices").size() > 5) {
                throw new ScenarioAssetUnavailableException();
            }
            for (JsonNode slice : series.path("slices")) {
                addRefs(refs, slice.path("bands"));
            }
        }
        for (JsonNode context : manifest.path("context_layers")) {
            addRefs(refs, context.path("bands"));
        }
        if (refs.size() > MAX_RASTER_REFERENCES) {
            throw new ScenarioAssetUnavailableException();
        }
        long totalBytes = 0;
        for (JsonNode ref : refs) {
            long size = ref.path("size_bytes").asLong(-1);
            if (size < 1 || size > MAX_RASTER_BYTES || totalBytes + size > MAX_TOTAL_RASTER_BYTES) {
                throw new ScenarioAssetUnavailableException();
            }
            verifyRaster(realRoot, ref);
            totalBytes += size;
        }
    }

    private static void addRefs(List<JsonNode> refs, JsonNode bands) {
        if (!bands.isObject()) {
            throw new ScenarioAssetUnavailableException();
        }
        for (Iterator<JsonNode> it = bands.elements(); it.hasNext();) {
            refs.add(it.next());
        }
    }

    private void verifyRaster(Path realRoot, JsonNode ref) throws IOException {
        String relativeValue = ref.path("path").asText("");
        Path relative = Path.of(relativeValue);
        long expectedSize = ref.path("size_bytes").asLong(-1);
        String expectedHash = ref.path("sha256").asText("");
        if (relativeValue.contains("\\") || relative.isAbsolute()
                || relative.normalize().startsWith("..")
                || expectedSize < 1 || expectedSize > MAX_RASTER_BYTES
                || !SHA256.matcher(expectedHash).matches()) {
            throw new ScenarioAssetUnavailableException();
        }
        Path realFile = realRoot.resolve(relative).normalize().toRealPath();
        if (!realFile.startsWith(realRoot) || !Files.isRegularFile(realFile)
                || Files.size(realFile) != expectedSize) {
            throw new ScenarioAssetUnavailableException();
        }
        String actualHash = sha256(realFile, expectedSize);
        if (!expectedHash.equals(actualHash)) {
            throw new ScenarioAssetUnavailableException();
        }
    }

    private static String sha256(Path path, long expectedSize) throws IOException {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            long totalBytes = 0;
            try (var input = Files.newInputStream(path)) {
                byte[] buffer = new byte[16 * 1024];
                int count;
                while ((count = input.read(buffer)) >= 0) {
                    totalBytes += count;
                    if (totalBytes > expectedSize) {
                        throw new IOException("Scenario raster changed during verification.");
                    }
                    digest.update(buffer, 0, count);
                }
            }
            if (totalBytes != expectedSize) {
                throw new IOException("Scenario raster changed during verification.");
            }
            return HexFormat.of().formatHex(digest.digest());
        } catch (NoSuchAlgorithmException exception) {
            throw new ScenarioAssetUnavailableException();
        }
    }

    private static void validateSelector(String eventId, String scenarioId) {
        try {
            if (eventId == null || !LocalDate.parse(eventId).toString().equals(eventId)) {
                throw new InvalidScenarioSelectorException();
            }
        } catch (DateTimeParseException exception) {
            throw new InvalidScenarioSelectorException();
        }
        if (scenarioId == null || !SCENARIO_ID.matcher(scenarioId).matches()) {
            throw new InvalidScenarioSelectorException();
        }
    }

    public static final class InvalidScenarioSelectorException extends RuntimeException {
        public InvalidScenarioSelectorException() { super("Invalid scenario selector."); }
    }

    public static final class ScenarioAssetNotFoundException extends RuntimeException {
        public ScenarioAssetNotFoundException() { super("No exact saved scenario asset was found."); }
    }

    public static final class ScenarioIdentityConflictException extends RuntimeException {
        public ScenarioIdentityConflictException() { super("Scenario identity is duplicated or ambiguous."); }
    }

    public static final class ScenarioAssetUnavailableException extends RuntimeException {
        public ScenarioAssetUnavailableException() { super("Scenario assets are unavailable."); }
    }
}
