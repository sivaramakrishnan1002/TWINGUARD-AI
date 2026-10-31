# A21 preregistration — three-state routing, decision stability, and literature review

**Frozen before comparison:** 2026-10-31 (Asia/Kolkata). Analysis version: `A21-three-state-v1`; route seed `21031`; shelter tie rule and all comparisons below are fixed before outcome inspection. This is a saved-simulation OSSE, not observed route/flood validation.

## Inputs and immutable hashes

All listed inputs were SHA-256 checked before analysis. Any mismatch at execution stops the affected analysis; no source output may be rewritten. Byte lengths are shown so identity is auditable.

| Input | SHA-256 |
|---|---|
| `data/features/routing/time_dependent_batch2/directed_arcs.parquet` | `2656b15ef015f17b8bfd8bf57ac8c2a25741bed3c496c56b5a8880add4b37e30` |
| `data/features/routing/time_dependent_batch2/static_segments.parquet` | `f880831228537af5c52f85a40a4eb03620d6f98ef2480ce00c300a59f13de4c8` |
| `data/features/routing/time_dependent_batch2/snapshot_index.parquet` | `36aad7ae5efbfbebaf2c60bb2c4ceb297718e175c687c79666f038a3e5019aa5` |
| `data/features/routing/time_dependent_batch2/run_summary.json` | `0a044b7229bdf97281ccc3418fe319e0fdbdfc028c148eea2228173e56a05e3f` |
| `data/features/roads/chennai_road_graph.gpkg` | `1cac487841d9b1128bf5e0b846a22b3b7ca2ac9210bc900c3ac0c64232f74b61` |
| `data/features/forecast/batch2_v1/forecast_summary.json` | `0bc0e322041c0d264a214d995912fd648fbda3534616f3e4588122e292e94dba` |
| `data/features/routing/results/batch2_v1/revision_3/route_results.jsonl` | `ee4e33b45268ba869cfc0f3f48eee1c10ac2c5ae83837b1d82165c6ca6c2ea7f` |
| `data/features/routing/results/batch2_v1/revision_3/comparison_metrics.csv` | `b21f007f94c7307b8b0dee5d0500072f30462d66be20ac5a955cc13f42eea6ad` |
| `data/features/routing/results/batch2_v1/revision_3/summary.json` | `3d0784a481aaaf451456e9e9f1bb1291461bb0a3680b6cc7019335d0501adc3b` |
| `data/features/decision/shelters/batch2_v3/allocation_cases.parquet` | `3c204884af00ea0fb713b9f72c04f36f21647c7aa9b5b710bc6c98f03220276d` |
| `data/features/decision/shelters/batch2_v3/allocation_detail.parquet` | `7c9b5e263e6d0201933ae9e4033e345010178af03f1619b9fb66edf7f6925d97` |
| `data/features/decision/shelters/batch2_v3/candidate_facilities.parquet` | `7af8330922a5f0b8e14722f3dd426f1b0290104805e3ff59b7d861e0f1b58171` |
| `data/features/decision/shelters/batch2_v3/run_summary.json` | `ed0f2a2773d26282644b1f4ae7e93c4f16cdc37975bc9f3990644a9f2c75563c` |
| `docs/ROUTING_GRAPH_BATCH2.md` | `5303559d381c50bc0a5b0bee86d552639e57b447648bb065fbb50d759b9f502e` |
| `docs/ROUTING_BATCH2.md` | `035e592dc400a05041de44e1e395d80f674672629a68058fb0e14256b84635f2` |
| `docs/VALIDATION_REPORT.md` | `dd4978c521c31357f566e33db4eb8f1e2edf7f00b953fb9422ee28b5c0a6fdd5` |
| `docs/DECISION_LAB_BATCH2.md` | `a194f75f9f60af55e317b7e564693cf7361523271eaa434e91a25c37cc1d65c0` |
| `docs/SHELTER_ALLOCATION_BATCH2.md` | `e9cb81e27206283c6577c6443b643d50d6c943bc5eaf56e172717f606773bcb2` |

### Saved A08 graph-state archives (20 members × saved horizons per archive)

| Archive | SHA-256 |
|---|---|
| `2015-12-02_perfect_foresight_imerg_snapshots.npz` | `a25711367c9fb1b6224e354f3fa4a4b9c5bace441c2da5404ee6d7d99911a9fc` |
| `2015-12-02_persistence_previous_day_snapshots.npz` | `b9cff0bc3b4a9b25f94c61b66dcbba7f9ca289a3672b71ae57d947b35a2acbee` |
| `2015-12-02_rain_error_q10_snapshots.npz` | `dea5ebac0aaae195602157f9a174893e366dc7435cd61c106f77afb0077440e0` |
| `2015-12-02_rain_error_q50_snapshots.npz` | `f2f47173abf7ca5e21fc79e4803c94356deab0d5d3e7eaacf67654a895d7e9ba` |
| `2015-12-02_rain_error_q90_snapshots.npz` | `0c7c67bf7f9b9725d41ef7901d2d61992ddafd56f8716186573ff47bd7a6a893` |
| `2021-11-13_perfect_foresight_imerg_snapshots.npz` | `6ca267de7159eda0c00f2e6f975e437dbd69258dbad7a6beaa919d67b1ccc2a1` |
| `2021-11-13_persistence_previous_day_snapshots.npz` | `550e23d6d64ac5ba2da7bcf402420f9109496a8cbc984abed29d6ef14710d201` |
| `2021-11-13_rain_error_q10_snapshots.npz` | `3f482ca75650a0eef11b464021814e9e3e78994a4ef00202b3f6b6f8332b5973` |
| `2021-11-13_rain_error_q50_snapshots.npz` | `be527cfee400e3e17e35570909ad6f9ed690a82b1a242335163b4fe0d2d1bf99` |
| `2021-11-13_rain_error_q90_snapshots.npz` | `1d2ea9f159e69f0c8ed91d8ef1c895420d8f7ff2a43cbeac4e8c4d3eb3e2c8cc` |
| `2023-12-04_perfect_foresight_imerg_snapshots.npz` | `7bc72789687daffc13b2e23d47125a1071a80a781af00b73276c38fbbc1c397f` |
| `2023-12-04_persistence_previous_day_snapshots.npz` | `e165722f22e23b4023e08263ce456a39e9e39b638bf56f76c44e0f758115c267` |
| `2023-12-04_rain_error_q10_snapshots.npz` | `4e933b7bbec00abc25ba67ead5263e176b0dbf9cd7d1e6736f9013cbcfda87e2` |
| `2023-12-04_rain_error_q50_snapshots.npz` | `450276f16cb7ca44b8f9ae539d95a1d610748b4ac8146cdbc5fb5bb5a051dba8` |
| `2023-12-04_rain_error_q90_snapshots.npz` | `64622f231dc8e3fc471fafc15256d181654dbb3347161988cbabe2bf2ee98dd3` |

### Saved A05 member-depth archives

All paths use `data/features/forecast/batch2_v1/<event>/<scenario>/depth_members_by_horizon_DERIVED.npz`.

| Event | Scenario | SHA-256 |
|---|---|---|
| 2015-12-02 | perfect_foresight_imerg | `aec5b132b41635d26507f0b2263ca0d13fd0716c52a3d2549822e2bd9a33dda1` |
| 2015-12-02 | persistence_previous_day | `79024792f9a9c9bb4ec4e6b3c6a4a9f50953f7d56141d76c9c482801aaa2adf5` |
| 2015-12-02 | rain_error_q10 | `d90b3a149285e430c256510e41cff51f28c38b77382f527c3b209293b3e062c4` |
| 2015-12-02 | rain_error_q50 | `b3425f7a3fd7536db7f13c74b977c2b5342d2f9be3f5d9bd5a358923c16256e9` |
| 2015-12-02 | rain_error_q90 | `4dc4591f6f6b49565d23c25c74e2e851a058fcc38514bc20d23488560c4b3591` |
| 2021-11-13 | perfect_foresight_imerg | `7c05444cbd217832420096999ba1344f1107cb39b94f8fedea0cb90dc8554e37` |
| 2021-11-13 | persistence_previous_day | `caa0d92d3e4dc254a221afb7719e5212f5eb13a36e2d64e4e04aa13cc45bf8be` |
| 2021-11-13 | rain_error_q10 | `78902122a247cd9b2b44a3b4ca805c7dbde4ce48491f2c0be0a9a5d0450bdcfb` |
| 2021-11-13 | rain_error_q50 | `0c0151f4bb7f0941d6247d90cc69fb8dbdc32b6072c272092054ab00f1b5c11a` |
| 2021-11-13 | rain_error_q90 | `2554e41203d39dfd71fc9a6658a885c94178429569632d719c027efc5ab1f624` |
| 2023-12-04 | perfect_foresight_imerg | `1190f2ba97d402af0768cbd3cb37e2e01aee7ef00282f53f77828c46f5a9ef56` |
| 2023-12-04 | persistence_previous_day | `0049f906fcfd74e16c34c14fbc56cd5988a107528f60084af145f46fe999512b` |
| 2023-12-04 | rain_error_q10 | `17aff2f578eecf4410be404e322a99e470c9523b7e5a3d4912052dc6d490cc5f` |
| 2023-12-04 | rain_error_q50 | `1d353e60a4ff03fe08377d3e8ff3ff69000a93c697b0b295ee35442ca8cf915f` |
| 2023-12-04 | rain_error_q90 | `34f8777471a26c7e76ec6870ec302cb369624574a8bb0e61ccc187778ee7f07f` |

## Frozen methods and denominators

### Edge-state mapping

- A08 ordinary road/tunnel-proxy states OPEN or REDUCED map to `ASSESSED_PASSABLE`; BLOCKED maps to `ASSESSED_BLOCKED`.
- Missing A07 cell, ambiguous segment join, non-finite sampled depth/state, or A08 `UNASSESSED_STRUCTURE` maps to `UNKNOWN`, preserving the most specific existing reason (`NO_A07_ELIGIBLE_CELL`, ambiguous/unmatched key, `UNKNOWN_NODATA`, `UNASSESSED_STRUCTURE`/bridge, or other code). `UNKNOWN` is never converted to dry, passable, blocked, zero, or successful truth.
- Reuse A08's saved assumptions without tuning: ordinary threshold 0.30 m, tunnel/underpass proxy 0.15 m, bridges unassessed, speed multiplier `max(0.2, 1 - 0.8 × depth/threshold)` below threshold. These are screening assumptions, not validated closure/speed laws.

### OD sampling

- Use the directed graph in EPSG:32644. Geographic sector = origin node's quadrant around the median X and median Y of all road nodes from the immutable road-node layer; sectors are NW, NE, SW, SE (boundary ties go east/north). Network-distance band is shortest directed physical distance on the unweighted-by-flood static directed graph: `<5,000 m`, `5,000–<15,000 m`, and `≥15,000 m`.
- Generator: NumPy PCG64 seed 21031. For each of the 12 sector × distance strata in fixed order NW/NE/SW/SE then short/medium/long, permute candidate origin nodes and, for each, candidate destination node IDs; use directed shortest distance to classify reachable candidates. Select the first 10 previously unused directed OD pairs in each stratum. Stop after 500 sampled origins per sector; if fewer than 10 pairs are feasible in any stratum, record the exact infeasibility and do not substitute another stratum. Pair uniqueness is ordered `(origin_osmid, destination_osmid)`.
- Add a separately identified deterministic supplement of up to 12 static-disconnected directed pairs (three per origin sector, seeded selection from distinct SCC labels) so known no-topological-path cases are represented. Supplement cases are excluded from the 120 primary-strata denominator and reported separately.
- Coverage classes are computed from each selected route's edge evidence: full (all edges assessed), partial (some assessed and some unknown), absent (zero assessed edges). Report counts per class; no post-outcome resampling to force a class count.

### Route methods and comparisons

- For every sampled OD and each available A08 `(event, scenario, horizon 6/24/72 h, member 1–20)` snapshot, compute the baseline fail-closed path using only `ASSESSED_PASSABLE` edges and the saved per-edge A08 travel-time cost. If none exists, baseline is `NO_ASSESSED_PATH`.
- Three-state method first returns the same passable-only route if one exists. Otherwise, conditional search admits only `ASSESSED_PASSABLE` and `UNKNOWN` arcs, excludes blocked arcs, minimizes total unknown-edge length first and assessed travel time second (strict lexicographic objective; ties by arc index sequence). Any path with unknown distance is `CONDITIONAL_NEEDS_VERIFICATION`. No route is `NO_PATH`.
- Compare exact directed arc sequences. The shared-path case must match the fail-closed baseline exactly; the secondary result is added only when fail-closed has no path. Report route/no-route/conditional counts, path length, unknown length and share, assessed-edge fraction, and route changes. Denominators: eligible sampled OD × saved snapshot/member combinations; missing snapshots and no-decision cases remain explicit. Requested main grid: 120 primary OD pairs × 3 events × 5 scenarios × 3 saved horizons × 20 members = 54,000 route cases; plus eligible supplement cases separately. No interpolation.
- For forecast-choice OSSE risk summaries, routes selected from members 1–19 are checked against matched saved member 20 only. Calculate simulated blocked-edge/travel exposure/failure only if every route edge has an assessable member-20 state. Incomplete truth remains `UNKNOWN_TRUTH`, excluded from outcome numerator/denominator and reported separately. Member 20 is not used to choose routes.
- A09 revision 3 has only six OD probes and the perfect-foresight scenario. Reproduce its fail-closed assessed-edge behavior for the primary 120-pair comparison; separately compare matching A09 saved rows only for the six identical OD/event/horizon/method probes actually present. Never claim A09 saved records cover the expanded sample.

### Decision stability (secondary, descriptive)

- Routes: for the fixed three-state method, compare each member 1–19 exact directed arc path with the same event/scenario/horizon/OD route for saved member 12. Separately compare same event/member 1–19/horizon/OD across the four non-reference A08 scenarios with the matching `perfect_foresight_imerg` case. Member 20 is held-out simulated truth and excluded from choice stability. Record changed metadata dimensions (member, event, scenario, horizon) as correlates only; no causal attribution if multiple dimensions change.
- Shelters: use A10 `allocation_detail.parquet` only. Sum `allocated_people_model_estimate` by candidate OSM ID within each saved case; the candidate with greatest total is the descriptive representative. Equal maxima are ties; choose the lowest numeric OSM ID only for a deterministic representative and report tie counts. Compare members to the exact event/scenario/horizon `member_id=12`, `capacity_factor=1.0` case. A10 only saved `perfect_foresight_imerg`; cross-scenario stability is therefore unavailable, not synthesized. Report any capacity factor other than 1.0 as recorded context, not a matched nominal comparison. This is not a shelter recommendation.
- Metrics separately: stability `identical choices / member decisions made`; change frequency `changed choices / paired comparable decisions`; scenario-count coverage `decisions made / eligible registered case-member combinations`. Report numerator, denominator, ties, missing/no-decision and unmatched counts/reasons, event/scenario/horizon/member/capacity-factor strata. Fractions describe these simulations; they are not probabilities, calibration, confidence, or a composite score.
- Unknown-priority ranking: rank each explicit unknown road arc by number of distinct tested conditional OD cases whose selected conditional route includes it; tie-break by greater unknown-edge distance contribution, then ascending `arc_index`. Report cases covered and denominator; no unknown changes state. Also report recorded A10 missing-data keys only where explicitly represented. Do not infer missing inputs from absent rows.

### Failures, exclusions, uncertainty, immutable inputs

- Stop affected comparisons on any preregistered input hash mismatch, duplicated/non-unique route or shelter join key, malformed snapshot, or ambiguous matching. Preserve any failed output directory as a failed new version; never overwrite it.
- No-path, absent snapshot, unknown edge evidence, missing allocation, and unknown held-out truth are not zero/success/passable. Keep eligible-case denominator and label no-decision; exclude from paired-choice denominator only when no unambiguous counterpart exists, while reporting unmatched counts and reasons. Do not replace absent member-12 or capacity-factor baselines.
- Report counts/fractions with event- and OD-cluster bootstrap 95% intervals only where at least two event clusters and enough paired OD clusters exist; otherwise state interval unavailable. No thresholds are optimized from comparisons. Failure to meet the registered sample/validity checks means report infeasible/inconclusive rather than loosen criteria.
- No independent observed route closure/access or date-matched flood-depth truth is available in registered evidence. All accuracy/trade-off language is OSSE against another simulated member; no real-world route quality, safety, operational or emergency claim.

## Literature search preregistration

- Publication date range: 2025-01-01 through 2026-10-31. Search date, exact queries, search interface/date, result counts, screening and exclusions will be recorded in the literature report.
- Indexes: OpenAlex Works search API and Crossref works API, using the exact query strings below. For each candidate, follow DOI or venue proceedings links and verify title/authors/date/method on the primary publisher/proceedings page. Search only publication records in range; include peer-reviewed journal/conference papers and clearly mark preprints/technical reports separately.
- Exact query strings, each run in both scholarly indexes: `flood-aware route planning uncertain inundation road network`; `flood routing incomplete flood evidence unknown edge network`; `three-state routing network unknown edge conditional path`; `conditional routing unknown road closure flood verification`; `verification prioritization road closures flood routing information value`; `decision stability scenario-based evacuation routing flood`; `decision-focused value of information flood road network routing`.
- Screening: title/abstract for route planning under flood/road evidence uncertainty, explicit unknown or missing edge treatment, conditional route selection, verification prioritization, scenario decision stability, or decision-focused information value. Retain nearest methodological neighbors even if different hazard/application. Exclude generic flood mapping with no routing/decision method, duplicates, outside-date records, inaccessible records without a verifiable bibliographic record, and non-primary commentary; list exclusions by reason.
- Compare methods, graph state model, how missingness/uncertainty affects traversal, verification/information prioritization, evaluation/ground truth, and overlap with A21. A negative or inconclusive novelty outcome is acceptable. Do not assert novelty from absence of exact terminology.

## Preregistration freeze

This file must be committed before writing/running comparative route or shelter analysis. Any change after comparison starts requires a dated amendment, rationale, affected metrics, and preservation of the original preregistration; post-result changes cannot replace the registered primary analysis.
