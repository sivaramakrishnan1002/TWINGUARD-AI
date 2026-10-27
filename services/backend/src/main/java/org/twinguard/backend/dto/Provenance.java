package org.twinguard.backend.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

public record Provenance(
        @NotNull SourceClass source,
        @JsonProperty("source_id") @NotBlank @Size(max = 128) String sourceId,
        @JsonProperty("schema_version") @NotBlank @Size(max = 32)
        @Pattern(regexp = "[A-Za-z0-9][A-Za-z0-9._-]*") String schemaVersion,
        @JsonProperty("source_file") @Size(max = 512) String sourceFile,
        @JsonProperty("source_sha256") @Pattern(regexp = "[0-9a-f]{64}") String sourceSha256,
        @JsonProperty("run_id") @Size(max = 128) String runId) {}
