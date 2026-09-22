# IDBI Innovate 2026 — TODO

**Track 03 · Financial Inclusion · MSME Financial Health Card ("SHROFF")**
Round-1 deadline (passed): Jul 13, 2026. **Status: shortlisted, Top 24.** Currently in the
**Prototype Refinement Phase**, submissions open until **Sep 6, 2026** (extended from Sep 2).
See `given/round-2/` for shortlist, mentor-session, and sandbox-access material.

---

## ✅ Done

### Recon & submission logistics
- [x] Reverse-engineered the Hack2skill SPA backend API → confirmed **deadline extended to Jul 13** (from Jul 9); shortlist = top 25 (Aug 1), prototype phase Aug 2–16, winners Aug 31
- [x] Captured the round-1 submission rules (deck mandatory on official template → PDF; deployment link + GitHub link = shortlisting boosters)
- [x] Moved the official template deck into `given/` and mapped all 15 slides (README)
- [x] Fixed the bias in `explain-3.txt` — now two-sided (approve the invisible-healthy **and** catch the clean-on-paper-risky)

### Design & research
- [x] Parallel research (academic papers, open-source repos, India AA/OCEN/ULI stack, architecture decision) → `BUILD-SPEC-track03.md`
- [x] Locked architecture: **deterministic core, generative shell** (monotonic LightGBM + SHAP; no LLM on the decision path)
- [x] Designed **Pillar 3** — negative-registry cross-reference + PAN-spine entity graph (phoenix-fraud detection)
- [x] Folded in Gayatri's platform-expansion ideas (continuous monitoring, dynamic limit, supply-chain risk)
- [x] Locked tech stack (`STACK.md`) + agent coordination contract (`CONTRACTS.md`)

### Build — SHROFF MVP (works end-to-end)
- [x] `ml/` — 8,000-MSME synthetic generator + 45-feature engine + 4 monotonic LightGBM sub-models → calibrated PD → 300–900 scorecard (**holdout AUC 0.856 / KS 0.575**, LogReg regulator-view baseline 0.867)
- [x] `ml/` — FastAPI scoring service (score, screen, graph, whatif, personas) on :8000
- [x] `ml/screening/` — negative-registry SQLite + PAN-spine entity graph + phoenix detection
- [x] `web/` — Next.js "Underwriter's Ledger" console on :3000 (gauge, radar, verdict stamp, reasons, bank-vs-GST divergence chart, EWS, screening panel, React Flow entity graph); builds clean; live-API + fixture-fallback both verified in a real browser
- [x] Integration + smoke test — **16/16 checks**; 3 personas hold (RAMESH001 769/A/APPROVE ₹12.5L · SURESH002 419/E/DECLINE · PHOENIX003 678/C/REFER-via-phoenix)

### Real-data upgrade (negative registries)
- [x] Upgraded screening to **~45,000 REAL government rows** (99%, was ~4.7k) — captured via headless-browser network inspection + `curl_cffi` TLS impersonation, staged to `ml/screening/seeds/real/*.csv`, loaded offline by `seed_db.py`
- [x] Real sources wired: MahaGST NGTP (11,410 GSTINs), SEBI/NSE debarred PANs (11,631), CBDT defaulters (79), OpenSanctions UAPA/NSE/SEBI/PEP names (20,853), RBI Alert List (95), data.gov.in MCA Strike-Off CINs (900)
- [x] Browser-verified each real source is genuine (RBI Alpari/AvaTrade; MahaGST PLANWELL INDUSTRIES first row; CBDT totalCount=96)
- [x] Confirmed IBBI CIRP + MCA disqualified-DIN are genuinely gated → kept as honestly-labeled `is_sample=1`
- [x] Fixed real false-positive: advisory name-only hits (common names like "Ramesh Kumar") no longer auto-decline — surfaced for manual disposition (bank AML pattern); only exact-ID + phoenix-graph force the verdict
- [x] Re-verified all 3 personas from a cold rebuild; updated `SOURCES.md`

### Proof & benchmark (run locally, captured, published)
- [x] Re-ran the **full pipeline from scratch** — datagen (12s) → features (4s) → train (20s), deterministic (seed 42), combined AUC 0.856 / KS 0.575 reproduced exactly
- [x] Built `ml/train/benchmark.py` — decision-quality benchmark on the untouched holdout: **PD-by-band rank-ordering** (A 1.26% → E 37.42%), **approval simulation** (approve A/B → 41.4% approval, 1.36% bad-rate = 7.6× cleaner than 10.24% population, 94.5% of defaults caught), confusion matrix, score-cutoff tradeoff → `artifacts/benchmark.json`
- [x] Captured **persona input→output** via the live API — all 3 match ground truth (RAMESH good→APPROVE, SURESH default→DECLINE, PHOENIX clean-but-tainted→REFER) → `artifacts/proof_data.json`
- [x] Verified real-data screening through the live API (real MahaGST/CBDT/RBI hits with `is_sample=false`)
- [x] Published a shareable **Pipeline Proof & Benchmark** page → `docs/pipeline-proof.html` (also feeds deck slides 10–11)

### ULI/OCEN output rail (closes the last gap vs the original plan)
- [x] Built the **OCEN 4.0 output rail** — `ml/api/rails.py` reshapes the decision into an OCEN-aligned loan offer with **risk-based pricing** (Band A 13.77% → Band C 18.14% p.a.), reducing-balance EMI, processing fee, validity; `GET /api/ocen/offer/{id}` + `GET /api/rails`
- [x] **DataSourceAdapter registry** — honest status: AA `live-capable` · OCEN `spec-conformant` (output) · ULI/EPFO `adapter-ready` (no fake "connected"; real field shapes)
- [x] **Lending Rail panel** in the console (`lending-rail.tsx`) — origination flow strip (AA→SHROFF→OCEN→IDBI) + the OCEN loan-offer artifact; wired into the health card, live-verified, clean prod build
- [x] Verdict→offer mapping verified: APPROVE→APPROVED (full offer) · REFER→PENDING_MANUAL_REVIEW (priced + review note) · DECLINE→REJECTED (reason). This implements explain-3.txt Step 5 ("plug into ULI/OCEN") + README Track 03 "ULI/OCEN/AA integration"

---

## ✅ Round 1 — submitted, shortlisted (superseded, kept for history)

- [x] Registered the team on Hack2skill as **Walrus Securitas**
- [x] `git` commit + push the public GitHub repo
- [x] Built the **deck** + submitted round 1 on the Hack2skill dashboard before Jul 13
- [x] Shortlisted Top 24 — see `given/round-2/shortlisted-team.txt`, `shortlisting-mail.txt`
- [ ] Deploy **web → Vercel** and **ml → Render** (needs your accounts) — still not done; moved to Phase 2 §G below, now competing against the fuller AWS path in `docs/INFRA-AWS.md`
- [ ] Record the 3-min demo video — still needed for the prototype-phase deliverable

## ⬜ Optional / stretch (from round 1 — mostly folded into Phase 2 below)

- [ ] Second submission on **Track 04 (MSME default prediction)** — shares ~80% of the engine (same GBM+SHAP stack, different label) — business decision, not started

---

## ⬜ Phase 2 — build backlog (compiled after Aug 26 mentor session)

Everything still left to build, pulled from `docs/INFRA-AWS.md`, `docs/TECHNICAL-WALKTHROUGH.md`,
`docs/SANDBOX-FORM-ANSWERS.md`, `given/round-2/track03-competitors-deep-dive.md` §5, and
`given/round-2/data-field-requirements-submission.md`. Items marked **(quick win)** are small,
proven, or already benchmarked — do these first.

### A. Real data — negative-registry scraping gaps
- [ ] MahaGST live refresh — XLSX link embeds a changing "as-on" date; needs link-discovery + `openpyxl`
- [ ] CBDT defaulters live refresh — Akamai-blocked; needs `curl_cffi` TLS-fingerprint impersonation (not in `refresh_live.py` yet)
- [ ] PAN/GSTIN extraction from OpenSanctions `identifiers` column — live-refresh currently pulls names only
- [ ] **(quick win)** Register a free **data.gov.in API key** → removes the 10-row clamp, 900 → 129,694 MCA struck-off rows, zero new code
- [ ] Scheduled/continuous refresh (EventBridge Scheduler + Step Functions) — `refresh_live.py` is on-demand only today
- [ ] `negreg_din` / `cirp_cases` stay synthetic — genuinely gated, no free bulk source exists; revisit only if a paid feed becomes available

### B. Loan products — 2 of 4 real
- [ ] **Invoice / Bill Discounting** — size against a specific invoice's value + the buyer's creditworthiness
- [ ] **Trade Finance** — size against LC/shipment value + trade-cycle length

### C. The agentic layer — designed, zero code yet
- [ ] Read-only "Talk to your Health Card" Q&A agent (tools return already-computed facts only)
- [ ] Continuous post-disbursal monitoring — re-run the EWS pipeline monthly per disbursed loan
- [ ] Adverse-media / entity-risk scanner — reuse the existing `news-module` (Hono+Drizzle+Gemini)
- [ ] RAG over ~8 RBI/SIDBI policy PDFs — regulatory citation on each decline reason
- [ ] Cyber-exposure agent — dark-web/breach/phishing-domain monitoring on the borrower's identity, reusing the PAN-graph (Walrus Securitas overlap)
- [ ] Compliance-citation agent — RBI/DPDP/AML, same read-only-tool pattern

### D. Trust features Track 03 rivals have that we don't
- [ ] **(quick win)** Counterfactual recourse ("what exact change moves DECLINE→APPROVE") — cheap given the monotonic model; SAARTHI has this
- [ ] Fairness/bias audit (demographic-parity check, audit-only) — SAARTHI has this, RBI FREE-AI rewards it
- [ ] Maker-checker approval workflow + model governance screen — presentational, no new modeling; Megalodon's "HealthLens" has this
- [ ] Real external-dataset validation of the core scoring model — UdyamAI/DRISHTi/SAARTHI all validate on real public credit data; ours is synthetic-only on the scoring side (registry screening is already real) — **sharpest gap a juror could name**

### E. Going from "adapter-ready" to actually live
- [ ] Real Account Aggregator connection (Finvu/Setu/OneMoney) — the big unlock, everything downstream is already shaped for it
- [ ] Real EPFO connector — currently a stub on the real establishment-search shape
- [ ] Real ULI connection — needs RBIH lender onboarding, not just sandbox access
- [ ] OCEN Loan Agent registration — so the loan-offer JSON has somewhere real to go
- [ ] Replace `bank_impact` panel's industry-benchmark ranges with IDBI's own real per-application cost — already flagged in-product, not hidden
- [ ] Supabase/Aurora Postgres swap — consent logs, portfolio persistence, auth (`STACK.md`'s named production path, not wired in v1)

### F. Known, proven, not-yet-merged fixes
- [ ] **(quick win)** Token-blocking index for name screening — measured 20ms→0.7ms, same recall, proven in `docs/INFRA-AWS.md` research, never merged into `registry.py`
- [ ] **(quick win)** Lock down CORS (`allow_origins=["*"]` today) — one line, required before anything is public
- [ ] `/api/ready` distinct from `/api/health` — health currently reports `degraded` instead of failing, risks a load balancer routing to a dead container
- [ ] Split serving vs. training Python dependencies — ~211MB off the container image; verify `shap` doesn't eagerly pull in `matplotlib` first

### G. Deployment
- [ ] Actually go live on a public URL — still open. Either `STACK.md`'s Vercel+Render plan, or the fuller AWS path in `docs/INFRA-AWS.md` — needs your go-ahead + cloud accounts connected

**If time is short before Sep 6, priority order: A's data.gov.in key → D's counterfactual recourse → F's name-screening fix.** Highest ratio of impact to effort, in that order.
