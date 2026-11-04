export type SourceMode = 'LIVE' | 'REPLAY' | 'SIMULATED';
export type AvailabilityFreshness = 'current' | 'STALE' | 'UNAVAILABLE';
export type ObservationValueState = 'value' | 'unknown' | 'unavailable' | 'zero' | 'dry' | 'nodata';
export type SourceTimePrecision = 'instant' | 'date' | 'unknown';

export interface SourceTimeMetadata {
  precision: SourceTimePrecision;
  value: string | null;
  timezone: string | null;
  semantics: string;
}

export interface ReadinessProvenance {
  reference: string | null;
  sha256: string | null;
}

export interface VerifiedLiveEvidence {
  ownerAuthorization: string;
  runtimeEvidence: string;
  verifiedAt: string;
  observationHash: string;
}

export interface SourceFreshnessMetadata {
  sourceMode: SourceMode;
  availability: AvailabilityFreshness;
  sourceIdentity: string | null;
  sourceTime: SourceTimeMetadata;
  receivedAt: string | null;
  refreshedAt: string | null;
  ageSeconds: number | null;
  freshnessBasis: string | null;
  provenance: ReadinessProvenance;
  unavailableReason: string | null;
  demoLabel: 'DEMO' | null;
  liveEvidence: VerifiedLiveEvidence | null;
}

const modes = new Set<SourceMode>(['LIVE', 'REPLAY', 'SIMULATED']);
const availabilityStates = new Set<AvailabilityFreshness>(['current', 'STALE', 'UNAVAILABLE']);
const precisions = new Set<SourceTimePrecision>(['instant', 'date', 'unknown']);
const digest = /^[a-f0-9]{64}$/;

export function validateSourceFreshness(input: unknown): SourceFreshnessMetadata {
  if (!isRecord(input)) throw new TypeError('Source metadata must be an object.');
  if (!modes.has(input.sourceMode as SourceMode)) throw new TypeError('Source mode must be LIVE, REPLAY, or SIMULATED.');
  if (!availabilityStates.has(input.availability as AvailabilityFreshness)) throw new TypeError('Availability must be current, STALE, or UNAVAILABLE.');
  const sourceMode = input.sourceMode as SourceMode;
  const availability = input.availability as AvailabilityFreshness;
  if (!isRecord(input.sourceTime) || !precisions.has(input.sourceTime.precision as SourceTimePrecision)) {
    throw new TypeError('Source time precision must be instant, date, or unknown.');
  }
  const sourceTime = input.sourceTime as unknown as SourceTimeMetadata;
  if (typeof sourceTime.semantics !== 'string' || !sourceTime.semantics.trim()) throw new TypeError('Source time semantics must be explicit.');
  if (sourceTime.precision === 'instant') {
    if (typeof sourceTime.value !== 'string' || !hasOffset(sourceTime.value)) throw new TypeError('Instant source time must include its supplied UTC offset.');
  } else if (sourceTime.precision === 'date') {
    if (typeof sourceTime.value !== 'string' || !isDate(sourceTime.value)) throw new TypeError('Date precision requires an ISO calendar date.');
    if (sourceTime.timezone !== 'unknown') throw new TypeError('Date-only observation timezone must remain unknown.');
  } else if (sourceTime.value !== null || sourceTime.timezone !== null) {
    throw new TypeError('Unknown source time must not contain an inferred value or timezone.');
  }
  if (input.sourceIdentity !== null && !nonEmpty(input.sourceIdentity)) throw new TypeError('Source identity must be non-empty or null.');
  if (input.receivedAt !== null && !hasOffset(input.receivedAt)) throw new TypeError('Received time must preserve an explicit UTC offset or remain null.');
  if (input.refreshedAt !== null && !hasOffset(input.refreshedAt)) throw new TypeError('Refresh time must preserve an explicit UTC offset or remain null.');
  if (!isRecord(input.provenance) || (input.provenance.reference !== null && !nonEmpty(input.provenance.reference))) {
    throw new TypeError('Provenance reference must be a non-empty value or null.');
  }
  if (input.provenance.sha256 !== null && (typeof input.provenance.sha256 !== 'string' || !digest.test(input.provenance.sha256))) {
    throw new TypeError('Provenance hash must be a lowercase SHA-256 digest or null.');
  }
  if (input.ageSeconds !== null && (typeof input.ageSeconds !== 'number' || !Number.isFinite(input.ageSeconds) || input.ageSeconds < 0)) {
    throw new TypeError('Age must be a non-negative finite number or null.');
  }
  if (input.freshnessBasis !== null && !nonEmpty(input.freshnessBasis)) throw new TypeError('Freshness basis must be explicit or null.');
  if (availability === 'UNAVAILABLE') {
    if (!nonEmpty(input.unavailableReason)) throw new TypeError('Unavailable data requires an explicit reason.');
  } else {
    if (input.unavailableReason !== null) throw new TypeError('Available data cannot carry an unavailable reason.');
    if (!nonEmpty(input.sourceIdentity) || !nonEmpty(input.freshnessBasis)) throw new TypeError('Available data requires source identity and freshness basis.');
  }
  if (availability === 'STALE' && input.ageSeconds === null) throw new TypeError('Stale data requires a measured age.');
  if (sourceMode === 'SIMULATED' && input.demoLabel !== 'DEMO') throw new TypeError('Simulated sources must retain the DEMO label.');
  if (sourceMode !== 'SIMULATED' && input.demoLabel !== null && input.demoLabel !== 'DEMO') throw new TypeError('Demo label must be DEMO or null.');
  validateLiveEvidence(sourceMode, availability, input.liveEvidence);
  if (sourceMode === 'LIVE' && availability !== 'UNAVAILABLE') {
    if (sourceTime.precision !== 'instant' || input.receivedAt === null || input.ageSeconds === null) {
      throw new TypeError('Available LIVE data requires source and receipt instants plus a measured age.');
    }
    if (!isRecord(input.liveEvidence) || input.provenance.sha256 !== input.liveEvidence.observationHash) {
      throw new TypeError('LIVE provenance hash must match the verified observation hash.');
    }
  }
  return input as unknown as SourceFreshnessMetadata;
}

function validateLiveEvidence(mode: SourceMode, availability: AvailabilityFreshness, value: unknown): void {
  if (mode !== 'LIVE') {
    if (value !== null) throw new TypeError('Live verification evidence is valid only for LIVE source mode.');
    return;
  }
  if (availability === 'UNAVAILABLE') {
    if (value !== null) throw new TypeError('Unconnected LIVE mode cannot claim verified source evidence.');
    return;
  }
  if (!isRecord(value) || !nonEmpty(value.ownerAuthorization) || !nonEmpty(value.runtimeEvidence) ||
      !hasOffset(value.verifiedAt) || !nonEmpty(value.observationHash) || !digest.test(String(value.observationHash))) {
    throw new TypeError('LIVE data requires source-owner authorization and verified runtime/provenance evidence.');
  }
}

export function observationValueLabel(state: ObservationValueState, value?: number | string | null): string {
  switch (state) {
    case 'value': return value === null || value === undefined ? 'Unknown' : String(value);
    case 'zero': return 'Known zero';
    case 'dry': return 'Explicit dry observation';
    case 'nodata': return 'NoData';
    case 'unavailable': return 'Unavailable';
    case 'unknown': return 'Unknown';
  }
}

export function demoScenarioMetadata(metadata: {
  sourceIdentity: string;
  runId: string;
  version: string;
  timeSemantics: string;
}): SourceFreshnessMetadata {
  return validateSourceFreshness({
    sourceMode: 'SIMULATED', availability: 'current', sourceIdentity: metadata.sourceIdentity,
    sourceTime: { precision: 'unknown', value: null, timezone: null, semantics: metadata.timeSemantics },
    receivedAt: null, refreshedAt: null, ageSeconds: null,
    freshnessBasis: 'Local DEMO fixture is loaded; source age and refresh are not measured.',
    provenance: { reference: `${metadata.runId} · ${metadata.version}`, sha256: null },
    unavailableReason: null, demoLabel: 'DEMO', liveEvidence: null,
  });
}

export function unavailableLiveMetadata(reason: string): SourceFreshnessMetadata {
  return validateSourceFreshness({
    sourceMode: 'LIVE', availability: 'UNAVAILABLE', sourceIdentity: null,
    sourceTime: { precision: 'unknown', value: null, timezone: null, semantics: 'No source metadata is available.' },
    receivedAt: null, refreshedAt: null, ageSeconds: null, freshnessBasis: null,
    provenance: { reference: null, sha256: null }, unavailableReason: reason,
    demoLabel: null, liveEvidence: null,
  });
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function nonEmpty(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0;
}

function hasOffset(value: unknown): value is string {
  if (typeof value !== 'string' || !/(Z|[+-]\d{2}:\d{2})$/i.test(value)) return false;
  return Number.isFinite(Date.parse(value));
}

function isDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const parsed = new Date(`${value}T00:00:00Z`);
  return !Number.isNaN(parsed.valueOf()) && parsed.toISOString().slice(0, 10) === value;
}
