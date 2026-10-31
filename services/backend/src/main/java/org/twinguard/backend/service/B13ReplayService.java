package org.twinguard.backend.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.util.regex.Pattern;

/** Bounded pass-through for the single CR-012 replay selector. */
@Service
public class B13ReplayService {
    private static final String APPROVED_EVENT_ID = "replay:POONDI:date:2015-12-01";
    private static final Pattern RUN_ID = Pattern.compile("^sha256:[a-f0-9]{64}$");
    private final RestClient client;
    private final ObjectMapper mapper;
    private final URI aiServiceBase;

    public B13ReplayService(
            RestClient.Builder builder,
            ObjectMapper mapper,
            @Value("${twinguard.b13.ai-service-base-url:http://127.0.0.1:8000}") URI aiServiceBase) {
        this.client = builder.build();
        this.mapper = mapper;
        this.aiServiceBase = aiServiceBase;
    }

    public ResponseEntity<byte[]> lookup(String eventId) {
        try {
            URI target = URI.create(aiServiceBase.toString().replaceAll("/$", "") + "/replay-alerts/" + eventId);
            return client.get().uri(target).accept(MediaType.APPLICATION_JSON).exchange((request, response) -> {
                int status = response.getStatusCode().value();
                byte[] body = response.getBody().readAllBytes();
                if (status == 200 && !validSuccess(body, eventId)) {
                    return unavailable();
                }
                if (status != 200 && status != 400 && status != 404 && status != 409 && status != 503) {
                    return unavailable();
                }
                if (status != 200 && !validError(body, status)) {
                    return unavailable();
                }
                return ResponseEntity.status(status).contentType(MediaType.APPLICATION_JSON).body(body);
            });
        } catch (Exception ignored) {
            return unavailable();
        }
    }

    private boolean validSuccess(byte[] body, String eventId) {
        try {
            JsonNode root = mapper.readTree(body);
            JsonNode source = root.path("source_observation");
            JsonNode replay = root.path("replay");
            JsonNode derived = root.path("derived_output");
            if (!"C4-v2".equals(root.path("contract_version").asText())
                    || !eventId.equals(source.path("event_id").asText())
                    || !"REPLAY".equals(source.path("source_mode").asText())
                    || !"date".equals(source.path("time_precision").asText())
                    || !"2015-12-01".equals(source.path("source_date").asText())
                    || !"POONDI".equals(source.path("reservoir_key").asText())
                    || !source.path("observed_at").isNull()
                    || !"unknown".equals(source.path("observation_timezone").asText())
                    || !source.path("received_at").isTextual()
                    || !"01-12-2015".equals(source.path("raw_source_row").path("Date").asText())
                    || !"2745.00".equals(source.path("raw_source_row").path("POONDI").asText())
                    || !"7645febde7ccc21871200487139d1c8a84ea90a6dd2eccc93b7d1f06faf69197".equals(source.path("provenance").path("archive_sha256").asText())
                    || !"3b4b6f2f53b5db20513d2829c2dba265c5738a55bf0c8eade51e0e2d5cfeaef7".equals(source.path("provenance").path("member_sha256").asText())
                    || source.path("provenance").path("csv_physical_line").asInt(-1) != 4354
                    || !"trackb-rule-v1".equals(replay.path("algorithm_id").asText())
                    || !RUN_ID.matcher(replay.path("replay_run_id").asText()).matches()
                    || !replay.path("configuration_sha256").asText().matches("^[a-f0-9]{64}$")
                    || !replay.path("normalized_input_sha256").asText().matches("^[a-f0-9]{64}$")) {
                return false;
            }
            String state = derived.path("status").asText();
            if ("not_produced".equals(state)) {
                return derived.path("alert").isNull() && derived.path("output_sha256").isNull();
            }
            return "produced".equals(state)
                    && !derived.path("alert").isNull()
                    && derived.path("output_sha256").asText().matches("^[a-f0-9]{64}$")
                    && eventId.equals(derived.path("alert").path("event_id").asText())
                    && derived.path("alert").path("observed_at").isNull()
                    && derived.path("alert").path("valid_from").isNull()
                    && derived.path("alert").path("valid_to").isNull()
                    && "unknown".equals(derived.path("alert").path("observation_timezone").asText());
        } catch (Exception ignored) {
            return false;
        }
    }

    private boolean validError(byte[] body, int status) {
        try {
            JsonNode root = mapper.readTree(body);
            return root.path("status").asInt(-1) == status
                    && root.path("code").isTextual()
                    && root.path("detail").isTextual()
                    && !root.path("detail").asText().isBlank();
        } catch (Exception ignored) {
            return false;
        }
    }

    private static ResponseEntity<byte[]> unavailable() {
        byte[] body = ("{\"status\":503,\"code\":\"asset_unavailable\",\"detail\":\"The approved replay service is unavailable.\"}")
                .getBytes(StandardCharsets.UTF_8);
        return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                .header(HttpHeaders.CACHE_CONTROL, "no-store")
                .contentType(MediaType.APPLICATION_JSON)
                .body(body);
    }
}
