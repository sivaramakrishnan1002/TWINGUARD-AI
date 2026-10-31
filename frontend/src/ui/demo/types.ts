export type DemoSourceMode = 'DEMO' | 'SIMULATED';
export type DemoStateKind = 'value' | 'unknown' | 'unavailable' | 'zero' | 'dry' | 'nodata';

export interface DemoValue<T = string | number> {
  kind: DemoStateKind;
  value?: T;
  explanation: string;
}

export interface DemoProvenance {
  sourceMode: DemoSourceMode;
  source: string;
  runId: string;
  version: string;
  timeBasis: string;
  timestampLabel: string;
  units: string[];
  uncertainty: string;
  limitation: string;
}

export interface DemoFrame {
  id: string;
  label: string;
  visualLevel: number;
  waterPath3d: string;
  waterPath2d: string;
  illustrativeOnly: true;
}

export interface DemoReservoir {
  id: string;
  name: string;
  storageMcft: number | null;
  capacityMcft: number | null;
  releaseCusecs: number | null;
  alertLabel: string;
  history: number[];
}

export interface DemoImpactSummary {
  populationExposure: number;
  facilities: number;
  roadSegments: number;
  hazardCoverage: string;
  roadAccess: string;
  note: string;
}

export interface DemoRoute {
  id: string;
  name: string;
  mode: string;
  minutes: number;
  distanceKm: number;
  topologicalReachability: 'connected' | 'disconnected';
  hazardAssessment: 'unknown';
  note: string;
}

export interface DemoShelter {
  id: string;
  name: string;
  designation: 'candidate';
  demoSlots: number;
  status: 'simulated';
  note: string;
}

export interface DemoScenario {
  id: string;
  name: string;
  description: string;
  provenance: DemoProvenance;
  frames: DemoFrame[];
  reservoirs: DemoReservoir[];
  impacts: DemoImpactSummary;
  routes: DemoRoute[];
  shelters: DemoShelter[];
}

export interface WhatIfInputs {
  rainfallMm: number;
  reservoirId: string;
  reservoirReleaseCusecs: number;
  unavailableShelterId: string | null;
}

export interface DemoWorkspace {
  scenario: DemoScenario;
  frameIndex: number;
  frame: DemoFrame;
  adjustedFrame: DemoFrame;
  inputs: WhatIfInputs;
  adjustedVisualLevel: number;
  adjustedImpact: DemoImpactSummary;
  adjustedRoutes: DemoRoute[];
  baseline: DemoImpactSummary;
}

export interface ProductExperienceAdapter {
  listScenarios(): DemoScenario[];
  getWorkspace(scenarioId: string, frameIndex: number, inputs: WhatIfInputs): DemoWorkspace;
  getInitialInputs(scenarioId: string): WhatIfInputs;
}
