package org.twinguard.backend.scenario;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.web.servlet.MockMvc;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoMoreInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
class ScenarioVisualizationControllerTest {
    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @MockBean
    private ScenarioVisualizationAssets assets;

    private ScenarioVisualizationAssets realAssets;

    @BeforeEach
    void setUp() {
        realAssets = new ScenarioVisualizationAssets(projectRoot(), objectMapper);
    }

    @Test
    void catalogReturnsCompleteSavedResearchProjection() throws Exception {
        when(assets.catalog()).thenReturn(realAssets.catalog());

        mockMvc.perform(get("/scenario-visualization-assets"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("DERIVED_ASSUMPTION_BASED_RESEARCH_SCENARIO"))
                .andExpect(jsonPath("$.artifact_version").value("batch2_v1"))
                .andExpect(jsonPath("$.nodata.meaning").value(
                        "outside assessed CMA or otherwise unmodelled; it is unknown coverage, not dry"))
                .andExpect(jsonPath("$.scenario_series.length()").value(3));
        verify(assets).catalog();
        verifyNoMoreInteractions(assets);
    }

    @Test
    void exactDetailReturnsSavedTimesAndSourceModeWithoutRasterBytes() throws Exception {
        when(assets.asset("2015-12-02", "perfect_foresight_imerg"))
                .thenReturn(realAssets.asset("2015-12-02", "perfect_foresight_imerg"));

        mockMvc.perform(get("/scenario-visualization-assets/2015-12-02/perfect_foresight_imerg"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.series.source_mode").value("PERFECT_FORESIGHT_HINDCAST"))
                .andExpect(jsonPath("$.series.slices.length()").value(5))
                .andExpect(jsonPath("$.depth_units.value").value("m"))
                .andExpect(content().string(org.hamcrest.Matchers.not(
                        org.hamcrest.Matchers.containsString("data:image/"))));
        verify(assets).asset("2015-12-02", "perfect_foresight_imerg");
        verifyNoMoreInteractions(assets);
    }

    @Test
    void invalidSelectorAndUnexpectedInputMapTo400() throws Exception {
        doThrow(new ScenarioVisualizationAssets.InvalidScenarioSelectorException())
                .when(assets).asset("2015-02-30", "perfect_foresight_imerg");

        mockMvc.perform(get("/scenario-visualization-assets/2015-02-30/perfect_foresight_imerg"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.detail").value("event_id or scenario_id is invalid."))
                .andExpect(jsonPath("$.series").doesNotExist());
        mockMvc.perform(get("/scenario-visualization-assets").param("mode", "live"))
                .andExpect(status().isBadRequest());
        mockMvc.perform(get("/scenario-visualization-assets").content("untrusted"))
                .andExpect(status().isBadRequest());
    }

    @Test
    void noMatchMapsTo404() throws Exception {
        doThrow(new ScenarioVisualizationAssets.ScenarioAssetNotFoundException())
                .when(assets).asset("2015-12-02", "absent");
        mockMvc.perform(get("/scenario-visualization-assets/2015-12-02/absent"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.series").doesNotExist());
    }

    @Test
    void duplicateIdentityMapsTo409WithoutPartialResponse() throws Exception {
        doThrow(new ScenarioVisualizationAssets.ScenarioIdentityConflictException()).when(assets).catalog();
        mockMvc.perform(get("/scenario-visualization-assets"))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.scenario_series").doesNotExist());
    }

    @Test
    void unavailableAssetsMapTo503WithoutPartialResponseOrFilesystemDetails() throws Exception {
        doThrow(new ScenarioVisualizationAssets.ScenarioAssetUnavailableException())
                .when(assets).asset("2015-12-02", "perfect_foresight_imerg");
        mockMvc.perform(get("/scenario-visualization-assets/2015-12-02/perfect_foresight_imerg"))
                .andExpect(status().isServiceUnavailable())
                .andExpect(jsonPath("$.series").doesNotExist())
                .andExpect(content().string(org.hamcrest.Matchers.not(
                        org.hamcrest.Matchers.containsString("data/features"))));
    }

    @Test
    void postIsNotSupportedAndCannotWriteScenarioState() throws Exception {
        mockMvc.perform(post("/scenario-visualization-assets"))
                .andExpect(status().isMethodNotAllowed());
        verifyNoMoreInteractions(assets);
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
}
