# SHROFF — technical walkthrough (every step, every section, every ask)

Prep doc for being grilled live. Structured so you can skim the bold lines for a fast answer and
drop into the detail underneath if pushed. Every number and code path here was re-verified against
the actual repo while writing this — nothing is from memory.

---

## 0. The one-sentence answer, if that's all the time you get

> **A monotonic gradient-boosted model reads a business's real bank/GST/EPFO cash-flow trail and
> gives it an explainable 300–900 credit score in seconds; a separate, deterministic registry-and-
> graph layer checks whether the people behind the business are clean — and that second layer can
> only ever make the verdict worse, never better, because fraud detection should never be allowed
> to rescue a bad score.**

---

## 1. End-to-end pipeline, step by step

This is the order data actually moves through the system — walk it in this sequence if asked "how
does it work":

**Step 1 — Consent.** A borrower's Account Aggregator consent artefact (ReBIT v2 JSON, purpose
code 103, `PERIODIC` fetch, `[DEPOSIT, GSTR1_3B]` FI types) authorizes a 24-month pull of bank
statements + GST returns. EPFO payroll is a third input. Today this consent artefact is generated
in the exact real shape (`api/scoring.py: consent()`), not live-fetched — that's what sandbox
access unlocks.

**Step 2 — Raw monthly ledger.** One row per MSME per month: `bank_inflow_inr, bank_outflow_inr,
eod_balance_avg_inr, eod_balance_min_inr, days_near_zero, upi_txn_count, upi_inflow_share,
bounce_count, emi_debit_inr, self_transfer_inr, gst_turnover_declared_inr, gst_filed_on_time,
gst_filing_delay_days, gst_nil_return, b2b_share, top3_buyer_share, employees_epfo, wage_bill_inr`
— plus a separate counterparties table (`msme_id, month, counterparty_gstin, counterparty_name,
share`) from GSTR-1. This exact schema is what `given/round-2/data-field-requirements-submission.md`
asks IDBI's sandbox to return.

**Step 3 — Feature engineering (`ml/features/build.py`).** The raw ledger becomes **45 named
features in 4 groups** — cash_flow (14), growth (9), stability (12), compliance (10). Every
feature computes over the *available* window, not a fixed one — short-history applicants (a
14-month-old company) get `k = min(6, n//2)` windows instead of crashing or being zero-filled, and
`st_history_months` carries the thin-file signal explicitly rather than hiding it.

**Step 4 — Four separate monotonic LightGBM sub-models (`ml/train/train.py`), not one model.**
Each group trains its own `LGBMClassifier` with `monotone_constraints` set per-feature (`+1` =
risk can only rise as the feature rises, `-1` = can only fall, `0` = unconstrained) — so "more
revenue" can never mathematically increase predicted default risk, which is what makes the SHAP
reason codes trustworthy instead of just plausible-looking.

**Step 5 — Stacking, done leak-free.** Each sub-model's out-of-fold predictions (5-fold
`StratifiedKFold`, computed only on the training split) feed a **logistic-regression meta-
combiner**, fit on the *logit* of the four sub-model probabilities. This produces one meta
coefficient per group (cash_flow / growth / stability / compliance) — the exact weights that later
decide how much each group's SHAP values count toward the final reason ranking.

**Step 6 — Calibration.** The meta-combiner's holdout output is isotonic-calibrated
(`IsotonicRegression(y_min=0.002, y_max=0.98)`) into a genuine 12-month probability of default —
so "PD 2.1%" is a calibrated probability, not a raw model score dressed up as one.

**Step 7 — Scorecard scaling.** PD → score via the standard credit-scorecard PDO formula:
`score = 660 + 72·log2(odds / odds_at_660)`, clamped to [300, 900] — 660 = 5% PD by construction,
every halving of default odds adds 72 points. Bands: A ≥750 · B 680–749 · C 600–679 · D 500–599 ·
E <500.

**Step 8 — The regulator-view baseline, reported side by side.** A plain, standardized
`LogisticRegression` over all 45 features is trained and reported next to the GBM
(`baseline_logreg` in `metrics.json`) — this exists specifically because `BUILD-SPEC-track03.md`
cites RBI's FREE-AI committee finding that 38% of Indian FIs prefer simple, explainable models. If
asked "why not just logistic regression," the honest answer is: **we ship both, and let the jury
see the AUC gap for themselves** rather than asserting one is better.

**Step 9 — TreeSHAP reason codes (`ml/api/reasons.py`).** SHAP runs on each of the four *deciding*
sub-models directly — not a separate surrogate model that might disagree with the real one — and
each sub-model's SHAP contribution is weighted by its meta-combiner coefficient before ranking.
Top 3–5 reasons are chosen, both-directions-guaranteed (if all top reasons happen to point the
same way, the next best opposite-signed one is forced in), each filled with the *actual* feature
value in human units ("₹8.1L/month", "24 months of history") via a curated formatter, never a raw
z-score.

**Step 10 — Deterministic overlays, called in-process (`ml/api/decision.py`).** Three independent
checks run on top of the score, and none of them can ever improve a verdict:
- **Early-warning system**: last 3 months vs. prior 9 — inflow drop >25%, ≥2 bounces, GST late/nil
  streak ≥2, headcount drop >25%. 0 triggers = green, 1 = amber, ≥2 = red. EWS red caps the
  effective band at C, regardless of what the model scored.
- **Registry screening** (`check_msme`): **8 separate identifier fields** per applicant — company
  PAN, GSTIN, CIN, DIN, promoter PAN, promoter DIN, business name, legal name, promoter name —
  each checked against the negative registries. A **high-confidence exact-ID match forces
  DECLINE**. A **name-only fuzzy match is advisory only** — surfaced for manual disposition,
  never auto-declining, because a real watchlist of ~21,000 names makes common promoter names
  collide constantly (a bank's actual AML pattern).
- **Entity-graph phoenix check** (`ml/screening/graph.py`): a breadth-first walk from the
  applicant's PAN — PAN → own companies/GSTINs → directors (DIN) → co-directors' *other*
  companies (2 hops) → shared-registered-address companies. If any node reached *beyond the
  applicant's own identity* carries a struck-off, wilful-defaulter, or director-of-struck-off
  flag, `phoenix_flag = true` and the verdict is forced to at least REFER, with a plain-language
  narrative naming exactly which entity and via which director.

**Step 11 — The decision (still `decision.py`).** Base verdict by effective band: A/B → APPROVE,
C/D → REFER, E → DECLINE. Amount: `eligible = 0.20 × (12 × mean monthly bank inflow) × band_factor`
(A 0.65 · B 0.50 · C 0.30 · D 0.15 · E 0) — the 20% is the Nayak Committee working-capital norm,
cited by name in the on-screen rationale. `amount = min(requested, eligible)`, rounded to ₹50k.
Tenure by band: A/B 24–36mo, C/D 12mo, E none.

**Step 12 — Optional LLM narrative (`ml/api/narrative.py`), off by default.** If (and only if) an
`LLM_API_KEY` env var is set, exactly one call to an OpenAI-compatible endpoint turns the
*already-computed* facts into 3–4 sentences of prose — the prompt literally says "do not invent
numbers or change any figure." Any failure (no key, network error, bad response) silently falls
back to nothing, and the template reason codes — which are always computed regardless — are what
ships by default. **No LLM is ever on a path that produces a number.**

**Step 13 — OCEN 4.0 output (`ml/api/rails.py`).** The decision reshapes into a Loan-Agent-
consumable offer: risk-based interest rate (band base rate + up to +3% PD-linked premium within
band — A 13.5%, B 15.0%, C 17.5%, D 20.0%, E unlendable), a real reducing-balance EMI calculation,
1% processing fee, 30-day offer validity, and an explicit `PENDING_MANUAL_REVIEW` /
`REJECTED` / `APPROVED` status mapped straight from the verdict.

---

## 2. "What special thing are we doing" — the differentiators, ranked by how defensible they are

1. **Deterministic core, generative shell — architected, not just claimed.** Every number on the
   card traces to a specific trained model or a specific SQL/graph query. The one place an LLM can
   touch the system (the narrative) is proven incapable of changing a figure, by construction
   (prompted against fixed facts, and the whole feature is env-gated off by default). This is the
   single point worth repeating if pressed on "is this just a wrapper around GPT."
2. **Four monotonic sub-models, not one.** Monotonicity isn't a modeling nicety here — it's what
   makes the SHAP reason codes safe to show a regulator: a feature that objectively helps the
   business (more revenue, more UPI activity) can never be shown pushing the score down, because
   the constraint makes that mathematically impossible, not just empirically rare.
3. **The registry-plus-graph layer answers a question the score literally cannot.** A phoenix
   operator's *own* numbers can look completely clean — the fraud lives in who they're connected
   to, not what their bank statement says. That's why this is a separate, deterministic overlay
   walking real identity graphs, not a model feature (no training data honestly links "network
   reaches a struck-off company" to a default probability — encoding it as a feature would be
   fabricating a signal, so it's an overlay with cited evidence instead).
4. **Overlays only ever worsen the verdict, never improve it — enforced in code, not policy.**
   `worse_band()` and `_worsen()` are one-directional by construction. A perfect score cannot be
   rescued by a clean screening result; a clean score can be knocked down by a dirty one. That
   asymmetry is deliberate: it means the fraud layer's job is strictly to catch bad actors, never
   to vouch for good ones.
5. **~45,000 real government rows, not a synthetic mock-up, for the one layer where "real" is
   checkable today.** MahaGST (11,410 real non-genuine GSTINs), SEBI/NSE debarred (11,631 real
   PANs), CBDT defaulters, RBI Alert List, OpenSanctions (20,853 real names) — captured via
   documented real access methods (headless-browser network inspection, `curl_cffi` TLS
   impersonation to get past Akamai on the CBDT endpoint), not fabricated. Every row carries an
   `is_sample` flag so nothing is silently faked.
6. **The honest gap, stated before anyone else has to point it out**: the *scoring* model itself
   currently trains on synthetic financial data (by design — judge-proof, zero network dependency,
   per `STACK.md`). If asked "has this ever seen real money move," the correct answer is: not yet
   on the scoring side, yes on the registry side, and closing that gap is exactly what sandbox
   access is for. Several Track-03 rivals make the identical disclosure about their own synthetic
   core (see `given/round-2/track03-competitors-deep-dive.md`) — it's the expected honest answer
   at this stage of the program, not a unique weakness.

---

## 3. AI / agentic logic — what's live, what's designed, and why the boundary is where it is

**Live today:** exactly one generative touchpoint, described in Step 12 above. Nothing else in the
serving path is generative.

**Designed, documented, not yet wired (`BUILD-SPEC-track03.md`):**
- **A read-only "Talk to your Health Card" Q&A agent.** Its tools would return the *already-
  computed* features, SHAP values, and registry/graph results — it literally cannot hallucinate a
  number because it has no path to produce one; it can only fetch and phrase facts that already
  exist.
- **Continuous risk monitoring (post-disbursal EWS).** Reuses the identical feature pipeline on a
  monthly cadence per disbursed loan — same triggers, same thresholds, proactive alert instead of
  a one-time gate. This is the "living score" half of the platform-expansion story.
- **Adverse-media / entity-risk scanner.** Repurposes an existing news-ingestion module
  (fetch → dedupe → entity-match → LLM-classify severity) as a compliance-sub-score overlay —
  explicitly an overlay, not a model feature, for the same reason the registry layer is an
  overlay: no training data links a news hit to a default probability.
- **RAG over ~8 RBI/SIDBI policy PDFs**, for citing a regulation next to a decline reason —
  deliberately kept as stuffed context rather than a vector database, because 8 documents doesn't
  justify pgvector infrastructure.

**The one sentence that answers almost any "how far can the AI go" question:** *every agent this
platform will ever run is a read-only tool that returns facts into a deterministic decision
engine — never a component that computes the decision itself.* That's not a limitation being
worked around; it's the architectural choice that makes the whole system auditable to a bank's
model-risk function in the first place.

**Where this could reach next (raised in the sandbox-access justification,
`docs/SANDBOX-FORM-ANSWERS.md`):** the same pattern extends cleanly to a cyber-exposure agent
(dark-web/breach/phishing-domain monitoring on the borrower's identity, reusing the PAN-graph
already built) and a compliance-citation agent (RBI/DPDP/AML) — both additional *overlays*, not
new decision paths, so the deterministic-core guarantee never has to be renegotiated to add them.

---

## 4. The UI, section by section, in the order a viewer actually sees them

### Landing page (`/`)
- Hero: **"Sees the invisible borrower — in both directions"** + a 4-stat strip (6.3 Cr registered
  MSMEs, ₹25L Cr formal credit gap, 24-month consented window, <60s score-to-sanction).
- **Three pillars** (cash-flow truth, deterministic score, registry + graph) — the same three-part
  structure as this whole document.
- **The both-directions thesis**, side by side: the deserving-invisible kirana store vs. the
  clean-on-paper business that's actually burning cash — this is the single most important framing
  slide/section if you only have time to explain one thing.
- **Three demo dossiers** linking straight to the three personas' health cards.
- Footer honesty strip: *"Deterministic core · generative shell — no LLM ever computes a number"*
  and *"Synthetic demo data · sample registry rows carry `is_sample` chips"* — literally printed on
  the page, not just in documentation.

### Portfolio console (`/console`)
- A **live/fixture data-source chip** — shows whether the page is talking to the real running API
  or the bundled fixture fallback (the demo-can't-die circuit breaker).
- **Four stat tiles**: Assessed / Approved / Referred / Declined, computed live from the actual
  verdicts returned.
- **The assessment ledger table** — one row per persona, each a live link to its full health card,
  showing borrower, segment, requested amount, score+band, and the verdict stamp inline.

### The health card itself (`/console/{id}`) — six stacked rows
1. **Identity header** — MSME ID, entity type, city, business name, and an ID-chip strip
   (PAN / GSTIN / CIN / promoter DIN / UDYAM) plus a **consent popover** showing the actual ReBIT
   v2 consent artefact JSON — this is where "is this consented data or scraped data" gets answered
   visually, on the spot.
2. **Row 1 — Health score gauge + 12-month PD** · **Sub-score radar** (cash_flow / growth /
   stability / compliance, each a population percentile) · **Decision card** — the APPROVE/REFER/
   DECLINE stamp, sanction amount, tenure, the plain-English rationale citing the Nayak norm, and a
   footer line stamping the exact model version + AUC + KS + `trained_on` tag.
3. **Row 2 — Signed reason codes (TreeSHAP)** spanning two columns, next to a stacked
   **early-warning strip** and **registry-screening panel** — the panel literally lists which
   identifier fired and against which real-vs-sample registry.
4. **Row 3 — the divergence chart**: bank-verified inflows vs. GST-declared turnover, monthly, two
   lines on one ₹ axis. This is the single chart that makes "clean on paper, burning in reality"
   visible without narration — point at where the lines diverge and stop talking.
5. **Row 4 — the entity graph** (React Flow, flagged nodes in oxide red, phoenix banner when
   triggered) next to the **supply-chain concentration bar** (top-3-buyer share + any distressed
   counterparty flagged against the same registry).
6. **Row 5 — the lending rail**: the decision reshaped into the actual OCEN 4.0 loan-offer JSON
   (rate, EMI, processing fee, validity) — proof the score isn't a dead end, it's wired to
   something a Loan Agent could act on today.

---

## 5. "What APIs do we want from IDBI" — the short verbal version

Full detail already drafted in two files — point to them if asked for specifics, but the spoken
version is:

- **GSTN**: IDBI's own sample schema mostly covers what we need; we've asked for two additions —
  per-counterparty GSTIN breakdown (not just an aggregate %, because our entity graph needs to walk
  *named* counterparties) and a top-3 concentration figure (their sample gives top-1/top-5; our
  trained feature is top-3).
- **Account Aggregator bank-statement feed**, **UPI feed**, and **EPFO feed** — none were in
  IDBI's sample, so we drafted full request/response schemas from scratch, field-mapped exactly to
  our existing pipeline (`given/round-2/data-field-requirements-submission.md`) — so real data
  slots in with zero schema rework the moment it's available.
- **Sandbox infra**: Fargate-sized compute (1 vCPU/2GB for the scoring API, measured not
  estimated — `docs/INFRA-AWS.md`), Aurora Postgres for the registry/consent layer, Mumbai region,
  full detail in `docs/SANDBOX-FORM-ANSWERS.md`.
- **The one open question worth asking them back**: does IDBI's sandbox expose any internal
  watchlist/struck-off/DIN-disqualification feed to validate our public-registry screening layer
  against — or should that stay sourced from public data (MahaGST/SEBI/CBDT/RBI/OpenSanctions/MCA)
  for this phase? That's mentor-question #3 in the data-field-requirements submission, and it's a
  good one to actually ask out loud.

---

## 6. Fast answers to the questions most likely to actually come up

- **"Why four models instead of one?"** Each risk dimension (cash-flow, growth, stability,
  compliance) has a different feature vocabulary and a different monotonicity story; stacking them
  through a meta-combiner also gives a clean, interpretable weight per dimension instead of one
  opaque blended importance ranking.
- **"Why not just use GPT/an LLM to score this?"** Cited directly in `BUILD-SPEC-track03.md`:
  published benchmarks put LLM-as-scorer AUROC around 0.52–0.63 vs. 0.85–0.89 for trained models on
  this exact problem class, and LLM self-explanations have been shown not to match the model's own
  real SHAP attributions — confidently wrong reasons are worse than no reasons.
- **"What happens if the registry/screening service is down?"** `run_screening()` is wrapped in a
  guarded import with a bare `except`; on any failure it reports `checked: false` rather than
  crashing the whole score — the score still returns, just without that overlay for that request.
- **"Can the phoenix graph produce a false positive?"** Yes, and that's why it forces REFER
  (manual review), not DECLINE — only a high-confidence exact-ID hit on the applicant's *own*
  identifiers forces DECLINE. The graph flag is deliberately a human-review trigger, not an
  automated rejection.
- **"Is any of this actually running, or is it slides?"** Yes — booted and hit directly as recently
  as this conversation: `/api/health` returns `{"status":"ok","artifacts_loaded":true}` and
  RAMESH001 scores 769/A/APPROVE on a live call, matching the documented numbers exactly.
