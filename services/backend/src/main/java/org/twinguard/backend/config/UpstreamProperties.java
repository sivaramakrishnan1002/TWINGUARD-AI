package org.twinguard.backend.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

import java.net.URI;

/** Optional upstream locations. Credentials belong in a future credential provider, never in URLs. */
@ConfigurationProperties("twinguard.upstreams")
public record UpstreamProperties(URI aiServiceBaseUrl, URI trackBBaseUrl) {}
