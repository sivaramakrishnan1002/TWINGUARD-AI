/** API-facing view models. Optional fields stay absent until supplied by a service. */
export type EvidenceStatus = 'OBSERVED' | 'DERIVED' | 'ASSUMPTION' | 'PLACEHOLDER' | 'UNAVAILABLE';
export type SourceMode = 'OBSERVED' | 'DERIVED' | 'ASSUMPTION' | 'LIVE' | 'REPLAY' | 'SIMULATED' | 'NONE';
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

export type C7C8SourceMode = 'OBSERVED' | 'DERIVED' | 'SIMULATED' | 'ASSUMPTION' | 'REPLAY';

export type DistributionStatus = 'AVAILABLE' | 'PARTIAL' | 'UNAVAILABLE';

export interface ImpactDistribution {
  status: DistributionStatus;
  unit: string;
  mean: number | null;
  p05: number | null;
  p50: number | null;
  p95: number | null;
  member_count: number;
  interpretation: string;
}

export interface ImpactEvent {
  event_key: string;
  /** RFC 3339 UTC instant; null preserves unknown source time. */
  event_start_utc: string | null;
  event_end_utc: string | null;
  time_basis: 'UTC';
}

export interface ImpactAggregationInterval {
  start_utc: string;
  end_utc: string;
  convention: '[start,end)';
}

export interface ImpactThresholds {
  road_block_depth_m: number;
  road_threshold_is_assumption: boolean;
  sensitivity_depth_thresholds_m: number[];
  mapped_facility_exposure_threshold_m: number | null;
  population_exposure_threshold_m: number | null;
  exposure_thresholds_are_assumptions: boolean;
}

export interface ImpactMetrics {
  population_exposed_people: ImpactDistribution | null;
  affected_road_length_m: ImpactDistribution | null;
  affected_facilities_count: ImpactDistribution | null;
  facility_access_loss_fraction: ImpactDistribution | null;
}

export type FacilityCategory = 'hospital' | 'shelter' | 'candidate_shelter';

export interface FacilityAccessSummary {
  category: FacilityCategory;
  facility_count: number;
  reachable_count: number;
  unreachable_count: number;
  unassessed_count: number;
  access_loss_fraction: number | null;
  coverage_fraction: number | null;
  baseline_core_count?: ImpactDistribution;
  baseline_core_reachable_count_distribution?: ImpactDistribution;
  unreachable_from_anchor_count?: ImpactDistribution;
  outside_baseline_core_count?: ImpactDistribution;
  reachable_count_distribution?: ImpactDistribution;
  unreachable_count_distribution?: ImpactDistribution;
  coverage_fraction_mean?: number | null;
  interpretation: string;
}

export interface ImpactSensitivity {
  threshold_m: number;
  population_exposed_known_people: ImpactDistribution | null;
  affected_road_length_m: ImpactDistribution | null;
  mapped_facilities_exposed_count: ImpactDistribution | null;
  facility_access_loss_fraction: ImpactDistribution | null;
  facility_access_by_category: FacilityAccessSummary[];
}

export interface CoverageSlice {
  assessed_count: number;
  eligible_count: number;
  nodata_count: number;
  fraction_assessed?: number | null;
  coverage_basis?: string;
}

export interface ImpactCoverage {
  population: CoverageSlice;
  roads: CoverageSlice;
  facilities: CoverageSlice;
  hazard_grid: CoverageSlice;
}

export interface ImpactUncertainty {
  method: string;
  ensemble_id: string | null;
  member_count: number;
  interpretation: string;
}

export interface ImpactSourceReference {
  source_id: string;
  source_sha256: string | null;
  version: string | null;
  role: string;
}

export interface ImpactProvenance {
  sources: ImpactSourceReference[];
  algorithm: string;
  algorithm_version: string | null;
  code_commit: string | null;
  parameters: Record<string, unknown>;
  grid: { crs: string; resolution_m: number };
}

/** Exact snake_case projection of the A07 C7 JSONL record. */
export interface ImpactResult {
  schema_id: 'twinguard.impact_result';
  schema_version: string;
  result_id: string;
  run_id: number;
  run_version: string;
  source_mode: C7C8SourceMode;
  event: ImpactEvent;
  valid_at_utc: string;
  aggregation_interval: ImpactAggregationInterval | null;
  aggregation_basis: string | null;
  generated_at_utc: string;
  scenario_key: string;
  thresholds: ImpactThresholds;
  metrics: ImpactMetrics;
  facility_access_by_category: FacilityAccessSummary[];
  sensitivity: ImpactSensitivity[];
  coverage: ImpactCoverage;
  uncertainty: ImpactUncertainty;
  provenance: ImpactProvenance;
  qc_flags: string[];
  event_reference_note: string | null;
}

export interface ShelterSummary {
  id: number;
  name?: string;
  candidateOnly: boolean;
  capacityPeople?: number | null;
  accessibilityProbability?: number | null;
  provenance: Provenance;
}

export type RouteTravelMode = 'vehicle' | 'walking';

export interface RouteRequest {
  run_id: number;
  departure_at: string;
  origin: string;
  destination: string;
  mode?: RouteTravelMode;
  minimum_accessibility_probability?: number;
}

export type RouteResultStatus =
  | 'ROUTE_FOUND'
  | 'NO_TOPOLOGICAL_PATH'
  | 'INSUFFICIENT_HAZARD_COVERAGE'
  | 'BELOW_ACCESSIBILITY_CONSTRAINT'
  | 'INPUT_UNAVAILABLE';

export type RouteMethod = 'static' | 'current_flood_aware' | 'horizon_aware' | 'uncertainty_aware';

export interface RouteEdge {
  edge_id: number;
  entry_at_utc: string | null;
  exit_at_utc: string | null;
  distance_m: number | null;
  travel_time_seconds: number | null;
  depth_max_m: number | null;
  passable_probability: number | null;
  bridge: boolean | null;
  tunnel: boolean | null;
  assessment_status: string;
}

export interface RouteEdgeCoverage {
  route_edge_count: number;
  assessed_edge_count: number;
  unassessed_edge_count: number;
  fraction_assessed?: number | null;
}

export interface RouteDepthThresholds {
  ordinary_block_at_or_above_m: number;
  tunnel_proxy_block_at_or_above_m: number;
  bridge_rule: string;
  thresholds_are_assumptions: boolean;
  uncertainty_route_accessibility_minimum?: number | null;
  sensitivity_m: number[];
}

export interface RouteGraph {
  graph_id: string;
  graph_version: string;
  graph_sha256?: string | null;
  crs: string;
  edge_source_ids: string[];
  build_algorithm: string;
  build_version: string;
  assumptions: string[];
}

export interface RouteHazardRun {
  run_id: number | null;
  version: string;
  issued_at_utc: string | null;
  valid_start_utc: string | null;
  valid_end_utc: string | null;
  depth_source_id: string;
  depth_source_sha256?: string | null;
  ensemble_id: string | null;
}

export interface RouteUncertainty {
  method: string;
  ensemble_member_count: number;
  travel_time_spread_seconds?: number | null;
  failure_probability_constraint?: number | null;
  limitations: string[];
}

export interface RouteResultProvenance {
  algorithm: string;
  algorithm_version: string;
  code_commit: string;
  generated_at_utc: string;
  parameters: Record<string, unknown>;
}

export interface RouteResult {
  schema_id: 'twinguard.route_result';
  schema_version: string;
  result_id: string;
  status: RouteResultStatus;
  run_id: number | null;
  scenario_key: string;
  source_mode: C7C8SourceMode;
  method: RouteMethod;
  origin_id: string;
  destination_id: string;
  travel_mode: RouteTravelMode;
  departure_at_utc: string;
  arrival_at_utc: string | null;
  requested_horizon_seconds: number | null;
  distance_m: number | null;
  travel_time_seconds: number | null;
  /** Graph topology only. This does not mean a route is flood accessible or safe. */
  topologically_reachable: boolean | null;
  route_accessibility_probability: number | null;
  route_failure_probability: number | null;
  minimum_accessibility_probability: number | null;
  route_geometry: { type: 'LineString'; coordinates: [number, number][] } | null;
  node_path: number[];
  edges: RouteEdge[];
  depth_thresholds: RouteDepthThresholds;
  edge_coverage: RouteEdgeCoverage;
  graph: RouteGraph;
  hazard_run: RouteHazardRun;
  uncertainty: RouteUncertainty;
  provenance: RouteResultProvenance;
  qc_flags: string[];
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
