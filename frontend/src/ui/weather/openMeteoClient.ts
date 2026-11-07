export const OPEN_METEO_ENDPOINT = 'https://api.open-meteo.com/v1/forecast';
export const OPEN_METEO_ATTRIBUTION_URL = 'https://open-meteo.com/en/docs';
export const CHENNAI_POINT = { latitude: 13.0827, longitude: 80.2707 } as const;

export interface OpenMeteoWeatherSnapshot {
  requestedPoint: typeof CHENNAI_POINT;
  gridPoint: { latitude: number; longitude: number; elevationM: number | null };
  timezone: 'Asia/Kolkata';
  current: {
    validTimeLocal: string;
    intervalSeconds: number;
    precipitationMm: number | null;
    rainMm: number | null;
    temperatureC: number | null;
    relativeHumidityPercent: number | null;
  };
  hourly: Array<{ validTimeLocal: string; precipitationMm: number | null }>;
  fetchedAt: string;
  attribution: 'Open-Meteo · CC BY 4.0';
}

export type FetchLike = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;

export function chennaiForecastUrl(): string {
  const url = new URL(OPEN_METEO_ENDPOINT);
  url.search = new URLSearchParams({
    latitude: String(CHENNAI_POINT.latitude),
    longitude: String(CHENNAI_POINT.longitude),
    current: 'precipitation,rain,temperature_2m,relative_humidity_2m',
    hourly: 'precipitation',
    timezone: 'Asia/Kolkata',
    timeformat: 'iso8601',
    temperature_unit: 'celsius',
    precipitation_unit: 'mm',
    forecast_hours: '24',
  }).toString();
  return url.toString();
}

export async function fetchChennaiWeather(fetcher: FetchLike = fetch, now: () => Date = () => new Date(), signal?: AbortSignal): Promise<OpenMeteoWeatherSnapshot> {
  const response = await fetcher(chennaiForecastUrl(), {
    method: 'GET',
    headers: { Accept: 'application/json' },
    credentials: 'omit',
    cache: 'no-store',
    signal,
  });
  if (!response.ok) throw new Error(`Weather provider returned HTTP ${response.status}.`);
  let payload: unknown;
  try { payload = await response.json(); }
  catch { throw new Error('Weather provider response was not valid JSON.'); }
  return parseChennaiWeather(payload, now().toISOString());
}

export function parseChennaiWeather(value: unknown, fetchedAt: string): OpenMeteoWeatherSnapshot {
  if (!isRecord(value)) throw new Error('Weather response must be an object.');
  if (value.timezone !== 'Asia/Kolkata' || value.utc_offset_seconds !== 19800) throw new Error('Weather response timezone did not match Asia/Kolkata.');
  const latitude = finite(value.latitude);
  const longitude = finite(value.longitude);
  if (latitude === null || longitude === null || Math.abs(latitude - CHENNAI_POINT.latitude) > 0.2 || Math.abs(longitude - CHENNAI_POINT.longitude) > 0.2) {
    throw new Error('Weather response coordinates are outside the requested Chennai area.');
  }
  const current = isRecord(value.current) ? value.current : null;
  const currentUnits = isRecord(value.current_units) ? value.current_units : null;
  const hourly = isRecord(value.hourly) ? value.hourly : null;
  const hourlyUnits = isRecord(value.hourly_units) ? value.hourly_units : null;
  if (!current || !currentUnits || !hourly || !hourlyUnits) throw new Error('Weather response is missing current or hourly data.');
  if (currentUnits.precipitation !== 'mm' || currentUnits.rain !== 'mm' || currentUnits.temperature_2m !== '°C' || currentUnits.relative_humidity_2m !== '%') {
    throw new Error('Weather response units did not match the requested metric fields.');
  }
  if (hourlyUnits.precipitation !== 'mm') throw new Error('Hourly precipitation units were not millimetres.');
  const currentTime = validLocalTime(current.time);
  const interval = finite(current.interval);
  if (!currentTime || interval === null || interval <= 0) throw new Error('Current model valid time or accumulation interval is missing.');
  const times = hourly.time;
  const amounts = hourly.precipitation;
  if (!Array.isArray(times) || !Array.isArray(amounts) || times.length === 0 || times.length !== amounts.length || times.length > 24) {
    throw new Error('Hourly precipitation times and values are missing or misaligned.');
  }
  const hourlyRows = times.map((time, index) => {
    const validTime = validLocalTime(time);
    const amount = nullableNonNegative(amounts[index]);
    if (!validTime || amount === undefined) throw new Error('Hourly model data contains an invalid time or value.');
    return { validTimeLocal: validTime, precipitationMm: amount };
  });
  const receivedAt = new Date(fetchedAt);
  if (!Number.isFinite(receivedAt.valueOf())) throw new Error('Fetch time must be a valid timestamp.');
  return {
    requestedPoint: CHENNAI_POINT,
    gridPoint: { latitude, longitude, elevationM: requireNullableFinite(value.elevation, 'elevation') },
    timezone: 'Asia/Kolkata',
    current: {
      validTimeLocal: currentTime,
      intervalSeconds: interval,
      precipitationMm: requireNullableNonNegative(current.precipitation, 'current precipitation'),
      rainMm: requireNullableNonNegative(current.rain, 'current rain'),
      temperatureC: requireNullableFinite(current.temperature_2m, 'temperature'),
      relativeHumidityPercent: nullableBounded(current.relative_humidity_2m, 0, 100),
    },
    hourly: hourlyRows,
    fetchedAt: receivedAt.toISOString(),
    attribution: 'Open-Meteo · CC BY 4.0',
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function finite(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function nullableFinite(value: unknown): number | null {
  return value === null || value === undefined ? null : finite(value);
}

function requireNullableFinite(value: unknown, field: string): number | null {
  const result = nullableFinite(value);
  if (result === null && value !== null && value !== undefined) throw new Error(`${field} must be numeric or unknown.`);
  return result;
}

function nullableNonNegative(value: unknown): number | null | undefined {
  if (value === null || value === undefined) return null;
  const number = finite(value);
  return number !== null && number >= 0 ? number : undefined;
}

function requireNullableNonNegative(value: unknown, field: string): number | null {
  const result = nullableNonNegative(value);
  if (result === undefined) throw new Error(`${field} must be non-negative or unknown.`);
  return result;
}

function nullableBounded(value: unknown, minimum: number, maximum: number): number | null {
  if (value === null || value === undefined) return null;
  const number = finite(value);
  if (number === null || number < minimum || number > maximum) throw new Error('Relative humidity must be between 0 and 100 percent or unknown.');
  return number;
}

function validLocalTime(value: unknown): string | null {
  return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(value) ? value : null;
}
