export const SERIES_COLORS = ['#4cc3e6', '#f2b45a', '#9b8cff', '#5ad1a4', '#f07fa3'];

const fmt = (v: number) => (Math.abs(v) >= 1000 ? `${Math.round(v / 100) / 10}k` : Math.abs(v) >= 10 ? String(Math.round(v)) : String(Math.round(v * 100) / 100));

function niceMax(v: number) {
  if (v <= 0) return 1;
  const p = 10 ** Math.floor(Math.log10(v));
  const n = v / p;
  return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10) * p;
}

export function LineChart({ title, xLabels, series, unit, height = 190, highlightIndex }: {
  title: string;
  xLabels: string[];
  series: { name: string; values: number[]; color?: string }[];
  unit: string;
  height?: number;
  highlightIndex?: number;
}) {
  const W = 520;
  const H = height;
  const pad = { l: 46, r: 14, t: 12, b: 28 };
  const max = niceMax(Math.max(...series.flatMap((s) => s.values), 0));
  const x = (i: number) => pad.l + (i * (W - pad.l - pad.r)) / Math.max(1, xLabels.length - 1);
  const y = (v: number) => H - pad.b - (v / max) * (H - pad.t - pad.b);
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => f * max);
  const summary = series.map((s) => `${s.name}: ${s.values.map((v, i) => `${xLabels[i]} ${fmt(v)}`).join(', ')}`).join('; ');
  return (
    <figure className="tg-chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${title} (${unit}). ${summary}`}>
        {ticks.map((t) => <g key={t}><line x1={pad.l} x2={W - pad.r} y1={y(t)} y2={y(t)} className="tg-chart__grid" /><text x={pad.l - 8} y={y(t) + 4} textAnchor="end" className="tg-chart__tick">{fmt(t)}</text></g>)}
        {xLabels.map((l, i) => <text key={l} x={x(i)} y={H - 8} textAnchor="middle" className={`tg-chart__tick${i === highlightIndex ? ' is-current' : ''}`}>{l}</text>)}
        {highlightIndex !== undefined && <line x1={x(highlightIndex)} x2={x(highlightIndex)} y1={pad.t} y2={H - pad.b} className="tg-chart__cursor" />}
        {series.map((s, si) => {
          const color = s.color ?? SERIES_COLORS[si % SERIES_COLORS.length];
          const d = s.values.map((v, i) => `${i ? 'L' : 'M'}${x(i)},${y(v)}`).join(' ');
          return <g key={s.name}><path d={d} fill="none" stroke={color} strokeWidth="2" />{s.values.map((v, i) => <circle key={i} cx={x(i)} cy={y(v)} r={i === highlightIndex ? 4 : 2.6} fill={color} />)}</g>;
        })}
      </svg>
      {series.length > 1 && <figcaption className="tg-legend-row">{series.map((s, si) => <span key={s.name}><i style={{ background: s.color ?? SERIES_COLORS[si % SERIES_COLORS.length] }} />{s.name}</span>)}</figcaption>}
    </figure>
  );
}

export function BarList({ title, rows, unit, max: forcedMax }: { title: string; rows: { label: string; value: number | null; note?: string; color?: string }[]; unit: string; max?: number }) {
  const max = forcedMax ?? Math.max(1e-9, ...rows.map((r) => r.value ?? 0));
  return (
    <div className="tg-bars" role="list" aria-label={`${title} (${unit})`}>
      {rows.map((r) => (
        <div className="tg-bars__row" role="listitem" key={r.label}>
          <span className="tg-bars__label">{r.label}</span>
          <span className="tg-bars__track">{r.value !== null && <i style={{ width: `${Math.max(1.5, (r.value / max) * 100)}%`, background: r.color }} />}</span>
          <strong className="tg-bars__value">{r.value === null ? (r.note ?? 'Not assessed') : `${r.value.toLocaleString('en-IN', { maximumFractionDigits: 2 })}${unit ? ` ${unit}` : ''}`}</strong>
        </div>
      ))}
    </div>
  );
}
