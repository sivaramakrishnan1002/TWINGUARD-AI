package org.twinguard.backend.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.twinguard.backend.scenario.ScenarioVisualizationAssets;

import java.nio.file.Path;
import java.nio.file.Files;

@Configuration
public class ScenarioVisualizationAssetsConfiguration {
    @Bean
    ScenarioVisualizationAssets scenarioVisualizationAssets(
            ObjectMapper objectMapper,
            @Value("${twinguard.scenario.project-root:${user.dir}}") String projectRoot) {
        Path root = Path.of(projectRoot).toAbsolutePath().normalize();
        while (root != null && !Files.isRegularFile(root.resolve(
                "data/features/visualization3d/batch2_v1/manifest.json"))) {
            root = root.getParent();
        }
        if (root == null) {
            // Keep startup healthy when local assets are not mounted; requests fail closed with 503.
            root = Path.of(projectRoot).toAbsolutePath().normalize();
        }
        return new ScenarioVisualizationAssets(root, objectMapper);
    }
}
