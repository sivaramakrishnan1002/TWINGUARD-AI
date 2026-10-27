export type StatusTone = 'neutral' | 'warning' | 'positive' | 'derived' | 'assumption' | 'simulated' | 'replay' | 'live' | 'error';

const markerByTone: Record<StatusTone, string> = {
  neutral: '—', warning: '!', positive: '✓', derived: 'ƒ', assumption: '!', simulated: '∿', replay: '↺', live: '●', error: '×',
};

export function StatusBadge({ tone, label }: { tone: StatusTone; label: string }) {
  return <span className={`status-badge status-badge--${tone}`}><span className="status-badge-marker" aria-hidden="true">{markerByTone[tone]}</span><span>{label}</span></span>;
}
