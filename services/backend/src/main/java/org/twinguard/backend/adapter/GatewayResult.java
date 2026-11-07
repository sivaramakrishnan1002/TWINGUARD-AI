package org.twinguard.backend.adapter;

import java.util.Objects;

public record GatewayResult<T>(
        Status status,
        T data,
        GatewayDependency dependency,
        Reason reason) {

    public enum Status { AVAILABLE, UNAVAILABLE }
    public enum Reason { NOT_CONFIGURED }

    public GatewayResult {
        Objects.requireNonNull(status, "status");
        if (status == Status.AVAILABLE && data == null) {
            throw new IllegalArgumentException("Available results require data");
        }
        if (status == Status.UNAVAILABLE && (data != null || dependency == null || reason == null)) {
            throw new IllegalArgumentException("Unavailable results require a dependency and reason, and no data");
        }
    }

    public static <T> GatewayResult<T> available(T data) {
        return new GatewayResult<>(Status.AVAILABLE, Objects.requireNonNull(data), null, null);
    }

    public static <T> GatewayResult<T> notConfigured(GatewayDependency dependency) {
        return new GatewayResult<>(Status.UNAVAILABLE, null, Objects.requireNonNull(dependency), Reason.NOT_CONFIGURED);
    }
}
