# Track 03 — MSME Financial Health Card: Architecture & Build Spec

> Synthesized from 4 parallel research agents (academic papers, open-source repos, India AA/OCEN/ULI
> stack, architecture decision). All claims cited inline. This is the decision doc — build from it.

## The one-line architecture: **"Deterministic core, generative shell."**

The credit score is a **monotonic-constrained gradient-boosted model (LightGBM/XGBoost) + SHAP reason
codes** — NOT an LLM, NOT RAG, NOT a fine-tuned model. LLMs/agents/RAG sit only at the edges: parsing
messy documents on the way in, and writing human explanations on the way out. **Nothing generative
ever sits on the decision path.** This is the single most important design decision and it's what wins
a PSU-bank jury.

---

## Answering the direct questions

### Should we use RAG?
Only as a tiny support layer — embeddings over ~8 RBI/SIDBI policy PDFs so each decline reason carries
a regulatory citation. It scores nothing. For 8 docs, stuffed context beats building pgvector infra.

### Should we use an AI agent with a harness?
Yes, but at the periphery — a read-only "Talk to your Health Card" Q&A agent whose tools return the
computed features/SHAP/news hits, so it can't hallucinate a number. Memorable demo layer, not the brain.

### Should we use a custom-trained AI model?
Yes — but "custom-trained" = **a gradient-boosted tree model we train on synthetic MSME data**, not a
fine-tuned LLM. Skip LLM fine-tuning entirely: 4 days, no proprietary data, zero payoff.

### Should we use the online credibility scanner (news-module)?
**Yes — it's the differentiator, and it directly solves the "risky-but-clean-on-paper" half of the brief.**
Reuse `/Users/atrey/Desktop/code/work/jobs/molecule-ventures/news-module` (Hono + Drizzle + Postgres +
Gemini; fetch→dedupe→entity-match→rank from NSE/SEBI/Google-News/RSS). Repurpose it as an
**adverse-media / entity-risk scanner**: match the borrower/promoter entity → LLM classifies each hit
(fraud/litigation/regulatory-action/default/positive) with confidence → severity-weighted, time-decayed
**overlay** on the compliance sub-score + a hard "refer to manual review" trigger above threshold.
- It's an **overlay, NOT a GBM feature** — no training data links news hits to defaults, so putting it
  inside the model would be fake. Overlay is honest and defensible.
- Sparse/asymmetric signal (a kirana shop has no news) — frame as a veto/boost, not a dense predictor.
- **Cap at half a day.** It already exists; wiring = one API call + one dashboard panel. If entity
  matching gets fiddly for demo personas, seed the DB with curated articles and say so.

---

## Why GBM/scorecard for the score (evidence, not opinion)

- **HKMA/ASTRI PoC (BIS Papers 148, 2024):** ~6 monthly bank-account variables → XGBoost **AUC 0.937**
  (1-mo), CatBoost 0.934, LogReg 0.916, **CNN only 0.849**. Deep learning lost.
- **Grinsztajn NeurIPS 2022 / Schmitt arXiv:2205.10535 / Lessmann EJOR 2015:** tree ensembles beat
  deep learning on tabular data; "GBM should be the go-to." LogReg is a strong baseline.
- **LLMs as scorers fail:** AUROC ~0.52–0.63 vs 0.85–0.89 for trained ML (PMC12012369); LLMs collapse
  to one-class predictions on credit data (arXiv:2310.00566); their self-explanations don't match
  empirical SHAP (arXiv:2510.25701) — confident score AND confident wrong reason. Disqualifying.
- **RBI FREE-AI committee (Aug 2025):** pushes explainability/auditability; 38% of Indian FIs prefer
  simple explainable models. Saying "monotonic LightGBM + SHAP, FREE-AI-aligned" is a kill shot;
  "GPT decides" is a self-inflicted wound.
- **Small-data nuance (AI-BAAM, arXiv:2510.16066):** with <1K training rows, **LogReg + WOE/IV binning
  beat GBMs outright.** So ship BOTH: an LR+WOE scorecard (the "regulator view") AND a monotonic
  LightGBM, side by side. Costs ~2 hrs, covers both outcomes.

### Build it as FOUR sub-models, not one
Cash-flow · Growth · Stability · Compliance — each a small GBM/scorecard over engineered features,
combined by weighted aggregation. Makes the sub-score radar chart *real*, each independently explainable.
**The four sub-scores ARE the SHAP feature groups.**

---

## The signal set (feature engineering IS the product — ~40–60 features)

Proven predictors from the literature — copy these:
- **log growth rate of average balance** (IV = 0.484, the #1 feature in AI-BAAM — 2x the best app feature)
- min-balance level/change, balance volatility, days-near-zero
- inflow regularity (count + amount coefficient of variation), MoM growth, seasonality
- bounced/returned payments (narration: RETURN/RTN/NACH RTN), OD/CC utilization vs drawing limit
- existing EMI debits (leverage stacking), circular/self-transfer detection (fraud padding)
- **cashless/UPI payment share** (Ghosh-Vallée-Zeng, J.Finance 2026, on Indindifi data: predicts
  approval + lower default; strongest for outflows)
- GST: turnover trend/seasonality, filing punctuality (late-fee incidence), buyer/supplier
  concentration (top-N counterparty GSTINs), B2B vs B2C mix, nil-return streaks
- EPFO: headcount trend, contribution regularity, wage-bill/turnover ratio
- **THE KILLER CROSS-CHECK:** GST-declared turnover vs bank-credit inflows — divergence = inflated
  turnover / cash-heavy business. This is the single strongest MSME fraud check and the demo money-shot.

### "Both directions" without two models
Same feature pipeline, **two heads**: an onboarding PD score + a monthly-refresh early-warning score
(triggers: balance-depletion days, bounced payments, GST nil-filing streaks, inflow collapse). HKMA's
AUC decay (0.94→0.76 over horizon) is the academic justification. Maps to Sahamati's "monitor loan
accounts" AA use case. This is the portfolio-quality differentiator.

---

## Explainability (the step amateur teams skip)

1. **TreeSHAP on the deciding model** (not a surrogate) → per-applicant top 3–4 negative contributors
   (mirrors ECOA's "up to four principal reasons").
2. **Curated reason-code dictionary** (~40 entries, one evening): `gst_filing_gap_days →
   "AA-07: Irregular GST filing (3 missed returns in 12 months)"`. Feature → code → human sentence →
   RAG regulatory citation. This is what makes it feel like a bank product, not a Kaggle notebook.
3. **Monotonic constraints** (`monotone_constraints` — one param): more revenue can never lower the
   score. Guarantees directionally-sane, stable SHAP; fixes the known SHAP-instability problem on
   mid-importance features (MDPI Risks 2025). Almost no team knows this exists.
4. **Show both views:** SHAP waterfall (analyst) + plain-sentence reason codes (borrower). "Same math,
   two audiences."
- Validated by FinRegLab + Stanford (2022/23), patent-documented grouped-SHAP adverse-action pattern,
  AAAI-20 IAAI precedent (Barnwal et al., XGBoost+SHAP on small-business banking data — our exact stack).

---

## Repos to clone (steal like an artist)

1. **optbinning** (530★, Apache-2.0) — scorecard engine: WOE/IV binning, monotonic constraints,
   points-as-reason-codes, AND a `Counterfactual` class = "what to change to get approved" for free.
   Core of the product.
2. **HarshApurva/IntelliCredit** (MIT) — IIT-H Hackathon 2026 top-10, our EXACT problem: Indian GST +
   bank-statement parsing (pdfplumber/PyMuPDF/pytesseract) → LLM extraction → XGBoost+SHAP →
   dashboard. Fork and gut it. Its gaps (no AA, no UPI cash-flow, no scorecard/reason codes, no decision
   engine) = our whitespace.
3. **namebrandon/Sparkov_Data_Generation** (176★, MIT) — persona-based synthetic transaction generator.
   Re-skin personas as MSME archetypes → powers the whole demo. **Day-1 priority.**
4. **shadcn-fintech** (50★, MIT, Next.js) — 11 fintech pages, spending heatmap → cash-flow heatmap,
   cards → Health Card. The UI.
5. **shap** (25.6★, MIT) + optionally **interpretml/interpret** (EBM glassbox) — waterfall per borrower.
6. **iharshlalakiya/statementsparser** (`pip install statementsparser`, MIT) — parses SBI/HDFC/ICICI/
   Axis PDFs, extracts UPI metadata, auto-categorizes. The "upload real bank PDF" wow-moment.
7. **S25Digital/aa-client** (TS FIU client, MIT) + **Sahamati/account-aggregator-standards** (official
   OpenAPI + FI schemas) + **S25Digital/mock-mate** (auto-gen a mock AA server you fully control).

---

## India stack: integrate vs stub (be surgical + honest on the slide)

| Rail | 4-day sandbox? | Verdict |
|------|----------------|---------|
| **AA (bank txns + GSTR1_3B)** | **Yes — Setu AA (bridge.setu.co) or Finvu UAT** | **INTEGRATE FOR REAL.** Live consent→data→decrypt |
| GST via GSP | Yes (Sandbox.co.in free) but redundant with AA GSTR1_3B | Skip |
| OCEN | No public sandbox; spec only (OCEN 4.0) | **Stub** — expose score as OCEN derived-data-provider API |
| ULI | No — regulated-lender onboarding via RBIH only | **Stub** — `ULIConnector` adapter + cite real numbers |
| EPFO | No lender API; not an AA FIP yet | **Mock** synthetic ECR |
| UPI | Not separate — arrives as `mode=UPI` in AA deposit txns | Covered by AA |

**Winning move:** one `DataSourceAdapter` interface (`fetch(consent_ref, range) -> normalized_records`)
with impls `SetuAAAdapter` (live), `GSTAdapter`, `EPFOAdapter` (synthetic), `ULIAdapter` (stub with real
API shape). Say in the submission: "IDBI's sandbox becomes one more adapter, integrated in hours."

### Ecosystem-credibility proof points (what to SHOW)
1. **Real ReBIT consent artefact JSON** — Purpose code 103 (loan underwriting), `fetchType: PERIODIC`,
   `fiTypes: [DEPOSIT, GSTR1_3B]`, `consentTypes: [PROFILE, SUMMARY, TRANSACTIONS]` + FIU→AA→FIP sequence
   diagram. Almost no team knows Purpose codes exist.
2. "GSTN is a live AA FIP since Feb 2023 — GST + bank via one consent, 18-mo window" → demo the
   GST-vs-bank reconciliation fraud check.
3. Position vs ULI with RBI's own Dec-2025 numbers (**64 lenders, 136+ data services**; 600K+ loans /
   ₹27,000 cr, ₹14,500 cr to MSMEs): "ULI has the pipes but no scoring brain — we're the decision layer."
4. Working sandbox screenshots (Setu/Finvu) + the adapter diagram.
5. OCEN 4.0 fluency: expose score as Loan-Agent-consumable API (GST Sahay/SIDBI pattern), name exact
   schema fields per score component.

### Policy anchors for the pitch (be honest about the evidence gap)
- **U.K. Sinha Committee (RBI, 2019)** explicitly recommends cash-flow-based MSME lending — our product
  IS that recommendation implemented. Credit gap ~₹30 lakh crore (SIDBI 2025).
- **CIBIL MSME Pulse (May 2025):** NTC = **57% of PSU-bank originations** at 1.87% delinquency — the
  exact IDBI-relevant fact: PSU banks already originate majority-NTC and need this layer.
- **Invisible Primes (Di Maggio, Mgmt Science 2024):** alt-data approves 15–30% of low-score applicants
  rejected traditionally, at lower rates, with better outcomes AND higher returns. The "healthy-invisible"
  direction, quantified.
- **Honest negative:** no peer-reviewed Indian AA/GST underwriting AUC has been published. Benchmark
  against HKMA (0.93) and AI-BAAM (0.85), and position the Health Card as producing that missing evidence.

---

## Datasets for the prototype (no GST/UPI/EPFO data is public — synthesize)

- **SBA "Should This Loan Be Approved or Denied?"** (~899K labeled US small-business loans) — train core PD.
- **PKDD'99 Berka** (Czech bank, 1M+ real txns + loan outcomes) — template for cash-flow feature engineering.
- **Amex Default Prediction** (458K customers, time-series behavioral) — transaction-behavior patterns.
- **Home Credit Default Risk** — alt-data benchmark.
- **Synthesize GSTR-1/3B + UPI ledgers + EPFO ECR** calibrated to the signal list, in **Sahamati AA JSON
  schema** so the demo is "AA-ready." Say openly: "trained on synthetic data encoding known MSME risk
  economics; production = retrain on IDBI portfolio via same pipeline." Judges respect this over a
  silently-Kaggle-trained model.

---

## Recommended stack

- **Frontend:** Next.js + shadcn/Tailwind + Recharts on Vercel (from shadcn-fintech).
- **Scoring service:** Python FastAPI (LightGBM + shap + sklearn calibration + optbinning) on Railway/Render.
- **Credibility scanner:** existing news-module (Hono+Drizzle+Postgres+Gemini) as-is, one new adapter.
- **LLM:** an LLM for parse/narrate/Q&A (grounded, never scoring).
- **RAG:** stuffed context over ~8 RBI/SIDBI PDFs (don't build infra).

## Demo personas (these two ARE the brief)
- **(a) Invisible-but-healthy:** no CIBIL, 24 months clean GST + growing UPI inflows → **approve ₹8L**.
- **(b) Clean-on-paper-but-risky:** decent statements BUT GST-vs-bank turnover mismatch + inflow
  round-tripping + promoter adverse-media hit → **decline/refer with cited reasons**.

## "Wow" moments (ranked)
1. Live upload of a messy bank-statement PDF → score + decision + reasons in ~15s.
2. What-if slider: "file your pending GST returns → score +41 points" (counterfactuals; nobody else has these).
3. Adverse-media panel lighting up on the risky persona with a real ranked article.
4. "Why was my limit only ₹8L?" → answer cites actual feature values.

## How teams LOSE this (avoid)
- **Unvalidated black box** ("LLM returns a score"). Judge asks "same applicant twice, same score? show
  the ROC" → dead. Fails determinism + ground truth + defensible reasons.
- Over-engineering the pipes (real AA auth/microservices) → demoing plumbing, no scoring.
- Happy-path only (approvals only) → ignored half the brief (portfolio quality).
- **Countermeasures:** deterministic core; a **validation slide** (AUC/KS on held-out synthetic split +
  calibration curve + PD-by-band + honest synthetic-data note) — 2 hrs, almost no team has it, reads as
  "these people could deploy"; the decline persona with reason codes; mock at edges never at core.

---

## 4-day build sequence

- **Day 1 — Data + features.** Synthetic MSME generator (archetypes + economically-motivated default
  labels) — the quant's day, highest leverage. Define AA-format JSON schemas. Feature engine (~50).
  Scaffold FastAPI + Next.js, deploy hello-world so the deployment link exists from hour 6.
- **Day 2 — Score + decision.** Train 4 sub-GBMs (monotonic) + LR/WOE scorecard, calibrate, aggregate,
  band. Decision policy engine (approve/refer/decline + amount = k × avg net inflow). TreeSHAP wiring.
  Generate validation artifacts. Start reason-code dictionary in parallel.
- **Day 3 — Explanation + scanner + dashboard.** Reason-code dictionary + grounded LLM narrative +
  RBI-citation micro-RAG. Wire credibility scanner (½-day cap; seed demo-persona articles). Both
  dashboard views: score dial, radar, SHAP waterfall, what-if slider, adverse-media panel. Build personas.
- **Day 4 — Flourishes + polish + deck.** PDF-upload parse path. Q&A agent. Rehearse until the two
  money-shot personas run flawlessly. Deck (on IDBI template → PDF): problem → architecture
  (deterministic core/generative shell) → validation → explainability → both-sides personas →
  production path. Freeze code mid-afternoon; rehearse.

**Priority order if time collapses:** model+SHAP+decision engine > dashboard > reason codes > personas >
scanner > PDF parse > Q&A agent. Everything above "scanner" is the win condition; below is memorability.

---

# PILLAR 3 — Negative Registry Cross-Reference Engine (the winning differentiator)

Three signal types now, deliberately different in kind:
1. **GBM cash-flow score** — probabilistic, from transactions (Pillar 1).
2. **Adverse-media scanner** — unstructured, from news (news-module, the overlay).
3. **Negative-registry + PAN-spine entity graph** — DETERMINISTIC, from government blocklists (this).

Pillar 3 is the strongest because it's not a probability — "this DIN is on MCA's disqualified-directors
list" / "this CIN is under CIRP" / "this GSTIN is on Maharashtra's non-genuine-taxpayer list" is a
hard, verifiable, government-sourced fact. It's a **veto / manual-review trigger**, not a soft score.

### Correction baked in: UPI PIN is NOT a lookup key
UPI PIN is a secret user credential (like a card PIN) — never stored in any directory, never queryable.
Category error + security red flag. The mappable UPI identifier is the **VPA/handle** (`name@bank`),
which resolves to a linked **bank account + registered mobile**. The I4C Suspect Registry itself accepts
**UPI ID** (not PIN) as a searchable field — industry confirmation. Screen on VPA, account, phone, IMEI,
DIN, CIN, GSTIN, PAN, IEC — never on PIN.

## The killer differentiator: the PAN-spine entity graph (catches "phoenix fraud")

Every screening engine checks the *applicant* against blacklists — that only catches borrowers already
caught. The **phoenix** — a defaulter/struck-off promoter who opens a spotless NEW company — passes
every direct blacklist check because the new entity is genuinely clean. This is EXACTLY the
"risky-but-clean-on-paper" case, at the entity-graph level.

**PAN is the deterministic join key.** Build the graph from three FREE public sources:
- **GSTIN ⇄ PAN is pure string logic** — GSTIN characters 3–12 ARE the PAN. Bidirectional decoder, zero
  dependencies. Demo this first: type a GSTIN, extract the PAN instantly.
- **DIN is one-per-person-for-life** (Companies Act s.155) → a 1:1 proxy for a director's identity across
  all of MCA. MCA even exposes a "Verify DIN-PAN" service.
- **MCA Company Master Data** (bulk) → CIN → directors → co-directors' DINs.

**The graph walk:** borrower PAN → enumerate GSTINs → legal name → MCA name-search → DINs →
directorships → collect **co-directors' DINs** → check the applicant AND every co-director against
(a) struck-off companies, (b) directors-of-struck-off list, (c) wilful-defaulter/suit-filed lists.
A "clean new company" whose promoter or co-promoter touches any tainted node = **phoenix flag**. Shared
registered address / phone / co-directors between a struck-off entity and the new one = corroborating
edges. **You're scoring who is BEHIND the borrower, not just the borrower.**

**The demo that wins:** type one PAN → watch the graph light up a struck-off shell two co-directors away.
No commercial bureau surfaces this cleanly; name-matching can't.

## What's REAL in 4 days vs seeded vs stubbed

### One access fact that shapes everything
Every `.gov.in` endpoint blocks server-side fetches (403 to datacenter IPs / non-browser UAs) and most
are keyed by ENTITY NAME, not clean IDs. So: **pre-seed local Postgres tables from bulk files offline**
(one-time download / `curl_cffi` Chrome-TLS-impersonation / Playwright), NOT live per-request calls
during the demo. Core algorithm = normalized fuzzy name matching, with ID joins (PAN/CIN/GSTIN) as the
high-confidence exception. Show ID matches as high-confidence, name-only as advisory.

### LOAD LIVE — free, bulk, clean ID joins (build these, ~4-5 real tables)
1. **data.gov.in Company Master Data** (OGD API, free key, no scraping) → `negreg_company_status`
   keyed on **CIN** (Active / Struck Off / Under Liquidation / Under Process). Day-1 MVP core. Stale
   (~2024) but fine — label as freshness limitation.
2. **Maharashtra GST non-genuine taxpayer list** (~10,783 entities, GSTIN + trade name, Excel/PDF) →
   `negreg_gstin`. Best single free bulk blocklist in the whole task. `mahagst.gov.in/en/cancelled-gstin-cases-0`
3. **CBDT tax defaulters** (~96 rows, **unmasked PAN**, seed manually) → `negreg_pan`. Only clean PAN
   join available free. `incometaxindia.gov.in/tax-defaulters`
4. **OpenSanctions India** (free bulk, CC BY-NC): NSE-debarred (~15.4k), MHA/UAPA-banned, PEPs, +
   global OFAC/UN/EU/Interpol → `negreg_name`. Already parsed to CSV/JSON. Fastest watchlist layer.
5. **RBI Alert List** (unauthorised forex/ETP, ~95 rows, one PDF via bank mirror) → `negreg_name`.

Together: clean joins on **CIN, GSTIN, PAN** + name-matching on securities/forex/sanctions. A genuine
multi-identifier deterministic engine, not a toy.

### LIVE ON-DEMAND (single-lookup, fire only when not already in a bulk table)
- **NCRP Suspect Repository** (`cybercrime.gov.in/Webform/suspect_search_repository.aspx`) — the
  GOVERNMENT'S OWN public negative registry, searchable by mobile/email/account/UPI-ID/social. Open,
  CAPTCHA-gated, single-query UI. Do ONE live lookup in the pitch — highest-credibility India source.
- **IDfy self-serve sandbox** (`apicentral.idfy.com`, no card) — live PAN/GSTIN/AML-PEP calls. The
  standout free commercial sandbox. (HyperVerge free tier as backup; Probe42 trial if approved by day 0.)
- **GSTIN live status** (cancelled/suspended) + **DGFT DEL** (IEC) — free-trial verify APIs / SPA XHR,
  one-at-a-time.

### SCRAPE A SAMPLE (few hundred records for realism)
- **IBBI CIRP corporate debtors** (~11.4k, CIN-keyed) — blank search returns all; hit the backend JSON
  XHR. Freshest insolvency signal.
- **MCA struck-off / directors-of-struck-off / disqualified directors (DIN)** — per-ROC, bot-blocked;
  scrape 2-3 major ROCs. (data.gov.in status flag covers most struck-off need without scraping.)
- **watchoutinvestors.com** — most scrapeable wilful-defaulter/suit-filed source.
- **ScamSearch.io** — free search + free API; bulk seed for fraud identifiers.

### STUB WITH REAL SCHEMA (label honestly — this EARNS credit at a bank hackathon)
- **I4C Suspect Registry (core bank API)** — 23L+ suspect IDs, but bank-API-onboarding + LEA-gated. Mock
  the contract; "integration-ready once IDBI onboards." IDBI, as a regulated bank, already has this right.
- **RBI DPIP** (Digital Payments Intelligence Platform) — literally the concept we're mimicking; pre-GA,
  bank-gated. Name it as the production target.
- **RBI MuleHunter.ai** — bank-deployed in-house, no API. **Replicate its 19 mule-behaviour features**
  (pass-through, fan-in/out, dormant-then-burst, round-tripping, new-account velocity) on synthetic
  transactions; frame "MuleHunter-style, RBIH-aligned." Strong bank-jury framing.
- **CRILC + credit bureaus (CIBIL/CRIF)** — PAN-keyed, license/consent-gated. `BureauAdapter` returns
  synthetic scores. Note: every gated feed here is data IDBI already holds internally — the engine drops
  straight into their existing data rights. Say exactly this.

### DROP (don't waste time)
EPFO defaulters (no list published — use establishment-search only for "employer exists" KYC), CVC bank
frauds (names redacted), RBI Cautions page (awareness, not a registry), Sanchar Saathi Chakshu/TAFCOP/DIP
(report-only or self/bank-gated), TRAI DND (report-only; use 140/1600 caller-prefix as a rule feature only).

## How Pillar 3 plugs into the decision
- Deterministic hits are **overlays / hard triggers**, NOT GBM features (no training data links a
  registry hit to default probability — putting it in the model would be fake). A confirmed hit →
  compliance sub-score veto + "refer to manual review" / decline, with the registry + matched identifier
  cited as the reason code.
- ID-match (PAN/CIN/GSTIN) = high-confidence auto-flag. Name-only match = advisory, human-confirm.
- Architecture: one interface `checkIdentifier(type, value) → {hit, category, source, confidence}`
  behind which each adapter is real / seeded / stubbed, clearly labeled. This is how a real bank engine
  layers gated feeds — reads as production-ready, not faked.

## Third demo money-shot (add to personas a & b)
**(c) Phoenix borrower:** brand-new company, clean GST, thin but positive cash flow — Pillars 1 & 2 say
"maybe." Then the PAN-spine graph fires: promoter's DIN is a co-director of a company struck off 14
months ago that appears on the wilful-defaulter list → **hard decline / refer, reason cited with the
government source**. This single demo proves the whole "who's behind the borrower" thesis.

## Platform expansion layer (the "scalability" story — from Gayatri, all on-theme)
These three are the vision/scalability narrative (PS asks for "long-term commercial scalability"). Core
Health Card = score+explain+decide; these turn it into a platform. Show each, don't over-build each.
1. **Continuous Risk Monitoring (post-disbursal EWS).** Already core — this IS Pillar 1's "both
   directions / early-warning" head: same feature pipeline, monthly AA refresh, triggers on declining
   revenue / lower txn activity / delayed GST filing / payroll shrinkage → proactive intervention →
   fewer NPAs. Maps to Sahamati's "monitor loan accounts" use case. Cheap: reuse the features. TAKE IT.
2. **Dynamic Credit Limit + Tenure Recommendation.** Already core — this IS the decision engine's
   output: not approve/reject but optimal amount (≈ k × avg monthly net inflow) + tenure + risk band →
   personalized credit products, capital efficiency. Her framing is good pitch language. TAKE IT.
3. **Supply-Chain Risk Analysis (GST invoice graph).** Genuine ADDITION. Two tiers:
   - **Tier A (cheap, do it):** buyer/supplier concentration from GSTR-1 counterparty GSTINs — top-N
     customer share = dependency risk. Already in the feature list; just surface it.
   - **Tier B (money-shot, stretch):** cross-check the borrower's buyers/suppliers against Pillar 3's
     negative registry + distress signals — "your largest customer is under CIRP / on the non-genuine
     GSTIN list." Extends the entity graph from "who's BEHIND the borrower" to "who the borrower DEPENDS
     on." Needs counterparty GSTINs in the synthetic data. Seed one distressed-counterparty demo case.

## Compliance flags (one line each — rule vs principle, your call)
- OpenSanctions bulk is CC BY-NC — fine for the hackathon; a productized Walrus Securitas SaaS reselling
  screening would need their paid commercial/OEM license.
- Scraping `.gov.in` public registries + matching a CONSENTING borrower is standard RegTech; the gated
  feeds (I4C, CRILC, bureau) stay stubbed precisely because they're access-controlled — that honesty is
  the credibility play, not a limitation.
