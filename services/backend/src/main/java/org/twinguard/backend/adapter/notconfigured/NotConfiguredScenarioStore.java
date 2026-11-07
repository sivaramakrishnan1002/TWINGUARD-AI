package org.twinguard.backend.adapter.notconfigured;

import org.springframework.stereotype.Component;
import org.twinguard.backend.adapter.GatewayDependency;
import org.twinguard.backend.adapter.GatewayResult;
import org.twinguard.backend.adapter.ScenarioStorePort;
import org.twinguard.backend.dto.ScenarioCreateRequest;
import org.twinguard.backend.dto.ScenarioResponse;

import java.util.List;
import java.util.Optional;

@Component
public class NotConfiguredScenarioStore implements ScenarioStorePort {
    @Override
    public GatewayResult<List<ScenarioResponse>> listScenarios() {
        return GatewayResult.notConfigured(GatewayDependency.SCENARIO_STORE);
    }

    @Override
    public GatewayResult<Optional<ScenarioResponse>> getScenario(String scenarioKey) {
        return GatewayResult.notConfigured(GatewayDependency.SCENARIO_STORE);
    }

    @Override
    public GatewayResult<ScenarioResponse> createScenario(ScenarioCreateRequest request) {
        return GatewayResult.notConfigured(GatewayDependency.SCENARIO_STORE);
    }
}
