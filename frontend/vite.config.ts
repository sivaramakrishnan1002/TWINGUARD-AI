import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// CR-018: during development, mirror the packaged nginx same-origin proxy to the AI service.
const aiTarget = process.env.TWINGUARD_AI_URL ?? 'http://127.0.0.1:8000';

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api/ai': { target: aiTarget, changeOrigin: true, rewrite: (path) => path.replace(/^\/api\/ai/, '') },
    },
  },
});
