import { defineConfig, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';
import { cpSync, createReadStream, existsSync, statSync } from 'node:fs';
import { extname, join, normalize, resolve } from 'node:path';

// CR-018: during development, mirror the packaged nginx same-origin proxy to the AI service.
const aiTarget = process.env.TWINGUARD_AI_URL ?? 'http://127.0.0.1:8000';

// B48: CesiumJS needs its Workers/Assets/Widgets/ThirdParty served as static files at CESIUM_BASE_URL.
const CESIUM_BUILD = resolve(__dirname, 'node_modules/cesium/Build/Cesium');
const CESIUM_DIRS = ['Workers', 'ThirdParty', 'Assets', 'Widgets'];
const MIME: Record<string, string> = { '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml', '.wasm': 'application/wasm', '.xml': 'application/xml', '.glb': 'model/gltf-binary', '.ktx2': 'image/ktx2' };

function cesiumStatic(): Plugin {
  return {
    name: 'twinguard-cesium-static',
    configureServer(server) {
      server.middlewares.use('/cesium', (req, res, next) => {
        const rel = normalize(decodeURIComponent((req.url ?? '/').split('?')[0])).replace(/^([/\\])+/, '');
        const file = join(CESIUM_BUILD, rel);
        if (!file.startsWith(CESIUM_BUILD) || !existsSync(file) || !statSync(file).isFile()) return next();
        res.setHeader('Content-Type', MIME[extname(file)] ?? 'application/octet-stream');
        createReadStream(file).pipe(res);
      });
    },
    writeBundle(options) {
      const outDir = options.dir ?? resolve(__dirname, 'dist');
      for (const dir of CESIUM_DIRS) cpSync(join(CESIUM_BUILD, dir), join(outDir, 'cesium', dir), { recursive: true });
    },
  };
}

export default defineConfig({
  plugins: [react(), cesiumStatic()],
  define: { CESIUM_BASE_URL: JSON.stringify('/cesium/') },
  server: {
    proxy: {
      '/api/ai': { target: aiTarget, changeOrigin: true, rewrite: (path) => path.replace(/^\/api\/ai/, '') },
    },
  },
});
