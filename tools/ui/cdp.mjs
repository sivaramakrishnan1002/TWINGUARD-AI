// Minimal Chrome DevTools Protocol driver shared by the UI probes and the end-to-end test (no Playwright dependency).
// launch({ gpu: true }) uses the real GPU (ANGLE/D3D11 on Windows); gpu: false uses SwiftShader (CI-like, slow).
import { spawn } from 'node:child_process';
import { existsSync, mkdtempSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';

export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const CHROME = ['C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', '/usr/bin/google-chrome', '/usr/bin/chromium'].find((p) => existsSync(p));

export async function launch({ port = 9391, width = 1600, height = 1000, gpu = true } = {}) {
  if (!CHROME) throw new Error('Chrome or Edge not found');
  const gfx = gpu ? ['--use-angle=d3d11', '--enable-gpu-rasterization', '--ignore-gpu-blocklist'] : ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'];
  const proc = spawn(CHROME, ['--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${mkdtempSync(join(tmpdir(), 'tg-cdp-'))}`, ...gfx,
    '--disable-background-timer-throttling', '--disable-renderer-backgrounding', '--disable-backgrounding-occluded-windows', '--hide-scrollbars', `--window-size=${width},${height}`, 'about:blank'], { stdio: 'ignore' });
  let page;
  for (let i = 0; i < 60 && !page; i += 1) {
    try { page = (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find((t) => t.type === 'page'); } catch { /* starting */ }
    if (!page) await sleep(300);
  }
  if (!page) { proc.kill(); throw new Error('DevTools endpoint not reachable'); }
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((r, j) => { ws.addEventListener('open', r, { once: true }); ws.addEventListener('error', j, { once: true }); });
  let id = 0;
  const pend = new Map();
  const listeners = new Set();
  ws.addEventListener('message', (e) => {
    const m = JSON.parse(e.data);
    if (m.id && pend.has(m.id)) { pend.get(m.id)(m); pend.delete(m.id); return; }
    for (const l of listeners) l(m);
  });
  const send = (method, params = {}) => new Promise((r) => { id += 1; pend.set(id, r); ws.send(JSON.stringify({ id, method, params })); });
  const errors = [];
  const requests = [];
  listeners.add((m) => {
    if (m.method === 'Runtime.exceptionThrown') errors.push(m.params.exceptionDetails.exception?.description?.slice(0, 400) ?? m.params.exceptionDetails.text);
    if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') errors.push(m.params.args.map((a) => a.value ?? a.description).join(' ').slice(0, 400));
    if (m.method === 'Log.entryAdded' && m.params.entry.level === 'error') errors.push(`LOG ${m.params.entry.text.slice(0, 300)} ${m.params.entry.url ?? ''}`);
    if (m.method === 'Network.requestWillBeSent') requests.push({ method: m.params.request.method, url: m.params.request.url, headers: m.params.request.headers, body: m.params.request.postData ?? '' });
  });
  await send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: false });
  await send('Runtime.enable'); await send('Network.enable'); await send('Log.enable'); await send('Page.enable');
  const evaluate = async (expression) => {
    const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    if (r.result?.exceptionDetails) throw new Error(`evaluate: ${r.result.exceptionDetails.exception?.description ?? r.result.exceptionDetails.text}`);
    return r.result?.result?.value;
  };
  return {
    send, evaluate, errors, requests,
    on: (fn) => listeners.add(fn),
    goto: async (url) => { await send('Page.navigate', { url }); },
    screenshot: async () => Buffer.from((await send('Page.captureScreenshot', { format: 'png' })).result.data, 'base64'),
    /** wait until expression is truthy */
    waitFor: async (expression, timeoutMs = 60000, step = 250) => {
      const t0 = Date.now();
      for (;;) { const v = await evaluate(expression).catch(() => null); if (v) return v; if (Date.now() - t0 > timeoutMs) throw new Error(`timeout: ${expression.slice(0, 120)}`); await sleep(step); }
    },
    click: async (selectorExpr) => evaluate(`(() => { const el = ${selectorExpr}; if (!el) return false; el.scrollIntoView({ block: 'center' }); el.click(); return true; })()`),
    drag: async (x0, y0, x1, y1, steps = 60, stepMs = 16) => {
      await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: x0, y: y0 });
      await send('Input.dispatchMouseEvent', { type: 'mousePressed', x: x0, y: y0, button: 'left', clickCount: 1 });
      for (let i = 1; i <= steps; i += 1) { await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: x0 + ((x1 - x0) * i) / steps, y: y0 + ((y1 - y0) * i) / steps, button: 'left', buttons: 1 }); await sleep(stepMs); }
      await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: x1, y: y1, button: 'left', clickCount: 1 });
    },
    close: () => { try { ws.close(); } catch { /* closed */ } proc.kill(); },
  };
}

/** In-page frame meter: rAF intervals (what the user perceives) plus Cesium scene renders when window.__tgViewer is exposed. */
export const METER = `window.__tgMeter = (() => {
  let on = false, last = 0, gaps = [], renders = 0, off = null;
  const loop = (t) => { if (!on) return; if (last) gaps.push(t - last); last = t; requestAnimationFrame(loop); };
  return {
    start() { gaps = []; last = 0; renders = 0; on = true; requestAnimationFrame(loop); const v = window.__tgViewer; if (v && !v.isDestroyed()) off = v.scene.postRender.addEventListener(() => { renders += 1; }); this.t0 = performance.now(); },
    stop() { on = false; off?.(); off = null; const secs = (performance.now() - this.t0) / 1000; const s = [...gaps].sort((a, b) => a - b); const q = (p) => s.length ? s[Math.min(s.length - 1, Math.floor(p * s.length))] : null;
      return { secs: +secs.toFixed(2), fps: +(gaps.length / secs).toFixed(1), p50ms: +(q(0.5) ?? 0).toFixed(1), p95ms: +(q(0.95) ?? 0).toFixed(1), maxms: +(s[s.length - 1] ?? 0).toFixed(1), janky: s.filter((g) => g > 50).length, sceneRenders: window.__tgViewer ? renders : null, sceneFps: window.__tgViewer ? +(renders / secs).toFixed(1) : null }; },
  };
})(); true`;
