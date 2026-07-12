# CONTRACTS.md — build coordination (AUTHORITATIVE — every agent reads this first)

Product working name: **SHROFF** — "MSME Financial Health Card". Tagline: *"Sees the invisible
borrower — in both directions."* Name is a single constant, renameable later.

Repo root: `/Users/atrey/Desktop/code/hackathons/idbi-innovate-2026`

## Directory ownership (hard boundaries — do not cross)

```
ml/                    ← Track A (datagen agent, then model agent). Python 3.12 via uv.
  pyproject.toml       ← ONLY Track A runs `uv add`. Track B must NOT touch it.
  datagen/generate.py  → writes ml/data/*.parquet + personas.json + DATA.md
  features/build.py    + FEATURES.md
  train/train.py       → ml/artifacts/ (models, calibrator, metrics.json, plots)
  api/                 main.py, schemas.py, scoring.py, reasons.py, decision.py
  screening/           ← Track B (screening agent) ONLY. Stdlib-only code (sqlite3, csv,
                         urllib, json, re). Extra deps go in screening/REQUIREMENTS.txt
                         for the integration agent — never `uv add` from Track B.
web/                   ← Track C (web agent) ONLY. Next.js (create-next-app latest).
RUN.md                 ← integration agent writes this at the end.
```

Ports: ML API **:8000** (uvicorn), web **:3000**. Web reads `NEXT_PUBLIC_ML_API`
(default `http://localhost:8000`). ML API sets CORS `allow_origins=["*"]`.

`ml/api/main.py` mounts screening with a guarded import so boot order never breaks:

```python
try:
    from screening.router import router as screening_router
    app.include_router(screening_router)
except Exception:
    pass  # screening lands via Track B; integration agent verifies mounting
```

## The three demo personas (fixed IDs — must exist consistently in EVERY layer)

All identifiers are format-valid. GSTIN chars 3–12 embed the PAN (this is demoed live).
Checksum digits are NOT enforced anywhere — validators check structure only.

### RAMESH001 — the invisible-but-healthy borrower → APPROVE
- Ramesh Kumar, **"Ramesh Kirana & General Stores"**, proprietorship, Pune, Maharashtra.
- PAN `ABCPR3456K` (4th char P = individual) · GSTIN `27ABCPR3456K1Z5` · UDYAM-MH-26-0012345.
- No CIN/DIN (proprietorship). Requested loan: ₹15,00,000.
- Story in the monthlies: ~₹8L/mo bank inflows growing ~1.5%/mo, UPI share ~0.75, GST filed
  on time 23/24 months, GST-declared turnover ≈ bank inflows (±5%), 4 EPFO employees stable,
  zero bounces, healthy min balances. Top-3 buyer share ~0.55 (mild concentration → advisory).
- **Expected output: score 750–800, band A, verdict APPROVE, amount ≈ ₹12,00,000, 24–36 mo.**

### SURESH002 — clean-on-paper-but-risky → DECLINE
- Suresh Mehta, **"Suresh Trading Co."**, proprietorship, Mumbai, Maharashtra.
- PAN `AKLPM8765D` · GSTIN `27AKLPM8765D1Z3`. Requested loan: ₹10,00,000.
- Story: inflows declining ~20% over last 6 months; 3 bounces in last quarter; GST filed late
  twice + one nil return; **GST-declared turnover ~40% ABOVE bank inflows** (the divergence
  money-shot); visible self-transfer round-tripping; top-3 buyer share 0.78 and his largest
  buyer's GSTIN `27AABCT5678Q1Z9` ("Trident Textiles") sits on the negreg_gstin seed list
  (distressed-counterparty demo).
- **Expected output: score 380–450, band D/E, verdict DECLINE (or REFER w/ ≤₹2L), EWS red.**

### PHOENIX003 — the phoenix borrower → score says maybe, graph says REFER
- **"Nexon Trading Pvt Ltd"**, Delhi, incorporated ~May 2025 (14 months old).
- CIN `U51909DL2025PTC412345` · company PAN `AAECN1234F` · GSTIN `07AAECN1234F1Z2`.
- Promoter: **Vikram Malhotra**, PAN `AEXPM4521C`, DIN `08234567`. Requested: ₹20,00,000.
- Clean thin financials: 14 months modest positive cash flow, GST on time, no bounces.
- **The graph story (Track B seeds this exactly):** Vikram (DIN 08234567) was co-director of
  **"Vertex Impex Pvt Ltd"** CIN `U74999DL2019PTC356789` (company PAN `AABCV9876L`) together
  with **Rakesh Sharma** DIN `07654321`. Vertex: status **Struck Off** (May 2025), present in
  `negreg_company_status` AND its name on the wilful-defaulter `negreg_name` list; Rakesh's DIN
  in `negreg_din` (director_of_struck_off). Nexon and Vertex share a normalized registered
  address (`14 KAROL BAGH INDUSTRIAL AREA DELHI 110005`). Walk: Nexon GSTIN → PAN → CIN →
  Vikram DIN → Vertex → co-director + struck-off + wilful-defaulter hits ⇒ `phoenix_flag: true`.
- **Expected output: score 620–690, band B/C — but overlay forces verdict REFER, reason cites
  the registry + matched identifier.**

## ML API contract (FastAPI, all JSON, prefix `/api`)

- `GET /api/health` → `{"status":"ok","model_version":"v1","artifacts_loaded":true}`
- `GET /api/personas` → `[{id,name,business,city,segment,requested_amount_inr,blurb}]`
- `GET /api/msme/{id}` → `{"profile":{...all profile fields...},"consent":{...ReBIT-style
  artefact: purpose code 103, fetchType PERIODIC, fiTypes [DEPOSIT, GSTR1_3B], consentTypes
  [PROFILE,SUMMARY,TRANSACTIONS]...},"monthly":[{month:"2024-07",...see monthly schema...}]}`
- `POST /api/score` body `{"msme_id":"RAMESH001"}` → **ScoreResponse** (below)
- `GET /api/screen?type=pan|gstin|cin|din|name|account|vpa&value=...` →
  `{"query":{"type":"pan","value":"..."},"hits":[{"registry":"negreg_gstin",
  "list_name":"Maharashtra GST non-genuine taxpayers","matched_on":"GSTIN",
  "confidence":"high"|"advisory","detail":"...","source_url":"...","is_sample":true}]}`
- `GET /api/graph/{pan}` → `{"nodes":[{"id","type":"pan|company|din|gstin|address",
  "label","flag":null|"struck_off"|"wilful_defaulter"|"director_of_struck_off"|"non_genuine"}],
  "edges":[{"source","target","relation"}],"phoenix_flag":bool,"narrative":"one paragraph"}`
- `POST /api/whatif` body `{"msme_id","overrides":{feature_name:value}}` → ScoreResponse (optional/stretch)

### ScoreResponse (exact field names — web fixtures MUST mirror this)

```json
{
  "msme_id": "RAMESH001", "name": "Ramesh Kirana & General Stores",
  "score": 782, "band": "A", "pd_12m": 0.021,
  "sub_scores": {"cash_flow": 84, "growth": 71, "stability": 76, "compliance": 88},
  "decision": {"verdict": "APPROVE", "amount_inr": 1200000, "tenure_months": 24,
               "rationale": "one sentence citing the working-capital norm and band"},
  "reasons": [{"code": "CF-01", "group": "cash_flow", "direction": "positive",
               "text": "Consistent bank inflows averaging ₹8.1L/month with 24-month history",
               "value": "₹8.1L/mo", "shap": 0.42}],
  "overlays": {
    "screening": {"checked": true, "hits": [], "phoenix_flag": false},
    "early_warning": {"level": "green", "triggers": []},
    "supply_chain": {"top3_buyer_share": 0.55, "distressed_counterparties": []}
  },
  "model": {"version": "v1", "auc": 0.0, "ks": 0.0, "trained_on": "synthetic-v1"}
}
```

`reasons`: 3–5 entries, both directions, ordered by |shap|. `verdict` ∈ APPROVE|REFER|DECLINE.

## Scoring + decision policy (model agent implements exactly this)

- 4 monotonic LightGBM sub-models (cash_flow, growth, stability, compliance feature groups) →
  logistic meta-combiner → isotonic-calibrated 12-mo PD. Plus a plain LogReg all-features
  baseline reported side-by-side ("regulator view").
- Scorecard scaling: **score 660 at PD 5%, +72 points per halving of odds**, clamped [300,900].
- Bands: A ≥750 · B 680–749 · C 600–679 · D 500–599 · E <500.
- Sub-scores 0–100 = percentile of each sub-model's (inverted-risk) output vs the synthetic population.
- Amount: `eligible = 0.20 × annualized bank-verified turnover × band_factor` with band_factor
  A 0.65 · B 0.50 · C 0.30 · D 0.15 · E 0; `amount = min(requested, eligible)` rounded to ₹50k.
  Rationale cites the 20% working-capital norm (Nayak committee).
- Tenure: A/B 24–36 · C 12–18 · D 12 · E —.
- Overlay logic (deterministic beats probabilistic): high-confidence registry hit on the
  borrower's own identifiers → **DECLINE**; phoenix_flag or advisory/name-only hit → **REFER**
  (floor: verdict can only get worse via overlays, never better); EWS red → cap band at C.
- EWS rules (last 3 months vs prior 9): inflow drop >25% · ≥2 bounces · GST late/nil streak ≥2 ·
  headcount drop >25% → each a trigger; 0 green, 1 amber, ≥2 red.

## Monthly schema (datagen emits; features consume) — one row per msme per month, 24 months ending 2026-06

`msme_id, month(YYYY-MM), bank_inflow_inr, bank_outflow_inr, eod_balance_avg_inr,
eod_balance_min_inr, days_near_zero, upi_txn_count, upi_inflow_share, bounce_count,
emi_debit_inr, self_transfer_inr, gst_turnover_declared_inr, gst_filed_on_time(0/1),
gst_filing_delay_days, gst_nil_return(0/1), b2b_share, top3_buyer_share, employees_epfo,
wage_bill_inr`

Counterparties table: `msme_id, month, counterparty_gstin, counterparty_name, share`.
Profile table: `msme_id, name, legal_name, entity_type, sector, city, state_code, pan, gstin,
cin, promoter_name, promoter_pan, promoter_din, udyam, incorporated_on, requested_amount_inr,
default_12m(label), is_persona`. Personas are EXCLUDED from training rows.

## Screening SQLite schema (Track B, `ml/screening/registry.db` built by `seed_db.py`)

Tables: `negreg_company_status(cin,name,status,roc,source,is_sample)`,
`negreg_gstin(gstin,trade_name,state,reason,source,is_sample)`,
`negreg_pan(pan,name,category,amount_inr,source,is_sample)`,
`negreg_din(din,name,list_type,source,is_sample)`,
`negreg_name(name_norm,name_raw,list_type,authority,source,is_sample)`,
`cirp_cases(cin,company_name,status,source,is_sample)`,
plus graph tables `companies(cin,name,pan,address_norm,incorporated_on,status)`,
`directors(din,name,pan)`, `directorships(din,cin,role,from_date,to_date)`.
Every row carries `is_sample` (0 = real government data, 1 = synthetic sample mirroring the
real schema) — the UI shows this honestly as a chip.

## Design system (web agent — commit fully, no drift)

**Concept: "The Underwriter's Ledger"** — the paper loan ledger, reborn as a live data console.
Single committed light theme (no dark mode in v1 — one polished theme beats two half-themes).

- Surface: warm paper `#FAF7F1`; panel white `#FFFFFF`; ruled hairlines `#E5DFD3`.
- Ink (text): navy-black `#1A2332`; secondary `#5C6470`; muted `#8A8F98`.
- Primary: ledger teal `#0A6E5C` · accent: saffron `#C2571B` (sparingly) · decline: oxide red
  `#B3372E` · approve-stamp green `#1E6E3C` · refer amber `#8A6D1A`. Status colors are
  reserved for status, never used as chart series colors.
- Type (next/font/google): **Fraunces** for display headings, **IBM Plex Sans** body,
  **IBM Plex Mono** for ALL numerals, identifiers (PAN/GSTIN/DIN), table figures —
  `font-variant-numeric: tabular-nums`. NO Inter, NO Space Grotesk, NO purple gradients.
- Signature detail: **ink-stamp verdict chips** — APPROVE/REFER/DECLINE in a double-ruled
  rounded-rect, letterspaced small caps, rotated ~-2°, stamp-color ink at ~90% opacity.
  Section labels: small-caps mono with a short rule. Tables get ledger ruling (horizontal
  hairlines only). Staggered page-load reveal (CSS animation-delay), subtle and fast.
- Charts (dataviz rules): series palette `#0A6E5C` (teal) then `#C2571B` (burnt saffron) then
  `#3D5A80` (slate blue) — validate with
  `node "path/to/dataviz/scripts/validate_palette.js" "#0A6E5C,#C2571B,#3D5A80" --mode light`
  against surface #FAF7F1 and snap to passing if any check fails. One axis only, never dual-axis
  (bank-vs-GST divergence = two lines, SAME ₹ axis). Legend for ≥2 series + selective direct
  labels; recessive grids; 2px lines; hover tooltips on every chart; text in ink tokens, never
  series color. Score gauge = single arc 300→900 with band ticks; radar = one series fill (teal
  @ 15% opacity, 2px stroke).

## Web pages (Track C)

- `/` landing: product story (problem → 3 pillars → both-directions thesis), CTA to console.
- `/console`: portfolio view — stat tiles (assessed / approved / referred / declined counts from
  fixtures), persona table (name, segment, score-if-scored, verdict stamp), "Run assessment".
- `/console/[id]`: **the Health Card** — identity header (name, PAN/GSTIN mono chips, consent
  artefact popover showing the ReBIT JSON), score gauge + band + verdict stamp, 4-sub-score
  radar, decision panel (amount, tenure, rationale), signed reason codes list, monthly trends
  line chart (bank inflows vs GST-declared turnover — THE divergence view), EWS strip,
  screening panel (registry hits w/ source + is_sample chip), entity graph (React Flow,
  flagged nodes in oxide red, phoenix banner when flag true), supply-chain concentration bar.
- `web/src/lib/api.ts` typed client of the contract; `web/src/lib/fixtures.ts` mirrors the
  EXACT ScoreResponse shapes for all three personas (used automatically when API unreachable —
  demo resilience). `.env.local.example` with NEXT_PUBLIC_ML_API.

## Non-negotiables for every agent

1. Read this file + skim BUILD-SPEC-track03.md before writing anything.
2. Stay in your subtree. Contract fields are law — if something feels wrong, implement the
   contract anyway and flag it in your report.
3. Verify by RUNNING your code before returning; paste real output in your report.
4. Deterministic core, generative shell: nothing generative ever computes a number. LLM
   narrative is optional, env-gated (LLM_API_KEY, OpenAI-compatible model), template
   fallback default ON.
5. Honesty artifacts are features: metrics.json, VALIDATION.md, SOURCES.md, is_sample chips.
