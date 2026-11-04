import type { SourceFreshnessMetadata } from './model';

export function SourceReadinessPanel({ demo, live }: { demo: SourceFreshnessMetadata; live: SourceFreshnessMetadata }) {
  return <section className="tg-product__source-boundary" aria-labelledby="source-boundary-title">
    <div className="tg-product__section-minihead">
      <div><span className="tg-product__eyebrow">SOURCE MODE · AVAILABILITY ARE SEPARATE</span><h3 id="source-boundary-title">Source and freshness state</h3></div>
    </div>
    <SourceFreshnessCard metadata={demo} />
    <SourceFreshnessCard metadata={live} />
  </section>;
}

export function SourceFreshnessCard({ metadata, exampleLabel }: { metadata: SourceFreshnessMetadata; exampleLabel?: string }) {
  const modeLabel = exampleLabel ?? (metadata.sourceMode === 'LIVE'
    ? metadata.availability === 'UNAVAILABLE' ? 'No verified live source' : 'LIVE'
    : metadata.sourceMode === 'SIMULATED' ? 'DEMO · SIMULATED' : 'REPLAY');
  const unavailable = metadata.availability === 'UNAVAILABLE';
  return <article className={`tg-product__source-state${unavailable ? ' tg-product__source-state--unavailable' : ''}`} data-source-mode={metadata.sourceMode} data-availability={metadata.availability}>
    <div><span>Source mode</span><strong>{modeLabel}</strong></div>
    <div><span>Availability / freshness</span><strong>{metadata.availability}</strong></div>
    <p>Source: {metadata.sourceIdentity ?? 'Unknown'}</p>
    <p>Source time: {metadata.sourceTime.value ?? 'Unknown'} · {metadata.sourceTime.precision} precision · {metadata.sourceTime.semantics}</p>
    <p>Source timezone: {metadata.sourceTime.timezone ?? 'Unknown'}</p>
    <p>Received / refreshed: {metadata.receivedAt ?? 'Not recorded'} / {metadata.refreshedAt ?? 'Not refreshed'}</p>
    <p>Age: {metadata.ageSeconds === null ? 'Unknown' : `${metadata.ageSeconds} seconds`} · basis: {metadata.freshnessBasis ?? 'Unknown'}</p>
    <p>Provenance: {metadata.provenance.reference ?? 'Unknown'} · SHA-256 {metadata.provenance.sha256 ?? 'not supplied'}</p>
    {unavailable && <p>Reason: {metadata.unavailableReason}</p>}
    {metadata.sourceMode === 'SIMULATED' && <small>DEMO fixture only. “current” means the local fixture is loaded; it is not a source-age or live freshness claim.</small>}
    {metadata.sourceMode === 'LIVE' && unavailable && <small>No verified LIVE source metadata is present; no connection was attempted.</small>}
    {exampleLabel && <small>Local fixture example; no external source was queried.</small>}
  </article>;
}
