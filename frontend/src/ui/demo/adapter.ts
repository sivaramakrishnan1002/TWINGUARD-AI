import { DEMO_SCENARIOS } from './fixtures';
import type { DemoImpactSummary, DemoRoute, DemoScenario, ProductExperienceAdapter, WhatIfInputs } from './types';

export const defaultWhatIfInputs: WhatIfInputs = {
  rainfallMm: 40,
  reservoirId: 'demo-north',
  reservoirReleaseCusecs: 180,
  unavailableShelterId: null,
};

export function advanceDemoFrame(current: number, direction: -1 | 1, frameCount: number, wrap = false): number {
  if (frameCount <= 0) return 0;
  const next = current + direction;
  if (wrap) return (next + frameCount) % frameCount;
  return Math.min(frameCount - 1, Math.max(0, next));
}

export function setDemoShelterAvailability(inputs: WhatIfInputs, shelterId: string, unavailable: boolean): WhatIfInputs {
  return { ...inputs, unavailableShelterId: unavailable ? shelterId : inputs.unavailableShelterId === shelterId ? null : inputs.unavailableShelterId };
}

function clamp(value: number, low: number, high: number): number {
  return Math.min(high, Math.max(low, value));
}

export function evaluateDemoImpact(base: DemoImpactSummary, inputs: WhatIfInputs): DemoImpactSummary {
  const rainfallFactor = inputs.rainfallMm / 40;
  const releaseFactor = inputs.reservoirReleaseCusecs / 180;
  return {
    ...base,
    populationExposure: Math.round(base.populationExposure * (0.85 + rainfallFactor * 0.15 + releaseFactor * 0.08)),
    facilities: Math.max(0, Math.round(base.facilities * (0.9 + rainfallFactor * 0.1))),
    roadSegments: Math.max(0, Math.round(base.roadSegments * (0.8 + rainfallFactor * 0.2))),
    note: 'DEMO calculation from synthetic sliders; not a model or an observed impact.',
  };
}

export function evaluateDemoRoutes(routes: DemoRoute[], inputs: WhatIfInputs): DemoRoute[] {
  const adjustment = Math.round((inputs.rainfallMm - 40) / 10) + Math.round((inputs.reservoirReleaseCusecs - 180) / 100);
  return routes.map((route, index) => route.topologicalReachability === 'disconnected'
    ? route
    : { ...route, minutes: Math.max(1, route.minutes + adjustment + index), note: 'DEMO travel-time arithmetic only; route hazards remain unknown.' });
}

function findScenario(scenarioId: string): DemoScenario {
  return DEMO_SCENARIOS.find((scenario) => scenario.id === scenarioId) ?? DEMO_SCENARIOS[0];
}

export const demoAdapter: ProductExperienceAdapter = {
  listScenarios: () => DEMO_SCENARIOS,
  getInitialInputs: () => ({ ...defaultWhatIfInputs }),
  getWorkspace(scenarioId, frameIndex, inputs) {
    const scenario = findScenario(scenarioId);
    const safeIndex = clamp(Math.trunc(frameIndex), 0, scenario.frames.length - 1);
    const safeInputs = {
      rainfallMm: clamp(Math.round(inputs.rainfallMm), 0, 120),
      reservoirId: scenario.reservoirs.some((reservoir) => reservoir.id === inputs.reservoirId) ? inputs.reservoirId : scenario.reservoirs[0].id,
      reservoirReleaseCusecs: clamp(Math.round(inputs.reservoirReleaseCusecs), 0, 600),
      unavailableShelterId: inputs.unavailableShelterId,
    };
    const adjustedVisualLevel = clamp(scenario.frames[safeIndex].visualLevel + Math.round((safeInputs.rainfallMm - 40) / 40), 1, 4);
    const shapeFrame = scenario.frames.find((frame) => frame.visualLevel === adjustedVisualLevel) ?? scenario.frames[safeIndex];
    return {
      scenario,
      frameIndex: safeIndex,
      frame: scenario.frames[safeIndex],
      adjustedFrame: { ...scenario.frames[safeIndex], visualLevel: adjustedVisualLevel, waterPath3d: shapeFrame.waterPath3d, waterPath2d: shapeFrame.waterPath2d },
      inputs: safeInputs,
      adjustedVisualLevel,
      adjustedImpact: evaluateDemoImpact(scenario.impacts, safeInputs),
      adjustedRoutes: evaluateDemoRoutes(scenario.routes, safeInputs),
      baseline: scenario.impacts,
    };
  },
};
