package org.twinguard.backend.service;

import org.springframework.stereotype.Service;
import org.twinguard.backend.adapter.AiServicePort;
import org.twinguard.backend.adapter.GatewayResult;
import org.twinguard.backend.adapter.ScenarioStorePort;
import org.twinguard.backend.adapter.TrackBPort;
import org.twinguard.backend.dto.AlertRange;
import org.twinguard.backend.dto.AlertResponse;
import org.twinguard.backend.dto.RouteRequest;
import org.twinguard.backend.dto.RouteResponse;
import org.twinguard.backend.dto.ScenarioCreateRequest;
import org.twinguard.backend.dto.ScenarioResponse;
import org.twinguard.backend.dto.ShelterQuery;
import org.twinguard.backend.dto.ShelterResponse;
import org.twinguard.backend.dto.TwinStateQuery;
import org.twinguard.backend.dto.TwinStateResponse;

import java.util.List;
import java.util.Optional;

@Service
public class TwinGuardGatewayService {
    private final AiServicePort aiService;
    private final TrackBPort trackB;
    private final ScenarioStorePort scenarioStore;

    public TwinGuardGatewayService(AiServicePort aiService, TrackBPort trackB, ScenarioStorePort scenarioStore) {
        this.aiService = aiService;
        this.trackB = trackB;
        this.scenarioStore = scenarioStore;
    }

    public GatewayResult<TwinStateResponse> getTwinState(TwinStateQuery query) {
        return aiService.getTwinState(query);
    }

    public GatewayResult<List<AlertResponse>> listAlerts(AlertRange range) {
        return aiService.listAlerts(range);
    }

    public GatewayResult<List<ScenarioResponse>> listScenarios() {
        return scenarioStore.listScenarios();
    }

    public GatewayResult<Optional<ScenarioResponse>> getScenario(String scenarioKey) {
        return scenarioStore.getScenario(scenarioKey);
    }

    public GatewayResult<ScenarioResponse> createScenario(ScenarioCreateRequest request) {
        return scenarioStore.createScenario(request);
    }

    public GatewayResult<RouteResponse> requestRoute(RouteRequest request) {
        return trackB.requestRoute(request);
    }

    public GatewayResult<List<ShelterResponse>> listShelters(ShelterQuery query) {
        return trackB.listShelters(query);
    }
}
