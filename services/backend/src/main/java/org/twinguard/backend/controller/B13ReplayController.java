package org.twinguard.backend.controller;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;
import org.twinguard.backend.service.B13ReplayService;

import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.regex.Pattern;

@RestController
@ConditionalOnProperty(prefix = "twinguard.b13", name = "enabled", havingValue = "true")
public class B13ReplayController implements WebMvcConfigurer {
    private static final String APPROVED_EVENT_ID = "replay:POONDI:date:2015-12-01";
    private static final Pattern SELECTOR = Pattern.compile("^replay:[A-Z]+:date:[0-9]{4}-[0-9]{2}-[0-9]{2}$");
    private final B13ReplayService service;

    public B13ReplayController(B13ReplayService service) {
        this.service = service;
    }

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/replay-alerts/**")
                .allowedOrigins("http://127.0.0.1:8081")
                .allowedMethods("GET")
                .allowedHeaders("Accept")
                .allowCredentials(false)
                .maxAge(0);
    }

    @GetMapping(value = "/replay-alerts/{event_id}", produces = "application/json")
    public ResponseEntity<byte[]> lookup(@PathVariable("event_id") String eventId) {
        if (!SELECTOR.matcher(eventId).matches()) {
            return error(400, "invalid_selector", "event_id must be a date-only replay selector.");
        }
        try {
            LocalDate.parse(eventId.substring(eventId.lastIndexOf(':') + 1));
        } catch (DateTimeParseException invalidDate) {
            return error(400, "invalid_selector", "event_id must contain a valid calendar date.");
        }
        if (!APPROVED_EVENT_ID.equals(eventId)) {
            return error(404, "not_found", "No exact approved replay observation exists.");
        }
        return service.lookup(eventId);
    }

    private static ResponseEntity<byte[]> error(int status, String code, String detail) {
        String body = "{\"status\":" + status + ",\"code\":\"" + code + "\",\"detail\":\"" + detail + "\"}";
        return ResponseEntity.status(status).header("Cache-Control", "no-store")
                .header("Content-Type", "application/json").body(body.getBytes(java.nio.charset.StandardCharsets.UTF_8));
    }
}
