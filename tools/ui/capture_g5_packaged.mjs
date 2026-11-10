// B50: capture Tabs 2 and 7 from the packaged UI (http://127.0.0.1:8081) with console, network and label checks.
// Usage: [INCIDENTS=1] [AREA=Velachery] node tools/ui/capture_g5_packaged.mjs <url with ?tab=&run=&frame=> <out.png> [waitMs]
// Prints CONSOLE_ERRORS, label checks, TOKEN_IN_API (ion/Google key seen in any /api/ai request) and the /api/ai calls.
import { spawn } from 'node:child_process';
import { mkdtempSync, writeFileSync } from 'node:fs';
import { join } from 'node:path'; import { tmpdir } from 'node:os';
const [,, url, out, wait = '25000'] = process.argv;
const PORT = 9367; const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const chrome = spawn('C:/Program Files/Google/Chrome/Application/chrome.exe', ['--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${mkdtempSync(join(tmpdir(), 'tg-fc-'))}`, '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader', '--window-size=1600,1320', 'about:blank'], { stdio: 'ignore' });
let page; for (let i = 0; i < 50 && !page; i++) { try { page = (await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json()).find((t) => t.type === 'page'); } catch {} if (!page) await sleep(300); }
const ws = new WebSocket(page.webSocketDebuggerUrl); await new Promise((r) => ws.addEventListener('open', r, { once: true }));
let id = 0; const pend = new Map(); ws.addEventListener('message', (e) => { const m = JSON.parse(e.data); if (m.id && pend.has(m.id)) { pend.get(m.id)(m); pend.delete(m.id); } });
const send = (method, params = {}) => new Promise((r) => { id++; pend.set(id, r); ws.send(JSON.stringify({ id, method, params })); });
const ev = async (x) => (await send('Runtime.evaluate', { expression: x, returnByValue: true, awaitPromise: true })).result?.result?.value;
await send('Emulation.setDeviceMetricsOverride', { width: 1600, height: 1320, deviceScaleFactor: 1, mobile: false });
const logs=[]; ws.addEventListener('message',(e)=>{const m=JSON.parse(e.data); if(m.method==='Runtime.exceptionThrown') logs.push(m.params.exceptionDetails.exception?.description?.slice(0,400)); if(m.method==='Runtime.consoleAPICalled'&&m.params.type==='error') logs.push(m.params.args.map(a=>a.value??a.description).join(' ').slice(0,400));}); await send('Runtime.enable'); await send('Network.enable'); await send('Log.enable');
const apiCalls = []; let tokenInApi = false;
ws.addEventListener('message', (e) => { const m = JSON.parse(e.data);
  if (m.method === 'Network.requestWillBeSent' && m.params.request.url.includes('/api/ai')) { const r = m.params.request; const blob = r.url + JSON.stringify(r.headers) + (r.postData ?? ''); if (/eyJhbGciOi|AIza/.test(blob)) tokenInApi = true; apiCalls.push(r.method + ' ' + r.url.replace(/^https?:\/\/[^/]+/, '')); }
  if (m.method === 'Log.entryAdded' && m.params.entry.level === 'error') logs.push('LOG ' + m.params.entry.text.slice(0, 300)); });
await send('Page.navigate', { url }); await sleep(Number(wait)); 
if (process.env.INCIDENTS) {
  await ev(`(() => { const b = [...document.querySelectorAll('button')].find((x) => x.textContent.trim().startsWith('Layers')); b?.click(); return !!b; })()`);
  await sleep(500);
  await ev(`(() => { const p = document.querySelector('.tg-menu__panel'); const l = p && [...p.querySelectorAll('label')].find((x) => x.textContent.includes('Generated incidents')); const i = l?.querySelector('input'); if (i && !i.checked) i.click(); const b = [...document.querySelectorAll('button')].find((x) => x.textContent.trim().startsWith('Layers')); b?.click(); return !!i; })()`);
}
await ev(`document.querySelector('.tg-search input')?.focus()`);
await send('Input.insertText', { text: process.env.AREA ?? 'Velachery' });
await sleep(1500);
await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 });
await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 });
await ev(`document.activeElement?.blur()`);
await sleep(Number(process.env.SETTLE ?? 35000));
console.log('CONSOLE_ERRORS', logs.length, logs.slice(0,6).join(' || '));
console.log(JSON.stringify(await ev(`(() => { const t = document.body.innerText; const credits = document.querySelector('.cesium-credit-lightbox-overlay, .cesium-widget-credits, .cesium-credit-textContainer')?.textContent ?? ''; const cr = [...document.querySelectorAll('.cesium-widget-credits, .cesium-credit-logoContainer img, .cesium-credit-logoContainer a')].map(e => e.textContent || e.title || e.alt || e.src?.slice(-40)).join(' | ');
  return { runIdShown: t.includes('evt-20261108T152128Z-59eba744'), selected: document.querySelector('select[aria-label="Simulation run"]')?.value ?? document.querySelector('.tg-runlist .is-active')?.textContent,
  replay: /REPLAY|MODEL_FORECAST/.test(t), simulated: t.includes('SIMULATED'), generated: /generated/i.test(t), demoBadges: t.split('DEMO / SIMULATION').length - 1,
  waterMotion: document.querySelector('.tg-legend__note')?.textContent, google: /Google/.test(document.querySelector('.cesium-viewer')?.innerText ?? '') || /google/i.test(cr), credits: cr.slice(0,300),
  flowReqs: performance.getEntriesByType('resource').filter(r=>r.name.includes('/flow')).map(r=>r.name.split('/v3')[1]+' '+r.responseStatus).slice(-3) }; })()`)));
console.log('TOKEN_IN_API', tokenInApi); console.log('API_CALLS', JSON.stringify([...new Set(apiCalls.map((c) => c.replace(/frame_index=\d+/, 'frame_index=N').replace(/bbox=[^&]+/, 'bbox=…')))]));
const s = await send('Page.captureScreenshot', { format: 'png' }); writeFileSync(out, Buffer.from(s.result.data, 'base64'));
ws.close(); chrome.kill();
