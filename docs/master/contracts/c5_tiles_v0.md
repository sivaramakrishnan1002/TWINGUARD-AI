# C5 tile/layer catalogue v0

**Status:** catalogue metadata and model/API projection are evidenced; HTTP tile serving is unavailable. Contract is frozen at v0 for G0.

- `GET /layers` returns JSON catalogue metadata: `layer_key`, `source_layer`, nullable `source_crs`, `target_srid`, `loaded_row_count`, `units`, nullable `zoom`, `attribution`, `vintage`, typed `provenance` (`source_sha256`, `source_url`), `nodata`, and `tile_endpoint_available`. Unknown units are `{}`; unknown metadata remains null or explicitly not declared; zero loaded rows means no features loaded for that catalogue entry.
- Migration 002 defines PostGIS MVT functions returning Mapbox Vector Tile bytes (`bytea`) for evidenced layer families at zoom z 0–22. This proves database function capability, not an HTTP route. The catalogue reports `tile_endpoint_available=false`.
- CRS, units, zoom, attribution, vintage, provenance and NoData are emitted only from catalogue/model evidence. Raster NoData conventions require a raster catalogue before raster layers are advertised.

The current AI OpenAPI Layer projection matches the Track B model, including required-but-nullable `source_crs`, typed source hash/URL provenance, NoData metadata and unavailable tile endpoint. I05's model-conformance test checks those constraints; Track B catalogue tests cover emitted metadata. No backend Layer endpoint or HTTP tile URL is claimed.

Evidence: `database/migrations/002_gis_views_and_mvt.sql`, `services/ai-service/app/database.py`, `services/ai-service/app/main.py`, `tests/trackb/test_catalogue_metadata.py`, `tests/ai_service/test_api.py`, `docs/api/ai-service.yaml`, and `tests/master/test_api_contract_projection.py`. C5 is frozen at v0 for G0; HTTP tile serving remains unavailable.
