export const professorDemoFlow = [
  { id: 'scenario', label: 'Choose a scenario', section: 'overview', action: 'focus-scenario' },
  { id: 'time-steps', label: 'Inspect local demo steps', section: 'twin', action: 'navigate' },
  { id: 'impacts', label: 'View impacts', section: 'impacts', action: 'navigate' },
  { id: 'response', label: 'Compare response options', section: 'response', action: 'navigate' },
  { id: 'what-if', label: 'Explore a what-if', section: 'what-if', action: 'navigate' },
] as const;

export type ProfessorDemoStepId = typeof professorDemoFlow[number]['id'];
export type ProfessorDemoSection = typeof professorDemoFlow[number]['section'];

export function fixtureBarHeight(value: number, values: number[]): string {
  return `${value / Math.max(...values, 1) * 34}px`;
}

export function activeProfessorStep(section: string): ProfessorDemoStepId | null {
  return professorDemoFlow.find((step) => step.section === section)?.id ?? null;
}

export function activateProfessorStep(
  stepId: ProfessorDemoStepId,
  handlers: { navigate: (section: ProfessorDemoSection) => void; focusScenario: () => void },
): void {
  const step = professorDemoFlow.find((item) => item.id === stepId);
  if (!step) return;
  handlers.navigate(step.section);
  if (step.action === 'focus-scenario') handlers.focusScenario();
}
