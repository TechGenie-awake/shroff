# Track 03 — Financial Health Score: the 4 teams SHROFF is actually competing against

Track 03 pays two winners (₹2L + ₹1L) out of five shortlisted teams. This is everything findable
— public and documented — on the four other teams in the room. Depth varies sharply by team, and
that variance is itself the finding: one competitor has published their entire strategic
playbook; three have published nothing, for very different reasons each worth understanding.

| Team | Product | What we know | Depth available |
|---|---|---|---|
| **Team UdyamAI** | UdyamAI | Full public repo — docs, roadmap, deck, cost model, architecture | **Exhaustive** |
| **Modus AI** | Udyam Sehat Card | Funded startup, real fraud-graph product, founder pedigree — no repo | **Company-level, no plan** |
| **Knight Fintech Pvt. Ltd.** | MSME Health Card | $23.6M Series A, 350+ staff, real lending infra at scale — no repo | **Company-level, no plan** |
| **ASM FinTech Developer** | FinRiskLensAI | One real person, real core-banking day job — nothing else public | **Identity only** |

---

## 1. Team UdyamAI — [SahanSrinivas/UdyamAI](https://github.com/SahanSrinivas/UdyamAI)

Team leader **Sahan Kolluri** (`26sahan@gmail.com` in the deck content, `kollurisahan@gmail.com`
on the official shortlist — same person, local dev path confirms it: `/Users/sahan_kolluri/...`).
Solo builder, IIT-Hyderabad-adjacent tooling stack (references "BabyFly SwiftUI" and "AarogyaGrid"
as prior projects). This is the one competitor who didn't just build a demo — he published his
entire planning process to `docs/`, including a literal `05-action-plan.md` and a 24-month
`PRODUCTION_ARCHITECTURE.md`. Everything below is drawn directly from those files, not inferred.

### 1.1 The core USP, in their own words

> **"Every existing player scores you at apply time. UdyamAI scores you continuously. That's
> Credit Karma for Indian MSMEs — and we're the first."**

Their `docs/04-incumbents.md` is a genuine competitor-landscape document — they mapped Perfios,
Jocata, Karza, Lendingkart, Indifi, FlexiLoans, NeoGrowth, Aye Finance, Khatabook, OkCredit,
Vyapar, PSB Loans 59 Minutes, and TReDS, and concluded:

> "Perfios/Jocata own the B2B rails. Lendingkart et al. own the transactional apply-once flow.
> Khatabook owns the users but not the credit layer. **The Credit-Karma-for-MSMEs slot is empty.**"

Their positioning is explicitly **borrower-facing**, not bank-facing — this is the single biggest
strategic divergence from SHROFF, which is built as a credit-officer's decisioning tool. If IDBI's
jury reads Track 03 as "help the bank underwrite," SHROFF's framing wins. If they read it as "help
the MSME get discovered and included," UdyamAI's framing wins. Worth deciding, deliberately, which
reading SHROFF should also lean into before Demo Day — it may not have to be either/or.

### 1.2 What's actually built (prototype, live)

- **Real data, not just synthetic** — ingests the **AgamiAI** open Hugging Face datasets
  (Apache 2.0) into **AWS Aurora Serverless v2 Postgres**: 200 real bank accounts, **97,106 real
  parsed transactions** (₹4,029 Cr aggregate volume — NEFT 17,344 / UPI 11,534 / RTGS 6,036 /
  CHEQUE 500 / IMPS 136), 100 real ITR filings. This is SHROFF's single most exposed gap — see §5.
- **Live retrain endpoint** (`POST /api/retrain`) — a real logistic-regression calibrator,
  per-lender (IDBI / SBI / HDFC), retrained on the real transaction distribution, with weights +
  holdout AUC persisted to a `lr_training_runs` table on every run. A "live retrain badge" shows
  the current AUC in the UI.
- **Real bounce-detection** wired directly to `agami_transactions.failed = TRUE` in the lender
  view — not a mocked trigger, an actual field in the real dataset.
- **Benchmarked, per-lender model numbers**, reported without inflation:

  | Lender | Accuracy | AUC | Bias | Top feature |
  |---|---|---|---|---|
  | IDBI Bank | 87.3% | 0.729 | −0.14 | Revenue Stability (+1.14) |
  | SBI | 82.8% | 0.789 | +0.00 | Compliance (+1.21) |
  | HDFC Bank | 88.8% | 0.721 | −0.04 | Revenue Stability (+0.99) |

  (600 holdout samples per lender, 2,400 synthetic training samples, 260 epochs batch gradient
  descent — the LR model itself is trained synthetic, only the *retrain calibration* runs on real
  AgamiAI data.)
- **Vernacular explanation** — Gemini 1.5 Flash, English / Hindi / Telugu, described as a
  "direct-tone prompt," not a hedge-everything disclaimer bot.
- **Quantified nudge engine** — not "improve your compliance," but *"Late GST filing costs 34
  points → file on time next cycle → +34 points."* Numeric, signed, actionable.
- **OCEN 4.0 as a first-class citizen** — a real simulated LA→Lender protocol (search / offer /
  accept / status), with **64-lender ULI framing** baked into the pitch itself, and a Model Card
  endpoint exposing per-lender coefficients live in the product (`GET /api/health-card`).
- **On-device GSTIN checksum validation**, live FX/market strip (RBI repo, MCLR, USD/INR via the
  free Frankfurter API), 6 hand-crafted demo personas each linked to a real ITR entity name.
- Measured latency (Vercel Edge): landing 190ms cold / 45ms warm; full dashboard score pipeline
  900ms cold / 220ms warm; Gemini explanation ~1.4s cold.
- **Last commit: 2026-08-19** — the day before the induction session, meaning this team is
  actively iterating through the exact window you're reading this in, not coasting on a frozen
  round-1 submission.

### 1.3 Documented future plan (verbatim structure from their own roadmap)

**0–6 months (their stated "Round 2 candidates" — i.e., what they intend to ship *during the same
prototype-refinement phase you're in right now*):**
- Real Finvu AA sandbox integration (bank statements + GST via consented pull, not synthetic)
- Real UPI counterparty graph (actual concentration risk from the transaction graph, not a
  self-reported field)
- 90-day cash-flow LSTM for repayment capacity
- Real OCEN LA registration — becoming a licensed Loan Agent against real ULI endpoints

**6–18 months (post-Series-A framing):**
- Embedded distribution inside **Khatabook / OkCredit** (they cite 30M+ MSME users already there
  — "embed the Health Card instead of chasing installs")
- WhatsApp vernacular coaching bot (Gupshup/360dialog) — 6-month score-improvement journeys
- Sector cohort benchmarking ("your inventory turnover is bottom quartile for textile MSMEs in
  Surat")
- A "UdyamAI Current Account" — becoming the MSME's primary banking relationship, not just a score

**18–36 months:**
- RBI RegTech sandbox partnership as a reference implementation
- An insurance rail on the same AA data (life + shopfloor property scoring)
- International expansion — Indonesia (UMK), Vietnam, Bangladesh, same alternate-data thesis

**Full production architecture is documented down to the service level** — Django 5 + DRF on
Cloud Run, MongoDB Atlas for score history/event streams, Cloud SQL Postgres for transactional/
audit data, **Neo4j Aura for UPI counterparty graph + circular-payment-ring detection**, Vertex AI
(Gemini 2.0 Flash + AutoML Tabular LSTM), Digio/Signzy for Aadhaar eKYC, a named compliance stack
(RBI IT Framework 2023, DPDP Act 2023, RBI Digital Lending Guidelines, Sahamati Rulebook, SOC 2
Type II targeted within 12 months, ISO 27001 within 18). They even priced it: **₹5L one-time
build cost, ₹47k/month opex at 50k MSMEs, sub-₹1/MSME/month, break-even at one bank paying ₹500
per converted lead × 100 leads/month.** A hiring plan is attached too (backend engineer by month
3, mobile + BD by month 4, data/ML/DevOps/compliance by month 6).

**Read this section for what it signals, not just its content:** publishing a fully-priced,
service-by-service, month-by-month production plan is itself a competitive move — it tells a
jury "we've already thought past the demo," which is exactly the signal `TODO.md`'s own strategy
notes says jury selection rewards. SHROFF's `STACK.md` has a real production path (Supabase swap)
but nothing at this level of granularity publicly documented.

### 1.4 Where UdyamAI is weaker than SHROFF (say this plainly, don't just praise them)

- **No negative-registry / fraud-graph screening at all.** Nothing in their repo checks a
  promoter, PAN, GSTIN, or director against any watchlist, struck-off register, or defaulter list
  — SHROFF's entire Pillar 2/3 (45k real government rows + PAN-spine phoenix-fraud graph) has no
  equivalent here. Their model would score a spotless-looking phoenix borrower as healthy with no
  override mechanism. This is SHROFF's clearest, sharpest, most defensible edge against this
  specific rival.
- **Model choice is a plain logistic regression**, framed as a feature ("auditable coefficients,
  RBI model-risk approvable") rather than SHROFF's monotonic-constrained LightGBM ensemble + TreeSHAP.
  Their own `docs/04-incumbents.md` even calls LR-vs-GBM a deliberate trade-off. This is a genuine
  point where SHROFF's `BUILD-SPEC-track03.md` research (HKMA/ASTRI, Grinsztajn, Lessmann — GBM
  beats LR on this exact problem class) is the stronger-cited position, and worth stating with
  that evidence rather than assuming it's obviously better.
- **No OCEN risk-based pricing output** comparable to SHROFF's `rails.py` (band-based EMI/tenure/
  processing-fee offer) — UdyamAI shows "pre-qualified quotes ranked by approval confidence," not
  a priced loan offer.
- Two-sided "catch the looks-fine-but-failing borrower" framing (SHROFF's explicit dual-direction
  thesis, per `README.md`) doesn't appear anywhere in UdyamAI's materials — theirs is purely
  inclusion-facing, not fraud/deterioration-facing.

---

## 2. Modus AI — "Udyam Sehat Card"

Team leader contact: `manav@modussecure.com`. **No public repository found** after exhaustive
GitHub repo, code-content, and user search — this is the one "not found" in Track 03 that comes
with real company-level intelligence behind it, gathered from the company's own site and press.

### 2.1 What Modus AI actually is (documented, real company — not a hackathon team in the usual sense)

- Founded **2025**, Bengaluru. **10 employees** as of May 2026 (Tracxn). Backed by **WTFund,
  Inuka Ventures, MeitY, and DeVC Ventures** — a government-linked (MeitY) plus VC funding mix,
  with their most recent round reported as a "Grant (prize money)" round dated Feb 2025.
- **Founders:**
  - **Sunit Gautam** (Co-founder, CEO) — ex-Goldman Sachs fraud strategy; **built AI + graph
    fraud detection for Apple Card in the US**; IIT Kanpur alumnus.
  - **Somesh Lund** (Co-founder, COO) — forensic investigator; advisor to banks and regulators.
  - **Vamshi Krishna** (Head of Engineering) — 10+ years building scalable fintech systems.
- **Core product** (per their own site, `modussecure.com`): an AI **fraud-detection co-pilot**
  for financial institutions —
  - **Graph AI over transaction records** to identify mule networks and high-risk customer
    clusters
  - AI agents that automate compliance document review and regulatory checks
  - Customer/merchant monitoring with anomaly detection
  - Risk-ops automation: alert triage, chargeback resolution, **AML/PEP screening**, onboarding
    risk linkages

### 2.2 Why this is the single most technically dangerous Track 03 rival for SHROFF specifically

Every other team in this track (including UdyamAI) built a credit-scoring product with no fraud
layer. Modus AI is the mirror image: **a production-grade fraud/AML graph-detection company**
that is almost certainly repackaging their existing mule-network and PEP-screening engine as the
"Udyam Sehat Card" wrapper. That means Modus AI's Track 03 entry may arrive with:

- A genuinely production-tested **entity/transaction graph engine** — not a hackathon-weekend
  approximation of one, built by someone who shipped graph fraud detection at Apple Card scale
- Real **AML/PEP screening** experience, which is structurally the same problem as SHROFF's
  negative-registry check (PAN/GSTIN/CIN/DIN against watchlists) — they may already have cleaner
  entity-resolution and fuzzy-matching than a hackathon-timeline build could produce
- Credibility with a bank jury on the compliance/regulatory-automation angle specifically, because
  "advisor to banks and regulators" (Somesh Lund) is a direct credential match to what a PSU bank
  jury screens for

**Where SHROFF still likely leads:** Modus AI's core business is fraud/AML, not credit
*decisioning* — turning a fraud-graph engine into a calibrated, monotonic, SHAP-explained 300–900
credit score with sub-scores, bands, and an OCEN-priced loan offer is a different build than
detecting mule accounts. If their Track 03 entry is a thin credit-scoring wrapper bolted onto a
fraud engine, SHROFF's scoring depth (four monotonic sub-models, isotonic calibration, LogReg
regulator-baseline side-by-side) is likely the more complete answer to the actual problem
statement. **This is the one competitor where "did they actually build a real credit health card,
or just relabel their existing fraud product" is the single most important open question** — worth
watching for at Demo Day specifically.

### 2.3 Documented future plan

None found. Enterprise/funded teams in this survey do not publish roadmaps publicly — there is no
`docs/`, no deck, no interview specifically about their IDBI Innovate entry. Their *general*
company trajectory (funded, hiring, MeitY-backed, actively selling to "banks and insurers" per
their own investor's public post) is the only forward signal available, and it points toward "this
is a real product they intend to keep selling into banks regardless of this hackathon's outcome" —
IDBI winning or not is unlikely to be existential for them, which usually means a competent,
low-risk submission rather than an all-in one.

---

## 3. Knight Fintech Pvt. Ltd. — "MSME Health Card"

Team leader contact: `parthesh@knightfintech.com`. **No public repository found** — same pattern
as Modus AI, but at a much larger institutional scale.

### 3.1 What Knight Fintech actually is

- Founded **2019**, Mumbai. **350+ employees.** Real, operating **digital lending
  infrastructure** connecting banks, non-bank lenders, and platforms — not a startup pitching a
  hypothetical, a company already running production credit rails.
- **Scale claimed:** 150+ partnerships across **85 lenders**, spanning retail/MSME/agricultural
  lending, **$7B+ cumulative loan disbursements**, **$5B+ assets under management**.
- **Product portfolio:** co-lending, digital lending, embedded finance, treasury management — two
  named products, **Knight Utopia** and **Knight Aurix**.
- **Just raised $23.6M Series A** (part of a $30M+ multi-tranche round), led by **Accel**, with
  IIFL and Rocket Capital participating — reported as **India's first "soonicorn" of 2026**.
  **Sanat Rao, former global CEO of Infosys Finacle**, joined as an investor/board advisor —
  about as strong a core-banking credibility signal as exists in Indian fintech.
- **The new capital is explicitly earmarked for**, per multiple funding-round reports: an
  **"AI-first roadmap" covering automated credit underwriting, risk intelligence, fraud
  detection, portfolio monitoring, and debt recovery** — plus international expansion into the
  Middle East and Asia-Pacific.

### 3.2 Why this is the highest-institutional-scale threat in the track

Knight Fintech isn't building a demo to impress a jury — **they are, right now, building the exact
AI underwriting/risk-intelligence product category Track 03 asks for, with $23.6M of fresh
capital specifically allocated to it, independent of this hackathon.** Their Track 03 submission
is very likely a live, real-production capability (or a near-term roadmap item they're already
funded to build) shown to IDBI as a live capability, not a synthetic prototype. Two implications:

- **On credibility and "can this actually ship inside a bank," nobody else in this track — SHROFF
  included — can currently match "already processes real loans for 85 lenders."** If IDBI's
  selection criteria weight execution risk heavily (a PSU bank's real concern with any hackathon
  winner), Knight Fintech is structurally the safest choice for the judges to make.
- **They also submitted to Track 02** (Prospect Assist AI, same leader/email) — a company this
  size treating IDBI Innovate as a genuine two-track sales motion into a real bank account, not a
  side hackathon. That's the strongest signal in the whole shortlist that at least one competitor
  is playing this as enterprise business development, not a student competition.

**Where SHROFF still has room:** a company at Knight Fintech's scale optimizes for their *existing*
enterprise customer base (large lenders, standard bureau-available borrowers) — their core
business is not obviously built around the **credit-invisible, New-to-Credit/New-to-Bank**
alternate-data problem that is Track 03's actual, specific brief. A large infra vendor's "MSME
Health Card" may be a feature bolted onto an existing underwriting suite rather than a
purpose-built alternate-data-only NTC/NTB solution — SHROFF's whole design (zero reliance on
bureau/CIBIL, alternate-data-only scoring) is a sharper, more literal answer to the stated problem
than a general-purpose lending-infra company is structurally likely to build for a hackathon demo.
This is worth stating explicitly and often in the pitch: **not "we're more advanced than Knight
Fintech" (false), but "we are purpose-built for exactly this brief; they are a platform company
retrofitting a feature."**

### 3.3 Documented future plan

None specific to the hackathon submission. Their *company-level* roadmap (from funding
announcements) is explicit: automated credit underwriting + risk intelligence + fraud detection +
portfolio monitoring + debt recovery, funded, in progress, with Middle East/APAC expansion — but
none of this is scoped to the IDBI Innovate track specifically. Same caveat as Modus AI: no
`docs/`, no deck, no roadmap tied to this competition found anywhere public.

---

## 4. ASM FinTech Developer — "FinRiskLensAI"

Team leader: `abhinavmukwane@gmail.com`. **No public repository, code, or documented plan found**
— the least-visible entrant in the track, and worth treating carefully rather than dismissing.

### 4.1 What's actually confirmed about the person

- **Real name: Abhinav Mukwane.** LinkedIn confirms: **Software Developer at Trust Fintech
  Limited**, self-described "AI & Cloud Enthusiast and Full-Stack Engineer," working since 2018.
- **Trust Fintech Limited is a real, listed banking-software company** whose specialties (per his
  LinkedIn) include **Core Banking Solution, Micro-finance Solution, GST Solution, Business
  Intelligence, System Integration** — i.e., his day job is *literally* building the kind of
  systems (core banking + microfinance + GST) that a Track 03 MSME Health Card needs to
  interface with. This is real, directly-relevant domain background, even without a visible
  hackathon build.
- Education: **PG-DAC (Centre for Development of Advanced Computing)** — a respected applied
  computing credential in Indian enterprise software circles.
- His personal site (`abhinavmukwane.in`) renders as an empty client-side loading shell when
  fetched headlessly — likely a React SPA that needs a real browser to render; **inconclusive**,
  not evidence of an empty portfolio.
- His public GitHub (`abhinavmukwane`) shows only generic ASP.NET/CRUD/encryption practice repos
  from 2022–2024 — nothing IDBI-dated, nothing named FinRiskLensAI, nothing fintech-risk-specific.
  A repo named `FinTechEncryption` ("Enterprise Hybrid Encryption Library for Secure FinTech
  Application and API," pushed March 2026) is the closest adjacent signal — general-purpose
  security tooling, not a credit-scoring product.

### 4.2 Honest read

Team name **"ASM FinTech Developer"** reads like a placeholder/individual-entrant name (similar
in style to "Team X" elsewhere on the shortlist) rather than a company or a named collective —
most consistent with a **solo entrant building this on the side of a full-time core-banking job**,
the same profile as several Track 01/02/04 solo builders found elsewhere in this shortlist
(Raunak Kanoji, Jeyaanth Anandan, Srijan Sharma all fit this exact pattern and *did* publish
real, working repos). The absence of a public repo here most likely means either: the repo is
private, it hasn't been pushed publicly yet, or it exists under a GitHub username with no
discoverable link to his name/email — **not** necessarily that nothing has been built. His actual
production experience with core-banking/microfinance/GST systems is a genuine, real qualification
for this exact problem statement, even in the absence of visible code.

### 4.3 Documented future plan

None found — no roadmap, no deck, no repo, no press. This entrant is currently a pure identity
match with zero technical evidence either way. Re-check closer to Demo Day (Sep 3) if a public
repo surfaces.

---

## 5. Cross-competitor synthesis — what actually decides "two winners out of five"

**The real-data gap is SHROFF's most exposed single weakness in this specific field.** UdyamAI
retrains live against 97,106 real bank transactions in a real Postgres instance and shows a live
AUC badge doing it. Modus AI's founders have shipped real fraud-graph systems at Apple Card scale.
Knight Fintech already processes real loans for 85 lenders. Against that field, SHROFF's synthetic
core-scoring data (deliberate, for judge-proof reproducibility per `STACK.md`) is the one place a
sharp juror could reasonably ask "but has this ever seen a real rupee move." **If there is any
build time left before Sep 3, a small real-external-dataset validation pass — even a lightweight
one, reusing the exact side-by-side-with-LogReg-baseline pattern `ml/train/benchmark.py` already
has — closes this gap at low cost and directly rebuts the strongest thing any of the four
competitors can say.**

**SHROFF's least-contested asset across all four:** the PAN-spine phoenix-fraud entity graph +
~45,000 real government negative-registry rows. UdyamAI has zero fraud/registry layer. Modus AI
*might* bring a stronger fraud-graph engine than SHROFF's — that's the one real technical
uncertainty in the whole track, worth watching for specifically at Demo Day. Knight Fintech's
scale is in lending infrastructure, not alternate-data-only NTC/NTB scoring. ASM FinTech is an
unknown. On the literal problem statement — "aggregates alternate data... computes a
multidimensional financial health score... catches what bureau-only scoring misses" — SHROFF's
two-sided thesis (approve the invisible-but-healthy *and* catch the clean-on-paper-but-failing,
*and* catch the phoenix promoter) is the only one of the five submissions in this track that
visibly answers all three parts of that brief at once.

**On institutional credibility, SHROFF is the underdog against Knight Fintech specifically** — no
amount of hackathon polish changes that a 350-person, Series-A, ex-Finacle-CEO-advised company is
in the room. The counter isn't to out-credential them; it's to be unambiguously the most precise,
purpose-built answer to Track 03's literal brief, which a platform company retrofitting a feature
is structurally less likely to be.

---

## 6. Verification log — checking a second opinion's claims (2026-08-20)

A second AI's search on this same question reported: *"Exact match for ASM FinTech
(abhinavmukwane/FinRiskLensAI) and strong candidates for UdyamAI (SahanSrinivas/UdyamAI) and
Knight Fintech (knightspan/MSME-Healthcard)."* Verified each directly against the GitHub API
rather than accepting the claim. Result: one real, one fabricated, one real-but-misattributed.

### ASM FinTech — `abhinavmukwane/FinRiskLensAI` — **does not exist**

`gh api repos/abhinavmukwane/FinRiskLensAI` returns a 404. A full, unfiltered, paginated listing
of every one of Abhinav Mukwane's 20 public repos confirms no repository by that name, or any
fintech-risk-scoring name, exists under his account. §4's finding stands unchanged: no public
repo found for ASM FinTech Developer. The "exact match" claim was incorrect.

### Team UdyamAI — `SahanSrinivas/UdyamAI` — **confirmed, no change**

Matches §1 exactly. Both searches agree.

### Knight Fintech — `knightspan/MSME-Healthcard` — **real repo, wrong team**

This repo is genuine — created 2026-07-08, pushed 2026-07-13, live at
[msme-healthcard.vercel.app](https://msme-healthcard.vercel.app), a real XGBoost+SHAP build (see
below). But **its own README states, in the Team section: "Built by Team Anvay."** "Team Anvay"
appears nowhere on the official 24-team shortlist. The GitHub account `knightspan` has ~20 other
repos with no connection to enterprise fintech — `Uber-clone`, `slot-machine`, `evil-meter`,
`Jal-Sanchalak`, `Venture-Compass`, `Aurixys-Website`, `The-Gentlemen-s-Collective` — the profile
of a solo hackathon-hopper, not an account belonging to a 350-person, $23.6M-Series-A company
with its own domain (`knightfintech.com`) and named contact (`parthesh@knightfintech.com`). The
"Knight Fintech" match was username pattern-matching ("knightspan" ≈ "Knight" + "fintech") without
reading the content — exactly the failure mode §1's verification methodology exists to prevent.
**Do not cite this repo as Knight Fintech Pvt. Ltd.'s submission.**

That said, it's worth knowing about as unattached Track-03-flavored competitive landscape (an
unlisted round-1 entrant, same pattern as several others found and correctly excluded from the
original 24-team survey): real XGBoost PD model trained on Kaggle's public "Give Me Some Credit"
dataset with a documented alt-data feature bridge (and an explicit, honest disclosure that it
isn't trained on IDBI's real portfolio), SHAP explainability, a 4-pillar rule-based composite
score (Revenue Stability 30% / Compliance 25% / Cash-Flow 25% / Formality-Payroll 20%) with
missing-data weight redistribution, a provider-agnostic `DataSourceAdapter` interface nearly
identical in intent to SHROFF's own adapter pattern, an AI Credit Copilot, PDF credit-memo export,
a what-if simulator, and OCEN-compatible output. Genuinely one of the better-built Track-03-shaped
prototypes surfaced in this whole search — just not a competitor in your actual pool of five.

### What this changes

Nothing in §1–5's conclusions. It does confirm one real gap in method, now closed: the original
sweep searched `"MSME Health Card"` (spaced) and similar phrases, which does not token-match a
hyphenated, unspaced `"MSME-Healthcard"`. Re-running every Track 03 product name through both a
spaced and an unspaced/hyphenated variant is now standard practice for any follow-up pass — and
running it against Modus AI's and ASM FinTech's product names in this same session surfaced no
further hits, so their "not found" status is now confirmed under both tokenizations, not just one.
