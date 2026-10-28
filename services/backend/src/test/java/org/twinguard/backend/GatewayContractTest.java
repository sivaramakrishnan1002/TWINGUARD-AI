package org.twinguard.backend;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.validation.Validator;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.web.servlet.MockMvc;
import org.twinguard.backend.adapter.GatewayDependency;
import org.twinguard.backend.adapter.GatewayResult;
import org.twinguard.backend.config.UpstreamProperties;
import org.twinguard.backend.dto.AlertRange;
import org.twinguard.backend.dto.ImpactResponse;
import org.twinguard.backend.dto.RouteMode;
import org.twinguard.backend.dto.RouteRequest;
import org.twinguard.backend.dto.RouteResponse;
import org.twinguard.backend.dto.ScenarioCreateRequest;
import org.twinguard.backend.dto.ShelterQuery;
import org.twinguard.backend.dto.ShelterResponse;
import org.twinguard.backend.dto.TwinStateQuery;
import org.twinguard.backend.dto.TwinStateResponse;
import org.twinguard.backend.service.TwinGuardGatewayService;

import java.io.InputStream;
import java.time.Instant;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest(properties = {
        "twinguard.upstreams.ai-service-base-url=https://ai.example.invalid/api",
        "twinguard.upstreams.track-b-base-url=https://trackb.example.invalid/api"
})
@AutoConfigureMockMvc
class GatewayContractTest {
    @Autowired private ObjectMapper objectMapper;
    @Autowired private Validator validator;
    @Autowired private TwinGuardGatewayService gateway;
    @Autowired private UpstreamProperties upstreamProperties;
    @Autowired private MockMvc mockMvc;

    @Test
    void routeRequestUsesContractNamesAndNormalizesOffsetTimestampToUtc() throws Exception {
        RouteRequest request = objectMapper.readValue("""
                {"run_id":7,"departure_at":"2026-10-25T08:00:00+05:30","origin":"A","destination":"B","mode":"walking","minimum_accessibility_probability":0.7}
                """, RouteRequest.class);

        assertThat(request.runId()).isEqualTo(7);
        assertThat(request.departureAt()).isEqualTo(Instant.parse("2026-10-25T02:30:00Z"));
        assertThat(request.mode()).isEqualTo(RouteMode.WALKING);
        assertThat(request.minimumAccessibilityProbability()).isEqualTo(0.7);
        assertThat(objectMapper.readTree(objectMapper.writeValueAsString(request)).path("mode").asText())
                .isEqualTo("walking");
        assertThat(objectMapper.readTree(objectMapper.writeValueAsString(request))
                .path("departure_at").asText()).isEqualTo("2026-10-25T02:30:00Z");
    }

    @Test
    void twinStateNormalizesTimestampAndPreservesModeUncertaintyAndUnits() throws Exception {
        TwinStateResponse state = objectMapper.readValue("""
                {"run_id":3,"valid_at":"2026-10-25T08:30:00+05:30","version_key":"v1",
                 "state_artifacts":["depth"],"provenance":{"source_mode":"replay",
                 "uncertainty":{"depth_p90":0.8},"units":{"depth":"m"},"future_field":"kept"}}
                """, TwinStateResponse.class);

        JsonNode serialized = objectMapper.readTree(objectMapper.writeValueAsString(state));
        assertThat(serialized.path("valid_at").asText()).isEqualTo("2026-10-25T03:00:00Z");
        assertThat(serialized.path("provenance").path("source_mode").asText()).isEqualTo("replay");
        assertThat(serialized.path("provenance").path("uncertainty").path("depth_p90").decimalValue())
                .isEqualByComparingTo("0.8");
        assertThat(serialized.path("provenance").path("units").path("depth").asText()).isEqualTo("m");
        assertThat(serialized.path("provenance").path("future_field").asText()).isEqualTo("kept");
    }

    @Test
    void nullableShelterValuesRemainNullInsteadOfBecomingZeroOrFalse() throws Exception {
        ShelterResponse shelter = objectMapper.readValue("""
                {"facility_id":11,"name":null,"category":"candidate","candidate_only":true,
                 "capacity_people":null,"accessibility_probability":null}
                """, ShelterResponse.class);
        JsonNode json = objectMapper.readTree(objectMapper.writeValueAsString(shelter));

        assertThat(shelter.capacityPeople()).isNull();
        assertThat(shelter.accessibilityProbability()).isNull();
        assertThat(json.get("capacity_people").isNull()).isTrue();
        assertThat(json.get("accessibility_probability").isNull()).isTrue();
    }

    @Test
    void validatesScenarioAndRouteInputsWithoutEchoingValues() {
        var scenarioViolations = validator.validate(new ScenarioCreateRequest(" ", " ", 0, null));
        var routeViolations = validator.validate(new RouteRequest(
                0, null, " ", " ", null, 1.1));

        assertThat(scenarioViolations).extracting(v -> v.getPropertyPath().toString())
                .contains("scenarioKey", "title", "baseRunId", "parameters");
        assertThat(routeViolations).extracting(v -> v.getPropertyPath().toString())
                .contains("runId", "departureAt", "origin", "destination", "minimumAccessibilityProbability");
    }

    @Test
    void routeResponseRoundTripsOwnerProducedA09RecordsWithoutChangingUnitsOrUnknowns() throws Exception {
        RouteResponse route = readFixture("a09_route_found.json", RouteResponse.class);
        JsonNode serialized = objectMapper.readTree(objectMapper.writeValueAsString(route));

        assertThat(route.sourceMode()).isEqualTo(RouteResponse.SourceMode.SIMULATED);
        assertThat(route.status()).isEqualTo(RouteResponse.RouteStatus.ROUTE_FOUND);
        assertThat(route.method()).isEqualTo(RouteResponse.RouteMethod.CURRENT_FLOOD_AWARE);
        assertThat(route.topologicallyReachable()).isTrue();
        assertThat(route.routeAccessibilityProbability()).isNotNull();
        assertThat(serialized.path("departure_at_utc").asText()).endsWith("Z");
        assertThat(serialized.has("distance_m")).isTrue();
        assertThat(serialized.has("travel_time_seconds")).isTrue();
        assertThat(serialized.has("travel_time_minutes")).isFalse();
        assertThat(serialized.path("provenance").path("code_commit").asText())
                .isEqualTo("b9b6ea40f13c4af4a411bcafdbc773882c7f6acc");

        RouteResponse noPath = readFixture("a09_no_topological_path.json", RouteResponse.class);
        assertThat(noPath.topologicallyReachable()).isFalse();
        assertThat(noPath.distanceM()).isNull();
        assertThat(noPath.travelTimeSeconds()).isNull();
        assertThat(noPath.routeAccessibilityProbability()).isNull();

        RouteResponse unknownCoverage = readFixture("a09_insufficient_coverage.json", RouteResponse.class);
        assertThat(unknownCoverage.topologicallyReachable()).isTrue();
        assertThat(unknownCoverage.routeAccessibilityProbability()).isNull();
        assertThat(unknownCoverage.edgeCoverage().unassessedEdgeCount()).isPositive();
        assertThat(unknownCoverage.qcFlags()).isNotEmpty();
    }

    @Test
    void impactResponseRoundTripsOwnerProducedA07NoDataAndInstantaneousSemantics() throws Exception {
        ImpactResponse impact = readFixture("a07_impact_v4.json", ImpactResponse.class);
        JsonNode serialized = objectMapper.readTree(objectMapper.writeValueAsString(impact));

        assertThat(impact.sourceMode()).isEqualTo(RouteResponse.SourceMode.SIMULATED);
        assertThat(impact.aggregationInterval()).isNull();
        assertThat(impact.aggregationBasis()).contains("INSTANTANEOUS");
        assertThat(impact.coverage().population().nodataCount()).isPositive();
        assertThat(impact.metrics().populationExposedPeople().status())
                .isEqualTo(ImpactResponse.DistributionStatus.PARTIAL);
        assertThat(impact.facilityAccessByCategory().getFirst().category())
                .isEqualTo(ImpactResponse.FacilityCategory.HOSPITAL);
        assertThat(serialized.path("metrics").path("population_exposed_people").path("unit").asText())
                .isEqualTo("people");
        assertThat(serialized.path("qc_flags").toString()).contains("WORLDPOP_NOData_NOT_ZERO");
        assertThat(impact.provenance().sources()).isNotEmpty();
    }

    private <T> T readFixture(String filename, Class<T> type) throws Exception {
        try (InputStream input = getClass().getResourceAsStream("/owner-fixtures/" + filename)) {
            if (input == null) throw new IllegalStateException("missing owner fixture " + filename);
            return objectMapper.readValue(input, type);
        }
    }

    @Test
    void configuredBaseUrlsDoNotEnableUnimplementedAdapters() {
        var state = gateway.getTwinState(new TwinStateQuery(null, null));
        var alerts = gateway.listAlerts(new AlertRange(null, null));
        var routes = gateway.requestRoute(new RouteRequest(
                2, Instant.parse("2026-10-25T08:00:00Z"), "A", "B", null, null));
        var shelters = gateway.listShelters(new ShelterQuery(null, null));
        var scenarios = gateway.listScenarios();

        assertNotConfigured(state, GatewayDependency.AI_SERVICE);
        assertNotConfigured(alerts, GatewayDependency.AI_SERVICE);
        assertNotConfigured(routes, GatewayDependency.TRACK_B);
        assertNotConfigured(shelters, GatewayDependency.TRACK_B);
        assertNotConfigured(scenarios, GatewayDependency.SCENARIO_STORE);
    }

    @Test
    void designRoutesRemainUnexposed() throws Exception {
        mockMvc.perform(get("/twin/state")).andExpect(status().isNotFound());
        mockMvc.perform(get("/scenarios")).andExpect(status().isNotFound());
        mockMvc.perform(get("/alerts")).andExpect(status().isNotFound());
        mockMvc.perform(get("/shelters")).andExpect(status().isNotFound());
    }

    @Test
    void upstreamBaseUrlsAreOptionalAndConfigurable() {
        assertThat(upstreamProperties.aiServiceBaseUrl().toString()).isEqualTo("https://ai.example.invalid/api");
        assertThat(upstreamProperties.trackBBaseUrl().toString()).isEqualTo("https://trackb.example.invalid/api");
    }

    private static void assertNotConfigured(GatewayResult<?> result, GatewayDependency dependency) {
        assertThat(result.status()).isEqualTo(GatewayResult.Status.UNAVAILABLE);
        assertThat(result.data()).isNull();
        assertThat(result.dependency()).isEqualTo(dependency);
        assertThat(result.reason()).isEqualTo(GatewayResult.Reason.NOT_CONFIGURED);
    }
}
