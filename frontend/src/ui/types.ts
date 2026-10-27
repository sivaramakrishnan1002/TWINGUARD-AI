/** API-facing view models. Optional fields stay absent until supplied by a service. */
export type EvidenceStatus = 'OBSERVED' | 'DERIVED' | 'ASSUMPTION' | 'PLACEHOLDER' | 'UNAVAILABLE';
export type SourceMode = 'LIVE' | 'REPLAY' | 'SIMULATED' | 'NONE';
export type DataAvailability = 'LOADING' | 'AVAILABLE' | 'EMPTY' | 'PARTIAL' | 'STALE' | 'UNAVAILABLE' | 'ERROR';
export type EventWindowStatus = 'PLANNED' | 'HISTORICAL_REPLAY';

export interface DocumentedEventWindow {
  id: string;
  label: string;
  shortLabel: string;
  startDate: string;
  endDate: string;
  timeBasis: string;
  status: EventWindowStatus;
  source: string;
  limitations: string[];
}

export interface Provenance {
  source: string;
  sourceMode: SourceMode;
  observedAt?: string;
  runId?: number;
  version?: string;
  status: EvidenceStatus;
  limitations?: string[];
}

export interface MapLayer {
  id: string;
  label: string;
  kind: 'depth' | 'risk' | 'uncertainty' | 'nodata' | 'terrain' | 'reservoir' | 'roads' | 'shelters';
  unit?: string;
  status: EvidenceStatus;
  visible: boolean;
  provenance?: Provenance;
}

export interface FloodEvent {
  id: string;
  label: string;
  startAt: string;
  endAt?: string;
  sourceMode: SourceMode;
  provenance: Provenance;
}

export interface TwinRun {
  runId: number;
  version: string;
  issuedAt: string;
  validAt: string;
  status: EvidenceStatus;
  provenance: Provenance;
}

export interface Alert {
  id: number;
  severity: 'INFO' | 'WATCH' | 'WARNING' | 'EMERGENCY';
  sourceMode: SourceMode;
  issuedAt: string;
  validFrom: string;
  validTo: string;
  provenance: Provenance;
}

export interface RouteSummary {
  reachable: boolean;
  travelTimeMinutes?: number;
  accessibilityProbability?: number;
  provenance: Provenance;
}

export interface ShelterSummary {
  id: number;
  name?: string;
  candidateOnly: boolean;
  capacityPeople?: number | null;
  accessibilityProbability?: number | null;
  provenance: Provenance;
}

export interface ImpactSummary {
  runId: number;
  validAt: string;
  exposurePeople: number | null;
  affectedFacilities: number | null;
  affectedRoads: number | null;
  affectedRoadsUnit: string | null;
  provenance: Provenance;
  uncertainty?: string | null;
}

export type RouteTravelMode = 'vehicle' | 'walking';

export interface RouteRequest {
  runId: number;
  departureAt: string;
  origin: string;
  destination: string;
  mode: RouteTravelMode;
}

export interface PriorityZoneSummary {
  zoneId: string;
  label?: string;
  priorityRank?: number | null;
  provenance: Provenance;
}

export type CounterfactualScenarioKey = 'closed-bridge' | 'earlier-evacuation' | 'shelter-unavailable';

export interface CounterfactualRequest {
  scenarioKey: CounterfactualScenarioKey;
  baseRunId: number;
  parameters: Record<string, unknown>;
}
