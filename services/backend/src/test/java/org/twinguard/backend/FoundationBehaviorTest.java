package org.twinguard.backend;

import jakarta.validation.Validator;
import jakarta.validation.constraints.NotBlank;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.core.env.Environment;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest(properties = "server.port=0")
@AutoConfigureMockMvc
class FoundationBehaviorTest {
    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private Validator validator;

    @Autowired
    private Environment environment;

    @Test
    void missingEndpointReturnsGenericProblemResponse() throws Exception {
        mockMvc.perform(get("/not-implemented"))
                .andExpect(status().isNotFound())
                .andExpect(content().contentTypeCompatibleWith("application/problem+json"))
                .andExpect(content().json("""
                        {"status":404,"detail":"The requested resource was not found."}
                        """));
    }

    @Test
    void beanValidationRejectsBlankRequiredValuesWithoutEchoingInput() {
        var violations = validator.validate(new RequiredValue("   "));

        assertThat(violations).hasSize(1);
        assertThat(violations.iterator().next().getMessage()).isEqualTo("must not be blank");
    }

    @Test
    void unexpectedErrorsDoNotExposeExceptionMessages() {
        String secret = "token=never-return-this";
        var response = new org.twinguard.backend.error.ApiExceptionHandler()
                .handleUnexpected(new IllegalStateException(secret));

        assertThat(response.getStatus()).isEqualTo(HttpStatus.INTERNAL_SERVER_ERROR.value());
        assertThat(response.getDetail()).doesNotContain(secret);
    }

    @Test
    void serverPortCanBeConfiguredThroughSpringEnvironment() {
        assertThat(environment.getProperty("server.port")).isEqualTo("0");
    }

    private record RequiredValue(@NotBlank String value) {}
}
