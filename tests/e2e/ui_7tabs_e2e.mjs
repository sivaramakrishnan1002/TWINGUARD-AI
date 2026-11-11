// B56 end-to-end UI test against the running stack (start_twinguard.ps1: API :8000, Vite :5173), real GPU Chrome.
// Usage: node tests/e2e/ui_7tabs_e2e.mjs [baseUrl] [outDir]
//   default baseUrl http://localhost:5173/, outDir docs/ui/screenshots/e2e_b56
// Opens on the live run, switches to the Dec 2015 replay and back, asserts on-screen values against /v3 (depth,
// wards, run summary, live status), plays and scrubs the timeline, toggles 3D / 2D / Satellite, searches an area
// (Royapuram), runs a what-if to completion, requests a route, fetches the reservoir snapshot, measures FPS (idle,
// pan, playback, tab switching), visits all 7 tabs with 0 console errors, and saves screenshots at 1600x1000
// plus layout passes at 1366x768 and 1920x1080. Exit code 1 when any check fails. Writes <outDir>/e2e_results.json.
import { mkdirSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { launch, METER, sleep } from '../../tools/ui/cdp.mjs';

const BASE = process.argv[2] ?? 'http://localhost:5173/';
const OUT = resolve(process.argv[3] ?? 'docs/ui/screenshots/e2e_b56');
const REPLAY_LABEL = 'Chennai floods, Dec 2015';
const TABS = [
  ['overview', 'Situation Overview'], ['simulation', 'Flood Simulation'], ['emergency', 'Emergency Support'], ['routing', 'Road Routing'],
  ['what-if', 'What-if Simulation'], ['reservoirs', 'Reservoir Monitoring'], ['twin', 'Digital Twin (3D City)'],
];
mkdirSync(OUT, { recursive: true });
const results = { base: BASE, started: new Date().toISOString(), checks: [], fps: {}, screenshots: [], note: 'FPS depends on the power state: laptops on battery / power-saving plans throttle the GPU' };
const check = (name, ok, detail = '') => { results.checks.push({ name, ok: !!ok, detail }); console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? `  (${detail})` : ''}`); };

const b = await launch({ port: 9395, width: 1600, height: 1000, gpu: true });
const q = (sel) => `document.querySelector(${JSON.stringify(sel)})`;
const text = () => b.evaluate('document.body.innerText');
const frameNo = async () => Number((await text()).match(/Frame (\d+)\//)?.[1] ?? 0);
const badge = () => b.evaluate(`${q('.tg-top .tg-badge')}?.textContent ?? ''`);
const setValue = (sel, value, ev = 'change') => b.evaluate(`(() => { const el = ${q(sel)}; if (!el) return false; const proto = el instanceof HTMLSelectElement ? HTMLSelectElement.prototype : HTMLInputElement.prototype; Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, ${JSON.stringify(String(value))}); el.dispatchEvent(new Event(${JSON.stringify(ev)}, { bubbles: true })); return true; })()`);
const clickText = (selector, label) => b.evaluate(`(() => { const el = [...document.querySelectorAll(${JSON.stringify(selector)})].find((x) => x.textContent.trim() === ${JSON.stringify(label)} || x.getAttribute('aria-label') === ${JSON.stringify(label)}); if (!el) return false; el.click(); return true; })()`);
const errorsSince = (n) => b.errors.slice(n);
const sceneMode = () => b.evaluate('window.__tgViewer && !window.__tgViewer.isDestroyed() ? window.__tgViewer.scene.mode : null');
const measure = async (fn) => { await b.evaluate('window.__tgMeter.start(); true'); await fn(); return b.evaluate('window.__tgMeter.stop()'); };
const shot = async (name) => { await b.evaluate('window.scrollTo(0, 0); true'); await sleep(600); const p = join(OUT, `${name}.png`); writeFileSync(p, await b.screenshot()); results.screenshots.push(p); };
const api = (path) => b.evaluate(`fetch(${JSON.stringify('/api/ai/v3' + path)}).then((r) => r.ok ? r.json() : null)`);
const statValue = (label) => b.evaluate(`(() => { const s = [...document.querySelectorAll('.tg-stat')].find((x) => x.querySelector('.tg-stat__label')?.textContent.trim().startsWith(${JSON.stringify(label)})); return s ? s.querySelector('.tg-stat__value').textContent.replace(/[\\s,]/g, '') : null; })()`);
const ist = (iso) => new Date(iso).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'Asia/Kolkata' });
const mapReady = () => b.waitFor(`${q('.cesium-widget canvas')} && /Frame \\d+\\//.test(document.body.innerText)`, 90000);

try {
  /* 1. live-first load */
  await b.goto(`${BASE}?tab=overview`);
  await mapReady();
  await sleep(12000);
  await b.evaluate(METER);
  results.gpu = await b.evaluate(`(() => { const gl = document.createElement('canvas').getContext('webgl2'); const d = gl && gl.getExtension('WEBGL_debug_renderer_info'); return d ? gl.getParameter(d.UNMASKED_RENDERER_WEBGL) : 'unknown'; })()`);
  console.log(`GPU  ${results.gpu}`);
  const liveBadge = await badge();
  check('default view opens on a run with a run-kind badge', /LIVE FORECAST|REPLAY|WHAT-IF|CUSTOM|FORECAST/.test(liveBadge), liveBadge);
  check('disclaimer visible', (await text()).includes('Model forecast — not an official warning'));
  const live = await api('/live/status');
  if (live?.latest) {
    check('live run: badge shows LIVE FORECAST with the /v3 issue time', liveBadge.startsWith('LIVE FORECAST') && liveBadge.includes(ist(live.latest.issued_at)), `${liveBadge} vs issued ${live.latest.issued_at}`);
    check('live run: run picker shows the /v3 latest live run', (await b.evaluate(`${q('select[aria-label="Run on map"]')}?.value`)) === (live.latest.run_id), live.latest.run_id);
    check('live run: source health shown', /Open-Meteo/.test(await text()) && /CFM-DSS/.test(await text()));
  } else check('live run available', false, 'GET /v3/live/status has no latest run (live mode off?)');
  check('Google / Cesium attribution on the map', await b.evaluate(`/Google/.test(document.querySelector('.cesium-widget-credits')?.innerHTML ?? '') && !!document.querySelector('.cesium-credit-logoContainer')`));
  await shot('00_overview_live_run');

  /* 2. switch run: Dec 2015 replay (citywide), then back to the latest live run */
  const replayId = await b.evaluate(`(() => { const s = ${q('select[aria-label="Run on map"]')}; const o = s && [...s.options].find((x) => x.textContent.startsWith(${JSON.stringify(REPLAY_LABEL)}) && /citywide/i.test(x.textContent) && /48 h/.test(x.textContent)) || s && [...s.options].find((x) => x.textContent.startsWith(${JSON.stringify(REPLAY_LABEL)})); return o ? o.value : null; })()`);
  check('Dec 2015 replay run listed', !!replayId, replayId ?? 'none');
  if (replayId) {
    await setValue('select[aria-label="Run on map"]', replayId);
    await b.waitFor(`${q('.tg-top .tg-badge')}?.textContent.startsWith('REPLAY')`, 30000).catch(() => null);
    check('switch to replay shows REPLAY badge', (await badge()).startsWith('REPLAY'), await badge());
    const back = await clickText('button', 'Back to live forecast');
    if (back) {
      await b.waitFor(`${q('.tg-top .tg-badge')}?.textContent.startsWith('LIVE FORECAST')`, 30000).catch(() => null);
      check('back to the latest live forecast', (await badge()).startsWith('LIVE FORECAST'), await badge());
      await setValue('select[aria-label="Run on map"]', replayId);
      await b.waitFor(`${q('.tg-top .tg-badge')}?.textContent.startsWith('REPLAY')`, 30000).catch(() => null);
    } else check('back to the latest live forecast', false, 'no live run / button not shown (live mode off?)');
    await sleep(6000);
  }

  /* 3. timeline: scrub to the flood, play, pause */
  await setValue('input.tg-timeline__range', 50, 'input');
  await b.waitFor('/Frame 51\\//.test(document.body.innerText)', 15000).catch(() => null);
  check('scrub timeline to frame 51', (await frameNo()) === 51, `frame ${await frameNo()}`);
  await sleep(5000);
  if (replayId) {
    const [depth, wards, run] = await Promise.all([api(`/simulations/${replayId}/depth?frame_index=50&layer=depth_mean`), api(`/simulations/${replayId}/wards?frame_index=50`), api(`/simulations/${replayId}`)]);
    const shownMax = parseFloat(await statValue('Max depth'));
    check('overview Max depth = /v3 depth max_value (frame 51)', depth && Math.abs(shownMax - depth.max_value) < 0.006, `UI ${shownMax} m, API ${depth?.max_value}`);
    const affected = (wards?.wards ?? []).filter((w) => (w.max_depth_m ?? 0) >= 0.1).length;
    const shownWards = await statValue('Wards affected');
    check('overview Wards affected = /v3 wards (≥ 0.10 m)', shownWards === `${affected}/${wards?.wards.length}`, `UI ${shownWards}, API ${affected}/${wards?.wards.length}`);
    results.replay = { run_id: replayId, summary: run?.summary ?? null };
  }
  const f0 = await frameNo();
  results.fps.playback = await measure(async () => { await b.click(`${q('button.tg-play')}`); await sleep(10000); await b.click(`${q('button.tg-play[aria-pressed="true"]')}`); });
  const f1 = await frameNo();
  results.fps.playback.framesAdvanced = (f1 - f0 + 97) % 97;
  check('playback advances frames', results.fps.playback.framesAdvanced >= 4, `${results.fps.playback.framesAdvanced} frames in 10 s at ${results.fps.playback.fps} fps`);
  check('playback ≥ 30 fps', results.fps.playback.fps >= 30, `${results.fps.playback.fps} fps, p95 ${results.fps.playback.p95ms} ms`);
  await setValue('input.tg-timeline__range', 50, 'input');
  await sleep(4000);

  /* 4. idle and pan FPS */
  results.fps.idle = await measure(() => sleep(4000));
  const r = await b.evaluate(`(() => { const x = ${q('.cesium-widget canvas')}.getBoundingClientRect(); return { cx: x.x + x.width / 2, cy: x.y + x.height / 2 }; })()`);
  results.fps.pan = await measure(async () => { for (let i = 0; i < 3; i += 1) { await b.drag(r.cx - 160, r.cy, r.cx + 160, r.cy + 40, 45, 16); await b.drag(r.cx + 160, r.cy + 40, r.cx - 160, r.cy, 45, 16); } });
  check('pan ≥ 30 fps', results.fps.pan.fps >= 30, `${results.fps.pan.fps} fps, p95 ${results.fps.pan.p95ms} ms`);

  /* 5. 3D / 2D / Satellite */
  for (const [label, mode] of [['2D Map', 2], ['Satellite', 3], ['3D Digital Twin', 3], ['2D Map', 2], ['3D Digital Twin', 3]]) {
    const n = b.errors.length;
    await clickText('.tg-seg button', label);
    await sleep(3500);
    const m = await sceneMode();
    check(`view mode ${label}`, (m == null || m === mode) && !errorsSince(n).length, `scene.mode ${m}${errorsSince(n).length ? ` errors: ${errorsSince(n).join(' | ')}` : ''}`);
  }

  /* 6. area search */
  await b.evaluate(`(() => { const el = ${q('input[aria-label="Search area, locality or ward"]')}; el.focus(); Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(el, 'Royapuram'); el.dispatchEvent(new Event('input', { bubbles: true })); return true; })()`);
  await b.waitFor(`document.querySelectorAll('#tg-search-list li[role="option"]').length > 0 && !${q('#tg-search-list .tg-search__none')}`, 10000).catch(() => null);
  const hit = await b.evaluate(`(() => { const li = ${q('#tg-search-list li[role="option"]')}; if (!li || li.classList.contains('tg-search__none')) return null; const t = li.textContent; li.dispatchEvent(new MouseEvent('mousedown', { bubbles: true })); return t; })()`);
  await sleep(4500);
  const camPos = await b.evaluate('window.__tgViewer ? (() => { const c = window.__tgViewer.camera.positionCartographic; return [c.longitude * 180 / Math.PI, c.latitude * 180 / Math.PI, c.height]; })() : null');
  check('area search finds Royapuram', !!hit && /royapuram/i.test(hit), hit ?? 'no hit');
  check('camera flies to Royapuram', !camPos || (Math.abs(camPos[1] - 13.11) < 0.08 && Math.abs(camPos[0] - 80.29) < 0.08 && camPos[2] < 15000), camPos ? camPos.map((x) => x.toFixed(3)).join(', ') : 'viewer not exposed (production build)');

  /* 7. tab switching FPS: tour all 7 tabs, 3 s each */
  results.fps.tabSwitch = await measure(async () => {
    for (const [, label] of [...TABS.slice(1), TABS[0]]) { await b.click(`[...document.querySelectorAll('.tg-nav button')].find((x) => x.getAttribute('aria-label') === ${JSON.stringify(label)})`); await sleep(3000); }
  });
  check('tab switching ≥ 30 fps', results.fps.tabSwitch.fps >= 30, `${results.fps.tabSwitch.fps} fps, p95 ${results.fps.tabSwitch.p95ms} ms, ${results.fps.tabSwitch.janky} frames > 50 ms`);

  /* 8. tabs: 0 console errors and a screenshot each (Dec 2015 replay, frame 51, home view) */
  await clickText('.tg-tools button', 'Whole city view');
  await sleep(3000);
  for (const [id, label] of TABS) {
    const n = b.errors.length;
    await b.click(`[...document.querySelectorAll('.tg-nav button')].find((x) => x.getAttribute('aria-label') === ${JSON.stringify(label)})`);
    await sleep(id === 'overview' ? 4000 : 9000);
    if (id === 'simulation' && results.replay?.summary) {
      const sm = results.replay.summary;
      const peak = await statValue('Peak extent');
      check('simulation Peak extent = /v3 summary.flooded_area_km2', peak && Math.abs(parseFloat(peak) - sm.flooded_area_km2) < 0.06, `UI ${peak}, API ${sm.flooded_area_km2}`);
      const roads = await statValue('Roads screened');
      check('simulation Roads screened = /v3 summary.roads_blocked_km', roads && Math.abs(parseFloat(roads) - sm.roads_blocked_km) < 0.6, `UI ${roads}, API ${sm.roads_blocked_km}`);
      check('simulation run details show the run_id', (await text()).includes(results.replay.run_id));
    }
    if (id === 'emergency') {
      const items = await b.evaluate(`document.querySelectorAll('.tg-alerts--scroll .tg-alert').length`);
      check('emergency: incident queue populated', items > 0, `${items} rows`);
    }
    if (id === 'routing') {
      await b.click(`[...document.querySelectorAll('button')].find((x) => x.textContent.trim() === 'Find Routes')`);
      const routed = await b.waitFor(`!!document.querySelector('.tg-table tbody tr') || /no route|not found|unavailable/i.test(document.querySelector('.tg-status')?.textContent ?? '')`, 60000).then(() => true).catch(() => false);
      const rows = await b.evaluate(`[...document.querySelectorAll('.tg-table tbody tr')].map((r) => r.innerText.replace(/\\s+/g, ' ')).slice(0, 4)`);
      check('routing: route request answered', routed && rows.length > 0, rows.join(' / ') || (await b.evaluate(`document.querySelector('.tg-status')?.textContent ?? ''`)));
      await sleep(3000);
    }
    if (id === 'what-if') {
      await b.click(`[...document.querySelectorAll('button')].find((x) => x.textContent.trim() === 'Run What-if Simulation')`);
      const t0 = Date.now();
      const done = await b.waitFor(`/^(Completed:|Saved-results mode)/.test(document.querySelector('.tg-status')?.textContent ?? '') || /fail|error|unavailable|rate/i.test(document.querySelector('.tg-status')?.textContent ?? '')`, 600000, 2000).then(() => true).catch(() => false);
      const status = await b.evaluate(`document.querySelector('.tg-status')?.textContent ?? ''`);
      check('what-if: run completes', done && /^Completed:/.test(status), `${status} (${Math.round((Date.now() - t0) / 1000)} s)`);
      const cmp = await b.evaluate(`[...document.querySelectorAll('.tg-table tbody tr')].map((r) => r.innerText.replace(/\\s+/g, ' ')).slice(0, 3)`);
      check('what-if: comparison table filled', cmp.some((x) => /▲|▼|\d/.test(x.split(' ').slice(-1)[0] ?? '')), cmp.join(' / '));
      await sleep(6000);
    }
    if (id === 'reservoirs') {
      await b.click(`[...document.querySelectorAll('button')].find((x) => /Fetch (published )?snapshot/.test(x.textContent.trim()))`);
      const ok = await b.waitFor(`document.querySelectorAll('.tg-res-cards button').length > 0 || /Unavailable/.test(document.querySelector('.tg-status')?.textContent ?? '')`, 60000).then(() => true).catch(() => false);
      const cards = await b.evaluate(`[...document.querySelectorAll('.tg-res-cards button')].map((x) => x.innerText.replace(/\\s+/g, ' '))`);
      check('reservoirs: published snapshot shown', ok && cards.length > 0, cards.join(' / ') || (await b.evaluate(`document.querySelector('.tg-status')?.textContent ?? ''`)));
      await sleep(3000);
    }
    const errs = errorsSince(n);
    check(`tab ${id}: 0 console errors`, errs.length === 0, errs.join(' | '));
    check(`tab ${id}: map rendered`, await b.evaluate(`!!${q('.cesium-widget canvas')} && ${q('.cesium-widget canvas')}.width > 300`));
    await shot(`${String(TABS.findIndex((t) => t[0] === id) + 1).padStart(2, '0')}_${id.replace('-', '_')}`);
  }
  /* 9. layout passes: every tab at 1366x768 and 1920x1080 (map share of the window, no horizontal scroll) */
  results.layout = {};
  for (const [w, h] of [[1366, 768], [1920, 1080]]) {
    await b.send('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 1, mobile: false });
    await sleep(2500);
    for (const [id, label] of TABS) {
      const n = b.errors.length;
      await b.click(`[...document.querySelectorAll('.tg-nav button')].find((x) => x.getAttribute('aria-label') === ${JSON.stringify(label)})`);
      await sleep(6000);
      const m = await b.evaluate(`(() => { const c = document.querySelector('.cesium-widget canvas')?.getBoundingClientRect(); return { map: c ? [Math.round(c.width), Math.round(c.height)] : null, share: c ? +((c.width * c.height) / (innerWidth * innerHeight)).toFixed(2) : 0, overflowX: document.documentElement.scrollWidth > innerWidth }; })()`);
      (results.layout[`${w}x${h}`] ??= {})[id] = m;
      check(`layout ${w}x${h} ${id}: map ≥ 25% of window, no horizontal scroll, 0 errors`, m.share >= 0.25 && !m.overflowX && errorsSince(n).length === 0, `map ${m.map?.join('x')} (${Math.round(m.share * 100)}%)${errorsSince(n).length ? ` errors: ${errorsSince(n).join(' | ')}` : ''}`);
      await shot(`layout_${w}x${h}_${String(TABS.findIndex((t) => t[0] === id) + 1).padStart(2, '0')}_${id.replace('-', '_')}`);
    }
  }
  results.consoleErrors = b.errors;
  results.tokenInApiRequests = b.requests.filter((r) => r.url.includes('/api/ai')).some((r) => /eyJhbGciOi|AIza/.test(r.url + JSON.stringify(r.headers) + r.body));
  check('no Cesium/Google key in any /api/ai request', !results.tokenInApiRequests);
} catch (e) {
  check('run without exceptions', false, e instanceof Error ? e.message : String(e));
} finally {
  b.close();
}
results.finished = new Date().toISOString();
results.passed = results.checks.filter((c) => c.ok).length;
results.failed = results.checks.filter((c) => !c.ok).length;
writeFileSync(join(OUT, 'e2e_results.json'), JSON.stringify(results, null, 1));
console.log(`\n${results.passed} passed, ${results.failed} failed · FPS idle ${results.fps.idle?.fps} · pan ${results.fps.pan?.fps} · playback ${results.fps.playback?.fps}`);
process.exit(results.failed ? 1 : 0);
