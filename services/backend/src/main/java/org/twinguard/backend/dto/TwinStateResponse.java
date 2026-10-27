package org.twinguard.backend.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.databind.JsonNode;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import org.twinguard.backend.validation.JsonObject;

import java.time.Instant;
import java.util.List;

public record TwinStateResponse(
        @JsonProperty("run_id") @Positive long runId,
        @JsonProperty("valid_at") @NotNull Instant validAt,
        @JsonProperty("version_key") @NotBlank String versionKey,
        @JsonProperty("state_artifacts") @NotNull List<String> stateArtifacts,
        @JsonObject JsonNode provenance) {}
