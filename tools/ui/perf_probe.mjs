// Map performance probe on the real GPU: idle, pan, playback FPS and frame-step latency for one run.
// Usage: node tools/ui/perf_probe.mjs [baseUrl] [runId] [tab] [out.json]
//   e.g. node tools/ui/perf_probe.mjs http://localhost:5173/ evt-20261108T152128Z-59eba744 overview
import { writeFileSync } from 'node:fs';
import { launch, METER, sleep } from './cdp.mjs';

const BASE = process.argv[2] ?? 'http://localhost:5173/';
const RUN = process.argv[3] ?? 'evt-20261108T152128Z-59eba744';
const TAB = process.argv[4] ?? 'overview';
const OUT = process.argv[5];
const b = await launch({ port: 9391, width: 1600, height: 1000, gpu: true });
const longTasks = `window.__tgLong = { total: 0, n: 0 }; new PerformanceObserver((l) => { for (const e of l.getEntries()) { window.__tgLong.total += e.duration; window.__tgLong.n += 1; } }).observe({ type: 'longtask', buffered: false }); true`;
try {
  await b.goto(`${BASE}?tab=${TAB}&run=${RUN}`);
  await b.waitFor(`document.querySelector('.cesium-widget canvas') && /Frame 1\\//.test(document.body.innerText)`, 90000);
  await sleep(20000);
  await b.evaluate(METER);
  await b.evaluate(longTasks);
  const gpu = await b.evaluate(`(() => { const gl = document.querySelector('.cesium-widget canvas').getContext('webgl2') || document.querySelector('.cesium-widget canvas').getContext('webgl'); const d = gl.getExtension('WEBGL_debug_renderer_info'); return d ? gl.getParameter(d.UNMASKED_RENDERER_WEBGL) : 'unknown'; })()`);
  const measure = async (label, fn) => {
    await b.evaluate(`window.__tgLong.total = 0; window.__tgLong.n = 0; window.__tgMeter.start(); true`);
    await fn();
    const m = await b.evaluate(`window.__tgMeter.stop()`);
    const lt = await b.evaluate(`({ ...window.__tgLong })`);
    return { label, ...m, longTaskMs: Math.round(lt.total), longTasks: lt.n };
  };
  const rect = await b.evaluate(`(() => { const r = document.querySelector('.cesium-widget canvas').getBoundingClientRect(); return { x: r.x, y: r.y, w: r.width, h: r.height }; })()`);
  const cx = rect.x + rect.w / 2;
  const cy = rect.y + rect.h / 2;
  const results = { gpu, run: RUN, tab: TAB, mapCanvas: `${Math.round(rect.w)}x${Math.round(rect.h)}`, at: new Date().toISOString() };
  results.idle = await measure('idle 5 s', () => sleep(5000));
  results.pan = await measure('pan (3 drags)', async () => {
    for (let i = 0; i < 3; i += 1) { await b.drag(cx - 150, cy, cx + 150, cy + 40, 45, 16); await b.drag(cx + 150, cy + 40, cx - 150, cy, 45, 16); }
  });
  await sleep(3000);
  const f0 = await b.evaluate(`Number((document.body.innerText.match(/Frame (\\d+)\\//) || [])[1] || 0)`);
  results.playback = await measure('playback 12 s', async () => {
    await b.click(`document.querySelector('button.tg-play')`);
    await sleep(12000);
    await b.click(`document.querySelector('button.tg-play[aria-pressed="true"]')`);
  });
  const f1 = await b.evaluate(`Number((document.body.innerText.match(/Frame (\\d+)\\//) || [])[1] || 0)`);
  results.playback.framesAdvanced = f1 - f0;
  await sleep(2000);
  // frame step latency: set the range input like a user drag, wait for the frame's depth response (if fetched) and two paints
  const step = `async (k) => {
    const input = document.querySelector('input.tg-timeline__range');
    const t0 = performance.now();
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set; setter.call(input, String(k)); input.dispatchEvent(new Event('input', { bubbles: true }));
    const want = 'frame_index=' + k + '&';
    let seen = false;
    for (let i = 0; i < 200; i += 1) {
      const e = performance.getEntriesByType('resource').find((r) => r.name.includes('/depth?') && (r.name.includes(want) || r.name.endsWith('frame_index=' + k)) && r.startTime >= t0 - 1);
      if (e && e.responseEnd > 0) { seen = true; break; }
      if (i > 6 && !seen && !performance.getEntriesByType('resource').some((r) => r.startTime >= t0 - 1 && r.name.includes('/depth?'))) break;
      await new Promise((r) => setTimeout(r, 25));
    }
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
    return { k, ms: Math.round(performance.now() - t0), fetched: seen };
  }`;
  const steps = [];
  for (const k of [10, 30, 50, 70, 90, 51, 52, 53]) { steps.push(await b.evaluate(`(${step})(${k})`)); await sleep(800); }
  results.frameStep = { steps, medianMs: steps.map((s) => s.ms).sort((a, c) => a - c)[Math.floor(steps.length / 2)] };
  // tab switching: click through all 7 tabs; time until the new tab's map canvas has painted, FPS over the whole tour
  const TABS = ['Flood Simulation', 'Emergency Support', 'Road Routing', 'What-if Simulation', 'Reservoir Monitoring', 'Digital Twin (3D City)', 'Situation Overview'];
  const switches = [];
  results.tabSwitch = await measure('tab switching (7 tabs, 3 s each)', async () => {
    for (const label of TABS) {
      const ms = await b.evaluate(`(async () => { const t0 = performance.now(); [...document.querySelectorAll('.tg-nav button')].find((x) => x.getAttribute('aria-label') === ${JSON.stringify(label)}).click();
        for (let i = 0; i < 400; i += 1) { await new Promise((r) => requestAnimationFrame(r)); const c = document.querySelector('.cesium-widget canvas'); if (c && c.width > 300 && document.querySelector('.tg-nav button[aria-current="page"]')?.getAttribute('aria-label') === ${JSON.stringify(label)}) break; }
        await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))); return Math.round(performance.now() - t0); })()`);
      switches.push({ tab: label, ms });
      await sleep(3000);
    }
  });
  results.tabSwitch.switches = switches;
  results.pendingTilesBadge = await b.evaluate(`document.querySelector('.tg-twin__progress')?.textContent ?? null`);
  results.consoleErrors = b.errors.length;
  console.log(JSON.stringify(results, null, 1));
  if (OUT) writeFileSync(OUT, JSON.stringify(results, null, 1));
} finally {
  b.close();
}
