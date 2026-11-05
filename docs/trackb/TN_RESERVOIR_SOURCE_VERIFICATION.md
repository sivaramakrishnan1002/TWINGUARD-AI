# B39 — Tamil Nadu reservoir source readiness

**Disposition: source identified for further review; live readiness not verified.** This is source documentation and a single permitted unauthenticated page check, not a telemetry validation, source-owner confirmation, authorization, or connector test. No credentials, database, service, Docker, package installation, or source-owner contact was used. A21, B38-owned paths, C3, and frozen contracts were not changed.

## Candidate product and access

The exact official candidate is the Tamil Nadu Department of Agriculture – Farmers Welfare Agrisnet page [“Storage and Flow Data on Major Reservoirs”](https://www.tnagrisnet.tn.gov.in/home/reservoir/), published under the Government of Tamil Nadu Agrisnet site. Its displayed table labels a selected date and gives current-year and last-year columns. The official page describes the publisher as the Department of Agriculture – Farmers Welfare. This establishes who publishes this page, but does **not** establish that department as the measurement record holder/operator for every listed reservoir.

The page is publicly addressable. On 2026-11-05, an unauthenticated HTTPS GET to the exact page returned HTTP 200, `text/html; charset=UTF-8`, with a server `Date` response header of `Thu, 05 Nov 2026 07:43:08 GMT`; the response was a client-rendered page shell and the check did not retrieve a table row, data sample, or documented machine endpoint. No page API/XHR endpoint was inferred or called. The official search-indexed rendering showed the table schema and a selected date of 03-07-2026, but that is a dated indexed rendering, not evidence of the current page payload or of current source freshness. The related Agrisnet ARS report route `/ARS/acrs_apc_dashboard/reservoirs/` redirected to an officer login requesting username, password, and OTP; it was not accessed beyond that gate.

Official documentation does not describe a reusable data API, authentication/authorization policy for automated access, rate limits, fees, or permission to retain/redistribute records. No product-specific licence or terms were found in the reviewed official page/documentation. Treat all of these as **UNKNOWN/PENDING**, not as permission granted by a browser-accessible page. The public CFM-DSS dashboard separately shows Chennai-basin reservoir water-level/storage panels and names Poondi, Chembarambakkam, Red Hills, Cholavaram, and Thervoy Kandigai; it does not expose a documented reservoir data schema or downloadable reservoir time series in the reviewed page. It is not substituted for the Agrisnet table.

## Documented fields and unresolved semantics

The official Agrisnet table headings document:

| Field | Published unit/meaning in heading | Status and caveat |
|---|---|---|
| Reservoir name | Name | One row per listed reservoir in the displayed table; spatial point coordinates, basin identifiers, and completeness policy are not documented. |
| Full depth | feet | Reference/full depth; datum and measurement convention UNKNOWN. |
| Full capacity | M.Cft (million cubic feet) | Capacity at an unstated reference condition; source heading only. |
| Current year level | feet | Level meaning, gauge datum, and measurement time UNKNOWN. “Current year” is the page’s label, not a guarantee of a real-time observation. |
| Current year storage | M.Cft | Storage meaning and calculation/version UNKNOWN. |
| Current year inflow | CuSecs (cusecs) | Whether instantaneous, interval mean, or daily total/representative rate is UNKNOWN; interval and measurement time UNKNOWN. |
| Current year outflow | CuSecs (cusecs) | Whether this is total discharge, controlled release, spill, downstream release, or a rate over a defined interval is UNKNOWN. Do not relabel it “release” without owner confirmation. |
| Last year level | feet | Comparator date/selection alignment and measurement-time semantics UNKNOWN. |
| Last year storage | M.Cft | Comparator semantics and revision policy UNKNOWN. |

The table’s published rendering identifies 19 reservoirs, including four Karnataka Cauvery-basin reservoirs and Tamil Nadu reservoirs; this is a table-level scope, not evidence of complete statewide reservoir coverage or of coverage for any requested operating record. No point coordinates or spatial layer were documented. The public Chennai CFM-DSS dashboard identifies its own panels for the four Chennai drinking-water reservoirs plus Thervoy Kandigai, but is a separate product and not evidence that the Agrisnet table is complete for those reservoirs or offers them all.

The public table has a date selector and a displayed `DATE`/selected date. Official materials reviewed do not define whether that date is an observation instant, morning gauge round, reporting date, daily aggregation interval, or publication date. Time of day, timezone/offset, source valid time, publication time, fetch/received time, and their relation are **UNKNOWN**. Keep historical source dates date-only under C3 (`observed_at=null`, timezone unknown); never synthesize midnight or infer Asia/Kolkata. For level versus flow values, measurement timing and whether inflow/outflow refer to an instantaneous rate or a reporting interval require source-owner clarification.

## Cadence, freshness, revisions, and data quality

- **Documented publication cadence:** **UNKNOWN.** A date selector/table and date-stamped render do not document a daily publication commitment or schedule.
- **Update cadence actually observed:** **UNKNOWN.** One unauthenticated GET observed only the HTML shell on 2026-11-05. There was no table-row payload and no repeated observation window. The indexed official rendering dated 03-07-2026 is a single stale snapshot and cannot establish cadence or latency.
- **Publication latency / freshness threshold:** **UNKNOWN.** No source timestamp or documented publication delay supports `LIVE` or `REAL-TIME`.
- **Revision/backfill behavior and provenance:** **UNKNOWN.** No version, source record ID, revision log, source method, or row-level provenance was supplied with the page check. Do not hash or treat the search cache as a sample.
- **Missing/NoData behavior:** **UNKNOWN.** No documented rule explains blank, absent, dash, zero, delayed, or corrected values. Preserve missing as unavailable; zero must remain a value only when explicitly supplied and interpreted by the source owner.
- **Terms, retention, redistribution, rate limits, fees, and automated access permission:** **UNKNOWN/PENDING.** A public page response is not written permission for ingestion or reuse.

## Existing repository evidence and human follow-up

Repository evidence remains consistent with B34: historical Kaggle and OpenCity material is `REPLAY`, not current telemetry; the Kaggle date-only source meaning/timezone is unknown; no verified release series exists. See [B34 inventory](LIVE_SOURCE_READINESS_INVENTORY.md), [authorization decision request](../master/LIVE_SOURCE_AUTHORIZATION_DECISION_REQUEST.md), [C3 contract](../master/contracts/c3_messages_v0.md), and [manual TODO](../MANUAL_TODO.md). Official published references: [Agrisnet reservoir page](https://www.tnagrisnet.tn.gov.in/home/reservoir/), [Agrisnet static reservoir capacity/flow reference](https://www.tnagrisnet.tn.gov.in/dashboard/report/04_07.pdf), [Agrisnet ARS route (login gate)](https://www.tnagrisnet.tn.gov.in/ARS/acrs_apc_dashboard/reservoirs/), [Chennai CFM-DSS dashboard](https://chennaifloodmonitor.tn.gov.in/HomePage/Dashboard), and [CFM-DSS project description](https://chennaifloodmonitor.tn.gov.in/Master/AboutUs).

Before B41 or any live claim, the project owner must identify the authoritative record holder for each intended reservoir/field and obtain written owner confirmation of: product/version and lawful programmatic access; schema/sample and exact source timestamps; units, datum, inflow/outflow/release/gate definitions and measurement intervals; timezone; covered reservoirs; publication/update cadence, latency and freshness; revisions/backfills; missing-value behavior; provenance; terms, retention/redistribution rights, fees/rate limits, and any authentication/custodian requirements. Do not access the ARS login route without a separately authorized process. Until those items are evidenced and D3/D8 are resolved, status is **UNKNOWN/PENDING**, access remains unverified, and values must not be labeled `LIVE`.

## Checks

- B39 source review used official published government pages and one unauthenticated HTTPS GET; no authenticated route or undocumented data API was accessed.
- Focused offline schema/claim-boundary test: `tests/trackb/test_tn_reservoir_source_verification.py`.
- Master state verifier and task selectors are recorded in the closeout state; generic Lane B dirty-path audit reports pre-existing unrelated worktree changes and is not a B39 output conflict.
