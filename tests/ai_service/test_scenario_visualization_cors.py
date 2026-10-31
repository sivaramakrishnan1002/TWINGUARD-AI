"""B24 exact packaged-origin browser access policy."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/ai-service"))

from app.main import app


ALLOWED_ORIGIN = "http://127.0.0.1:8081"
CATALOG_PATH = "/scenario-visualization-assets"
DETAIL_PATH = "/scenario-visualization-assets/2015-12-02/perfect_foresight_imerg"
RASTER_PATH = "/scenario-visualization-assets/2015-12-02/perfect_foresight_imerg/raster"
_manifest = json.loads((ROOT / "data/features/visualization3d/batch2_v1/manifest.json").read_text(encoding="utf-8"))
_saved_slice = _manifest["scenario_series"][0]["slices"][0]
READ_REQUESTS = (
    pytest.param("catalog", CATALOG_PATH, {}, "application/json", id="catalog"),
    pytest.param("detail", DETAIL_PATH, {}, "application/json", id="detail"),
    pytest.param(
        "raster",
        RASTER_PATH,
        {"valid_time_utc": _saved_slice["valid_time_utc"], "band": "p50"},
        "image/tiff",
        id="raster",
    ),
)


@pytest.mark.parametrize("name,path,params,accept", READ_REQUESTS)
def test_only_packaged_frontend_origin_get_and_accept_are_allowed(name, path, params, accept):
    with TestClient(app) as client:
        preflight = client.options(
            path,
            params=params,
            headers={
                "Origin": ALLOWED_ORIGIN,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Accept",
            },
        )
        assert preflight.status_code == 200
        assert preflight.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
        assert preflight.headers["access-control-allow-methods"] == "GET"
        assert preflight.headers["access-control-allow-headers"].lower() == "accept"
        assert "access-control-allow-credentials" not in preflight.headers

        # The permitted origin can read each mounted operation. Raster bytes
        # are the exact saved asset; CORS adds no new selectors or data.
        response = client.get(path, params=params, headers={"Origin": ALLOWED_ORIGIN, "Accept": accept})
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
        assert "access-control-allow-credentials" not in response.headers
        if name == "raster":
            assert response.headers["content-type"].startswith("image/tiff")
        else:
            assert response.headers["content-type"].startswith("application/json")


@pytest.mark.parametrize("name,path,params,accept", READ_REQUESTS)
@pytest.mark.parametrize("origin", ("http://localhost:5173", "null", "http://127.0.0.1:3000", "http://127.0.0.1:8082"))
def test_other_null_and_development_origins_are_not_granted(name, path, params, accept, origin):
    with TestClient(app) as client:
        response = client.get(path, params=params, headers={"Origin": origin, "Accept": accept})
        # Origins are a browser read policy: the server may process a GET,
        # but it must never grant the browser access with ACAO.
        assert response.status_code == 200
        assert "access-control-allow-origin" not in response.headers
        assert "access-control-allow-credentials" not in response.headers


@pytest.mark.parametrize("name,path,params,accept", READ_REQUESTS)
@pytest.mark.parametrize("method,headers", (("POST", "Accept"), ("GET", "Accept, Authorization"), ("GET", "Content-Type")))
def test_preflight_rejects_other_method_or_header(name, path, params, accept, method: str, headers: str):
    with TestClient(app) as client:
        response = client.options(
            path,
            params=params,
            headers={
                "Origin": ALLOWED_ORIGIN,
                "Access-Control-Request-Method": method,
                "Access-Control-Request-Headers": headers,
            },
        )
        assert response.status_code == 400
        assert "access-control-allow-credentials" not in response.headers
