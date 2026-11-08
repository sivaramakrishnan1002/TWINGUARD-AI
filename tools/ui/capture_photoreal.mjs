// Before/after captures for the experimental "Photoreal roofs" toggle (B48).
// Usage (dev server on :5173): node tools/ui/capture_photoreal.mjs [baseUrl] [outDir]
// For each view: set the camera, capture with the toggle off, switch it on, wait for tiles, capture again.
import { spawn } from 'node:child_process';
import { existsSync, mkdirSync, mkdtempSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { tmpdir } from 'node:os';

const BASE = process.argv[2] ?? 'http://localhost:5173/';
const OUT = resolve(process.argv[3] ?? 'docs/ui/screenshots');
const VIEWS = [
  ['velachery', { lon: 80.2105, lat: 12.9655, h: 650, heading: 25, pitch: -24 }],
  ['t_nagar', { lon: 80.2300, lat: 13.0330, h: 700, heading: 15, pitch: -26 }],
];
const CHROME = ['C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find((p) => existsSync(p));
const PORT = 9341;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
mkdirSync(OUT, { recursive: true });
const chrome = spawn(CHROME, ['--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${mkdtempSync(join(tmpdir(), 'tg-photo-'))}`, '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader', '--hide-scrollbars', '--window-size=1600,1320', 'about:blank'], { stdio: 'ignore' });
let page;
for (let i = 0; i < 50 && !page; i += 1) { try { page = (await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json()).find((t) => t.type === 'page'); } catch { /* starting */ } if (!page) await sleep(300); }
const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener('open', r, { once: true }));
let id = 0; const pending = new Map();
ws.addEventListener('message', (ev) => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } });
const send = (method, params = {}) => new Promise((r) => { id += 1; pending.set(id, r); ws.send(JSON.stringify({ id, method, params })); });
const evaluate = async (expression) => (await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true })).result?.result?.value;
const settle = async () => {
  const deadline = Date.now() + 90_000;
  while (Date.now() < deadline) {
    await sleep(2000);
    const ok = await evaluate(`(() => { const v = window.__tgViewer; if (!v) return false; let t = true; for (let i = 0; i < v.scene.primitives.length; i++) { const p = v.scene.primitives.get(i); if (p && p.constructor && p.constructor.name === 'Cesium3DTileset') t = t && p.tilesLoaded; } return t && v.scene.globe.tilesLoaded; })()`);
    if (ok) break;
  }
  await sleep(5000);
  await evaluate(`(async () => { const v = window.__tgViewer; for (let i = 0; i < 15; i++) { v.resize(); v.render(); await new Promise((r) => setTimeout(r, 150)); } })()`);
};
const shot = async (name) => { const s = await send('Page.captureScreenshot', { format: 'png' }); writeFileSync(join(OUT, `${name}.png`), Buffer.from(s.result.data, 'base64')); console.log(`${name}.png`); };
const toggle = (on) => evaluate(`(() => { const l = [...document.querySelectorAll('.tg-toggle')].find((x) => x.textContent.includes('Photoreal roofs')); const i = l?.querySelector('input'); if (!i) return 'missing'; if (i.checked !== ${on}) i.click(); return i.checked; })()`);

await send('Emulation.setDeviceMetricsOverride', { width: 1600, height: 1320, deviceScaleFactor: 1, mobile: false });
await send('Page.navigate', { url: `${BASE}${BASE.includes('?') ? '&' : '?'}tab=twin` });
for (let i = 0; i < 40 && !(await evaluate('!!window.__tgViewer')); i += 1) await sleep(1000);
await sleep(4000);
for (const [name, cam] of VIEWS) {
  await toggle(false);
  await evaluate(`(() => { const v = window.__tgViewer; const C = v.camera.position.constructor; v.camera.cancelFlight(); v.camera.setView({ destination: C.fromDegrees(${cam.lon}, ${cam.lat}, ${cam.h} - 86), orientation: { heading: ${cam.heading} * Math.PI / 180, pitch: ${cam.pitch} * Math.PI / 180, roll: 0 } }); return true; })()`);
  await settle();
  await shot(`15_photoreal_${name}_before`);
  console.log('toggle', await toggle(true));
  await settle();
  await shot(`15_photoreal_${name}_after`);
}
await toggle(false);
ws.close();
chrome.kill();
