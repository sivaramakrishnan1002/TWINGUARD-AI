package org.twinguard.backend.dto;

import java.time.OffsetDateTime;
import jakarta.validation.constraints.Positive;

public record ShelterQuery(OffsetDateTime at, @Positive Long runId) {}
