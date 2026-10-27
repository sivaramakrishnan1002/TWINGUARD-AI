package org.twinguard.backend.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.PositiveOrZero;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Positive;

import java.math.BigDecimal;

public record ShelterResponse(
        @JsonProperty("facility_id") @Positive long facilityId,
        String name,
        @NotBlank String category,
        @JsonProperty("candidate_only") @jakarta.validation.constraints.NotNull Boolean candidateOnly,
        @JsonProperty("capacity_people") @PositiveOrZero Integer capacityPeople,
        @JsonProperty("accessibility_probability")
        @DecimalMin("0.0") @DecimalMax("1.0") BigDecimal accessibilityProbability) {}
