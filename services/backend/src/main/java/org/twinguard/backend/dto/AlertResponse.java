package org.twinguard.backend.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.databind.JsonNode;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.NotNull;
import org.twinguard.backend.validation.JsonObject;

import java.time.Instant;

public record AlertResponse(
        @JsonProperty("alert_id") @Positive long alertId,
        @NotNull AlertSeverity severity,
        @JsonProperty("issued_at") @NotNull Instant issuedAt,
        @JsonProperty("valid_from") @NotNull Instant validFrom,
        @JsonProperty("valid_to") @NotNull Instant validTo,
        @NotNull @JsonObject JsonNode provenance) {}
