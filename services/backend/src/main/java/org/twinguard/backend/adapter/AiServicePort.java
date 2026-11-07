package org.twinguard.backend.adapter;

import org.twinguard.backend.dto.AlertRange;
import org.twinguard.backend.dto.AlertResponse;
import org.twinguard.backend.dto.TwinStateQuery;
import org.twinguard.backend.dto.TwinStateResponse;

import java.util.List;

public interface AiServicePort {
    GatewayResult<TwinStateResponse> getTwinState(TwinStateQuery query);
    GatewayResult<List<AlertResponse>> listAlerts(AlertRange range);
}
