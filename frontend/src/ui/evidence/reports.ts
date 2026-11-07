/**
 * Saved research results transcribed from committed TwinGuard reports.
 *
 * Every value below is copied from the cited report. Nothing is live, nothing is
 * invented, and nothing here is an operational forecast, warning or route.
 * If a report changes, update the matching block and its `source`.
 */

export type EventId = '2015-12-02' | '2021-11-13' | '2023-12-04';
export type ScenarioId = 'perfect_foresight_imerg' | 'rain_error_q10' | 'rain_error_q50' | 'rain_error_q90' | 'persistence_previous_day';
export type Lead = 6 | 12 | 24 | 48 | 72;

export const LEADS: Lead[] = [6, 12, 24, 48, 72];

export interface EventWindow {
  id: EventId;
  label: string;
  windowUtc: string;
  windowStartUtc: string;
  reference: string;
}

export const EVENTS: EventWindow[] = [
  { id: '2015-12-02', label: 'Dec 2015 window', windowUtc: '30 Nov – 2 Dec 2015 UTC', windowStartUtc: '2015-11-30T00:00:00Z', reference: 'Includes the 1 Dec IMERG peak. No accepted official vector extent exists for the 1–8 Dec peak.' },
  { id: '2021-11-13', label: 'Nov 2021 window', windowUtc: '11 – 13 Nov 2021 UTC', windowStartUtc: '2021-11-11T00:00:00Z', reference: 'The 13 Nov NRSC reference is a PDF, not an accepted georeferenced raster.' },
  { id: '2023-12-04', label: 'Dec 2023 window', windowUtc: '2 – 4 Dec 2023 UTC', windowStartUtc: '2023-12-02T00:00:00Z', reference: 'The 7 Dec NDEM map is preliminary and not an accepted raster reference.' },
];

export const SCENARIOS: { id: ScenarioId; label: string; short: string; note: string }[] = [
  { id: 'perfect_foresight_imerg', label: 'Perfect-foresight IMERG', short: 'IMERG hindcast', note: 'Observed daily IMERG with an ERA5 hourly shape. Hindsight forcing, not an archived forecast.' },
  { id: 'rain_error_q10', label: 'Rain difference q10', short: 'q10', note: 'IMERG plus the 10th-percentile ERA5−IMERG daily difference (−25.544 mm/day).' },
  { id: 'rain_error_q50', label: 'Rain difference q50', short: 'q50', note: 'IMERG plus the median ERA5−IMERG daily difference (+0.466 mm/day).' },
  { id: 'rain_error_q90', label: 'Rain difference q90', short: 'q90', note: 'IMERG plus the 90th-percentile ERA5−IMERG daily difference (+12.851 mm/day).' },
  { id: 'persistence_previous_day', label: 'Previous-day persistence', short: 'Persistence', note: "Repeats the previous UTC day's rain. A simple baseline, not a plausible issued forecast." },
];

export const scenarioLabel = (id: ScenarioId) => SCENARIOS.find((s) => s.id === id)?.label ?? id;
export const eventLabel = (id: EventId) => EVENTS.find((e) => e.id === id)?.label ?? id;

/** A05 — docs/PHASE11_FORECAST_BATCH2.md, "Simulated scenario summaries" (ensemble-mean depth). */
export const A05_SUMMARY: Record<EventId, Record<ScenarioId, { rain72: number; mean24: number; area24_010: number; mean72: number; area72_010: number; area72_030: number }>> = {
  '2015-12-02': {
    perfect_foresight_imerg: { rain72: 351.54, mean24: 0.0215, area24_010: 50.4, mean72: 0.0418, area72_010: 59.76, area72_030: 36.0 },
    rain_error_q10: { rain72: 274.91, mean24: 0.0086, area24_010: 12.24, mean72: 0.034, area72_010: 54.36, area72_030: 33.84 },
    rain_error_q50: { rain72: 352.94, mean24: 0.0216, area24_010: 51.12, mean72: 0.042, area72_010: 60.12, area72_030: 36.36 },
    rain_error_q90: { rain72: 390.09, mean24: 0.0274, area24_010: 70.2, mean72: 0.0457, area72_010: 66.6, area72_030: 37.08 },
    persistence_previous_day: { rain72: 31.87, mean24: 0.001, area24_010: 0.36, mean72: 0.0026, area72_010: 5.4, area72_030: 0 },
  },
  '2021-11-13': {
    perfect_foresight_imerg: { rain72: 22.27, mean24: 0.0035, area24_010: 6.48, mean72: 0.0021, area72_010: 4.68, area72_030: 0 },
    rain_error_q10: { rain72: 0, mean24: 0, area24_010: 0, mean72: 0, area72_010: 0, area72_030: 0 },
    rain_error_q50: { rain72: 23.67, mean24: 0.0036, area24_010: 7.2, mean72: 0.0023, area72_010: 6.48, area72_030: 0 },
    rain_error_q90: { rain72: 60.82, mean24: 0.0076, area24_010: 22.68, mean72: 0.0126, area72_010: 29.52, area72_030: 8.28 },
    persistence_previous_day: { rain72: 313.95, mean24: 0.0415, area24_010: 90.36, mean72: 0.0601, area72_010: 108.0, area72_030: 43.56 },
  },
  '2023-12-04': {
    perfect_foresight_imerg: { rain72: 279.07, mean24: 0.0058, area24_010: 6.48, mean72: 0.048, area72_010: 86.76, area72_030: 41.04 },
    rain_error_q10: { rain72: 204.33, mean24: 0, area24_010: 0, mean72: 0.0424, area72_010: 79.56, area72_030: 39.24 },
    rain_error_q50: { rain72: 280.47, mean24: 0.006, area24_010: 7.56, mean72: 0.0481, area72_010: 86.76, area72_030: 41.04 },
    rain_error_q90: { rain72: 317.63, mean24: 0.0117, area24_010: 20.16, mean72: 0.0507, area72_010: 90.72, area72_030: 41.76 },
    persistence_previous_day: { rain72: 7.55, mean24: 0, area24_010: 0, mean72: 0, area72_010: 0, area72_030: 0 },
  },
};

/** A07 — docs/PHASE13_IMPACT_BATCH2_V4.md, "Selected 0.30 m ensemble summaries" (people, km, facilities). */
type ImpactRow = [people: number, roadKm: number, facilities: number];
export const A07_IMPACT: Record<EventId, Record<ScenarioId, Record<Lead, ImpactRow>>> = {
  '2015-12-02': {
    perfect_foresight_imerg: { 6: [0, 0, 0], 12: [0, 0, 0], 24: [34055.4, 96.93, 5.8], 48: [221131.2, 734.0, 39.2], 72: [110090.2, 341.05, 18.1] },
    rain_error_q10: { 6: [0, 0, 0], 12: [0, 0, 0], 24: [1152.8, 2.21, 0], 48: [201214.4, 657.93, 37.3], 72: [103134.2, 317.1, 15.8] },
    rain_error_q50: { 6: [0, 0, 0], 12: [0, 0, 0], 24: [34555.7, 100.66, 5.9], 48: [221113.9, 734.68, 39.2], 72: [110090.5, 341.28, 18.1] },
    rain_error_q90: { 6: [0, 0, 0], 12: [0, 0, 0], 24: [65451.2, 170.93, 13.2], 48: [229071.0, 767.56, 40.2], 72: [112126.5, 351.61, 18.9] },
    persistence_previous_day: { 6: [0, 0, 0], 12: [0, 0, 0], 24: [0, 0, 0], 48: [0, 0, 0], 72: [1441.0, 2.76, 0] },
  },
  '2021-11-13': {
    perfect_foresight_imerg: { 6: [0, 0, 0], 12: [0, 0, 0], 24: [1152.8, 2.21, 0], 48: [1152.8, 2.21, 0], 72: [864.6, 1.65, 0] },
    rain_error_q10: { 6: [0, 0, 0], 12: [0, 0, 0], 24: [0, 0, 0], 48: [0, 0, 0], 72: [0, 0, 0] },
    rain_error_q50: { 6: [0, 0, 0], 12: [576.4, 1.1, 0], 24: [1441.0, 2.76, 0], 48: [1441.0, 2.76, 0], 72: [1441.0, 2.76, 0] },
    rain_error_q90: { 6: [2655.3, 7.01, 0], 12: [7248.7, 26.11, 0], 24: [9574.5, 33.75, 0], 48: [25442.2, 75.62, 3.1], 72: [46812.3, 124.61, 9.5] },
    persistence_previous_day: { 6: [0, 0, 0], 12: [2947.9, 6.94, 0], 24: [106334.1, 291.42, 22.6], 48: [131754.4, 406.1, 24.2], 72: [135098.3, 421.71, 24.3] },
  },
  '2023-12-04': {
    perfect_foresight_imerg: { 6: [0, 0, 0], 12: [0, 0, 0], 24: [720.5, 1.38, 0], 48: [116434.2, 316.01, 23.6], 72: [122985.7, 389.98, 20.0] },
    rain_error_q10: { 6: [0, 0, 0], 12: [0, 0, 0], 24: [0, 0, 0], 48: [90277.6, 226.58, 20.0], 72: [115998.9, 364.27, 19.0] },
    rain_error_q50: { 6: [0, 0, 0], 12: [0, 0, 0], 24: [1008.7, 1.93, 0], 48: [117138.6, 318.85, 23.6], 72: [123001.1, 390.22, 20.0] },
    rain_error_q90: { 6: [0, 0, 0], 12: [0, 0, 0], 24: [9785.2, 28.25, 0.8], 48: [127516.9, 373.18, 24.5], 72: [125532.2, 402.88, 20.0] },
    persistence_previous_day: { 6: [0, 0, 0], 12: [0, 0, 0], 24: [0, 0, 0], 48: [0, 0, 0], 72: [0, 0, 0] },
  },
};

export const A07_CONTEXT = {
  source: 'docs/PHASE13_IMPACT_BATCH2_V4.md',
  threshold: 'Cells and road midpoints at or above 0.30 m simulated depth (assumed screen; 0.15 m and 0.50 m are sensitivity screens).',
  roadsAssessed: '405,601 of 566,307 road features (13,614.0 km) are midpoint-assessed; 160,706 are outside or unassessed on the model grid.',
  facilities: '1,492 mapped OSM facilities: 697 hospitals, 102 shelters, 693 schools/colleges as assumed candidate shelters.',
  population: 'Known WorldPop estimate in eligible cells: 4,836,739.3. 96,254 source cells are NoData and are not counted as zero. Every case is PARTIAL.',
  access72: [
    { event: '2015-12-02' as EventId, hospital: [422, 423, 1], shelter: [57, 66, 9], candidate: [409, 411, 2], loss: 0.0133 },
    { event: '2021-11-13' as EventId, hospital: [423, 423, 0], shelter: [66, 66, 0], candidate: [411, 411, 0], loss: 0 },
    { event: '2023-12-04' as EventId, hospital: [422, 423, 1], shelter: [57, 66, 9], candidate: [409, 411, 2], loss: 0.0133 },
  ],
};

/** A06 — docs/PHASE12_SIMULATION.md (Nov 2015 calibration pilot). */
export const A06_CALIBRATION = {
  source: 'docs/PHASE12_SIMULATION.md',
  rows: [
    { date: '2015-11-12', rain72: 86.381, prevalence: '6.89%', threshold: '0.05 m', roc: '0.673 ± 0.045', pr: '0.143 ± 0.043', brier: '0.064 ± 0.019', f1: '0.214 ± 0.085', iou: '0.122 ± 0.052' },
    { date: '2015-11-24', rain72: 66.7, prevalence: '8.27%', threshold: '0.01 m', roc: '0.698 ± 0.018', pr: '0.169 ± 0.057', brier: '0.078 ± 0.015', f1: '0.241 ± 0.077', iou: '0.139 ± 0.048' },
  ],
  thresholds: [0.01, 0.03, 0.05, 0.1, 0.15, 0.3, 0.5],
  area12: [363.96, 204.48, 126.72, 63.36, 38.88, 14.4, 2.88],
  area24: [282.6, 119.16, 69.84, 37.08, 24.12, 10.08, 1.44],
  massBalance: 'Largest relative mass-balance error 0.264% (12 Nov) and 0.203% (24 Nov); all 40 runs finite and non-negative.',
};

/** A09 — docs/ROUTING_BATCH2.md, comparison results over 54 route records per method. */
export const A09_METHODS = [
  { method: 'Static free-flow', withPath: 54, computable: 0, failure: null, truth: '0 / 0', time: null, exposure: null },
  { method: 'Current flood-aware', withPath: 18, computable: 18, failure: 0.1316, truth: '2 / 18', time: 1409.31, exposure: 254.04 },
  { method: 'Horizon-aware snapshot', withPath: 18, computable: 18, failure: 0.1316, truth: '2 / 18', time: 1412.42, exposure: 180.99 },
  { method: 'Uncertainty-aware', withPath: 15, computable: 15, failure: 0, truth: '0 / 15', time: 1355.84, exposure: 62.0 },
] as const;

export const A09_CONTEXT = {
  source: 'docs/ROUTING_BATCH2.md',
  graph: '508,854 nodes / 1,071,656 directed arcs; 768,688 arcs (71.73%) mapped to a depth cell, 302,968 (28.27%) unassessed.',
  design: 'Six sampled graph node pairs (not named hospitals or shelters) × 3 events × 6/24/72 h snapshots; member 20 hidden as simulated truth.',
};

/** A21 — docs/ROUTING_THREE_STATE_BATCH3.md. */
export const A21 = {
  source: 'docs/ROUTING_THREE_STATE_BATCH3.md',
  primaryCases: 108000,
  failClosed: 14148,
  conditional: 92750,
  noPath: 1102,
  anyRoute: 106898,
  coverage: { full: 6300, partial: 99000, absent: 2700 },
  intervals: [
    { label: 'Fail-closed route availability', range: '0.081 – 0.183' },
    { label: 'Three-state availability incl. conditional', range: '0.980 – 0.997' },
    { label: 'Conditional-route share', range: '0.805 – 0.911' },
  ],
  verificationQueue: [
    { edges: 1, covered: 20404 },
    { edges: 5, covered: 43603 },
    { edges: 10, covered: 54138 },
    { edges: 25, covered: 77552 },
    { edges: 50, covered: 92750 },
  ],
  queueNote: 'All 1,470 prioritised unknown arcs stayed UNKNOWN in all 900 saved snapshots, so no passable/blocked status was imposed.',
  stability: [
    { comparison: 'Member vs member 12', method: 'Fail-closed', paired: 12724, identical: 12518, changed: 206 },
    { comparison: 'Member vs member 12', method: 'Three-state', paired: 96186, identical: 84647, changed: 11539 },
    { comparison: 'Scenario vs perfect foresight', method: 'Fail-closed', paired: 10695, identical: 10010, changed: 685 },
    { comparison: 'Scenario vs perfect foresight', method: 'Three-state', paired: 80996, identical: 59807, changed: 21189 },
  ],
  novelty: 'Close prior work already covers uncertain road accessibility and flood-aware routing. Novelty and real-world benefit remain unproven.',
};

/** A10 — docs/SHELTER_ALLOCATION_BATCH2.md (final run batch2_v3). */
export const A10 = {
  source: 'docs/SHELTER_ALLOCATION_BATCH2.md',
  candidates: '102 OSM shelters, 559 schools and 134 colleges inside the grid. Schools and colleges are candidates by assumption; capacities (100 / 250 / 500 people) are hypothetical.',
  demand: 4836739.34,
  factors: [
    { factor: 0.5, capacity: 108475, served: 68546.65, unserved: 4768192.69, unreachable: 1733133.92 },
    { factor: 1.0, capacity: 216950, served: 136975.33, unserved: 4699764.01, unreachable: 1733133.92 },
    { factor: 2.0, capacity: 433900, served: 273757.83, unserved: 4562981.51, unreachable: 1733133.92 },
  ],
};

/** A11 — docs/PRIORITY_ZONES_BATCH2.md. */
export const A11 = {
  source: 'docs/PRIORITY_ZONES_BATCH2.md',
  products: [
    { name: 'Hazard', detail: '75 cases × 2,430 cells: simulated mean depth, member p05/p95 and the share of members at/above the 0.30 m screen.' },
    { name: 'Population exposure', detail: 'Known WorldPop estimate per case; population coverage 0.8986. Exposure only, not vulnerability.' },
    { name: 'Facility access loss', detail: 'Counts and access-loss fractions kept separate for hospitals, shelters and candidate shelters.' },
  ],
  rule: 'No vulnerability proxy, composite score, weighting, ranking or official priority zone was created.',
};

/** A13 — docs/DECISION_LAB_BATCH2.md. */
export const A13 = {
  source: 'docs/DECISION_LAB_BATCH2.md',
  h2: [
    { event: '2015-12-02' as EventId, m12: 0.00549, median: 0.004458, coverage: 79.69, width: 0.010191 },
    { event: '2021-11-13' as EventId, m12: 0.002768, median: 0.002841, coverage: 85.33, width: 0.005909 },
    { event: '2023-12-04' as EventId, m12: 0.004162, median: 0.003695, coverage: 82.44, width: 0.007809 },
  ],
  h2Summary: 'Ensemble median beat the deterministic member in 24, tied in 8 and lost in 43 of 75 cases. The nominal 90% band covered the held-out member in 82.48% of cells (7.52 points below nominal).',
  h3: [
    { outcome: 'Modelled route-failure fraction', record: '0 / 15 / 0 / 39', diff: '0.000', interval: '[0.000, 0.000]' },
    { outcome: 'Travel time (s)', record: '3 / 12 / 0 / 39', diff: '−0.010 s', interval: '[−0.017, 0.000] s' },
    { outcome: 'Depth-distance exposure (m²)', record: '1 / 12 / 2 / 39', diff: '−0.025 m²', interval: '[−0.076, +0.001] m²' },
    { outcome: 'Assessed-edge coverage', record: '0 / 15 / 0 / 39', diff: '0.000', interval: '[0.000, 0.000]' },
  ],
  h4: 'Horizon-aware minus current-state travel time averaged +3.314 s (descriptive interval −0.017 to +9.970 s): 3 better, 12 tied, 1 worse, 38 missing.',
  h5: [
    { check: 'Departure ±1 hour', status: 'Unavailable', detail: 'Snapshots exist only at 6/12/24/48/72 h; no interpolation or new route search was done.' },
    { check: 'Bridge closure', status: 'Path invalidation only', detail: 'Edge 64052 appears in 9 saved static routes. Reroutes without it were not computed.' },
    { check: 'Shelter unavailable', status: 'Allocation withdrawal only', detail: 'OSM shelter 28275720 held 63,000 people-model-estimate across 180 records; not redistributed.' },
  ],
};

/** Track B — docs/trackb/BACKTEST_REPORT.md and BACKTEST_RESULTS.json. */
export const TRACKB_BACKTEST = {
  source: 'docs/trackb/BACKTEST_REPORT.md',
  target: 'Future storage reaching 80% of current published capacity within 7 days (DEFAULT, to confirm). Not flood occurrence or a release decision.',
  split: 'Train 2004–2014 · calibrate 2015–2017 · held-out test 2018–2020',
  rows: [
    { entity: 'Poondi', prevalence: 0.006, rule: '0.333 / 0.957 / 0.040', persistence: '0.000', rain: '0.000', logistic: '0.000', gb: '0.000', brier: '0.007' },
    { entity: 'Cholavaram', prevalence: 0.0, rule: '— / 1.000 / 0.000', persistence: '—', rain: '—', logistic: '—', gb: '—', brier: '0.000' },
    { entity: 'Red Hills', prevalence: 0.179, rule: '0.995 / 0.442 / 0.556', persistence: '0.875', rain: '0.000', logistic: '0.721', gb: '0.905', brier: '0.016' },
    { entity: 'Chembarambakkam', prevalence: 0.015, rule: '0.875 / 0.741 / 0.250', persistence: '0.375', rain: '0.000', logistic: '0.875', gb: '0.625', brier: '0.006' },
    { entity: 'Combined', prevalence: 0.006, rule: '0.500 / 0.963 / 0.036', persistence: '0.000', rain: '0.000', logistic: '0.333', gb: '0.333', brier: '0.003' },
  ],
  caseStudy: '2015 legacy screen: 11 flags, five on 20–24 Nov before the 1 Dec reference date (earliest lead 11 days). Six outside-window flags are not validated false alarms.',
  limits: 'Capacity histories are not verified, rainfall units are INFERRED, daily storage ends 2020-12-03 and releases are unobserved.',
};

export type ReplayLevel = 'Watch' | 'Warning' | 'Critical';
/** docs/trackb/replay_2015_alerts.jsonl — 50 REPLAY alerts (reservoir, date, level, storage %, 3-day rain). */
export const TRACKB_REPLAY: [string, string, ReplayLevel, number, number][] = [
  ['CHEMBARAMBAKKAM', '2015-11-20', 'Warning', 89.7, 58.0], ['POONDI', '2015-11-20', 'Warning', 85.0, 116.0], ['REDHILLS', '2015-11-20', 'Watch', 73.2, 14.0],
  ['CHEMBARAMBAKKAM', '2015-11-21', 'Warning', 87.7, 73.0], ['POONDI', '2015-11-21', 'Warning', 84.5, 132.0], ['REDHILLS', '2015-11-21', 'Watch', 78.9, 52.0],
  ['CHEMBARAMBAKKAM', '2015-11-22', 'Warning', 87.0, 92.0], ['POONDI', '2015-11-22', 'Warning', 85.1, 128.8], ['REDHILLS', '2015-11-22', 'Warning', 84.5, 90.0],
  ['CHEMBARAMBAKKAM', '2015-11-23', 'Warning', 88.4, 81.0], ['CHOLAVARAM', '2015-11-23', 'Watch', 60.5, 128.0], ['POONDI', '2015-11-23', 'Warning', 84.4, 90.8], ['REDHILLS', '2015-11-23', 'Warning', 85.8, 121.0],
  ['CHEMBARAMBAKKAM', '2015-11-24', 'Warning', 88.4, 175.0], ['CHOLAVARAM', '2015-11-24', 'Watch', 64.5, 110.0], ['POONDI', '2015-11-24', 'Warning', 86.4, 127.8], ['REDHILLS', '2015-11-24', 'Warning', 87.0, 100.0],
  ['CHEMBARAMBAKKAM', '2015-11-25', 'Warning', 87.5, 153.0], ['POONDI', '2015-11-25', 'Warning', 82.6, 118.0], ['REDHILLS', '2015-11-25', 'Warning', 86.5, 62.0],
  ['CHEMBARAMBAKKAM', '2015-11-26', 'Warning', 86.1, 109.0], ['POONDI', '2015-11-26', 'Warning', 81.3, 53.0], ['REDHILLS', '2015-11-26', 'Watch', 85.6, 17.0],
  ['CHEMBARAMBAKKAM', '2015-11-27', 'Watch', 85.6, 0.0], ['POONDI', '2015-11-27', 'Watch', 82.6, 0.0], ['REDHILLS', '2015-11-27', 'Watch', 84.1, 0.0],
  ['CHEMBARAMBAKKAM', '2015-11-28', 'Watch', 85.7, 0.0], ['POONDI', '2015-11-28', 'Warning', 84.0, 0.0], ['REDHILLS', '2015-11-28', 'Watch', 83.7, 0.0],
  ['CHEMBARAMBAKKAM', '2015-11-29', 'Watch', 85.9, 3.0], ['POONDI', '2015-11-29', 'Warning', 85.0, 0.1], ['REDHILLS', '2015-11-29', 'Watch', 84.5, 4.0],
  ['CHEMBARAMBAKKAM', '2015-11-30', 'Watch', 85.8, 20.0], ['POONDI', '2015-11-30', 'Watch', 83.0, 12.1], ['REDHILLS', '2015-11-30', 'Warning', 84.6, 48.0],
  ['CHEMBARAMBAKKAM', '2015-12-01', 'Watch', 86.2, 37.0], ['POONDI', '2015-12-01', 'Warning', 85.0, 86.7], ['REDHILLS', '2015-12-01', 'Warning', 84.5, 75.0],
  ['CHEMBARAMBAKKAM', '2015-12-02', 'Critical', 93.2, 509.0], ['CHOLAVARAM', '2015-12-02', 'Watch', 74.4, 359.0], ['POONDI', '2015-12-02', 'Warning', 86.9, 276.0], ['REDHILLS', '2015-12-02', 'Critical', 95.9, 391.0],
  ['CHEMBARAMBAKKAM', '2015-12-03', 'Warning', 84.9, 527.0], ['CHOLAVARAM', '2015-12-03', 'Warning', 82.9, 353.0], ['POONDI', '2015-12-03', 'Warning', 82.6, 273.2], ['REDHILLS', '2015-12-03', 'Critical', 90.8, 370.4],
  ['CHEMBARAMBAKKAM', '2015-12-04', 'Warning', 85.9, 522.0], ['CHOLAVARAM', '2015-12-04', 'Warning', 81.4, 335.0], ['POONDI', '2015-12-04', 'Warning', 82.6, 206.4], ['REDHILLS', '2015-12-04', 'Warning', 82.7, 356.4],
];

export const TRACKB_RULE = 'trackb-rule-v1: Critical at storage ≥ 90%; Warning at ≥ 80% with a 3-day rise or 3-day rain above its p90; Watch at ≥ 70% or a 1-day rise with rain above p75. Storage % uses current published capacity (historical capacity not verified).';

/** Product status snapshot — docs/master/STATE.json (task and gate records). */
export const PRODUCT_STATUS = [
  { id: 'A05', name: 'Forecast / hindcast scenarios', status: 'done_with_caveats', report: 'docs/PHASE11_FORECAST_BATCH2.md' },
  { id: 'A06', name: 'Local-inertial flood simulation', status: 'done_with_caveats', report: 'docs/PHASE12_SIMULATION.md' },
  { id: 'A07', name: 'Ensemble impact analysis', status: 'done_with_caveats', report: 'docs/PHASE13_IMPACT_BATCH2_V4.md' },
  { id: 'A09', name: 'Routing decision comparison', status: 'done_with_caveats', report: 'docs/ROUTING_BATCH2.md' },
  { id: 'A10', name: 'Shelter allocation', status: 'done_with_caveats', report: 'docs/SHELTER_ALLOCATION_BATCH2.md' },
  { id: 'A11', name: 'Hazard, exposure and access-loss layers', status: 'done_with_caveats', report: 'docs/PRIORITY_ZONES_BATCH2.md' },
  { id: 'A13', name: 'Decision lab (H2–H5)', status: 'done_with_caveats', report: 'docs/DECISION_LAB_BATCH2.md' },
  { id: 'A20', name: '3D scenario visualization readiness', status: 'done_with_caveats', report: 'docs/FLOOD_3D_SCENARIO_READINESS.md' },
  { id: 'A21', name: 'Three-state evidence-aware routing', status: 'done_with_caveats', report: 'docs/ROUTING_THREE_STATE_BATCH3.md' },
  { id: 'B44', name: 'CFM-DSS reservoir snapshot API', status: 'done_with_caveats', report: 'docs/trackb/CFM_RESERVOIR_API.md' },
  { id: 'B45', name: 'Connect CFM reservoir snapshots to the UI', status: 'done_with_caveats', report: 'docs/master/CR-018_LIVE_PROTOTYPE_INTEGRATION.md' },
  { id: 'B40', name: 'Authorized IMD rainfall connector', status: 'blocked_prerequisite', report: 'docs/master/STATE.json' },
  { id: 'A23', name: 'Spatial Open-Meteo rainfall forcing', status: 'running', report: 'docs/master/STATE.json' },
];

export const GATES_SNAPSHOT = 'G1–G6 are not ready in docs/master/STATE.json; no contract freeze or operational use is implied.';
