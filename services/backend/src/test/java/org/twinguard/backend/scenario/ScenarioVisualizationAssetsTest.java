package org.twinguard.backend.scenario;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.web.servlet.MockMvc;

import java.nio.file.Path;
import java.nio.file.Files;
import java.util.NoSuchElementException;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
class ScenarioVisualizationAssetsTest {
    private final ObjectMapper mapper = new ObjectMapper();
    private ScenarioVisualizationAssets assets;

    @Autowired
    private MockMvc mockMvc;

    @BeforeEach
    void setUp() {
        assets = new ScenarioVisualizationAssets(projectRoot(), mapper);
    }

    private static Path projectRoot() {
        Path candidate = Path.of("").toAbsolutePath();
        while (candidate != null
                && !Files.isRegularFile(candidate.resolve("data/features/visualization3d/batch2_v1/manifest.json"))) {
            candidate = candidate.getParent();
        }
        if (candidate == null) {
            throw new IllegalStateException("A20 scenario manifest is not available to tests.");
        }
        return candidate;
    }

    @Test
    void catalogProjectsOwnerManifestMetadataAndUnknownCoverageExactly() throws Exception {
        JsonNode source = mapper.readTree(projectRoot().resolve("data/features/visualization3d/batch2_v1/manifest.json").toFile());
        JsonNode catalog = assets.catalog();

        assertThat(catalog.path("schema_version").asText()).isEqualTo(source.path("schema_version").asText());
        assertThat(catalog.path("artifact_version").asText()).isEqualTo("batch2_v1");
        assertThat(catalog.path("status").asText()).isEqualTo("DERIVED_ASSUMPTION_BASED_RESEARCH_SCENARIO");
        assertThat(catalog.path("grid")).isEqualTo(source.path("grid"));
        assertThat(catalog.path("depth_units")).isEqualTo(source.path("depth_units"));
        assertThat(catalog.path("nodata")).isEqualTo(source.path("nodata"));
        assertThat(catalog.path("provenance")).isEqualTo(source.path("provenance"));
        assertThat(catalog.path("scenario_series").size()).isEqualTo(3);
        assertThat(catalog.path("context_layers")).isEqualTo(source.path("context_layers"));

        boolean foundPeak = false;
        for (JsonNode context : catalog.path("context_layers")) {
            if ("per_cell_event_peak".equals(context.path("temporal_kind").asText())) {
                foundPeak = true;
                assertThat(context.path("valid_time_utc").isNull()).isTrue();
                assertThat(context.path("selected_hour_index_zero_based").isNull()).isTrue();
            }
        }
        assertThat(foundPeak).isTrue();
    }

    @Test
    void detailReturnsOnlyExactManifestIdentityWithSavedTimesAndHindcastMode() throws Exception {
        JsonNode source = mapper.readTree(projectRoot().resolve("data/features/visualization3d/batch2_v1/manifest.json").toFile());
        JsonNode series = source.path("scenario_series").get(0);
        JsonNode result = assets.asset(series.path("event_id").asText(), series.path("scenario_id").asText());

        assertThat(result.path("series")).isEqualTo(series);
        assertThat(mapper.readTree(mapper.writeValueAsBytes(result))).isEqualTo(result);
        assertThat(result.path("series").path("source_mode").asText()).isEqualTo("PERFECT_FORESIGHT_HINDCAST");
        assertThat(result.path("series").path("member_count").asInt()).isEqualTo(20);
        assertThat(result.path("series").path("slices").size()).isEqualTo(5);
        assertThat(result.path("grid").path("crs").asText()).isEqualTo("EPSG:32644");
        assertThat(result.path("depth_units").path("value").asText()).isEqualTo("m");
    }

    @Test
    void invalidAndUnknownSelectorsFailWithoutFilesystemPathInterpretation() {
        assertThatThrownBy(() -> assets.asset("../2015-11-12", "perfect_foresight_imerg"))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> assets.asset("2015-11-12", "../manifest"))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> assets.asset("2015-11-12", "unknown"))
                .isInstanceOf(NoSuchElementException.class);
    }

    @Test
    void malformedSavedTimestampFailsClosedBeforeAnyAssetRead(@TempDir Path tempRoot) throws Exception {
        Path root = projectRoot();
        JsonNode manifest = mapper.readTree(root.resolve("data/features/visualization3d/batch2_v1/manifest.json").toFile());
        ((ObjectNode) manifest.path("scenario_series").get(0).path("slices").get(0))
                .put("valid_time_utc", "2015-11-30T06:00:00");
        Path manifestCopy = tempRoot.resolve("data/features/visualization3d/batch2_v1/manifest.json");
        Files.createDirectories(manifestCopy.getParent());
        mapper.writeValue(manifestCopy.toFile(), manifest);
        ScenarioVisualizationAssets invalid = new ScenarioVisualizationAssets(tempRoot, mapper);
        assertThatThrownBy(invalid::catalog).isInstanceOf(IllegalStateException.class);
    }

    @Test
    void c9HttpOperationsRemainUnexposedUntilApproval() throws Exception {
        mockMvc.perform(get("/scenario-visualization-assets"))
                .andExpect(status().isNotFound());
        mockMvc.perform(get("/scenario-visualization-assets/2015-12-02/perfect_foresight_imerg"))
                .andExpect(status().isNotFound());
    }
}
