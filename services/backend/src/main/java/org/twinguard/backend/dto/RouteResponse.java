package org.twinguard.backend.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;
import com.fasterxml.jackson.databind.JsonNode;
import jakarta.validation.Valid;
import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.PositiveOrZero;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/** Lane A A09 route-result projection; topology is independent from accessibility. */
public record RouteResponse(
        @JsonProperty("schema_id") @NotNull String schemaId,
        @JsonProperty("schema_version") @NotNull String schemaVersion,
        @JsonProperty("result_id") @NotNull String resultId,
        @NotNull RouteStatus status,
        @JsonProperty("run_id") Long runId,
        @JsonProperty("scenario_key") @NotNull String scenarioKey,
        @JsonProperty("source_mode") @NotNull SourceMode sourceMode,
        @NotNull RouteMethod method,
        @JsonProperty("origin_id") @NotNull String originId,
        @JsonProperty("destination_id") @NotNull String destinationId,
        @JsonProperty("travel_mode") @NotNull TravelMode travelMode,
        @JsonProperty("departure_at_utc") @NotNull Instant departureAtUtc,
        @JsonProperty("arrival_at_utc") Instant arrivalAtUtc,
        @JsonProperty("requested_horizon_seconds") @PositiveOrZero Long requestedHorizonSeconds,
        @JsonProperty("distance_m") @PositiveOrZero BigDecimal distanceM,
        @JsonProperty("travel_time_seconds") @PositiveOrZero BigDecimal travelTimeSeconds,
        @JsonProperty("topologically_reachable") Boolean topologicallyReachable,
        @JsonProperty("route_accessibility_probability")
        @DecimalMin("0.0") @DecimalMax("1.0") BigDecimal routeAccessibilityProbability,
        @JsonProperty("route_failure_probability")
        @DecimalMin("0.0") @DecimalMax("1.0") BigDecimal routeFailureProbability,
        @JsonProperty("minimum_accessibility_probability")
        @DecimalMin("0.0") @DecimalMax("1.0") BigDecimal minimumAccessibilityProbability,
        @JsonProperty("route_geometry") JsonNode routeGeometry,
        @JsonProperty("node_path") @NotNull List<Long> nodePath,
        @NotNull List<@Valid Edge> edges,
        @JsonProperty("depth_thresholds") @NotNull @Valid DepthThresholds depthThresholds,
        @JsonProperty("edge_coverage") @NotNull @Valid EdgeCoverage edgeCoverage,
        @NotNull @Valid Graph graph,
        @JsonProperty("hazard_run") @NotNull @Valid HazardRun hazardRun,
        @NotNull @Valid Uncertainty uncertainty,
        @NotNull @Valid Provenance provenance,
        @JsonProperty("qc_flags") @NotNull List<String> qcFlags) {

    public enum RouteStatus { ROUTE_FOUND, NO_TOPOLOGICAL_PATH, INSUFFICIENT_HAZARD_COVERAGE,
        BELOW_ACCESSIBILITY_CONSTRAINT, INPUT_UNAVAILABLE }
    public enum SourceMode { OBSERVED, DERIVED, SIMULATED, ASSUMPTION, REPLAY }
    public enum RouteMethod {
        STATIC, CURRENT_FLOOD_AWARE, HORIZON_AWARE, UNCERTAINTY_AWARE;
        @JsonValue public String jsonValue() { return name().toLowerCase(Locale.ROOT); }
        @JsonCreator public static RouteMethod fromJson(String value) {
            return value == null ? null : valueOf(value.toUpperCase(Locale.ROOT));
        }
    }
    public enum TravelMode {
        VEHICLE, WALKING;
        @JsonValue public String jsonValue() { return name().toLowerCase(Locale.ROOT); }
        @JsonCreator public static TravelMode fromJson(String value) {
            return value == null ? null : valueOf(value.toUpperCase(Locale.ROOT));
        }
    }

    public record Edge(
            @JsonProperty("edge_id") long edgeId,
            @JsonProperty("entry_at_utc") Instant entryAtUtc,
            @JsonProperty("exit_at_utc") Instant exitAtUtc,
            @JsonProperty("distance_m") BigDecimal distanceM,
            @JsonProperty("travel_time_seconds") BigDecimal travelTimeSeconds,
            @JsonProperty("depth_max_m") BigDecimal depthMaxM,
            @JsonProperty("passable_probability") @DecimalMin("0.0") @DecimalMax("1.0") BigDecimal passableProbability,
            Boolean bridge,
            Boolean tunnel,
            @JsonProperty("assessment_status") String assessmentStatus) {}

    public record DepthThresholds(
            @JsonProperty("ordinary_block_at_or_above_m") BigDecimal ordinaryBlockAtOrAboveM,
            @JsonProperty("tunnel_proxy_block_at_or_above_m") BigDecimal tunnelProxyBlockAtOrAboveM,
            @JsonProperty("bridge_rule") String bridgeRule,
            @JsonProperty("thresholds_are_assumptions") boolean thresholdsAreAssumptions,
            @JsonProperty("uncertainty_route_accessibility_minimum") BigDecimal uncertaintyRouteAccessibilityMinimum,
            @JsonProperty("sensitivity_m") List<BigDecimal> sensitivityM) {}

    public record EdgeCoverage(
            @JsonProperty("route_edge_count") int routeEdgeCount,
            @JsonProperty("assessed_edge_count") int assessedEdgeCount,
            @JsonProperty("unassessed_edge_count") int unassessedEdgeCount,
            @JsonProperty("fraction_assessed") BigDecimal fractionAssessed) {}

    public record Graph(
            @JsonProperty("graph_id") String graphId,
            @JsonProperty("graph_version") String graphVersion,
            @JsonProperty("graph_sha256") String graphSha256,
            String crs,
            @JsonProperty("edge_source_ids") List<String> edgeSourceIds,
            @JsonProperty("build_algorithm") String buildAlgorithm,
            @JsonProperty("build_version") String buildVersion,
            List<String> assumptions) {}

    public record HazardRun(
            @JsonProperty("run_id") Long runId,
            String version,
            @JsonProperty("issued_at_utc") Instant issuedAtUtc,
            @JsonProperty("valid_start_utc") Instant validStartUtc,
            @JsonProperty("valid_end_utc") Instant validEndUtc,
            @JsonProperty("depth_source_id") String depthSourceId,
            @JsonProperty("depth_source_sha256") String depthSourceSha256,
            @JsonProperty("ensemble_id") String ensembleId) {}

    public record Uncertainty(
            String method,
            @JsonProperty("ensemble_member_count") int ensembleMemberCount,
            @JsonProperty("travel_time_spread_seconds") BigDecimal travelTimeSpreadSeconds,
            @JsonProperty("failure_probability_constraint") BigDecimal failureProbabilityConstraint,
            List<String> limitations) {}

    public record Provenance(
            String algorithm,
            @JsonProperty("algorithm_version") String algorithmVersion,
            @JsonProperty("code_commit") String codeCommit,
            @JsonProperty("generated_at_utc") Instant generatedAtUtc,
            Map<String, Object> parameters) {}
}
