package org.twinguard.backend.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.databind.JsonNode;

import java.util.Map;

public record ScenarioResponse(
        @JsonProperty("scenario_key") String scenarioKey,
        String title,
        @JsonProperty("base_run_id") long baseRunId,
        Map<String, JsonNode> parameters,
        ScenarioStatus status) {}
