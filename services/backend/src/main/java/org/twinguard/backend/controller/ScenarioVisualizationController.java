package org.twinguard.backend.controller;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;
import org.twinguard.backend.scenario.ScenarioVisualizationAssets;

@RestController
public class ScenarioVisualizationController {
    private final ScenarioVisualizationAssets assets;

    public ScenarioVisualizationController(ScenarioVisualizationAssets assets) {
        this.assets = assets;
    }

    @GetMapping("/scenario-visualization-assets")
    public Object list(HttpServletRequest request) {
        rejectQueryParameters(request);
        return assets.catalog();
    }

    @GetMapping("/scenario-visualization-assets/{event_id}/{scenario_id}")
    public Object detail(
            @PathVariable("event_id") String eventId,
            @PathVariable("scenario_id") String scenarioId,
            HttpServletRequest request) {
        rejectQueryParameters(request);
        return assets.asset(eventId, scenarioId);
    }

    private static void rejectQueryParameters(HttpServletRequest request) {
        if ((request.getParameterMap() != null && !request.getParameterMap().isEmpty())
                || request.getContentLengthLong() > 0) {
            throw new ScenarioVisualizationAssets.InvalidScenarioSelectorException();
        }
    }
}
