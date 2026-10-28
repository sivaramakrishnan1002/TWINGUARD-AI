package org.twinguard.backend.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.databind.JsonNode;
import jakarta.validation.Valid;
import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.PositiveOrZero;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Locale;

/** Lane A A07 impact-result projection; statistics are simulated, not observed impacts. */
public record ImpactResponse(
        @JsonProperty("schema_id") @NotNull String schemaId,
        @JsonProperty("schema_version") @NotNull String schemaVersion,
        @JsonProperty("result_id") @NotNull String resultId,
        @JsonProperty("run_id") @PositiveOrZero long runId,
        @JsonProperty("run_version") @NotNull String runVersion,
        @JsonProperty("source_mode") @NotNull RouteResponse.SourceMode sourceMode,
        @NotNull @Valid Event event,
        @JsonProperty("valid_at_utc") @NotNull Instant validAtUtc,
        @JsonProperty("aggregation_interval") @Valid AggregationInterval aggregationInterval,
        @JsonProperty("aggregation_basis") String aggregationBasis,
        @JsonProperty("generated_at_utc") @NotNull Instant generatedAtUtc,
        @JsonProperty("scenario_key") @NotNull String scenarioKey,
        @NotNull @Valid Thresholds thresholds,
        @NotNull @Valid Metrics metrics,
        @JsonProperty("facility_access_by_category") @NotNull List<@Valid FacilityAccess> facilityAccessByCategory,
        @NotNull List<JsonNode> sensitivity,
        @NotNull @Valid Coverage coverage,
        @NotNull @Valid Uncertainty uncertainty,
        @NotNull @Valid Provenance provenance,
        @JsonProperty("qc_flags") @NotNull List<String> qcFlags,
        @JsonProperty("event_reference_note") String eventReferenceNote) {

    public enum DistributionStatus { AVAILABLE, PARTIAL, UNAVAILABLE }
    public enum FacilityCategory {
        HOSPITAL, SHELTER, CANDIDATE_SHELTER;
        @com.fasterxml.jackson.annotation.JsonValue public String jsonValue() {
            return name().toLowerCase(Locale.ROOT);
        }
        @com.fasterxml.jackson.annotation.JsonCreator public static FacilityCategory fromJson(String value) {
            return value == null ? null : valueOf(value.toUpperCase(Locale.ROOT));
        }
    }

    public record Event(
            @JsonProperty("event_key") String eventKey,
            @JsonProperty("event_start_utc") Instant eventStartUtc,
            @JsonProperty("event_end_utc") Instant eventEndUtc,
            @JsonProperty("time_basis") String timeBasis) {}

    public record AggregationInterval(
            @JsonProperty("start_utc") Instant startUtc,
            @JsonProperty("end_utc") Instant endUtc,
            String convention) {}

    public record Thresholds(
            @JsonProperty("road_block_depth_m") BigDecimal roadBlockDepthM,
            @JsonProperty("road_threshold_is_assumption") boolean roadThresholdIsAssumption,
            @JsonProperty("sensitivity_depth_thresholds_m") List<BigDecimal> sensitivityDepthThresholdsM,
            @JsonProperty("mapped_facility_exposure_threshold_m") BigDecimal mappedFacilityExposureThresholdM,
            @JsonProperty("population_exposure_threshold_m") BigDecimal populationExposureThresholdM,
            @JsonProperty("exposure_thresholds_are_assumptions") boolean exposureThresholdsAreAssumptions) {}

    public record Distribution(
            DistributionStatus status,
            String unit,
            BigDecimal mean,
            BigDecimal p05,
            BigDecimal p50,
            BigDecimal p95,
            @JsonProperty("member_count") int memberCount,
            String interpretation) {}

    public record Metrics(
            @JsonProperty("population_exposed_people") @Valid Distribution populationExposedPeople,
            @JsonProperty("affected_road_length_m") @Valid Distribution affectedRoadLengthM,
            @JsonProperty("affected_facilities_count") @Valid Distribution affectedFacilitiesCount,
            @JsonProperty("facility_access_loss_fraction") @Valid Distribution facilityAccessLossFraction) {}

    public record FacilityAccess(
            FacilityCategory category,
            @JsonProperty("facility_count") Integer facilityCount,
            @JsonProperty("reachable_count") Integer reachableCount,
            @JsonProperty("unreachable_count") Integer unreachableCount,
            @JsonProperty("unassessed_count") Integer unassessedCount,
            @JsonProperty("access_loss_fraction") BigDecimal accessLossFraction,
            @JsonProperty("coverage_fraction") BigDecimal coverageFraction,
            @JsonProperty("baseline_core_count") JsonNode baselineCoreCount,
            @JsonProperty("baseline_core_reachable_count_distribution") JsonNode baselineCoreReachableCountDistribution,
            @JsonProperty("unreachable_from_anchor_count") JsonNode unreachableFromAnchorCount,
            @JsonProperty("outside_baseline_core_count") JsonNode outsideBaselineCoreCount,
            @JsonProperty("reachable_count_distribution") JsonNode reachableCountDistribution,
            @JsonProperty("unreachable_count_distribution") JsonNode unreachableCountDistribution,
            @JsonProperty("coverage_fraction_mean") BigDecimal coverageFractionMean,
            String interpretation) {}

    public record CoverageSlice(
            @JsonProperty("assessed_count") long assessedCount,
            @JsonProperty("eligible_count") long eligibleCount,
            @JsonProperty("nodata_count") long nodataCount,
            @JsonProperty("fraction_assessed") @DecimalMin("0.0") @DecimalMax("1.0") BigDecimal fractionAssessed,
            @JsonProperty("coverage_basis") String coverageBasis) {}

    public record Coverage(
            @Valid CoverageSlice population,
            @Valid CoverageSlice roads,
            @Valid CoverageSlice facilities,
            @JsonProperty("hazard_grid") @Valid CoverageSlice hazardGrid) {}

    public record Uncertainty(String method,
            @JsonProperty("ensemble_id") String ensembleId,
            @JsonProperty("member_count") int memberCount,
            String interpretation) {}

    public record SourceReference(
            @JsonProperty("source_id") String sourceId,
            @JsonProperty("source_sha256") String sourceSha256,
            String version,
            String role) {}

    public record Provenance(
            List<@Valid SourceReference> sources,
            String algorithm,
            @JsonProperty("algorithm_version") String algorithmVersion,
            @JsonProperty("code_commit") String codeCommit,
            Map<String, Object> parameters,
            Map<String, Object> grid) {}
}
