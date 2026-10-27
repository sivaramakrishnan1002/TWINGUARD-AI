package org.twinguard.backend.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.PositiveOrZero;

import java.math.BigDecimal;
import java.util.List;

public record RouteResponse(
        // This is graph reachability, not flood passability.
        @NotNull Boolean reachable,
        @JsonProperty("edge_ids") @NotNull List<Long> edgeIds,
        @JsonProperty("travel_time_minutes") @PositiveOrZero BigDecimal travelTimeMinutes,
        @JsonProperty("route_accessibility_probability")
        @jakarta.validation.constraints.DecimalMin("0.0")
        @jakarta.validation.constraints.DecimalMax("1.0") BigDecimal routeAccessibilityProbability,
        @NotNull @Valid Provenance provenance) {}
