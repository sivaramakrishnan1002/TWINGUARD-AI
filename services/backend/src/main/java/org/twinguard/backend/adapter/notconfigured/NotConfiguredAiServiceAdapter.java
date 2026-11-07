package org.twinguard.backend.adapter.notconfigured;

import org.springframework.stereotype.Component;
import org.twinguard.backend.adapter.AiServicePort;
import org.twinguard.backend.adapter.GatewayDependency;
import org.twinguard.backend.adapter.GatewayResult;
import org.twinguard.backend.dto.AlertRange;
import org.twinguard.backend.dto.AlertResponse;
import org.twinguard.backend.dto.TwinStateQuery;
import org.twinguard.backend.dto.TwinStateResponse;

import java.util.List;

@Component
public class NotConfiguredAiServiceAdapter implements AiServicePort {
    @Override
    public GatewayResult<TwinStateResponse> getTwinState(TwinStateQuery query) {
        return GatewayResult.notConfigured(GatewayDependency.AI_SERVICE);
    }

    @Override
    public GatewayResult<List<AlertResponse>> listAlerts(AlertRange range) {
        return GatewayResult.notConfigured(GatewayDependency.AI_SERVICE);
    }
}
