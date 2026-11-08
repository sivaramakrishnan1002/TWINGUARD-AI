import assert from 'node:assert/strict';
import test from 'node:test';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
const frontendRoot = path.join(root, 'frontend');
const require = createRequire(path.join(frontendRoot, 'package.json'));
const { createServer } = require('vite');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');

async function withModules(callback) {
  const server = await createServer({ configFile: path.join(frontendRoot, 'vite.config.ts'), root: frontendRoot, appType: 'custom', server: { middlewareMode: true }, define: { 'import.meta.env.VITE_GATE_G0_STATUS': JSON.stringify('unknown') } });
  try {
    const client = await server.ssrLoadModule('/src/ui/weather/openMeteoClient.ts');
    const component = await server.ssrLoadModule('/src/ui/weather/OpenMeteoWeatherCard.tsx');
    await callback({ client, component });
  } finally { await server.close(); }
}

function payload(overrides = {}) {
  return {
    latitude: 13.110721,
    longitude: 80.2459,
    elevation: 12,
    timezone: 'Asia/Kolkata',
    utc_offset_seconds: 19800,
    current_units: { time: 'iso8601', interval: 'seconds', precipitation: 'mm', rain: 'mm', temperature_2m: '°C', relative_humidity_2m: '%' },
    current: { time: '2026-11-06T10:15', interval: 900, precipitation: 0, rain: 0, temperature_2m: 28.9, relative_humidity_2m: 74 },
    hourly_units: { time: 'iso8601', precipitation: 'mm' },
    hourly: { time: ['2026-11-06T10:00', '2026-11-06T11:00'], precipitation: [0, 1.2] },
    ...overrides,
  };
}

test('Open-Meteo request is fixed to the Chennai weather-context scope and carries no credentials', async () => {
  await withModules(async ({ client }) => {
    let request;
    const snapshot = await client.fetchChennaiWeather(async (url, options) => {
      request = { url: new URL(String(url)), options };
      return new Response(JSON.stringify(payload()), { status: 200, headers: { 'content-type': 'application/json' } });
    }, () => new Date('2026-11-06T05:00:00.000Z'));
    assert.equal(request.url.origin, 'https://api.open-meteo.com');
    assert.equal(request.url.pathname, '/v1/forecast');
    assert.equal(request.url.searchParams.get('latitude'), '13.0827');
    assert.equal(request.url.searchParams.get('longitude'), '80.2707');
    assert.equal(request.url.searchParams.get('timezone'), 'Asia/Kolkata');
    assert.equal(request.url.searchParams.get('current'), 'precipitation,rain,temperature_2m,relative_humidity_2m,wind_speed_10m');
    assert.equal(request.url.searchParams.get('wind_speed_unit'), 'kmh');
    assert.equal(request.url.searchParams.get('hourly'), 'precipitation');
    assert.equal(request.url.searchParams.get('forecast_hours'), '24');
    assert.equal(request.options.method, 'GET');
    assert.equal(request.options.credentials, 'omit');
    assert.deepEqual(request.options.headers, { Accept: 'application/json' });
    assert.equal(snapshot.current.validTimeLocal, '2026-11-06T10:15');
    assert.equal(snapshot.current.intervalSeconds, 900);
    assert.equal(snapshot.fetchedAt, '2026-11-06T05:00:00.000Z');
    assert.deepEqual(snapshot.gridPoint, { latitude: 13.110721, longitude: 80.2459, elevationM: 12 });
  });
});

test('valid zero, null, and forecast amounts remain distinct', async () => {
  await withModules(async ({ client }) => {
    const sample = payload({
      current: { time: '2026-11-06T10:15', interval: 900, precipitation: 0, rain: null, temperature_2m: 28.9, relative_humidity_2m: null },
      hourly: { time: ['2026-11-06T10:00', '2026-11-06T11:00'], precipitation: [0, null] },
    });
    const parsed = client.parseChennaiWeather(sample, '2026-11-06T05:00:00.000Z');
    assert.equal(parsed.current.precipitationMm, 0);
    assert.equal(parsed.current.rainMm, null);
    assert.equal(parsed.current.relativeHumidityPercent, null);
    assert.deepEqual(parsed.hourly.map((hour) => hour.precipitationMm), [0, null]);
  });
});

test('invalid timezone, units, coordinates, and misaligned arrays fail closed', async () => {
  await withModules(async ({ client }) => {
    const cases = [
      payload({ timezone: 'UTC' }),
      payload({ current_units: { ...payload().current_units, precipitation: 'inch' } }),
      payload({ latitude: 0 }),
      payload({ hourly: { time: ['2026-11-06T10:00'], precipitation: [0, 1] } }),
    ];
    for (const item of cases) assert.throws(() => client.parseChennaiWeather(item, '2026-11-06T05:00:00.000Z'));
  });
});

test('HTTP and invalid JSON failures are surfaced without retry or fallback data', async () => {
  await withModules(async ({ client }) => {
    await assert.rejects(() => client.fetchChennaiWeather(async () => new Response('{}', { status: 503 })), /HTTP 503/);
    await assert.rejects(() => client.fetchChennaiWeather(async () => new Response('{', { status: 200 })), /valid JSON/);
  });
});

test('timeout and failed refresh never relabel a retained response as current', async () => {
  await withModules(async ({ client, component }) => {
    const saved = client.parseChennaiWeather(payload(), '2026-11-06T05:00:00.000Z');
    const initialTimeout = component.weatherRequestFailed(null, 'timeout', true);
    assert.equal(initialTimeout.status, 'unavailable');
    assert.match(initialTimeout.message, /timed out/i);
    const refreshTimeout = component.weatherRequestFailed(saved, 'timeout', true);
    assert.equal(refreshTimeout.status, 'refresh-failed');
    assert.strictEqual(refreshTimeout.snapshot, saved);
    assert.match(refreshTimeout.message, /not presented as current/i);
    const refreshError = component.weatherRequestFailed(saved, 'HTTP 503');
    assert.equal(refreshError.status, 'refresh-failed');
    assert.strictEqual(refreshError.snapshot, saved);
    assert.match(refreshError.message, /HTTP 503/);
  });
});

test('weather card copy distinguishes model data from observed and simulated flood outputs', async () => {
  await withModules(async ({ component }) => {
    const markup = renderToStaticMarkup(React.createElement(component.OpenMeteoWeatherCard));
    assert.match(markup, /EXTERNAL WEATHER MODEL/);
    assert.match(markup, /not rain-gauge observations/i);
    assert.match(markup, /does not drive flood, reservoir, alert, impact, route, or shelter results/i);
    assert.match(markup, /CC BY 4\.0/);
    assert.match(markup, /Refreshes at most every 30 minutes/);
  });
});
