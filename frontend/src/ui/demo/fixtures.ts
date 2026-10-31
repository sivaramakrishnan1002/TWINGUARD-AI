import type { DemoScenario } from './types';

/** All measurements below are synthetic teaching values, not Chennai observations. */
export const DEMO_SCENARIOS: DemoScenario[] = [
  {
    id: 'demo-monsoon',
    name: 'Monsoon tabletop · DEMO',
    description: 'Illustrative scenario for learning the interface; not a historical event.',
    provenance: {
      sourceMode: 'DEMO',
      source: 'Central TwinGuard UI demo fixture set',
      runId: 'demo-run-monsoon-01',
      version: 'ui-demo-v1',
      timeBasis: 'Synthetic elapsed steps; no calendar date or observation time',
      timestampLabel: 'Demo clock · T+0 to T+6 hours',
      units: ['rainfall: mm (synthetic)', 'storage: mcft (synthetic)', 'release: cusecs (synthetic)'],
      uncertainty: 'Illustrative inputs only; no calibrated uncertainty estimate.',
      limitation: 'Not a forecast, warning, physical hydraulic simulation, or emergency guidance.',
    },
    frames: [
      { id: 't0', label: 'T+0 h · setup', visualLevel: 1, waterPath3d: 'M0 244 C96 226 133 249 205 238 S324 228 420 246 L420 276 L0 276 Z', waterPath2d: 'M18 160 C90 132 145 172 214 149 S332 150 402 134 L402 205 C330 221 267 196 200 216 S79 197 18 224 Z', illustrativeOnly: true },
      { id: 't1', label: 'T+2 h · demo change', visualLevel: 2, waterPath3d: 'M0 225 C75 204 126 238 199 218 S331 211 420 232 L420 276 L0 276 Z', waterPath2d: 'M18 141 C88 111 143 158 214 128 S332 130 402 112 L402 221 C330 236 267 204 200 229 S79 207 18 244 Z', illustrativeOnly: true },
      { id: 't2', label: 'T+4 h · demo change', visualLevel: 3, waterPath3d: 'M0 205 C84 184 129 221 201 199 S329 190 420 214 L420 276 L0 276 Z', waterPath2d: 'M18 122 C88 92 143 138 214 108 S332 111 402 92 L402 238 C330 250 267 213 200 241 S79 218 18 260 Z', illustrativeOnly: true },
      { id: 't3', label: 'T+6 h · demo change', visualLevel: 4, waterPath3d: 'M0 184 C84 165 131 202 201 180 S329 171 420 193 L420 276 L0 276 Z', waterPath2d: 'M18 104 C88 74 143 120 214 90 S332 93 402 74 L402 253 C330 264 267 224 200 253 S79 229 18 270 Z', illustrativeOnly: true },
    ],
    reservoirs: [
      { id: 'demo-north', name: 'North Basin (demo)', storageMcft: 41, capacityMcft: 80, releaseCusecs: 220, alertLabel: 'Demo watch state', history: [34, 37, 39, 41] },
      { id: 'demo-west', name: 'West Basin (demo)', storageMcft: 0, capacityMcft: 65, releaseCusecs: 0, alertLabel: 'Demo baseline state', history: [0, 0, 0, 0] },
      { id: 'demo-unknown', name: 'Unreported Basin (unknown)', storageMcft: null, capacityMcft: null, releaseCusecs: null, alertLabel: 'Unknown', history: [] },
    ],
    impacts: { populationExposure: 860, facilities: 7, roadSegments: 4, hazardCoverage: 'DEMO footprint only', roadAccess: 'DEMO connectivity only', note: 'Fictional counts for interface demonstration; not a census or impact estimate.' },
    routes: [
      { id: 'route-a', name: 'Demo route A', mode: 'Vehicle', minutes: 24, distanceKm: 8.2, topologicalReachability: 'connected', hazardAssessment: 'unknown', note: 'Synthetic graph path; hazard exposure is unknown.' },
      { id: 'route-b', name: 'Demo route B', mode: 'Vehicle', minutes: 31, distanceKm: 10.4, topologicalReachability: 'connected', hazardAssessment: 'unknown', note: 'Synthetic alternate path; hazard exposure is unknown.' },
      { id: 'route-c', name: 'Demo route C', mode: 'Walking', minutes: 0, distanceKm: 0, topologicalReachability: 'disconnected', hazardAssessment: 'unknown', note: 'Explicit zero-length test case; does not mean a usable route exists.' },
    ],
    shelters: [
      { id: 'shelter-a', name: 'Demo candidate North', designation: 'candidate', demoSlots: 120, status: 'simulated', note: 'Synthetic slot count; location and operation are not verified.' },
      { id: 'shelter-b', name: 'Demo candidate Central', designation: 'candidate', demoSlots: 75, status: 'simulated', note: 'Synthetic slot count; location and operation are not verified.' },
    ],
  },
  {
    id: 'demo-cloudburst',
    name: 'Cloudburst tabletop · DEMO',
    description: 'A second synthetic scenario to exercise scenario selection and comparison.',
    provenance: {
      sourceMode: 'SIMULATED', source: 'Central TwinGuard UI demo fixture set', runId: 'demo-run-cloudburst-01', version: 'ui-demo-v1',
      timeBasis: 'Synthetic elapsed steps; no calendar date or observation time', timestampLabel: 'Demo clock · T+0 to T+6 hours',
      units: ['rainfall: mm (synthetic)', 'storage: mcft (synthetic)', 'release: cusecs (synthetic)'],
      uncertainty: 'Illustrative inputs only; no calibrated uncertainty estimate.',
      limitation: 'Not a forecast, warning, physical hydraulic simulation, or emergency guidance.',
    },
    frames: [
      { id: 't0', label: 'T+0 h · setup', visualLevel: 1, waterPath3d: 'M0 244 C96 226 133 249 205 238 S324 228 420 246 L420 276 L0 276 Z', waterPath2d: 'M18 160 C90 132 145 172 214 149 S332 150 402 134 L402 205 C330 221 267 196 200 216 S79 197 18 224 Z', illustrativeOnly: true },
      { id: 't1', label: 'T+2 h · demo change', visualLevel: 2, waterPath3d: 'M0 220 C76 202 129 233 199 214 S331 207 420 229 L420 276 L0 276 Z', waterPath2d: 'M18 136 C88 105 143 151 214 123 S332 126 402 105 L402 224 C330 239 267 206 200 232 S79 210 18 248 Z', illustrativeOnly: true },
      { id: 't2', label: 'T+4 h · demo change', visualLevel: 3, waterPath3d: 'M0 197 C82 177 131 214 201 192 S329 184 420 207 L420 276 L0 276 Z', waterPath2d: 'M18 115 C88 84 143 130 214 100 S332 103 402 83 L402 243 C330 255 267 216 200 245 S79 221 18 264 Z', illustrativeOnly: true },
      { id: 't3', label: 'T+6 h · demo change', visualLevel: 4, waterPath3d: 'M0 177 C84 159 131 195 201 173 S329 165 420 187 L420 276 L0 276 Z', waterPath2d: 'M18 98 C88 68 143 114 214 84 S332 87 402 67 L402 258 C330 270 267 229 200 258 S79 234 18 273 Z', illustrativeOnly: true },
    ],
    reservoirs: [
      { id: 'demo-north', name: 'North Basin (demo)', storageMcft: 53, capacityMcft: 80, releaseCusecs: 310, alertLabel: 'Demo watch state', history: [42, 46, 50, 53] },
      { id: 'demo-west', name: 'West Basin (demo)', storageMcft: 18, capacityMcft: 65, releaseCusecs: 90, alertLabel: 'Demo baseline state', history: [11, 13, 16, 18] },
      { id: 'demo-unknown', name: 'Unreported Basin (unknown)', storageMcft: null, capacityMcft: null, releaseCusecs: null, alertLabel: 'Unknown', history: [] },
    ],
    impacts: { populationExposure: 1240, facilities: 11, roadSegments: 6, hazardCoverage: 'DEMO footprint only', roadAccess: 'DEMO connectivity only', note: 'Fictional counts for interface demonstration; not a census or impact estimate.' },
    routes: [
      { id: 'route-a', name: 'Demo route A', mode: 'Vehicle', minutes: 29, distanceKm: 9.1, topologicalReachability: 'connected', hazardAssessment: 'unknown', note: 'Synthetic graph path; hazard exposure is unknown.' },
      { id: 'route-b', name: 'Demo route B', mode: 'Vehicle', minutes: 38, distanceKm: 12.6, topologicalReachability: 'connected', hazardAssessment: 'unknown', note: 'Synthetic alternate path; hazard exposure is unknown.' },
      { id: 'route-c', name: 'Demo route C', mode: 'Walking', minutes: 0, distanceKm: 0, topologicalReachability: 'disconnected', hazardAssessment: 'unknown', note: 'Explicit zero-length test case; does not mean a usable route exists.' },
    ],
    shelters: [
      { id: 'shelter-a', name: 'Demo candidate North', designation: 'candidate', demoSlots: 120, status: 'simulated', note: 'Synthetic slot count; location and operation are not verified.' },
      { id: 'shelter-b', name: 'Demo candidate Central', designation: 'candidate', demoSlots: 75, status: 'simulated', note: 'Synthetic slot count; location and operation are not verified.' },
    ],
  },
];

export const DEMO_STATE_EXAMPLES = {
  unknown: { kind: 'unknown', explanation: 'No value was supplied.' },
  unavailable: { kind: 'unavailable', explanation: 'No service is connected in DEMO mode.' },
  zero: { kind: 'zero', value: 0, explanation: 'A known numeric zero; it is not missing.' },
  dry: { kind: 'dry', explanation: 'Explicitly classified dry in this synthetic fixture.' },
  nodata: { kind: 'nodata', explanation: 'NoData coverage; unknown, not dry.' },
} as const;
