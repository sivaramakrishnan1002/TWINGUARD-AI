# CR-018 — Live prototype integration (same-origin AI proxy and live runs)

**Decision:** approved 2026-11-07. The project owner delegated deciding authority for completing the system to the Integrator session ("decision is completely up to you … make it live and completely full operational"). This CR records the decisions taken under that delegation. Frozen C1–C8 are unchanged; additions are versioned projections.

## 1. Same-origin API proxy (B45 and later live UI)

- The packaged frontend nginx proxies `/api/ai/` to `http://ai-service:8000/` (one `proxy_pass`). The Vite dev server mirrors it (`TWINGUARD_AI_URL`, default `http://127.0.0.1:8000`).
- The proxy strips `Set-Cookie` and adds `Cache-Control: no-store`. Methods are restricted by `limit_except`; GET only unless a later section of this CR names a POST operation.
- Browser code calls relative `/api/ai/...` paths only; no service origins are compiled into the bundle.

## 2. Live reservoir panel (B45)

- The Reservoirs section shows `ReservoirLivePanel` above the demo fixtures. It fetches `GET /api/ai/reservoirs/history` only on user action (no polling), labels data “Latest published dashboard snapshot”, keeps freshness unknown and date-only semantics, and never substitutes demo values on failure.

## Boundaries kept

Research and educational prototype on loopback. No public deployment, credentials, flood warnings, safe-route claims, or operational emergency guidance. Source caveats in CR-014/015/016/017 still apply.
