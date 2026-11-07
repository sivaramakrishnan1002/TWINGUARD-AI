package org.twinguard.backend.adapter;

import org.twinguard.backend.dto.RouteRequest;
import org.twinguard.backend.dto.RouteResponse;
import org.twinguard.backend.dto.ShelterQuery;
import org.twinguard.backend.dto.ShelterResponse;

import java.util.List;

public interface TrackBPort {
    GatewayResult<RouteResponse> requestRoute(RouteRequest request);
    GatewayResult<List<ShelterResponse>> listShelters(ShelterQuery query);
}
