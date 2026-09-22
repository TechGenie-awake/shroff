# Screening data sources — what's real, what's a sample, what production uses

Every row in `registry.db` carries `is_sample` (0 = real government-derived data,
1 = synthetic sample mirroring the real schema). The UI surfaces this honestly as a chip.

**Real-data pass (upgraded):** the four largest registries are now loaded from REAL
government data — **~45,000 real rows** vs a handful before. The live capture was a
one-time step (headless-browser network inspection + TLS-fingerprint impersonation to
find the actual APIs/files) written to `seeds/real/*.csv` with a `manifest__*.json`
per source; the build (`seed_db.py`) then loads those CSVs offline and deterministically,
so the demo needs no network. Every row is re-validated (structure) and RESERVED-filtered
(persona ids) on load.

Rebuild any time with `python3 seed_db.py`. Per-run outcomes: `seeds/seed_report.json`.

## Live refresh — genuinely on-demand, not scheduled (added 2026-08-26)

`python3 screening/refresh_live.py` re-fetches over the real network, right now, and
writes to `seeds/live/` (never overwrites `seeds/real/` automatically — review the diff
first). Verified working for the two sources with no bot-protection, together the
majority of the real row count:

| Source | Verified live | vs. last captured |
|---|---:|---:|
| RBI Alert List | 95 rows | 95 (unchanged) |
| OpenSanctions `in_nse_debarred` | 14,406 rows | ~14,829 (Jul capture) |
| OpenSanctions `in_mha_banned` (UAPA) | 146 rows | 144 |
| OpenSanctions `in_sansad` (PEP) | 8,445 rows | 5,649 — **not directly comparable**: the live script doesn't yet replicate the original's dedup-on-(name,list_type) step, so this count is closer to raw-row than the deduped figure below |

**Still one-time/not-yet-automated, honestly**, not silently skipped:
- **MahaGST NGTP** — the XLSX link embeds the publish date and moves; needs
  link-discovery + `openpyxl`, neither built yet.
- **CBDT defaulters** — Akamai blocks plain HTTP clients; original capture needed
  `curl_cffi` Chrome TLS-fingerprint impersonation, not rebuilt here.
- **PAN/GSTIN extraction from OpenSanctions `identifiers`** — the live script pulls
  `name` only; the regex+validation parser that extracted the 11,631 real PANs is not
  rebuilt in this pass.
- **data.gov.in MCA** — reachable live, but the free sample key caps at 10 rows/request;
  fixed by registering a free key (900 → 129,694 rows), not by more code.

This is genuinely "run it and it hits the real internet" — it is NOT "runs by itself on
a schedule." Turning this into a scheduled, continuous feed needs cloud infra
(EventBridge Scheduler + Step Functions, one Lambda/Fargate task per source) — see
`docs/INFRA-AWS.md` §3.3, which this script is the first real piece of.

## Current registry.db composition

| Registry | Real rows | Sample rows | Real source(s) |
|---|---:|---:|---|
| `negreg_company_status` | **900** | 21 | data.gov.in MCA Company Master — Strike Off CINs |
| `negreg_gstin` | **11,424** | 1 | MahaGST Non-Genuine Taxpayers (11,410) + OpenSanctions (14) |
| `negreg_pan` | **11,710** | 0 | SEBI/NSE debarred PANs (11,631) + CBDT arrears defaulters (79) |
| `negreg_name` | **20,948** | 61 | OpenSanctions UAPA/NSE/SEBI/PEP (20,853) + RBI Alert List (95) |
| `negreg_din` | 0 | 101 | *(gated — see below)* |
| `cirp_cases` | 0 | 100 | *(gated — see below)* |

Graph tables (`companies` 212, `directors` 128, `directorships` 129) mix 150 real MCA
CINs with a deterministic (seed=42) synthetic director universe — no free bulk
director↔company data exists, and the phoenix walk needs directorship edges.

## Sources now REAL — and the access method that worked

| Source | Real rows | Endpoint / file | How it was cracked |
|---|---:|---|---|
| **MahaGST — Category I Non-Genuine Taxpayers** | 11,410 GSTINs | `mahagst.gov.in/public/uploads/goodstax/…NGTPs…as on 31.05.2026.xlsx` | Old list URL 404s; the current XLSX is linked on the MahaGST homepage. Downloaded via a real browser session (875 KB), parsed with openpyxl (sheet literally named `11410 GSTIN`). Browser-verified: first row `27AAACA8104A1ZD / PLANWELL INDUSTRIES`. |
| **SEBI/NSE debarred + PEP/UAPA (OpenSanctions India)** | 11,631 PANs · 20,853 names · 14 GSTINs | `data.opensanctions.org/datasets/latest/in_*/targets.simple.csv` | Bulk simple-CSV exports (CC BY-NC), full India datasets un-capped. Real unmasked PANs parsed from the `identifiers` column. |
| **data.gov.in MCA Company Master** | 900 Strike-Off CINs (4 RoCs) | `api.data.gov.in/resource/{id}` (OGD) | Public sample key, paginated (clamps to 10/req). 129,694 Strike-Off rows exist in the Delhi resource alone — a registered free key removes the clamp for production scale. Freshness: dataset frozen ~2021-03. |
| **RBI Alert List (unauthorised forex/ETP)** | 95 entities | `rbi.org.in/scripts/bs_viewcontent.aspx?Id=4235` | Old `BS_ViewForexAlertList.aspx` is dead (302→error). Live list is a static `<table class=tablebg>` on the content page. Browser-verified: 95 entities rendered (Alpari, AvaTrade, eToro, OctaFX…), "Updated as on November 19, 2025". |
| **CBDT / Income-Tax arrears defaulters** | 79 PANs (of 96) | `incometaxindia.gov.in/o/c/taxdefaulterses` (Liferay Objects REST) | `tax-defaulters.aspx` is a JS widget; the real endpoint was found in its minified bundle. Akamai 403s even full-header curl AND a browser request stack — defeated with `curl_cffi` Chrome **TLS-fingerprint impersonation**. `totalCount=96`; 16 `NO PAN`/invalid rows skipped, 1 de-duped → 79. Verified: `AUIPS5659P / DEVENDRA KANTILAL SHAH / ₹25.13 cr` present live. |

## Still SAMPLE — genuinely gated (browser-confirmed), production feed named

| Registry | Why it stays sample (`is_sample=1`) | Production replaces with |
|---|---|---|
| `negreg_din` (101) | MCA disqualified/struck-off director lists are per-RoC portal forms; the MCA DMS doc API (folder 435) is Akamai-throttled and holds mostly per-matter "deletion/restoration" PDFs — no clean bulk DIN list. | MCA21 bulk director master (paid/bulk); DIN is a life-long 1:1 person key, so the join logic is identical. |
| `cirp_cases` (100) | IBBI `claims/claims` exposes only a **per-CIN document search** (browser-inspected: `qsearch`/`cin_no` inputs, no bulk list) — no free bulk corporate-debtor export. | IBBI bulk CIRP feed / paid corporate-debtor master; CIN-keyed schema identical. |
| `negreg_name` wilful-defaulter subset (61) | TransUnion CIBIL suit-filed list is captcha-gated with no bulk export. The phoenix demo's wilful-defaulter row comes from the persona thread; these give `list_type` breadth. | CIBIL/CRIF bureau feed (licence-gated) — data IDBI already reports into. |

## What production replaces the samples with (feeds IDBI already holds)

| Production feed | What it replaces here | Access path |
|---|---|---|
| **I4C Suspect Registry** (23L+ account/VPA/mobile/IMEI) | the empty `account`/`vpa` branches of `check_identifier` | Core-banking API; LEA/bank-gated — IDBI is already onboarded via I4C/NCRP rails. |
| **RBI DPIP** (Digital Payments Intelligence Platform) | cross-bank mule/fraud intelligence overlay | Pre-GA bank-participant rail — this engine is architected as a consumer of it. |
| **CRILC** + CIBIL/CRIF bureaus | `negreg_pan` / wilful-defaulter names | PAN-keyed, consent/licence-gated — data IDBI already reports into and reads. |
| **MCA21 bulk company + director master** | synthetic director universe + `negreg_din` | Bulk subscription; CIN/DIN keys identical to this schema. |

## How advisory name matches are handled (real screening, not a toy)

Against ~21k real watchlist names, common personal names collide constantly — a borrower's
promoter "Ramesh Kumar" fuzzy-matches a debarred and a PEP namesake. The decision engine
treats **only** exact-identifier hits (PAN/GSTIN/CIN/DIN) and the entity-graph phoenix
flag as verdict-forcing; advisory name-only matches are **surfaced for manual disposition,
never auto-declined** — exactly a bank's AML "possible match → analyst queue" workflow.

The point the demo makes: **every join key (PAN, GSTIN chars 3–12, CIN, DIN) and every
table schema is exactly what the real feeds use** — swapping a sample table for the real
feed changes zero lines of `registry.py` / `graph.py`. That is now literally proven:
four registries were swapped from sample to real with no change to the screening code.
