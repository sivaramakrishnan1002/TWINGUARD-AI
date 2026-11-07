import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { NODATA_MM, type DepthGrid } from '../evidence/grids';

/** Depth classes in metres. Zero inside the assessed area is a valid simulated zero, not NoData. */
export const DEPTH_CLASSES = [
  { min: 0, max: 0.01, label: '< 0.01 m', color: '#1b3a4a' },
  { min: 0.01, max: 0.05, label: '0.01 – 0.05 m', color: '#1f5f7a' },
  { min: 0.05, max: 0.1, label: '0.05 – 0.10 m', color: '#1e84a8' },
  { min: 0.1, max: 0.3, label: '0.10 – 0.30 m', color: '#2fb0d6' },
  { min: 0.3, max: 0.5, label: '0.30 – 0.50 m', color: '#7bd3f0' },
  { min: 0.5, max: 1.0, label: '0.50 – 1.00 m', color: '#c7a6ff' },
  { min: 1.0, max: Infinity, label: '≥ 1.00 m', color: '#f08ad0' },
] as const;

export function depthColor(m: number) {
  return (DEPTH_CLASSES.find((c) => m >= c.min && m < c.max) ?? DEPTH_CLASSES[DEPTH_CLASSES.length - 1]).color;
}

export interface HoverCell { col: number; row: number; depthM: number | null; easting: number; northing: number }

const ORIGIN_E = 390000;
const ORIGIN_N = 1471620;
const EXAGGERATION = 4000; // 3D view: 1 m depth drawn as 4 km of height (presentation only)

export function DepthMap({ grid, mode, compareTo, label, onHover }: {
  grid: DepthGrid | null;
  mode: '2d' | '3d';
  /** When set, the map shows grid minus compareTo (depth difference). */
  compareTo?: DepthGrid | null;
  label: string;
  onHover?: (cell: HoverCell | null) => void;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ w: 640, h: 480 });
  const [cellPx, setCellPx] = useState(0);
  const geomRef = useRef<{ ox: number; oy: number; cell: number; W: number; H: number } | null>(null);

  useLayoutEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const measure = () => {
      const rect = el.getBoundingClientRect();
      if (rect.width < 1) return;
      const next = { w: Math.max(200, Math.round(rect.width)), h: Math.max(200, Math.round(rect.height)) };
      setSize((prev) => (prev.w === next.w && prev.h === next.h ? prev : next));
    };
    measure();
    window.addEventListener('resize', measure);
    const ro = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(measure);
    ro?.observe(el);
    return () => { window.removeEventListener('resize', measure); ro?.disconnect(); };
  }, [grid === null]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !grid) return;
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    canvas.width = size.w * dpr;
    canvas.height = size.h * dpr;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, size.w, size.h);
    const { width: W, height: H, mm } = grid;
    const diff = compareTo ? compareTo.mm : null;
    const valueAt = (i: number) => {
      if (mm[i] === NODATA_MM) return null;
      if (diff) return diff[i] === NODATA_MM ? null : (mm[i] - diff[i]) / 1000;
      return mm[i] / 1000;
    };
    const fill = (v: number) => (diff ? diffColor(v) : depthColor(v));

    if (mode === '2d') {
      const cell = Math.min((size.w - 24) / W, (size.h - 24) / H);
      const ox = (size.w - cell * W) / 2;
      const oy = (size.h - cell * H) / 2;
      for (let r = 0; r < H; r += 1) {
        for (let c = 0; c < W; c += 1) {
          const v = valueAt(r * W + c);
          const x = ox + c * cell;
          const y = oy + r * cell;
          if (v === null) {
            ctx.fillStyle = 'rgba(148,170,186,0.16)';
            ctx.fillRect(x + cell / 2 - 0.6, y + cell / 2 - 0.6, 1.2, 1.2);
          } else {
            ctx.fillStyle = fill(v);
            ctx.fillRect(x, y, cell + 0.5, cell + 0.5);
          }
        }
      }
      geomRef.current = { ox, oy, cell, W, H };
      setCellPx((prev) => (Math.abs(prev - cell) > 0.01 ? cell : prev));
      return;
    }

    // 3D isometric extrusion of saved depths (presentation only; heights exaggerated).
    const tw = Math.min(((size.w - 40) * 2) / (W + H), ((size.h - 70) * 4) / (W + H));
    const th = tw / 2;
    const ox = size.w / 2 - ((W - H) * tw) / 4;
    const oy = 54;
    const px = (c: number, r: number) => ox + ((c - r) * tw) / 2;
    const py = (c: number, r: number) => oy + ((c + r) * th) / 2;
    // One tile spans one 600 m cell; vertical scale is EXAGGERATION metres of drawing per metre of depth.
    const unitH = (tw / grid.cellSizeM) * EXAGGERATION;
    for (let s = 0; s < W + H - 1; s += 1) {
      for (let r = Math.max(0, s - W + 1); r <= Math.min(H - 1, s); r += 1) {
        const c = s - r;
        const v = valueAt(r * W + c);
        if (v === null) continue;
        const x0 = px(c, r);
        const y0 = py(c, r);
        const top = [[x0, y0], [x0 + tw / 2, y0 + th / 2], [x0, y0 + th], [x0 - tw / 2, y0 + th / 2]];
        const h = diff ? Math.min(120, Math.abs(v) * unitH) : Math.min(180, Math.max(0, v) * unitH);
        // ground tile
        poly(ctx, top, '#13293a', '#1d3a4e');
        if (h > 0.4) {
          const lifted = top.map(([x, y]) => [x, y - h]);
          const color = fill(v);
          poly(ctx, [top[1], top[2], lifted[2], lifted[1]], shade(color, -0.28));
          poly(ctx, [top[2], top[3], lifted[3], lifted[2]], shade(color, -0.12));
          poly(ctx, lifted, color);
        } else {
          poly(ctx, top, fill(v));
        }
      }
    }
    geomRef.current = null;
  }, [grid, compareTo, mode, size]);

  function handleMove(event: React.MouseEvent<HTMLCanvasElement>) {
    if (!grid || !onHover || mode !== '2d') return;
    const geom = geomRef.current;
    if (!geom) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const c = Math.floor((event.clientX - rect.left - geom.ox) / geom.cell);
    const r = Math.floor((event.clientY - rect.top - geom.oy) / geom.cell);
    if (c < 0 || r < 0 || c >= geom.W || r >= geom.H) { onHover(null); return; }
    const raw = grid.mm[r * geom.W + c];
    const other = compareTo?.mm[r * geom.W + c];
    const depthM = raw === NODATA_MM || other === NODATA_MM ? null : compareTo ? (raw - (other ?? 0)) / 1000 : raw / 1000;
    onHover({ col: c, row: r, depthM, easting: ORIGIN_E + c * 600 + 300, northing: ORIGIN_N - r * 600 - 300 });
  }

  return (
    <div className="tg-map" ref={wrapRef}>
      {grid ? (
        <canvas ref={canvasRef} role="img" aria-label={label} style={{ width: size.w, height: size.h }} onMouseMove={handleMove} onMouseLeave={() => onHover?.(null)} />
      ) : (
        <div className="tg-map__empty" role="status">
          <strong>Saved depth grid not loaded</strong>
          <span>Run <code>tools/ui/export_ui_depth_grids.py</code> to bundle the saved A05 rasters. Report figures elsewhere on this page are still available.</span>
        </div>
      )}
      <div className={`tg-map__north${mode === '3d' ? ' is-iso' : ''}`} aria-hidden="true"><span>N</span></div>
      {grid && mode === '2d' && cellPx > 0 && <div className="tg-map__scale" aria-hidden="true"><i style={{ width: Math.round(cellPx * 10) }} /><span>6 km (10 cells)</span></div>}
      {grid && mode === '3d' && <div className="tg-map__note">Isometric view, north toward the top-right. Vertical exaggeration: 1 m of depth drawn as {EXAGGERATION / 1000} km. Presentation only.</div>}
    </div>
  );
}

export function diffColor(v: number) {
  if (Math.abs(v) < 0.005) return '#1b3a4a';
  if (v > 0) return v >= 0.1 ? '#ff8a65' : v >= 0.03 ? '#f6b26b' : '#a8794e';
  return v <= -0.1 ? '#5ad1a4' : v <= -0.03 ? '#3e9c7c' : '#2d6b5a';
}

function poly(ctx: CanvasRenderingContext2D, pts: number[][], fillStyle: string, stroke?: string) {
  ctx.beginPath();
  ctx.moveTo(pts[0][0], pts[0][1]);
  for (let i = 1; i < pts.length; i += 1) ctx.lineTo(pts[i][0], pts[i][1]);
  ctx.closePath();
  ctx.fillStyle = fillStyle;
  ctx.fill();
  if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = 0.4; ctx.stroke(); }
}

function shade(hex: string, amount: number) {
  const n = parseInt(hex.slice(1), 16);
  const ch = (v: number) => Math.max(0, Math.min(255, Math.round(v + (amount < 0 ? v * amount : (255 - v) * amount))));
  return `rgb(${ch((n >> 16) & 255)},${ch((n >> 8) & 255)},${ch(n & 255)})`;
}
