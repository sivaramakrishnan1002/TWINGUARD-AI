package org.twinguard.backend.error;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.servlet.resource.NoResourceFoundException;
import org.twinguard.backend.scenario.ScenarioVisualizationAssets;

@RestControllerAdvice
public class ApiExceptionHandler {
    private static final Logger logger = LoggerFactory.getLogger(ApiExceptionHandler.class);

    @ExceptionHandler(HttpRequestMethodNotSupportedException.class)
    public ProblemDetail handleMethodNotAllowed(HttpRequestMethodNotSupportedException exception) {
        return ProblemDetail.forStatusAndDetail(HttpStatus.METHOD_NOT_ALLOWED, "The requested method is not supported.");
    }

    @ExceptionHandler(ScenarioVisualizationAssets.InvalidScenarioSelectorException.class)
    public ProblemDetail handleInvalidScenarioSelector(
            ScenarioVisualizationAssets.InvalidScenarioSelectorException exception) {
        return ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST, "event_id or scenario_id is invalid.");
    }

    @ExceptionHandler(ScenarioVisualizationAssets.ScenarioAssetNotFoundException.class)
    public ProblemDetail handleScenarioNotFound(
            ScenarioVisualizationAssets.ScenarioAssetNotFoundException exception) {
        return ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, "No exact saved scenario asset was found.");
    }

    @ExceptionHandler(ScenarioVisualizationAssets.ScenarioIdentityConflictException.class)
    public ProblemDetail handleScenarioConflict(
            ScenarioVisualizationAssets.ScenarioIdentityConflictException exception) {
        return ProblemDetail.forStatusAndDetail(HttpStatus.CONFLICT, "Scenario identity is duplicated or ambiguous.");
    }

    @ExceptionHandler(ScenarioVisualizationAssets.ScenarioAssetUnavailableException.class)
    public ProblemDetail handleScenarioUnavailable(
            ScenarioVisualizationAssets.ScenarioAssetUnavailableException exception) {
        return ProblemDetail.forStatusAndDetail(HttpStatus.SERVICE_UNAVAILABLE, "Scenario assets are unavailable.");
    }

    @ExceptionHandler(NoResourceFoundException.class)
    public ProblemDetail handleNotFound(NoResourceFoundException exception) {
        return ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, "The requested resource was not found.");
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ProblemDetail handleInvalidRequest(MethodArgumentNotValidException exception) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(
                HttpStatus.UNPROCESSABLE_ENTITY, "One or more request fields are invalid.");
        problem.setProperty("invalidFields", exception.getBindingResult().getFieldErrors().stream()
                .map(error -> error.getField())
                .distinct()
                .sorted()
                .toList());
        return problem;
    }

    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ProblemDetail handleUnreadableRequest(HttpMessageNotReadableException exception) {
        return ProblemDetail.forStatusAndDetail(
                HttpStatus.UNPROCESSABLE_ENTITY, "The request body is missing or has an invalid format.");
    }

    @ExceptionHandler(Exception.class)
    public ProblemDetail handleUnexpected(Exception exception) {
        // Do not log exception messages or request values: either may contain user supplied secrets.
        logger.error("Unhandled request failure");
        return ProblemDetail.forStatusAndDetail(
                HttpStatus.INTERNAL_SERVER_ERROR,
                "The request could not be completed.");
    }
}
