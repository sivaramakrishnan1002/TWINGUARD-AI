/** Small geodesy helpers: UTM zone 44N (EPSG:32644) <-> WGS84, polygons, distances. */

const A = 6378137;
const F = 1 / 298.257223563;
const E2 = F * (2 - F);
const EP2 = E2 / (1 - E2);
const K0 = 0.9996;
const LON0 = (81 * Math.PI) / 180; // zone 44 central meridian
const FE = 500000;

export function utmToLonLat(easting: number, northing: number): [number, number] {
  const x = easting - FE;
  const m = northing / K0;
  const mu = m / (A * (1 - E2 / 4 - (3 * E2 * E2) / 64 - (5 * E2 ** 3) / 256));
  const e1 = (1 - Math.sqrt(1 - E2)) / (1 + Math.sqrt(1 - E2));
  const phi1 = mu + ((3 * e1) / 2 - (27 * e1 ** 3) / 32) * Math.sin(2 * mu) + ((21 * e1 * e1) / 16 - (55 * e1 ** 4) / 32) * Math.sin(4 * mu) + ((151 * e1 ** 3) / 96) * Math.sin(6 * mu) + ((1097 * e1 ** 4) / 512) * Math.sin(8 * mu);
  const s = Math.sin(phi1);
  const c = Math.cos(phi1);
  const t = Math.tan(phi1);
  const n1 = A / Math.sqrt(1 - E2 * s * s);
  const r1 = (A * (1 - E2)) / (1 - E2 * s * s) ** 1.5;
  const c1 = EP2 * c * c;
  const d = x / (n1 * K0);
  const lat = phi1 - ((n1 * t) / r1) * (d * d / 2 - ((5 + 3 * t * t + 10 * c1 - 4 * c1 * c1 - 9 * EP2) * d ** 4) / 24 + ((61 + 90 * t * t + 298 * c1 + 45 * t ** 4 - 252 * EP2 - 3 * c1 * c1) * d ** 6) / 720);
  const lon = LON0 + (d - ((1 + 2 * t * t + c1) * d ** 3) / 6 + ((5 - 2 * c1 + 28 * t * t - 3 * c1 * c1 + 8 * EP2 + 24 * t ** 4) * d ** 5) / 120) / c;
  return [(lon * 180) / Math.PI, (lat * 180) / Math.PI];
}

export function lonLatToUtm(lonDeg: number, latDeg: number): [number, number] {
  const lat = (latDeg * Math.PI) / 180;
  const lon = (lonDeg * Math.PI) / 180;
  const s = Math.sin(lat);
  const c = Math.cos(lat);
  const t = Math.tan(lat);
  const n = A / Math.sqrt(1 - E2 * s * s);
  const tt = t * t;
  const cc = EP2 * c * c;
  const a = c * (lon - LON0);
  const m = A * ((1 - E2 / 4 - (3 * E2 * E2) / 64 - (5 * E2 ** 3) / 256) * lat - ((3 * E2) / 8 + (3 * E2 * E2) / 32 + (45 * E2 ** 3) / 1024) * Math.sin(2 * lat) + ((15 * E2 * E2) / 256 + (45 * E2 ** 3) / 1024) * Math.sin(4 * lat) - ((35 * E2 ** 3) / 3072) * Math.sin(6 * lat));
  const easting = FE + K0 * n * (a + ((1 - tt + cc) * a ** 3) / 6 + ((5 - 18 * tt + tt * tt + 72 * cc - 58 * EP2) * a ** 5) / 120);
  const northing = K0 * (m + n * t * (a * a / 2 + ((5 - tt + 9 * cc + 4 * cc * cc) * a ** 4) / 24 + ((61 - 58 * tt + tt * tt + 600 * cc - 330 * EP2) * a ** 6) / 720));
  return [easting, northing];
}

export function haversineM(a: [number, number], b: [number, number]): number {
  const toRad = Math.PI / 180;
  const dLat = (b[1] - a[1]) * toRad;
  const dLon = (b[0] - a[0]) * toRad;
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(a[1] * toRad) * Math.cos(b[1] * toRad) * Math.sin(dLon / 2) ** 2;
  return 2 * 6371008.8 * Math.asin(Math.sqrt(h));
}

export function pointInRing(x: number, y: number, ring: number[][]): boolean {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i];
    const [xj, yj] = ring[j];
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi || 1e-12) + xi) inside = !inside;
  }
  return inside;
}

/** Point in a GeoJSON Polygon or MultiPolygon (outer rings minus holes). */
export function pointInGeometry(x: number, y: number, geom: { type: string; coordinates: unknown }): boolean {
  const polys = (geom.type === 'Polygon' ? [geom.coordinates] : geom.type === 'MultiPolygon' ? geom.coordinates : []) as number[][][][];
  return polys.some((rings) => pointInRing(x, y, rings[0]) && !rings.slice(1).some((h) => pointInRing(x, y, h)));
}

export function ringAreaM2(flatLonLat: number[]): number {
  let s = 0;
  const pts: [number, number][] = [];
  for (let i = 0; i < flatLonLat.length; i += 2) pts.push(lonLatToUtm(flatLonLat[i], flatLonLat[i + 1]));
  for (let i = 0; i < pts.length; i += 1) {
    const [x1, y1] = pts[i];
    const [x2, y2] = pts[(i + 1) % pts.length];
    s += x1 * y2 - x2 * y1;
  }
  return Math.abs(s) / 2;
}

export interface TerrainGrid { west: number; north: number; step: number; rows: number; cols: number; dm: Int16Array }

/** Bilinear ground height in metres from the exported DEM grid; 0 outside or at NoData. */
export function terrainHeight(t: TerrainGrid | null, lon: number, lat: number): number {
  if (!t) return 0;
  const fx = (lon - t.west) / t.step - 0.5;
  const fy = (t.north - lat) / t.step - 0.5;
  const x0 = Math.floor(fx);
  const y0 = Math.floor(fy);
  if (x0 < 0 || y0 < 0 || x0 + 1 >= t.cols || y0 + 1 >= t.rows) return 0;
  const g = (x: number, y: number) => { const v = t.dm[y * t.cols + x]; return v === -32768 ? 0 : v / 10; };
  const dx = fx - x0;
  const dy = fy - y0;
  return (g(x0, y0) * (1 - dx) + g(x0 + 1, y0) * dx) * (1 - dy) + (g(x0, y0 + 1) * (1 - dx) + g(x0 + 1, y0 + 1) * dx) * dy;
}

export function decodeBase64(b64: string): ArrayBuffer {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i += 1) bytes[i] = bin.charCodeAt(i);
  return bytes.buffer;
}
