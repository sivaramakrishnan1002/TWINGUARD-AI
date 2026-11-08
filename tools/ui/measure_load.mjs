// Measure B48 cold-load timings in headless Chrome (fresh profile per run).
// Usage: node tools/ui/measure_load.mjs [url] [runs]
// Reports: first contentful paint, tg-viewer-ready, tg-globe-loaded, tg-buildings-loaded (ms from navigation start),
// JS bytes transferred and request count.
import { spawn } from 'node:child_process';
import { existsSync, mkdtempSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';

const URL_ = process.argv[2] ?? 'http://localhost:4173/?tab=overview';
const RUNS = Number(process.argv[3] ?? 2);
const CHROME = ['C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find((p) => existsSync(p));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function once(port) {
  const profile = mkdtempSync(join(tmpdir(), 'tg-measure-'));
  const chrome = spawn(CHROME, ['--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--window-size=1600,1100', 'about:blank'], { stdio: 'ignore' });
  let page;
  for (let i = 0; i < 50 && !page; i += 1) { try { page = (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find((t) => t.type === 'page'); } catch { /* starting */ } if (!page) await sleep(300); }
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((r) => ws.addEventListener('open', r, { once: true }));
  let id = 0; const pending = new Map();
  ws.addEventListener('message', (ev) => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } });
  const send = (method, params = {}) => new Promise((r) => { id += 1; pending.set(id, r); ws.send(JSON.stringify({ id, method, params })); });
  const evaluate = async (expression) => (await send('Runtime.evaluate', { expression, returnByValue: true })).result?.result?.value;
  await send('Emulation.setDeviceMetricsOverride', { width: 1600, height: 1100, deviceScaleFactor: 1, mobile: false });
  await send('Page.navigate', { url: URL_ });
  const t0 = Date.now();
  let res = null;
  while (Date.now() - t0 < 120_000) {
    await sleep(1000);
    res = await evaluate(`(() => { const m = (n) => { const e = performance.getEntriesByName(n)[0]; return e ? Math.round(e.startTime) : null; };
      const fcp = performance.getEntriesByName('first-contentful-paint')[0];
      const rs = performance.getEntriesByType('resource');
      return { fcp: fcp ? Math.round(fcp.startTime) : null, viewer: m('tg-viewer-ready'), globe: m('tg-globe-loaded'), buildings: m('tg-buildings-loaded'),
        requests: rs.length, jsKB: Math.round(rs.filter((r) => r.initiatorType === 'script' || r.name.endsWith('.js')).reduce((s, r) => s + (r.transferSize || r.encodedBodySize || 0), 0) / 1024) }; })()`);
    if (res?.globe && res?.buildings) break;
  }
  ws.close(); chrome.kill();
  return res;
}

const results = [];
for (let i = 0; i < RUNS; i += 1) { const r = await once(9400 + i); results.push(r); console.log(`run ${i + 1}:`, JSON.stringify(r)); }
const med = (k) => { const v = results.map((r) => r?.[k]).filter((x) => x != null).sort((a, b) => a - b); return v.length ? v[Math.floor(v.length / 2)] : null; };
console.log('median:', JSON.stringify({ fcp: med('fcp'), viewer: med('viewer'), globe: med('globe'), buildings: med('buildings'), jsKB: med('jsKB'), requests: med('requests') }));
