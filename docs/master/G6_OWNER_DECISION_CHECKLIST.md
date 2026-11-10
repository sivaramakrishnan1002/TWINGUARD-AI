# G6 owner-decision checklist (Round 4) — prepared 2026-11-10

**For:** the project owner, directly or through the coordinator's delegation. **Prepared by:** the Integrator. Nothing here is decided yet.

**Where G6 stands:** G6 ("Validation, documentation, release tag v1.0") requires A15 ✔, A17 ✔, **I04**, and now also the Round 4 documentation tasks **A29** (final report/paper refresh) and **B55** (handbook refresh). G0–G5 are `ready`. Tick one option per item. Each item lists a recommended default.

## 1. I04 — release and backup (Integrator executes after these decisions)

| # | Decision | Options | Recommended |
|---|---|---|---|
| 1.1 | Version and tag | `v1.0` on the commit that closes G6 / another name | `v1.0`, an annotated tag on the G6 closure commit |
| 1.2 | Tag scope | Local tag only / also push to a remote (needs M4) | Local tag now; push only after M4 is decided |
| 1.3 | Release contents | Final report + paper (A29), handbook (B55), validation report (A15), gate reports G0–G6, CR/OD log, C4 v3 contract, package instructions | All of these. The repository already holds them; the tag marks them. |
| 1.4 | Required reviews before tagging | Mentor/supervisor review of the final report (M8) / owner review only | Owner review, with the mentor review date recorded (M8) |
| 1.5 | Database dump | Not required / required on a named isolated test database | **Not required.** No G1–G5 or Round 2 work wrote to the shared `twinguard` database. Migrations 100/101 exist only in the isolated `twinguard_trackb_test`. |
| 1.6 | Tokens in builds | Use URL-restricted Google Map Tiles and Cesium ion tokens / rebuild without tokens for any shared image / keep local only | Keep images local. For any demo build shared beyond this machine, use URL-restricted tokens, and never commit `.env.local`. |
| 1.7 | Tag owner and signer | Owner / delegate | Owner (git user Siva10022006) |

## 2. M4 — GitHub repository and push

| # | Decision | Options | Recommended |
|---|---|---|---|
| 2.1 | Create a remote | Yes (private or public) / no | Yes, **private** first |
| 2.2 | What is pushed | Code, docs and small evidence only / also data | Code, docs and evidence. Leave out `data/` (30.5 GB raw plus derived, already git-ignored), Docker images, `.env*`, `backups/` and run stores. |
| 2.3 | Before the first push | Secret scan, licence/attribution file (M7), README | Integrator runs a secret scan (no `AIza`, ion tokens or `.env` in history) and confirms `.gitignore` coverage |
| 2.4 | Who pushes | Owner only | Owner. Sessions never push. |

## 3. M7 — census and licence checks (confirm terms and attribution for the report and README)

| Source | Use in the project | Licence or terms to confirm | Attribution |
|---|---|---|---|
| OpenStreetMap (Geofabrik extract) | Roads, buildings, facilities, shelters | ODbL 1.0 | "© OpenStreetMap contributors" |
| WorldPop | Population exposure | CC BY 4.0 | WorldPop citation |
| Copernicus GLO-30 DEM | Terrain | Copernicus DEM licence (free, with attribution) | "© DLR e.V. 2010–2014 and © Airbus Defence and Space GmbH 2014–2018, provided under COPERNICUS by the European Union and ESA" |
| GPM IMERG (NASA) | Event rainfall | NASA open data | NASA GES DISC citation |
| ERA5 (Copernicus C3S) | Hourly rainfall shape | Copernicus licence | C3S citation |
| Open-Meteo | Forecast rainfall and weather | Free non-commercial use, CC BY 4.0 data | "Weather data by Open-Meteo.com" |
| CFM-DSS public dashboard (Tamil Nadu) | Reservoir snapshot | **No formal terms published.** CR-016/CR-021 bounds apply. | Source name, with no endorsement claim |
| UNOSAT / HDX flood extents | Labels (tier A) | UNOSAT terms (HDX) | UNOSAT citation |
| Sentinel-1 (ESA Copernicus) | SAR diagnostics | Copernicus open licence | Copernicus Sentinel data citation |
| NRSC/NDEM flood maps (2021, 2023) | Diagnostic out-of-event check | Government publication; confirm reuse terms | NRSC citation |
| Kaggle Chennai reservoir levels | Track B replay | Dataset licence on Kaggle (confirm) | Dataset citation |
| Google Map Tiles / Photorealistic 3D Tiles | 3D city in the UI | Google Maps Platform terms (attribution and logo visible; no caching beyond terms) | On-map Google attribution (kept) |
| CesiumJS / Cesium ion | 3D engine, terrain | CesiumJS Apache-2.0; Cesium ion terms (free tier, non-commercial) | Cesium credit (on map) |
| Census data (if used) | — | Confirm whether any census table is used; WorldPop is the population source | — |

**Decision:** the owner confirms each row, or marks it "use removed". The handbook's `16_References_and_Attribution.md` (B55) and the final report (A29) carry the confirmed list.

## 4. M8 — mentor review dates

| # | Decision | Recommended |
|---|---|---|
| 4.1 | Dates for mentor/supervisor review of the final report and demo | Set two dates: a draft review after A29 and B55, and the final demo before tagging `v1.0` |
| 4.2 | Who records the feedback | The owner. The Integrator registers any change requests that come out of it. |

## 5. Closing B40 and B42 (blocked since Round 1)

| Task | State | Recommended |
|---|---|---|
| **B40** IMD rainfall/weather connector | `blocked_prerequisite`; IMD access was never authorized (D2 approved Open-Meteo only) | **Park as superseded.** Live mode (CR-021) uses Open-Meteo model forecasts. Note in Limitations that no gauge or IMD observations are ingested. |
| **B42** observation-triggered recomputation | `blocked_prerequisite` on B40 | **Park as superseded by B51.** The live cycle recomputes on a schedule and on manual refresh from new forecast and reservoir inputs. Recomputation triggered by incoming *observations* stays out of scope. |

When the owner agrees, the Integrator sets both to `parked` with a superseded note. Nothing that G6 requires depends on them.

## 6. After the decisions

1. Lanes finish **A29** (final report/paper) and **B55** (handbook). B54 lands the packaged live screenshots.
2. The Integrator runs the full G6 protocol:
   - requirements and migration-number reconciliation;
   - the full test suite, the raw audit and `verify_state`;
   - the packaged smoke check;
   - `GATE_G6_REPORT.md`.
3. The Integrator then executes I04 under §1 (local tag; no dump if 1.5 holds).
4. The owner pushes, if M4 says so.
