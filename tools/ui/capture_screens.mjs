// Capture full-page screenshots of every B48 tab with headless Chrome over the DevTools protocol.
// Usage (dev server running on :5173):
//   node tools/ui/capture_screens.mjs [baseUrl] [outDir]
// Waits for the Cesium viewer and its 3D tiles to load, then renders a few frames before each capture.
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync, existsSync, mkdtempSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { tmpdir } from 'node:os';

const BASE = process.argv[2] ?? 'http://localhost:5173/';
const OUT = resolve(process.argv[3] ?? 'docs/ui/screenshots');
const VIEWS = process.argv[4] === 'views';
const RISE = process.argv[4] === 'rise';
const CLOSE = { lon: 80.2105, lat: 12.9655, h: 650, heading: 25, pitch: -24 };
const SHOTS = RISE ? [0, 1, 2, 3, 4].map((f) => ['twin', `10_velachery_rise_frame${f}`, CLOSE, f]) : VIEWS ? [
  ['twin', '08_citywide_oblique', { lon: 80.215, lat: 12.71, h: 30000, heading: 8, pitch: -38 }],
  ['twin', '09_velachery_closeup', { lon: 80.2105, lat: 12.9655, h: 650, heading: 25, pitch: -24 }],
] : null;
const TABS = [
  ['overview', '01_situation_overview'], ['simulation', '02_flood_simulation'], ['emergency', '03_emergency_support'], ['routing', '04_road_routing'],
  ['what-if', '05_what_if_simulation'], ['reservoirs', '06_reservoir_monitoring'], ['twin', '07_digital_twin_3d_city'],
];
const CHROME = ['C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find((p) => existsSync(p));
if (!CHROME) throw new Error('Chrome or Edge not found');
const W = 1600;
const H = 1320;
const PORT = 9333;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

mkdirSync(OUT, { recursive: true });
const profile = mkdtempSync(join(tmpdir(), 'tg-capture-'));
const chrome = spawn(CHROME, ['--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`, '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--hide-scrollbars', `--window-size=${W},${H}`, 'about:blank'], { stdio: 'ignore' });

async function target() {
  for (let i = 0; i < 50; i += 1) {
    try { const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json(); const page = list.find((t) => t.type === 'page'); if (page) return page; } catch { /* starting */ }
    await sleep(300);
  }
  throw new Error('DevTools endpoint not reachable');
}

const page = await target();
const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener('open', r, { once: true }));
let id = 0;
const pending = new Map();
ws.addEventListener('message', (ev) => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } });
const send = (method, params = {}) => new Promise((r) => { id += 1; pending.set(id, r); ws.send(JSON.stringify({ id, method, params })); });
const evaluate = async (expression) => (await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true })).result?.result?.value;

await send('Page.enable');
await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1, mobile: false });

for (const [tab, name, cam, frameIdx] of SHOTS ?? TABS) {
  if (frameIdx === undefined || frameIdx === 0) await send('Page.navigate', { url: `${BASE}${BASE.includes('?') ? '&' : '?'}tab=${tab}` });
  if (cam && (frameIdx === undefined || frameIdx === 0)) {
    for (let i = 0; i < 30 && !(await evaluate('!!window.__tgViewer')); i += 1) await sleep(1000);
    await sleep(4000);
    await evaluate(`(() => { const v = window.__tgViewer; const C = v.camera.position.constructor; const M = Math; v.camera.cancelFlight(); v.camera.setView({ destination: C.fromDegrees(${cam.lon}, ${cam.lat}, ${cam.h} - 86), orientation: { heading: ${cam.heading} * M.PI / 180, pitch: ${cam.pitch} * M.PI / 180, roll: 0 } }); return true; })()`);
  }
  if (frameIdx !== undefined) {
    for (let i = 0; i < 20 && !(await evaluate(`document.querySelectorAll('.tg-timeline__track button').length > ${frameIdx}`)); i += 1) await sleep(1000);
    await evaluate(`document.querySelectorAll('.tg-timeline__track button')[${frameIdx}].click()`);
    await sleep(2500);
  }
  const deadline = Date.now() + 90_000;
  let state = null;
  while (Date.now() < deadline) {
    await sleep(2000);
    state = await evaluate(`(() => { const v = window.__tgViewer; if (!v || v.isDestroyed()) return { ready: false };
      let tiles = null; for (let i = 0; i < v.scene.primitives.length; i++) { const p = v.scene.primitives.get(i); if (p && p.constructor && p.constructor.name === 'Cesium3DTileset') tiles = p.tilesLoaded; }
      return { ready: tiles !== false && v.scene.globe.tilesLoaded !== false, tiles, globe: v.scene.globe.tilesLoaded, err: !!document.querySelector('.tg-twin__error') }; })()`);
    if (state?.ready) break;
  }
  await sleep(6000); // async primitives (water, roads, rivers) finish building in workers
  await evaluate(`(async () => { const v = window.__tgViewer; for (let i = 0; i < 20 && v && !v.isDestroyed(); i++) { v.resize(); v.render(); await new Promise((r) => setTimeout(r, 150)); } })()`);
  const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
  writeFileSync(join(OUT, `${name}.png`), Buffer.from(shot.result.data, 'base64'));
  console.log(`${name}.png`, JSON.stringify(state));
}

ws.close();
chrome.kill();
