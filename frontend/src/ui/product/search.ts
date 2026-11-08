import type { GazPlace, GazWard } from '../api/fixtures';

/** One searchable entry: an OSM place, a GCC ward, or a curated callout. */
export interface SearchHit { kind: 'place' | 'ward'; label: string; sub: string; lon: number; lat: number; ward_id: number | null; rank: number; score: number; bbox?: [number, number, number, number] }

const norm = (s: string) => s.toLowerCase().normalize('NFKD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9஀-௿ ]+/g, ' ').replace(/\s+/g, ' ').trim();
/** Light transliteration folding so Tiruvottiyur ~ Thiruvottiyur, Puzhal ~ Puzal, etc. */
const fold = (s: string) => norm(s).replace(/th/g, 't').replace(/zh/g, 'z').replace(/aa/g, 'a').replace(/ee/g, 'i').replace(/oo/g, 'u').replace(/([a-z])\1/g, '$1');

function editDistance(a: string, b: string, max: number): number {
  if (Math.abs(a.length - b.length) > max) return max + 1;
  let prev = Array.from({ length: b.length + 1 }, (_, i) => i);
  for (let i = 1; i <= a.length; i += 1) {
    const cur = [i];
    let best = i;
    for (let j = 1; j <= b.length; j += 1) {
      cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
      best = Math.min(best, cur[j]);
    }
    if (best > max) return max + 1;
    prev = cur;
  }
  return prev[b.length];
}

function scoreName(q: string, name: string): number {
  const n = fold(name);
  if (!q) return 0;
  if (n === q) return 100;
  if (n.startsWith(q)) return 85 - Math.min(20, n.length - q.length);
  if (n.split(' ').some((w) => w.startsWith(q))) return 70;
  if (n.includes(q)) return 55;
  if (q.length >= 4) {
    const d = editDistance(q, n.slice(0, q.length + 2), 2);
    if (d <= 2) return 45 - d * 10;
  }
  return 0;
}

export function buildIndex(places: GazPlace[], wards: GazWard[], curated: { name: string; lon: number; lat: number }[]) {
  const entries: Omit<SearchHit, 'score'>[] = [
    ...curated.map((c) => ({ kind: 'place' as const, label: c.name, sub: 'Area', lon: c.lon, lat: c.lat, ward_id: null, rank: 1 })),
    ...places.map((p) => ({ kind: 'place' as const, label: p.name, sub: [p.type, p.ward_id ? `Ward ${p.ward_id}` : null, p.zone].filter(Boolean).join(' · '), lon: p.lon, lat: p.lat, ward_id: p.ward_id, rank: p.rank, alt: p.alt } as Omit<SearchHit, 'score'> & { alt?: string[] })),
    ...wards.map((w) => ({ kind: 'ward' as const, label: w.name, sub: w.zone ?? 'GCC ward', lon: w.lon, lat: w.lat, ward_id: w.ward_id, rank: 2, bbox: w.bbox })),
  ];
  return (query: string, limit = 12): SearchHit[] => {
    const q = fold(query);
    if (!q) return [];
    const wardNo = q.match(/^(?:ward\s*)?(\d{1,3})$/);
    const hits: SearchHit[] = [];
    const seen = new Set<string>();
    for (const e of entries) {
      let score = Math.max(scoreName(q, e.label), ...((e as { alt?: string[] }).alt ?? []).map((a) => scoreName(q, a) - 5));
      if (wardNo && e.kind === 'ward' && e.ward_id === Number(wardNo[1])) score = 120;
      if (score <= 0) continue;
      const key = `${fold(e.label)}|${e.lon.toFixed(2)}|${e.lat.toFixed(2)}`;
      if (seen.has(key)) continue;
      seen.add(key);
      hits.push({ ...e, score: score - e.rank });
    }
    return hits.sort((a, b) => b.score - a.score || a.label.localeCompare(b.label)).slice(0, limit);
  };
}
