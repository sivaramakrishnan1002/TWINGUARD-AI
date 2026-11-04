# B34 — Live-source readiness inventory

**Disposition:** no candidate source is verified as live or authorized for live ingestion. This inventory was built from repository files only on 2026-11-04. No external service was visited, no source owner contacted, no credentials used, no database accessed, and no service started. The machine-readable records are in [`live_source_readiness_inventory.json`](live_source_readiness_inventory.json).

## Findings

### Rainfall

| Candidate | Repository evidence and status | Evidence-backed properties | Gaps before use |
|---|---|---|---|
| GPM IMERG daily V07B | 86 local NetCDF4 files, listed in `docs/DATA_MANIFEST.csv` and `data/raw/weather/imerg/DOWNLOAD_LOG.txt`; **REPLAY** | 0.1° (~10 km), daily UTC, mm/day in manifest verification; selected 2015, 2021, 2023 windows only; per-file hashes; no gauge validation | Product-specific terms still to confirm; no current feed, latency, revision policy, or live authorization evidenced; local gaps stay gaps |
| Open-Meteo ERA5 archive | Nine point series and event-window outputs catalogued; **REPLAY** | ~25 km, EPSG:4326, daily comparison 2015–2023 and selected hourly windows; request evidence uses Asia/Kolkata for event-hour selections; terms recorded as CC BY 4.0 data plus non-commercial/rate-limited API conditions | Reanalysis, not gauge truth; live entitlement, SLA/latency, refresh and revision behavior not established; per-variable timestamp and unit metadata must be checked |
| NASA POWER daily | Nine local point responses; **REPLAY** | Daily 2015–2023, EPSG:4326, local `PRECTOTCORR` metadata says mm/day; UTC is recorded in repository comparison notes | POWER-specific license not found; native grid not quantified in manifest; no live adapter/SLA or gauge validation |
| ERA5 CDS | Not downloaded; **PROPOSED** | Manifest candidate is ~25 km/hourly | Product terms, selected fields/units, timestamp convention, local coverage, access and latency all unknown |
| IMD rainfall | Not downloaded; **PROPOSED** | Manifest describes product-dependent station/grid and hourly/daily candidate | Exact product, station coverage, terms/fees, units, timestamps, access, cadence and latency unknown |

Local rainfall comparisons characterize agreement between gridded products; they do not validate against a gauge. Kaggle rainfall numbers remain unit-uncertain and **INFERRED**, not an authoritative rainfall unit. Missing values remain missing, never zero.

### Reservoir and operations

| Candidate | Repository evidence and status | Evidence-backed properties | Gaps before use |
|---|---|---|---|
| Kaggle Chennai Water Management archive | Local archive; **REPLAY** | Four reservoirs, daily 2004-01-01–2020-12-03; storage described as mcft; archive SHA-256 `7645febde7ccc21871200487139d1c8a84ea90a6dd2eccc93b7d1f06faf69197`; ZIP CRC and row/date checks recorded | No current feed; original operator and measurement semantics unknown; rainfall unit undocumented; no release series. Per C3, preserve `source_date`; `observed_at=null`; timezone unknown; separate `received_at`; no midnight or interval |
| OpenCity / CMWSSB monthly lake storage | Local CSV snapshots; **REPLAY** | Per-reservoir hashes and row counts in manifest; Poondi, Cholavaram, Chembarambakkam, Veeranam, Red Hills/Puzhal 2003–2021; Kannankottai 2020–2021 with 11 blank months; storage in mcft per dataset description; month labels are monthly, generally first of month | Monthly values cannot resolve event-day operations; underlying source terms/custodian and timestamp semantics need confirmation; no live refresh |
| TN WRD / responsible reservoir division or operator series | No series collected; **PROPOSED** | `docs/MANUAL_TODO.md` describes requested levels/storage/inflow/outflow/gates and says no request was sent; Agrisnet historical page requires login/OTP, which was not accessed | Exact record holder/owner, access authorization, terms, units, timestamps/timezone, cadence, latency, coverage, revisions and gaps are unknown. Project owner must identify the record holder and obtain written source documentation/access |
| CWC public monitoring/bulletin candidate | Mentioned in `docs/MANUAL_TODO.md`; **PROPOSED** | Repository review says general current monitoring/public bulletins exist, but reviewed resources did not establish a Chennai historical series | Exact product, Chennai coverage, reusable access, terms, schema, units, timestamp semantics, cadence and latency unknown; no live feed verified |
| CWC Chembarambakkam/Poondi advisory | One local PDF snapshot dated 2020-11-23; **REPLAY** | Manifest hash `b77a8229f164f7ab7748484bd11f54e475f930b8142f33950b5d70e0a71f7bab`; nine-page PDF, partial two-reservoir coverage | One advisory is not a time series; PDF-specific terms not found; cannot represent current state |
| CAG 2017 report annotation | Local retrospective report evidence; **REPLAY** | `docs/MANUAL_TODO.md` records the 2015 Chembarambakkam discharge figures as limited annotation | Not a continuous release/gate series, no per-sample timestamp/timezone, no comparable series for other reservoirs, report terms unknown; do not convert it to telemetry |

There is no repository evidence of an authorized live reservoir or rainfall feed. The archive’s date-only rows do not establish whether the date is a measurement instant, reporting day, or aggregation period. C3’s unknown-time and unknown-timezone representation remains required; the contract policy does not resolve historical source meaning.

### Other relevant system inputs

The repository also contains static spatial context, not live forcing: Copernicus GLO-30 DSM (nominal ~30 m; not bare-earth terrain and vertical datum/QA remain material), OpenStreetMap/Geofabrik extracts (ODbL; no dated closure feed), and WorldPop R2025A 2021 population estimates (~100 m, CC BY 4.0). Their local evidence paths, hashes, vintages, coverage caveats and NoData rules are recorded in the JSON. These inputs cannot establish current terrain updates, road passability, shelter capacity/status, or current population. NoData remains unknown.

Other operational inputs remain absent or incomplete: no complete reservoir release/outflow/gate time series, no verified storm-drain/culvert network, no dated road-closure feed, and no independently validated live flood observation stream. The CWC advisory and CAG report are document snapshots/annotations, not feeds.

## Admission requirements

Before any candidate is connected to the system, the project owner must establish the authorized source owner/access route and terms, then record a sample’s exact provenance/hash, fields and units, coverage/resolution, source timestamp meaning/timezone, cadence, latency, revisions, missing-data behavior and validation evidence. A separate implementation task must define replay/live mode boundaries, freshness/readiness behavior, idempotency and safe failure behavior. Do not infer availability from historical local files, URLs, API examples or planning documents.

The JSON test checks required fields, evidence status, false live-verification flags, and explicit unknowns. It does not perform source access or validate the underlying science.
