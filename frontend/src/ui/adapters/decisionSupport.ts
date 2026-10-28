import type {
  CounterfactualRequest,
  ImpactResult,
  PriorityZoneSummary,
  RouteRequest,
  RouteResult,
  ShelterSummary,
} from '../types';

export type DecisionResult<T> =
  | { status: 'available'; data: T }
  | { status: 'unavailable'; reason: string };

/** UI-owned seam for future project APIs; no endpoint or network call is configured. */
export interface DecisionSupportAdapter {
  readonly availability: DecisionResult<null>;
  getImpactResult(runId: number, validAtUtc: string): Promise<DecisionResult<ImpactResult>>;
  requestRoute(request: RouteRequest): Promise<DecisionResult<RouteResult>>;
  listShelters(runId: number, validAt: string): Promise<DecisionResult<ShelterSummary[]>>;
  getPriorityZones(runId: number, validAt: string): Promise<DecisionResult<PriorityZoneSummary[]>>;
  evaluateCounterfactual(request: CounterfactualRequest): Promise<DecisionResult<unknown>>;
}

const reason = 'Impact, routing, shelter, priority-zone, and scenario services are not available to the UI.';

export const unavailableDecisionSupportAdapter: DecisionSupportAdapter = {
  availability: { status: 'unavailable', reason },
  async getImpactResult() { return { status: 'unavailable', reason }; },
  async requestRoute() { return { status: 'unavailable', reason }; },
  async listShelters() { return { status: 'unavailable', reason }; },
  async getPriorityZones() { return { status: 'unavailable', reason }; },
  async evaluateCounterfactual() { return { status: 'unavailable', reason }; },
};
