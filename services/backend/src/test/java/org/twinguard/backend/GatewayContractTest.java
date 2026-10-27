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
import org.twinguard.backend.dto.RouteMode;
import org.twinguard.backend.dto.Provenance;
import org.twinguard.backend.dto.RouteRequest;
import org.twinguard.backend.dto.RouteResponse;
import org.twinguard.backend.dto.SourceClass;
import org.twinguard.backend.dto.ScenarioCreateRequest;
import org.twinguard.backend.dto.ShelterQuery;
import org.twinguard.backend.dto.ShelterResponse;
import org.twinguard.backend.dto.TwinStateQuery;
import org.twinguard.backend.dto.TwinStateResponse;
import org.twinguard.backend.service.TwinGuardGatewayService;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

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
    void routeResponseUsesTypedProvenanceAndKeepsNullDistinctFromMeasuredZero() throws Exception {
        Provenance provenance = new Provenance(SourceClass.REPLAY, "fixture-run", "trackb.v1",
                null, null, "fixture-run");
        RouteResponse route = new RouteResponse(true, List.of(10L), null, BigDecimal.ZERO, provenance);
        JsonNode serialized = objectMapper.readTree(objectMapper.writeValueAsString(route));

        assertThat(serialized.path("reachable").asBoolean()).isTrue();
        assertThat(serialized.get("travel_time_minutes").isNull()).isTrue();
        assertThat(serialized.path("route_accessibility_probability").decimalValue())
                .isEqualByComparingTo(BigDecimal.ZERO);
        assertThat(serialized.path("provenance").path("source").asText()).isEqualTo("replay");
        assertThat(validator.validate(route)).isEmpty();

        Provenance invalidProvenance = new Provenance(SourceClass.REPLAY, "x".repeat(129), "trackb.v1",
                null, "invalid", null);
        var violations = validator.validate(new RouteResponse(true, List.of(), null, null, invalidProvenance));
        assertThat(violations).extracting(v -> v.getPropertyPath().toString())
                .contains("provenance.sourceId", "provenance.sourceSha256");
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
