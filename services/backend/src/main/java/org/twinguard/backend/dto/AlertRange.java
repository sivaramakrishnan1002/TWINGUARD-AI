package org.twinguard.backend.dto;

import java.time.OffsetDateTime;
import jakarta.validation.constraints.AssertTrue;
import jakarta.validation.constraints.NotNull;

public record AlertRange(@NotNull OffsetDateTime from, @NotNull OffsetDateTime to) {
    @AssertTrue(message = "from must not be after to")
    public boolean isOrdered() {
        return from == null || to == null || !from.isAfter(to);
    }
}
