package org.twinguard.backend.adapter;

import org.twinguard.backend.dto.ScenarioCreateRequest;
import org.twinguard.backend.dto.ScenarioResponse;

import java.util.List;
import java.util.Optional;

public interface ScenarioStorePort {
    GatewayResult<List<ScenarioResponse>> listScenarios();
    GatewayResult<Optional<ScenarioResponse>> getScenario(String scenarioKey);
    GatewayResult<ScenarioResponse> createScenario(ScenarioCreateRequest request);
}
