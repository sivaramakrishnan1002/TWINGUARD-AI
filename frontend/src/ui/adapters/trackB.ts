export type TrackBSource = 'replay' | 'live' | 'simulated';
export type TrackBAlertLevel = 'Normal' | 'Watch' | 'Warning' | 'Critical';

export interface TrackBProvenance {
  sourceId?: string;
  sourceFile?: string;
  sourceHash?: string;
  [key: string]: unknown;
}

/** UI view model; the mounted API's response schema still needs an agreed mapping. */
export interface ReservoirStateRecord {
  reservoirKey: string;
  observedAt: string | null;
  receivedAt: string | null;
  source: TrackBSource;
  storageValue: number | null;
  storageUnit: 'mcft' | null;
  capacityValue: number | null;
  capacityUnit: 'mcft' | null;
  releaseValue: number | null;
  releaseUnit: 'cusecs' | null;
  provenance: TrackBProvenance;
  qcFlags: string[];
}

export interface TrackBAlertRecord {
  eventId: string;
  observedAt: string;
  receivedAt: string;
  source: TrackBSource;
  reservoirKey: string;
  level: TrackBAlertLevel;
  validFrom: string;
  validTo: string;
  ruleVersion: string;
  confidence?: number | null;
  provenance: TrackBProvenance;
}

export type AdapterResult<T> =
  | { status: 'available'; data: T }
  | { status: 'unavailable'; reason: string };

/** UI-owned seam for the documented GET routes; no URL or network call is configured. */
export interface TrackBReadAdapter {
  readonly availability: AdapterResult<null>;
  getCurrentReservoirStates(): Promise<AdapterResult<ReservoirStateRecord[]>>;
  getRecentAlerts(limit?: number): Promise<AdapterResult<TrackBAlertRecord[]>>;
  getAlertTimeline(start: string, end: string): Promise<AdapterResult<TrackBAlertRecord[]>>;
}

const unavailableReason = 'Track B API is not mounted in the host app and no read adapter is configured.';

export const unavailableTrackBAdapter: TrackBReadAdapter = {
  availability: { status: 'unavailable', reason: unavailableReason },
  async getCurrentReservoirStates() {
    return { status: 'unavailable', reason: unavailableReason };
  },
  async getRecentAlerts() {
    return { status: 'unavailable', reason: unavailableReason };
  },
  async getAlertTimeline() {
    return { status: 'unavailable', reason: unavailableReason };
  },
};
