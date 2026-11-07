package org.twinguard.backend.adapter.notconfigured;

import org.springframework.stereotype.Component;
import org.twinguard.backend.adapter.GatewayDependency;
import org.twinguard.backend.adapter.GatewayResult;
import org.twinguard.backend.adapter.TrackBPort;
import org.twinguard.backend.dto.RouteRequest;
import org.twinguard.backend.dto.RouteResponse;
import org.twinguard.backend.dto.ShelterQuery;
import org.twinguard.backend.dto.ShelterResponse;

import java.util.List;

@Component
public class NotConfiguredTrackBAdapter implements TrackBPort {
    @Override
    public GatewayResult<RouteResponse> requestRoute(RouteRequest request) {
        return GatewayResult.notConfigured(GatewayDependency.TRACK_B);
    }

    @Override
    public GatewayResult<List<ShelterResponse>> listShelters(ShelterQuery query) {
        return GatewayResult.notConfigured(GatewayDependency.TRACK_B);
    }
}
