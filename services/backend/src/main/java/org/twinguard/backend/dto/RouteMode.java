package org.twinguard.backend.dto;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;

public enum RouteMode {
    VEHICLE, WALKING;

    @JsonValue
    public String jsonValue() {
        return name().toLowerCase(java.util.Locale.ROOT);
    }

    @JsonCreator
    public static RouteMode fromJson(String value) {
        return value == null ? null : valueOf(value.toUpperCase(java.util.Locale.ROOT));
    }
}
