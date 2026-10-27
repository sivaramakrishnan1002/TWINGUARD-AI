package org.twinguard.backend.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.DecimalMax;

import java.time.Instant;

public record RouteRequest(
        @JsonProperty("run_id") @Positive long runId,
        @JsonProperty("departure_at") @NotNull Instant departureAt,
        @NotBlank String origin,
        @NotBlank String destination,
        RouteMode mode,
        @JsonProperty("minimum_accessibility_probability")
        @DecimalMin("0.0") @DecimalMax("1.0") Double minimumAccessibilityProbability) {}
