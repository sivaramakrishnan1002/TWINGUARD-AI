import type { ReactNode } from 'react';
import { DEPTH_CLASSES } from './DepthMap';
import { LEADS, type Lead } from '../evidence/reports';

export function Card({ title, eyebrow, source, actions, children, className = '', id }: { title: string; eyebrow?: string; source?: string; actions?: ReactNode; children: ReactNode; className?: string; id?: string }) {
  const headingId = id ?? `card-${title.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`;
  return (
    <section className={`tg-card ${className}`} aria-labelledby={headingId}>
      <header className="tg-card__head">
        <div>
          {eyebrow && <span className="tg-eyebrow">{eyebrow}</span>}
          <h2 id={headingId}>{title}</h2>
        </div>
        {actions && <div className="tg-card__actions">{actions}</div>}
      </header>
      <div className="tg-card__body">{children}</div>
      {source && <footer className="tg-card__source"><span aria-hidden="true">⎘</span> Source: <code>{source}</code></footer>}
    </section>
  );
}

export function Kpi({ label, value, unit, note, tone }: { label: string; value: string; unit?: string; note?: string; tone?: 'water' | 'warn' | 'ok' | 'muted' }) {
  return (
    <div className={`tg-kpi${tone ? ` tg-kpi--${tone}` : ''}`}>
      <span className="tg-kpi__label">{label}</span>
      <strong className="tg-kpi__value">{value}{unit && <small> {unit}</small>}</strong>
      {note && <span className="tg-kpi__note">{note}</span>}
    </div>
  );
}

export function Tag({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'neutral' | 'sim' | 'warn' | 'ok' | 'bad' | 'info' }) {
  return <span className={`tg-tag tg-tag--${tone}`}>{children}</span>;
}

export function Segmented<T extends string | number>({ label, value, options, onChange }: { label: string; value: T; options: { value: T; label: string }[]; onChange: (v: T) => void }) {
  return (
    <div className="tg-seg" role="group" aria-label={label}>
      {options.map((o) => <button type="button" key={String(o.value)} aria-pressed={o.value === value} onClick={() => onChange(o.value)}>{o.label}</button>)}
    </div>
  );
}

export function LeadStepper({ lead, onChange }: { lead: Lead; onChange: (l: Lead) => void }) {
  const i = LEADS.indexOf(lead);
  return (
    <div className="tg-lead">
      <span className="tg-lead__label" id="tg-lead-label">Saved lead time</span>
      <div className="tg-lead__track" role="radiogroup" aria-labelledby="tg-lead-label">
        {LEADS.map((l, li) => (
          <button type="button" role="radio" aria-checked={l === lead} key={l} className={li < i ? 'is-past' : l === lead ? 'is-current' : ''} onClick={() => onChange(l)}>
            <i aria-hidden="true" /><span>+{l} h</span>
          </button>
        ))}
      </div>
      <small>Five saved snapshots, unevenly spaced. Nothing is interpolated between them.</small>
    </div>
  );
}

export function DepthLegend({ compact = false }: { compact?: boolean }) {
  return (
    <div className={`tg-depth-legend${compact ? ' is-compact' : ''}`}>
      <strong>Simulated depth (p50 unless noted)</strong>
      <ul>
        {DEPTH_CLASSES.map((c) => <li key={c.label}><i style={{ background: c.color }} />{c.label}</li>)}
        <li><i className="tg-swatch-nodata" />NoData: unknown, not dry</li>
      </ul>
    </div>
  );
}

export function InfoLine({ label, value }: { label: string; value: ReactNode }) {
  return <div className="tg-info"><span>{label}</span><strong>{value}</strong></div>;
}

export type CoverageKind = 'value' | 'zero' | 'nodata' | 'unknown' | 'unavailable';
export function StateBadge({ kind, label, detail }: { kind: CoverageKind; label: string; detail: string }) {
  const icon = { value: '●', zero: '0', nodata: '▧', unknown: '?', unavailable: '×' }[kind];
  return <div className={`tg-state tg-state--${kind}`}><span aria-hidden="true">{icon}</span><div><strong>{label}</strong><small>{detail}</small></div></div>;
}

export const people = (v: number) => Math.round(v).toLocaleString('en-IN');
export const num = (v: number, digits = 2) => v.toLocaleString('en-IN', { maximumFractionDigits: digits, minimumFractionDigits: 0 });
export const pct = (part: number, whole: number, digits = 1) => `${((part / whole) * 100).toFixed(digits)}%`;
export function utc(iso: string) {
  const d = new Date(iso);
  return `${d.toISOString().slice(0, 10)} ${d.toISOString().slice(11, 16)} UTC`;
}
