package org.twinguard.backend.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.databind.JsonNode;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;

import java.util.Map;

public record ScenarioCreateRequest(
        @JsonProperty("scenario_key") @NotBlank String scenarioKey,
        @NotBlank String title,
        @JsonProperty("base_run_id") @Positive long baseRunId,
        @NotNull Map<String, JsonNode> parameters) {}
