# IDBI Innovate 2026 — TODO

**Track 03 · Financial Inclusion · MSME Financial Health Card ("SHROFF")**
Round-1 (Proof of Concept / Idea Submission) deadline: **Jul 13, 2026, 23:59 IST**

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

## ⬜ Next — before Jul 13 submission

- [ ] Register the team on Hack2skill (team name + members — solo or with Gayatri?)
- [ ] Review the IP / participation agreement at registration (Walrus is the product — read before accepting)
- [ ] `git` commit + push the **public GitHub repo** (git initialized; needs first commit + public push) — shortlisting booster
- [ ] Deploy **web → Vercel** and **ml → Render** (needs your accounts); add a keep-warm ping for Render free tier — the Vercel URL is the deployment-link booster
- [ ] Build the **deck** (15-slide official template → PDF) from real screenshots + real metrics (`ml/artifacts/metrics.json`: AUC 0.856 / KS 0.575) — **mandatory deliverable**
- [ ] Record the **3-min demo video** (3-persona walk per `RUN.md`) → link on slide 13
- [ ] Submit round 1 on the Hack2skill dashboard before **Jul 13, 23:59 IST**

---

## ⬜ Optional / stretch

- [ ] Get a registered (free) **data.gov.in API key** (needs your login) → removes the 10-row clamp, scales MCA company-master from 900 to the 129,694 struck-off rows available
- [ ] Second submission on **Track 04 (MSME default prediction)** — shares ~80% of the engine (same GBM+SHAP stack, different label)
- [ ] Wire the adverse-media scanner (news-module) as the compliance-overlay adapter (½-day)
- [ ] Supply-chain Tier B: cross-check counterparties against the negative registry (distressed-buyer flag)

## ⬜ Later — if shortlisted (prototype phase, Aug 2–16)

- [ ] Sandbox access arrives ~Aug 4 → swap synthetic data for IDBI's sandbox APIs/datasets
- [ ] Retrain models on sandbox data via the same pipeline
- [ ] Prototype-phase polish + jury Demo Day (Aug 17–28)
