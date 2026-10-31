package org.twinguard.backend;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.test.web.servlet.MockMvc;
import org.twinguard.backend.service.B13ReplayService;

import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.options;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest(properties = "twinguard.b13.enabled=true")
@AutoConfigureMockMvc
class B13ReplayControllerTest {
    private static final String EVENT = "replay:POONDI:date:2015-12-01";
    private static final byte[] ENVELOPE = ("{\"contract_version\":\"C4-v2\",\"source_observation\":{\"event_id\":\"" + EVENT
            + "\",\"source_mode\":\"REPLAY\",\"time_precision\":\"date\",\"observed_at\":null,\"observation_timezone\":\"unknown\",\"received_at\":\"2026-10-31T10:00:00Z\"},"
            + "\"replay\":{\"replay_run_id\":\"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"},"
            + "\"derived_output\":{\"status\":\"not_produced\",\"alert\":null,\"output_sha256\":null},\"limitations\":[\"research only\"]}")
            .getBytes(java.nio.charset.StandardCharsets.UTF_8);

    @Autowired MockMvc mvc;
    @MockBean B13ReplayService service;

    @Test
    void approvedRouteForwardsExactEnvelopeReadOnly() throws Exception {
        when(service.lookup(EVENT)).thenReturn(ResponseEntity.ok().contentType(MediaType.APPLICATION_JSON).body(ENVELOPE));
        mvc.perform(get("/replay-alerts/{event_id}", EVENT).accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk())
                .andExpect(header().string("Content-Type", "application/json"))
                .andExpect(content().bytes(ENVELOPE));
        verify(service).lookup(EVENT);
    }

    @Test
    void invalidAndUnknownSelectorsMapTo400And404() throws Exception {
        mvc.perform(get("/replay-alerts/{event_id}", "broken"))
                .andExpect(status().isBadRequest());
        mvc.perform(get("/replay-alerts/{event_id}", "replay:CHOLAVARAM:date:2015-12-01"))
                .andExpect(status().isNotFound());
        verifyNoInteractions(service);
    }

    @Test
    void approvedErrorStatusesArePreservedWithoutPartialResults() throws Exception {
        for (int code : new int[]{400, 404, 409, 503}) {
            byte[] error = ("{\"status\":" + code + ",\"code\":\"asset_unavailable\",\"detail\":\"bounded error\"}")
                    .getBytes(java.nio.charset.StandardCharsets.UTF_8);
            when(service.lookup(EVENT)).thenReturn(ResponseEntity.status(code).contentType(MediaType.APPLICATION_JSON).body(error));
            mvc.perform(get("/replay-alerts/{event_id}", EVENT).accept(MediaType.APPLICATION_JSON))
                    .andExpect(status().is(code))
                    .andExpect(content().bytes(error));
        }
        verify(service, org.mockito.Mockito.times(4)).lookup(EVENT);
    }

    @Test
    void exactOriginGetAcceptPreflightIsAllowedWithoutCredentials() throws Exception {
        mvc.perform(options("/replay-alerts/{event_id}", EVENT)
                        .header("Origin", "http://127.0.0.1:8081")
                        .header("Access-Control-Request-Method", "GET")
                        .header("Access-Control-Request-Headers", "Accept"))
                .andExpect(status().isOk())
                .andExpect(header().string("Access-Control-Allow-Origin", "http://127.0.0.1:8081"))
                .andExpect(header().string("Access-Control-Allow-Methods", "GET"))
                .andExpect(header().string("Access-Control-Allow-Headers", "Accept"))
                .andExpect(header().doesNotExist("Access-Control-Allow-Credentials"));
    }

    @Test
    void otherOriginsMethodsAndHeadersAreDenied() throws Exception {
        mvc.perform(options("/replay-alerts/{event_id}", EVENT)
                        .header("Origin", "http://localhost:8081")
                        .header("Access-Control-Request-Method", "GET")
                        .header("Access-Control-Request-Headers", "Accept"))
                .andExpect(header().doesNotExist("Access-Control-Allow-Origin"));
        mvc.perform(options("/replay-alerts/{event_id}", EVENT)
                        .header("Origin", "http://127.0.0.1:8081")
                        .header("Access-Control-Request-Method", "POST")
                        .header("Access-Control-Request-Headers", "Accept"))
                .andExpect(header().doesNotExist("Access-Control-Allow-Origin"));
        mvc.perform(options("/replay-alerts/{event_id}", EVENT)
                        .header("Origin", "http://127.0.0.1:8081")
                        .header("Access-Control-Request-Method", "GET")
                        .header("Access-Control-Request-Headers", "X-Other"))
                .andExpect(header().doesNotExist("Access-Control-Allow-Origin"));
    }
}
