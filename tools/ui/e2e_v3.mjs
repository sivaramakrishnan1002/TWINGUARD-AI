// End-to-end check of the B48 UI against the live C4 v3 API (through the dev/nginx proxy).
// Usage: node tools/ui/e2e_v3.mjs [baseUrl] [screenshotDir]
// Clicks Run Simulation, Run What-if Simulation and Find Routes, waits for results, and screenshots each tab.
import { spawn } from 'node:child_process';
import { existsSync, mkdirSync, mkdtempSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { tmpdir } from 'node:os';

const BASE = process.argv[2] ?? 'http://localhost:5173/';
const OUT = resolve(process.argv[3] ?? 'docs/ui/screenshots');
const CHROME = ['C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find((p) => existsSync(p));
const PORT = 9355;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
mkdirSync(OUT, { recursive: true });

const chrome = spawn(CHROME, ['--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${mkdtempSync(join(tmpdir(), 'tg-e2e-'))}`, '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader', '--window-size=1600,1320', 'about:blank'], { stdio: 'ignore' });
let page;
for (let i = 0; i < 50 && !page; i += 1) { try { page = (await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json()).find((t) => t.type === 'page'); } catch { /* starting */ } if (!page) await sleep(300); }
const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener('open', r, { once: true }));
let id = 0; const pending = new Map();
ws.addEventListener('message', (ev) => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } });
const send = (method, params = {}) => new Promise((r) => { id += 1; pending.set(id, r); ws.send(JSON.stringify({ id, method, params })); });
const evaluate = async (expression) => (await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true })).result?.result?.value;
const waitFor = async (expr, ms = 240_000) => { const t = Date.now(); while (Date.now() - t < ms) { const v = await evaluate(expr); if (v) return v; await sleep(1500); } return null; };
const shot = async (name) => { const s = await send('Page.captureScreenshot', { format: 'png' }); writeFileSync(join(OUT, `${name}.png`), Buffer.from(s.result.data, 'base64')); };
const clickText = (sel, text) => evaluate(`(() => { const b = [...document.querySelectorAll(${JSON.stringify(sel)})].find((x) => x.textContent.includes(${JSON.stringify(text)})); if (!b) return false; b.click(); return true; })()`);
await send('Emulation.setDeviceMetricsOverride', { width: 1600, height: 1320, deviceScaleFactor: 1, mobile: false });
const results = {};

await send('Page.navigate', { url: `${BASE}?tab=simulation` });
results.dataSource = await waitFor(`(() => { const c = [...document.querySelectorAll('.tg-chip')].find((x) => x.textContent.includes('DATA:')); return c && !c.textContent.includes('CONNECTING') ? c.textContent.trim() : null; })()`, 60_000);
await waitFor(`document.querySelectorAll('.tg-runlist button').length > 0`, 60_000);
await clickText('button', 'Run Simulation');
results.simulation = await waitFor(`(() => { const s = document.querySelector('.tg-status'); return s && /Completed|cached|unavailable|rate|failed|error/i.test(s.textContent) ? s.textContent.trim() : null; })()`);
await sleep(8000);
await shot('11_e2e_flood_simulation');

await send('Page.navigate', { url: `${BASE}?tab=what-if` });
await waitFor(`document.querySelectorAll('select[aria-label="Baseline run"] option').length > 0`, 60_000);
await waitFor(`(() => { const b = [...document.querySelectorAll('button')].find((x) => x.textContent.includes('Run What-if Simulation')); return b && !b.disabled; })()`, 60_000);
await clickText('button', 'Run What-if Simulation');
results.whatIf = await waitFor(`(() => { const s = document.querySelector('.tg-status'); return s && /Completed|closest|unavailable|rate|failed|error|not completed|not found/i.test(s.textContent) ? s.textContent.trim() : null; })()`);
results.whatIfTable = await evaluate(`[...document.querySelectorAll('.tg-table tbody tr')].slice(0, 3).map((r) => r.textContent.replace(/\\s+/g, ' ').trim())`);
await sleep(8000);
await shot('12_e2e_what_if');

await send('Page.navigate', { url: `${BASE}?tab=routing` });
await waitFor(`!!document.querySelector('select[aria-label="Destination shelter"] option')`, 60_000);
await waitFor(`(() => { const b = [...document.querySelectorAll('button')].find((x) => x.textContent.includes('Find Routes')); return b && !b.disabled; })()`, 90_000);
await clickText('button', 'Find Routes');
results.route = await waitFor(`(() => { const t = document.querySelector('.tg-panel[aria-label="Candidate Routes"] table'); const s = document.querySelector('.tg-status'); return t ? t.textContent.replace(/\\s+/g, ' ').trim().slice(0, 240) : s ? s.textContent.trim() : null; })()`, 120_000);
await sleep(8000);
await shot('13_e2e_road_routing');

console.log(JSON.stringify(results, null, 2));
ws.close();
chrome.kill();
