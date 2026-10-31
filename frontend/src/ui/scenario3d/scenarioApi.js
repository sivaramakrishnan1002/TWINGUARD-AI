import { parseA20Float32GeoTiff } from './geotiff.js';

export const AI_SCENARIO_ORIGIN = 'http://127.0.0.1:8000';
export const FRONTEND_ORIGIN = 'http://127.0.0.1:8081';
export const ALLOWED_BANDS = Object.freeze(['p05', 'p50', 'p95']);
const MAX_JSON_BYTES = 2 * 1024 * 1024;
const MAX_RASTER_BYTES = 1024 * 1024;

export class ScenarioRequestError extends Error {
  constructor(message, status = null) {
    super(message);
    this.name = 'ScenarioRequestError';
    this.status = status;
  }
}

function checkedSelector(eventId, scenarioId) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(eventId) || !/^[a-z0-9_]+$/.test(scenarioId)) {
    throw new ScenarioRequestError('The saved scenario selector is invalid.');
  }
}

async function request(path, accept, maxBytes, signal) {
  let response;
  try {
    response = await fetch(`${AI_SCENARIO_ORIGIN}${path}`, {
      method: 'GET',
      mode: 'cors',
      credentials: 'omit',
      cache: 'no-store',
      headers: { Accept: accept },
      signal,
    });
  } catch {
    throw new ScenarioRequestError('The saved scenario service is unavailable.');
  }
  if (!response.ok) {
    const messages = {
      400: 'The saved scenario selector was rejected.',
      404: 'No exact saved scenario asset exists for this selection.',
      409: 'The saved scenario identity is ambiguous.',
      503: 'The saved scenario asset is temporarily unavailable.',
    };
    throw new ScenarioRequestError(messages[response.status] ?? 'The saved scenario request failed.', response.status);
  }
  const length = Number(response.headers.get('content-length') ?? 0);
  if (length > maxBytes) throw new ScenarioRequestError('The saved response exceeds its size limit.');
  const bytes = new Uint8Array(await response.arrayBuffer());
  if (bytes.byteLength === 0 || bytes.byteLength > maxBytes || (length > 0 && bytes.byteLength !== length)) {
    throw new ScenarioRequestError('The saved response is empty or incomplete.');
  }
  return { response, bytes };
}

export async function fetchScenarioCatalog(signal) {
  const { bytes } = await request('/scenario-visualization-assets', 'application/json', MAX_JSON_BYTES, signal);
  let catalog;
  try { catalog = JSON.parse(new TextDecoder().decode(bytes)); }
  catch { throw new ScenarioRequestError('The saved scenario catalog could not be read.'); }
  if (!Array.isArray(catalog.scenario_series)) throw new ScenarioRequestError('The saved scenario catalog is incomplete.');
  return catalog;
}

export async function fetchScenarioDetail(eventId, scenarioId, signal) {
  checkedSelector(eventId, scenarioId);
  const path = `/scenario-visualization-assets/${encodeURIComponent(eventId)}/${encodeURIComponent(scenarioId)}`;
  const { bytes } = await request(path, 'application/json', MAX_JSON_BYTES, signal);
  let detail;
  try { detail = JSON.parse(new TextDecoder().decode(bytes)); }
  catch { throw new ScenarioRequestError('The saved scenario detail could not be read.'); }
  if (detail.series?.event_id !== eventId || detail.series?.scenario_id !== scenarioId || !Array.isArray(detail.series.slices)) {
    throw new ScenarioRequestError('The service returned a mismatched saved scenario identity.');
  }
  return detail;
}

export function makeScenarioKey(series) {
  return `${series.event_id}::${series.scenario_id}`;
}

export function findScenario(catalog, key) {
  if (!catalog || typeof key !== 'string') return null;
  const matches = catalog.scenario_series.filter((series) => makeScenarioKey(series) === key);
  if (matches.length !== 1) return null;
  return matches[0];
}

export async function fetchScenarioRaster(detail, validTimeUtc, band, expectedHash, signal) {
  const series = detail.series;
  checkedSelector(series.event_id, series.scenario_id);
  if (!ALLOWED_BANDS.includes(band)) throw new ScenarioRequestError('The saved raster band is invalid.');
  const matches = series.slices.filter((slice) => slice.valid_time_utc === validTimeUtc);
  if (matches.length !== 1) throw new ScenarioRequestError('The saved timestamp does not identify exactly one slice.');
  const reference = matches[0].bands?.[band];
  if (!reference || reference.sha256 !== expectedHash || reference.size_bytes > MAX_RASTER_BYTES) {
    throw new ScenarioRequestError('The selected saved raster reference is unavailable.');
  }

  const query = new URLSearchParams({ valid_time_utc: validTimeUtc, band });
  const path = `/scenario-visualization-assets/${encodeURIComponent(series.event_id)}/${encodeURIComponent(series.scenario_id)}/raster?${query}`;
  const { response, bytes } = await request(path, 'image/tiff', MAX_RASTER_BYTES, signal);
  if (!response.headers.get('content-type')?.toLowerCase().startsWith('image/tiff')) {
    throw new ScenarioRequestError('The service did not return the saved GeoTIFF media type.');
  }
  if (bytes.byteLength !== reference.size_bytes) throw new ScenarioRequestError('The saved raster size does not match its manifest.');

  let digest;
  try {
    digest = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)))
      .map((value) => value.toString(16).padStart(2, '0')).join('');
  } catch {
    throw new ScenarioRequestError('This browser cannot verify the saved raster hash.');
  }
  if (digest !== expectedHash) throw new ScenarioRequestError('The saved raster hash does not match its manifest.');

  const grid = detail.grid;
  const expectedGrid = {
    width: grid.width,
    height: grid.height,
    epsg: Number(String(grid.crs).replace('EPSG:', '')),
    transform: grid.affine_transform,
    nodata: detail.nodata.value,
  };
  const raster = await parseA20Float32GeoTiff(bytes, expectedGrid);
  if (raster.validCount !== reference.valid_cell_count || raster.nodataCount !== reference.nodata_cell_count) {
    throw new ScenarioRequestError('The saved raster mask does not match its manifest.');
  }
  return { raster, reference, sha256: digest, validTimeUtc, band };
}
