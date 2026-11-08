/**
 * C4 v3 product API types, mirroring docs/api/ai-service.yaml § x-c4-v3-product-api
 * (CR-019 / OD-2026-11-07). Field names, units and enums follow the contract exactly.
 * Units: depth/height/tide m, distance m, duration s, rainfall mm per interval, flow m³/s.
 * `null` means unknown or outside the domain, never zero.
 */

export type SourceMode = 'SIMULATED' | 'MODEL_FORECAST' | 'PUBLISHED_SNAPSHOT' | 'SCENARIO_INPUT' | 'REPLAY' | 'STATIC_REFERENCE';
export interface LonLat { lon: number; lat: number }
export interface ApiError { detail: string; code: 'bad_request' | 'not_found' | 'conflict' | 'invalid' | 'rate_limited' | 'unavailable'; retry_after_s?: number | null }

export interface ProvenanceInput { name: string; source: string; source_mode: SourceMode; fetched_at?: string | null; sha256?: string | null }
export interface Provenance { engine_version: string; run_id: string; forcing_sha256?: string | null; static_assets_version?: string | null; inputs: ProvenanceInput[] }

/** Contract enum is 30/90/100/120 m; saved A05/A06/A23 runs are 600 m (flagged to the Integrator). */
export interface GridSpec { crs: 'EPSG:32644'; origin_x_m: number; origin_y_m: number; cell_size_m: number; rows: number; cols: number; bbox_wgs84: [number, number, number, number] }
export interface Frame { index: number; valid_time_utc: string; elapsed_minutes?: number }

export type SimMode = 'event' | 'custom' | 'forecast' | 'what_if';
export type FocusArea = 'VELACHERY' | 'ADYAR' | 'T_NAGAR' | 'PORUR';
export type ReservoirKey = 'CHEMBARAMBAKKAM' | 'POONDI' | 'PUZHAL' | 'CHOLAVARAM';
export interface CustomRainfall { start_time_utc: string; interval_minutes: 15 | 30 | 60; values_mm: number[] }
export interface WhatIfModifiers { base_run_id: string; rainfall_scale_pct?: number; reservoir_release_m3s?: Partial<Record<ReservoirKey, number>>; tide_offset_m?: number }
export interface SimulationRequest {
  mode: SimMode;
  event_key?: string;
  custom_rainfall?: CustomRainfall;
  what_if?: WhatIfModifiers;
  duration_hours?: number;
  resolution?: 'citywide' | 'focus';
  focus_area?: FocusArea;
  frame_interval_minutes?: 15 | 30;
}
export interface SimulationAccepted { run_id: string; state: 'queued' | 'running' | 'cached'; status_url: string; estimated_seconds?: number | null }
export interface SimulationSummary {
  max_depth_m?: number | null;
  flooded_area_km2?: number | null;
  buildings_affected?: number | null;
  population_exposed?: number | null;
  roads_blocked_km?: number | null;
  wards_affected?: number | null;
  peak_time_utc?: string | null;
}
export interface SimulationRun {
  run_id: string;
  state: 'queued' | 'running' | 'completed' | 'failed';
  mode: SimMode;
  request?: SimulationRequest;
  source_mode: 'SIMULATED';
  label?: string;
  created_at: string;
  completed_at?: string | null;
  progress_pct?: number | null;
  error?: string | null;
  grid?: GridSpec;
  frame_interval_minutes?: number;
  frames: Frame[];
  summary?: SimulationSummary;
  provenance: Provenance;
  limitations?: string[];
}
export interface SimulationList { runs: SimulationRun[]; next_cursor?: string | null }

export type DepthLayer = 'depth_mean' | 'depth_p05' | 'depth_p95' | 'velocity_mps';
export interface DepthFrame {
  run_id: string;
  frame_index?: number | null;
  valid_time_utc?: string | null;
  unit: 'm';
  layer?: DepthLayer;
  rows: number;
  cols: number;
  grid: GridSpec;
  /** Row-major, north row first, 0.01 m. null = outside model domain (not dry); 0 = dry. */
  values: (number | null)[][];
  max_value?: number | null;
}

export type DepthClass = 'dry' | 'lt_0_15' | '0_15_to_0_5' | '0_5_to_1_0' | 'gt_1_0' | 'unknown';
export interface BuildingDepth {
  building_id: string;
  centroid?: LonLat;
  ward_id?: number | null;
  height_m?: number | null;
  height_source?: 'osm_height' | 'osm_levels' | 'estimated';
  max_depth_m: number | null;
  time_of_max_utc?: string | null;
  depth_class: DepthClass;
}
export interface BuildingDepthPage { run_id: string; frame_index?: number | null; count: number; total?: number; buildings: BuildingDepth[]; next_cursor?: string | null }

export type RiskLevel = 'low' | 'moderate' | 'high' | 'severe';
export interface WardSummary {
  ward_id: number;
  ward_name: string;
  zone?: string | null;
  max_depth_m?: number | null;
  mean_flooded_depth_m?: number | null;
  flooded_area_km2?: number | null;
  flooded_fraction?: number | null;
  buildings_affected?: number | null;
  population_exposed?: number | null;
  roads_blocked_km?: number | null;
  shelters_reachable?: number | null;
  risk_level: RiskLevel;
}
export interface WardSummaryList { run_id: string; frame_index?: number | null; source_mode?: 'SIMULATED'; wards: WardSummary[] }

export type EdgeState = 'ASSESSED_PASSABLE' | 'ASSESSED_BLOCKED' | 'UNKNOWN';
export interface LineStringGeom { type: 'LineString'; coordinates: [number, number][] }
export interface RoadFeature {
  type: 'Feature';
  geometry: LineStringGeom;
  properties: { edge_id: string; state: EdgeState; unknown_reason?: string | null; depth_m?: number | null; speed_factor?: number | null; road_class?: string | null };
}
export interface RoadFeatureCollection { type: 'FeatureCollection'; run_id?: string; frame_index?: number | null; features: RoadFeature[] }

export type RoutePolicy = 'avoid_blocked' | 'avoid_blocked_and_unknown' | 'shortest_dry';
export type RouteProfile = 'car' | 'emergency_vehicle' | 'walk';
export interface RouteRequest { run_id: string; frame_index?: number | null; origin: LonLat; destination: LonLat; policy?: RoutePolicy; profile?: RouteProfile; blocked_depth_threshold_m?: number }
export interface RouteOption {
  policy: string;
  route_status: 'ASSESSED_PASSABLE' | 'CONDITIONAL' | 'NO_ROUTE';
  distance_m: number | null;
  travel_time_s: number | null;
  geometry: LineStringGeom | null;
  length_by_state_m?: Partial<Record<EdgeState, number>>;
  max_depth_on_route_m?: number | null;
}
export interface RouteResponse { run_id: string; frame_index?: number | null; status: 'found' | 'no_route' | 'origin_unreachable' | 'destination_unreachable'; routes: RouteOption[]; dry_baseline?: RouteOption | null; source_mode: 'SIMULATED' }

export interface Shelter {
  shelter_id: string;
  name: string;
  category: 'shelter' | 'school' | 'college' | 'community_hall';
  location: LonLat;
  ward_id?: number | null;
  capacity_people: number;
  capacity_source: 'assumed' | 'scenario_input' | 'published';
  site_max_depth_m?: number | null;
  reachable: boolean;
  assigned_population?: number | null;
  utilisation_pct?: number | null;
}
export interface ShelterReport {
  run_id: string;
  frame_index?: number | null;
  source_mode: 'SIMULATED';
  capacity_factor?: number;
  shelters: Shelter[];
  totals: { demand_people?: number | null; served_people?: number | null; unserved_people?: number | null; unreachable_people?: number | null; reachable_shelters?: number };
}

export type Severity = 'info' | 'watch' | 'warning' | 'critical';
export interface Incident {
  incident_id: string;
  generated: true;
  generated_from?: 'simulation';
  type: 'building_flooding' | 'road_blocked' | 'shelter_unreachable' | 'population_cut_off' | 'reservoir_release';
  severity: Severity;
  ward_id?: number | null;
  location: LonLat;
  valid_time_utc: string;
  title?: string;
  metrics?: Record<string, number | null>;
}
export interface IncidentList { run_id: string; source_mode: 'SIMULATED'; incidents: Incident[] }

export type ResourceType = 'boat' | 'rescue_team' | 'vehicle' | 'ambulance' | 'pump';
export interface Resource { resource_id: string; type: ResourceType; count: number; base: { name: string; location: LonLat }; source_mode?: 'SCENARIO_INPUT' }
export interface ResourceSet { version?: number; updated_at?: string | null; resources: Resource[] }
export interface EmergencyPlan {
  run_id: string;
  frame_index?: number | null;
  source_mode: 'SIMULATED';
  resource_set_version?: number;
  assignments: { incident_id: string; resource_id: string; units: number; eta_s?: number | null; route_status?: string | null }[];
  unassigned_incidents?: string[];
}
export interface Comparison {
  run_id: string;
  baseline_run_id: string;
  modifiers?: WhatIfModifiers;
  delta: SimulationSummary;
  ward_changes?: { ward_id: number; max_depth_change_m?: number | null; risk_level_before?: string; risk_level_after?: string }[];
}
export interface ApiEvent { event_key: string; label: string; start_utc: string; end_utc: string; rainfall_source?: string; source_mode?: SourceMode }
export interface EventList { events: ApiEvent[] }
export interface Weather {
  provider: 'open-meteo';
  model?: string | null;
  fetched_at: string;
  cache_age_s?: number;
  min_refresh_interval_s: number;
  location?: LonLat;
  current?: { temperature_c?: number | null; precipitation_mm?: number | null; relative_humidity_pct?: number | null; wind_speed_kmh?: number | null };
  hourly?: { time_utc: string; precipitation_mm?: number | null; precipitation_probability_pct?: number | null }[];
  source_mode: 'MODEL_FORECAST';
  attribution: string;
}
export interface Overview {
  generated_at: string;
  badge: 'DEMO / SIMULATION';
  latest_run?: SimulationRun | null;
  weather?: Weather | null;
  reservoirs?: Record<string, unknown> | null;
  incident_counts?: Record<string, number>;
  top_wards?: WardSummary[];
}
export interface EngineStatus {
  engine_version: string;
  static_available: boolean;
  running: boolean;
  running_run_id?: string | null;
  queue_length?: number;
  last_completed_run_id?: string | null;
  weather_min_refresh_interval_s?: number;
  weather_next_fetch_allowed_at?: string | null;
}
export interface StaticFeatureCollection { type: 'FeatureCollection'; layer?: string; source?: string; source_mode?: 'STATIC_REFERENCE'; attribution?: string; features: { type: 'Feature'; geometry: { type: string; coordinates: unknown }; properties: Record<string, unknown> }[]; next_cursor?: string | null }
export type StaticLayer = 'wards' | 'buildings' | 'shelters' | 'focus_areas';

/** The operations the UI needs. Implemented by the HTTP client (B47) and by typed fixtures until then. */
export interface TwinGuardApi {
  readonly kind: 'api' | 'fixture';
  status(): Promise<EngineStatus>;
  overview(): Promise<Overview>;
  events(): Promise<EventList>;
  weather(refresh?: boolean): Promise<Weather>;
  createSimulation(req: SimulationRequest): Promise<SimulationAccepted>;
  listSimulations(): Promise<SimulationList>;
  getSimulation(runId: string): Promise<SimulationRun>;
  depth(runId: string, frameIndex: number | null, layer?: DepthLayer): Promise<DepthFrame>;
  buildings(runId: string, frameIndex: number | null, bbox: [number, number, number, number]): Promise<BuildingDepthPage>;
  wards(runId: string, frameIndex: number | null): Promise<WardSummaryList>;
  roads(runId: string, frameIndex: number | null, bbox: [number, number, number, number], threshold?: number): Promise<RoadFeatureCollection>;
  shelters(runId: string, frameIndex: number | null, capacityFactor?: 0.5 | 1 | 2): Promise<ShelterReport>;
  incidents(runId: string, frameIndex: number | null, minSeverity?: Severity): Promise<IncidentList>;
  emergencyPlan(runId: string, frameIndex: number | null): Promise<EmergencyPlan>;
  comparison(runId: string, baselineRunId?: string): Promise<Comparison>;
  route(req: RouteRequest): Promise<RouteResponse>;
  getResources(): Promise<ResourceSet>;
  putResources(set: ResourceSet): Promise<ResourceSet>;
  staticLayer(layer: StaticLayer, bbox?: [number, number, number, number]): Promise<StaticFeatureCollection>;
}

export class ApiRequestError extends Error {
  constructor(public status: number, public body: ApiError | null) { super(body?.detail ?? `HTTP ${status}`); }
}
