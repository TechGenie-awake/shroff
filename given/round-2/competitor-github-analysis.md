# IDBI Innovate 2026 — Top-24 Competitor GitHub Map

Every public GitHub repository I could confirm belongs to one of the 23 other teams on the
official **Top-24 Shortlist** (`shortlisted-team.txt`), found via `gh search repos`, GitHub's
user/org search, and targeted web search — never guessed, never fabricated. Each entry below is
labeled with a **confidence level** so you know how solid the match is before you act on it.

**Coverage: 14 of 23 competitors found (61%), 9 not found.** The 9 misses split into two very
different buckets — read §4 before assuming "not found" means "no threat."

---

## 1. How matches were verified

Product names alone are useless signal — "MSME Health Card," "Sanket," "DRISHTi," and "Dhan
Sarthi" each collide with dozens of unrelated repos (other hackathons, other years, generic SaaS
products with the same name). Every match below was confirmed by at least one of:

- **Explicit text match** — the repo's README names IDBI Innovate 2026 and the exact track/product.
- **Identity match** — the team leader's email local-part appears in the repo owner's username, a
  local file path in the README (`C:\Users\ashok\...`, `D:\hema\...`), a live-demo subdomain
  (`koushikdeb.duckdns.org`), or the README lists contact emails directly (PRAHARI does this).
- **Product-pair match** — one GitHub account holding *two* repos that each match a *different*
  product name from the *same* shortlisted team (this is how RR Squad's Sanket + DRISHTi were
  both resolved to the same account, `jaiw1`, with high confidence despite no literal name match).

Where a repo's content **contradicts** the shortlist (wrong track, wrong product name), I flagged
it rather than silently reconciling it — see Megalodon in §3.4.

---

## 2. Master table

| # | Track | Team | Product (per shortlist) | GitHub | Confidence | Live demo |
|---|---|---|---|---|---|---|
| 1 | 01 Wealth Advisory | Atomic | Dhan Sarthi | [Krishna3451/dhan-sarthi](https://github.com/Krishna3451/dhan-sarthi) | **Confirmed** | [dhan-sarthi.vercel.app](https://dhan-sarthi.vercel.app) |
| 2 | 01 Wealth Advisory | Team X | IDBI WealthPilot | [RaunakKanoji/idbi-wealth-advisory](https://github.com/RaunakKanoji/idbi-wealth-advisory) | **Confirmed** | [idbi-wealth-advisory.vercel.app](https://idbi-wealth-advisory.vercel.app) |
| 3 | 01 Wealth Advisory | Innovative Warriors | MITRA | [JeyaanthAnandan/idbi_hackathon_track1](https://github.com/JeyaanthAnandan/idbi_hackathon_track1) | **Confirmed** | — |
| 4 | 01 Wealth Advisory | Flexi Masters | Dhan Sarthi | [Avishkarrrrrr/dhan-sarthi](https://github.com/Avishkarrrrrr/dhan-sarthi) | **Confirmed** | [dhan-sarthi-omega.vercel.app](https://dhan-sarthi-omega.vercel.app) |
| 5 | 01 Wealth Advisory | AlphaIQ | Vikram AI | — | **Not found** | — |
| 6 | 01 Wealth Advisory | Abhimanyu Gupta | Zenith | — | **Not found** | — |
| 7 | 02 Prospect Assist | Knight Fintech Pvt. Ltd. | *(unnamed)* | — | **Not found — enterprise** | — |
| 8 | 02 Prospect Assist | Vinsight AI | IDBI Pravaah AI | [vineets02/idbi-pravaah-ai](https://github.com/vineets02/idbi-pravaah-ai) | **Confirmed** | — (localhost only) |
| 9 | 02 Prospect Assist | Ganit | ProspectIQ | — | **Not found — enterprise** | — |
| 10 | 02 Prospect Assist | Srishti GenAI | IDBI Prospect Assist | [ashokbugude/idbi-prospect-assist](https://github.com/ashokbugude/idbi-prospect-assist) | **Confirmed** | [idbi-prospect-assist.onrender.com](https://idbi-prospect-assist.onrender.com) |
| 11 | 02 Prospect Assist | RR Squad | Sanket | [jaiw1/sanket-lead-intelligence](https://github.com/jaiw1/sanket-lead-intelligence) | **High confidence** | [sanket-leads.vercel.app](https://sanket-leads.vercel.app) |
| 12 | 03 Financial Health | Modus AI | Udyam Sehat Card | — | **Not found** (false lead ruled out, see §4) | — |
| 13 | 03 Financial Health | Knight Fintech Pvt. Ltd. | MSME Health Card | — | **Not found — enterprise** | — |
| 14 | 03 Financial Health | ASM FinTech Developer | FinRiskLensAI | — | **Not found** (weak lead ruled out, see §4) | — |
| 15 | 03 Financial Health | **Walrus Securitas (us)** | **SHROFF** | this repo | — | — |
| 16 | 03 Financial Health | Team UdyamAI | UdyamAI | [SahanSrinivas/UdyamAI](https://github.com/SahanSrinivas/UdyamAI) | **Confirmed** | [amplifyapp.com link](https://main.d3ijnc0ydmm7t9.amplifyapp.com/) |
| 17 | 04 Default Prediction | Megalodon | DRISHTI | [itikelabhaskar/IDBI-Megalodon](https://github.com/itikelabhaskar/IDBI-Megalodon) | **Confirmed owner, product mismatch — see §3.4** | [idbi-megalodon.vercel.app](https://idbi-megalodon.vercel.app) |
| 18 | 04 Default Prediction | Barquecon Technologies Pvt Ltd | MSME Loan Stress Forecasting | — | **Not found — enterprise** | — |
| 19 | 04 Default Prediction | RR Squad | DRISHTi | [jaiw1/drishti-msme-early-warning](https://github.com/jaiw1/drishti-msme-early-warning) | **High confidence** | [drishti-ews.vercel.app](https://drishti-ews.vercel.app) |
| 20 | 04 Default Prediction | The U-Team | PRAHARI | [arungeekay/prahari-ews](https://github.com/arungeekay/prahari-ews) | **Confirmed** (emails in README incl. shriramkv@) | — |
| 21 | 04 Default Prediction | SAARTHI | SAARTHI | [DevDaring/IDBI_SAARTHI](https://github.com/DevDaring/IDBI_SAARTHI) | **Confirmed** (koushikdeb subdomain) | [koushikdeb.duckdns.org](https://koushikdeb.duckdns.org) |
| 22 | 05 Open Innovation | MessageMe | MessageMe (Arishti Cybertech) | — | **Not found — enterprise** | — |
| 23 | 05 Open Innovation | De-Dupe Hunter | Face Sentinel | [srijan14/FaceSentinel](https://github.com/srijan14/FaceSentinel) | **Confirmed** | — |
| 24 | 05 Open Innovation | Fraud Shield Edge | Fraud Shield Edge (Jocata) | — | **Not found — enterprise** | — |

---

## 3. Per-team feature inventory

### 3.1 Track 01 — Digital Wealth Management

#### Atomic — "Dhan Sarthi" — [Krishna3451/dhan-sarthi](https://github.com/Krishna3451/dhan-sarthi)
**"Meet your future self"** — age-progressed AI avatar wealth advisor inside IDBI GO Mobile+, grounded in Hershfield et al.'s "future self" behavioral-finance research (people who interact with an age-progressed avatar of themselves save ~2x more).

- Avatar-based advisory with a SIP slider that visibly ages/de-ages the avatar's projected life as you drag it
- **Live voice call** via OpenAI's `gpt-realtime` speech-to-speech model over WebRTC — the agent *moves the SIP slider itself* mid-conversation and narrates the projection, can book a human RM callback, all by voice, with live captions
- Security-conscious: voice enabled for all visitors via a serverless token backend, key never leaves the server, 10-minute ephemeral tokens, per-IP rate limiting, origin allowlist
- SEBI risk-profiling & suitability with audit trail, AI-use disclosure (SEBI Intermediaries Amendment 2025), DPDP-consent flows, human-RM escalation
- **Edge to watch:** the voice-agent-that-controls-the-UI pattern (not just answers questions, but drives the on-screen simulation) is a genuinely memorable live-demo moment.

#### Team X — "IDBI WealthPilot" — [RaunakKanoji/idbi-wealth-advisory](https://github.com/RaunakKanoji/idbi-wealth-advisory) (branded "IDBI Wealth Copilot" in-repo)
A **process-heavy monorepo**: one responsive Next.js app (`apps/banking/`) built mobile-first → tablet → desktop, with explicit phase gating (mobile must stabilize before desktop work starts) and a documented decision log (`docs/DECISION-LOG.md`).
- Services split: `api`, `advisory-engine`, `financial-intelligence`, `recommendation-engine`, `conversational-ai`, `integration-gateway`
- Non-negotiable invariants baked into docs: 320px-width support with zero horizontal overflow, identical financial outputs across viewports, voice/avatar/dashboard all degrade gracefully if a service fails
- A **sibling repo**, [`wealth-advisory`](https://github.com/RaunakKanoji/wealth-advisory), is an earlier Expo (React Native) universal-app attempt with Clerk auth — pushed an hour before the current repo, likely superseded
- **Read honestly:** the public README is almost entirely process/architecture documentation (phases, invariants, repo layout) with very little concrete feature description — can't confirm from the repo alone how much of the actual advisory UI is built out. Same builder also has round-1 attempts at Track02 (`idbi-prospect-assist`) and Track04 (`idbi-default-prediction`) that were *not* shortlisted — a serial multi-track submitter.

#### Innovative Warriors — "MITRA" — [JeyaanthAnandan/idbi_hackathon_track1](https://github.com/JeyaanthAnandan/idbi_hackathon_track1)
**"My Intelligent Treasury & Robo Advisor"** — riffs on IDBI's own tagline *"Bank Aisa Dost Jaisa"* (a bank like a friend). One of the most feature-dense Track01 entries found — **23 distinct capabilities**, all claimed working in the prototype:
- Avatar with TTS/voice/emotes + live in-chat charts; full **Hindi mode** (voice in + voice out)
- 360° behavioral insights (idle-surplus, spend-spike vs 3-month baseline, unused-subscription leakage, 80C gap)
- **"Wealth Time Machine"** — drag extra-SIP + bear/base/bull market levers, watch "age of financial freedom" move live, with toggleable life events (wedding/child/home/parents' care) reshaping the curve
- Round-up investing (sweeps UPI spare change into a liquid fund), peer benchmarking ("top 22% of salaried 25-32 metro earners"), drift detection & SIP-glide rebalancing (no tax-triggering sells)
- **Portfolio X-Ray** — quantifies regular-vs-direct-plan commission drag (1.82% vs 0.72% → ₹1.9L lost over 15 yrs) and fund overlap
- **LTCG harvesting** — computes the ₹1.25L/yr tax-free gains window from actual holdings
- **Fraud Shield** — ask about any "guaranteed 30%" offer, gets a SEBI/RBI-based 5-point scam check
- Human RM handoff with an auto-prepared context brief; gamified "Wealth XP" levels
- Design language: real IDBI brand colors/logo, Apple-product-page structure, full motion system respecting `prefers-reduced-motion`
- **Note:** the same builder also has an *unshortlisted* Track 03 entry, "UdyamSetu" (see §3.5) — relevant reading for us even though it's not an official Track03 rival.

#### Flexi Masters — "Dhan Sarthi" — [Avishkarrrrrr/dhan-sarthi](https://github.com/Avishkarrrrrr/dhan-sarthi)
Voice-first avatar advisor grounded in a genuinely **360° financial picture** (mock AA bank linking + manually-added equity/MF/bonds/gold), in **6 Indian languages** via Sarvam AI voice.
- **Strategy Studio** — ML-predicted algo-trading strategy (ported from the team's own prior RandomForest project) + live Nifty technicals (EMA/RSI/India-VIX), simulated broker execution, clearly labeled as simulation
- **Company Lens** — 4-part LLM analysis of a company's concall + investor-presentation documents (Quarter results / Risks / Projections / Verdict)
- **MPT Optimizer** — Markowitz efficient-frontier max-Sharpe optimization over the user's actual holdings, current-vs-optimal allocation, simulated rebalance
- Explicitly reuses **three of the team's own prior hackathon projects** as folded-in features (`final_year_project`, `financial_statement_analyzer`/`concall_insights`, and a teammate's `Portfolio-Optimization`) — a smart way to look feature-complete fast
- Runs on free tiers only (Gemini + Sarvam ₹100 credits + Vercel ≈ ₹0) — cost-consciousness stated as a design goal
- **Edge to watch:** MPT/efficient-frontier portfolio optimization and the "Company Lens" concall analyzer are both real quant/analytical depth beyond a typical avatar-chat wealth demo.

#### AlphaIQ — "Vikram AI" — not found
#### Abhimanyu Gupta — "Zenith" — not found
No public repository located after exhausting GitHub repo/user search and web search on both the
team/product names and the `zeyro.in` company domain. Either private, not yet pushed, or hosted
without a discoverable public link.

---

### 3.2 Track 02 — Lead Generation / Prospect Assist AI

#### Vinsight AI — "IDBI Pravaah AI" — [vineets02/idbi-pravaah-ai](https://github.com/vineets02/idbi-pravaah-ai)
Confirmed via a Windows dev path (`D:\hema\frontend`) matching the leader's email. Labeled **"Phase 0 local scaffold"** — a FastAPI + Vite skeleton with a `/v1/leads`, `/v1/offers/simulate`, `/v1/outcomes`, `/v1/metrics` API surface sketched but not yet fleshed into a demo. **This is the least mature repo found in the whole set** — worth noting as the weakest visible Track02 entry, though a private, more-finished build is entirely possible by submission time.

#### Srishti GenAI — "IDBI Prospect Assist" — [ashokbugude/idbi-prospect-assist](https://github.com/ashokbugude/idbi-prospect-assist)
A genuinely mature, versioned (v0.7.0) prototype targeting IDBI's stated ~1% lead-conversion problem.
- Composite scoring across **4 dimensions**: Repayment Capacity (bureau + txn-inferred + multi-bank income), Purchase Intent (session depth, calculator usage), Behavioral Discipline (day-1 salary spend, UPI merchant mix), Delinquency Safety (12-month stress signal)
- Lead tiers: Quality Lead → Serious → Interested → Window-shop Risk; product-matched to Home/Mortgage/Auto/Personal/Consumer Durable
- **Simulated Account Aggregator flow**: consent → fetch other-bank statements → automatic rescore, shown as a before/after ("Interested → Serious after AA fetch")
- **GenAI RM call-brief** per customer + underwriter-PDF export + CSV export for RM outreach
- Hybrid ML: XGBoost, 35 features, a capped **±8pt nudge** that "never demotes Quality Leads" — a deliberate safety rail
- Ships a `/impact` page with **Monte Carlo backtest** methodology and a documented `docs/AMA_ALIGNMENT.md` traceability doc mapping every feature back to the problem statement — a jury-facing move worth noting.
- RM-facing login gate (`/login`, demo PIN), full model-card endpoint (`/api/ml/model-card`).

#### RR Squad — "Sanket" — [jaiw1/sanket-lead-intelligence](https://github.com/jaiw1/sanket-lead-intelligence)
**"Lead Intelligence for the Liability Book"** — reads a bank's *own* liability-side accounts (salary rhythm, rent step-ups, fuel/cab spend surges, pre-salary balance dips) rather than external data.
- Scores three axes: **Intent**, **Capacity** (a behavioral *retained-income* estimate, explicitly not just declared salary), and — the standout — **Uplift**: a real uplift/Qini model that asks "does calling this person actually change the outcome," separating persuadable customers from likely-organic-converters and protecting do-not-disturb profiles from pushy calls
- Reports **honest, methodologically-labeled numbers**: 1.3% cold-call baseline → 36.0% precision at a top-2% queue (28× lift); Qini 30.3 vs 11.4 incremental conversions/1,000 calls; income estimate within ±15% for 95% of customers (73% for gig workers)
- **Fairness**: explicit 80%-rule disparate-impact audit across 9 demographic groups — reports **8 of 9 pass, 1 fails (gig workers, 0.51) and shows the failure rather than hiding it**, with a stated mitigation
- **Real-data proof point**: backtested the ranking logic against **26,000+ real Indian businesses'** published financials — top-decile prospects raised borrowings next FY at 2× the rate of the rest
- **Edge to watch:** the uplift-modeling angle (not just "who will convert" but "who converts *because* you called") is a genuinely more sophisticated framing than plain lead-scoring, and the honest fairness-failure disclosure is exactly the kind of RBI-FREE-AI-aligned honesty a jury rewards.

#### Ganit — "ProspectIQ" — not found (enterprise)
Ganit Inc is an established data-analytics/AI consultancy (ganitinc.com) — no public GitHub org or repo found, consistent with an enterprise team keeping a client-facing hackathon submission private.

#### Knight Fintech Pvt. Ltd. — Track 02 entry (product name blank on the shortlist) — not found (enterprise)
Knight Fintech is a real, established Mumbai digital-lending-infrastructure company (per a third-party GitHub description: "powers 500+ financial institutions across co-lending, digital lending, treasury management, supply chain finance, embedded [finance]"). No public repo or org found — expected for a company of this profile. **They submitted to both Track 02 and Track 03** (see below), which signals they're treating this as a genuine sales-channel play into IDBI, not a weekend hack — arguably the single most institutionally credible name on the whole shortlist, even with zero visible code.

---

### 3.3 Track 03 — Financial Health Score (our track)

#### Team UdyamAI — [SahanSrinivas/UdyamAI](https://github.com/SahanSrinivas/UdyamAI)
**The most direct, best-built Track03 rival found**, and the one to study closely.

- **Explicit positioning against real incumbents**: *"Perfios / Jocata / Karza sell [a point-in-time] scoring engine to banks. Lendingkart / Indifi lend once and move on. Nobody has built a Credit-Karma-style borrower-facing product for Indian MSMEs."* — frames itself as a **living, borrower-facing** health score (updates monthly) rather than a one-shot underwriting tool.
- **Real transaction data, not synthetic** — pulls from **AWS Aurora Serverless v2 Postgres** loaded with the **AgamiAI open datasets (Apache 2.0)**: 200 real bank accounts / **97,106 real transactions**, 100 real ITR filings. This is a genuine differentiator versus a synthetic-only core model — **flagged explicitly in §5 below.**
- **Live retrain endpoint** (`/api/retrain`) — one-shot logistic-regression retrain per lender (IDBI/SBI/HDFC) against the real transaction distribution, persisting weights + holdout AUC on every run; a "live retrain badge with per-lender AUC" shown in the UI
- 0–1000 score, 4 sub-scores, LLM explanation in **EN/HI/TE**, ITR-verified chip pulled from real filings, counterparty graph, "application history then vs now," **3 pre-qualified loan quotes ranked by confidence**
- **Lender view** with a real portfolio dashboard and **real bounce-detection alerts** wired to actual failed-transaction rows in the dataset (not a mock trigger)
- On-device GSTIN checksum validation on the landing page before any lookup happens

#### Modus AI — "Udyam Sehat Card" — not found (false lead ruled out)
A repo named `udyam-sehat` exists ([Piyush-Goenka/udyam-sehat](https://github.com/Piyush-Goenka/udyam-sehat)) and is genuinely well-built (0–100 score with letter grade, ULI/AA consent flow, six product screens) — **but its own README states "Team: ToWin (solo)"**, not Modus AI. This is a different, unrelated entrant who happened to name their product almost identically for the same track. **Do not confuse this with Modus AI's actual submission** — no repo confirmed under the Modus AI name or the `modussecure.com` domain. (A GitHub org `Modus-AI` exists but holds zero public repos.)

#### Knight Fintech Pvt. Ltd. — "MSME Health Card" — not found (enterprise)
Same company as the Track 02 entry above; no public repo. Dozens of unrelated "msme-health-card"-named repos exist from other (non-shortlisted) hackathon entrants — none reference Knight Fintech or the leader's email, so none are attributable here.

#### ASM FinTech Developer — "FinRiskLensAI" — not found (weak lead ruled out)
One repo matches the name almost exactly ([Souru27101999/FinRiskLens-AI](https://github.com/Souru27101999/FinRiskLens-AI)) but it has **no README** and was last pushed **June 30, 2026** — before IDBI Innovate's own problem-statement-explainer session, and the owner's profile name ("Sourabh") doesn't match the ASM FinTech Developer leader. Treat as an unrelated name collision, not a real lead.

---

### 3.4 Track 04 — Default Prediction Model

#### The U-Team — "PRAHARI" — [arungeekay/prahari-ews](https://github.com/arungeekay/prahari-ews)
Confirmed with certainty — the README lists four team contact emails directly, including the shortlist's own `shriramkv@gmail.com`. One of the strongest-engineered Track04 entries.
- 12-month PD via XGBoost with **deliberately honest out-of-time metrics** (AUC ≈0.94, balanced accuracy ≈0.88) — the README explicitly states *"not a rigged 0.99"*
- **Runway clock** — expected months to 90+ DPD per account, paired with a deterioration storyline + SHAP reason codes
- **Contagion graph** — models stress propagating down anchor→supplier payment chains with an actual auditable formula (`s_j += Σ w_ij · s_i · dependency_ij`), so *"a credit officer can recompute any node by hand from the edge table"* — no black box
- **Cost-of-error framed in rupees**: a missed default costs ~380× a false alarm (provisioning jumps 0.4%→15%), used to justify tuning for recall over raw accuracy
- One-click **SMA memo & CRILC report generation**, a monthly agent run that compiles the watch-list, and an explicit Phase-2 AWS mapping (models→SageMaker, narratives→Bedrock, mock integrations→Lambda, data→S3) baked into the architecture diagram
- Every AI-generated document ends with *"Draft prepared by PRAHARI AI. For officer review — not a final decision"* — a compliance-conscious framing choice.

#### SAARTHI — [DevDaring/IDBI_SAARTHI](https://github.com/DevDaring/IDBI_SAARTHI)
Confirmed via the live demo's own subdomain (`koushikdeb.duckdns.org`) matching the leader's email. **The most rigorously "trustworthy-AI" engineered entry found in the entire shortlist** — worth reading closely regardless of track, because several of its patterns are directly portable to SHROFF's Track03 problem.
- Calibrated LightGBM PD (AUC ≈0.97 on the real SBA loan book), **per-loan 12-month survival curve** (Cox proportional-hazards when a time/vintage column exists, else a clearly-labeled Weibull estimate)
- **Fixed 10-code reason taxonomy** (e.g., `LIQUIDITY_STRESS`, `REPAYMENT_HISTORY_POOR`) so every loan is explained in directly comparable terms — explicitly framed as answering the problem statement's "common interpretation framework" requirement
- **Faithfulness judge** — a *second, different-family* LLM checks every generated explanation against the model's own SHAP evidence before badging it "✓ Verified"; failed checks regenerate once, never silently pass
- **Counterfactual recourse engine** — finds the smallest realistic change (tenure, collateral, working capital) and shows before-PD → action → after-PD
- **Difference-aware fairness audit** (fairlearn) — demographic-parity/equalized-odds gaps, explicitly restricted to *within-risk-band* residuals so it flags only disparities that persist among applicants who are already similarly risky (protected attributes are audit-only, never model inputs)
- Validated end-to-end on **real, public datasets** — SBA (899k rows), German Credit, Taiwan Default, Berka, Lending Club, Kiva
- 5-layer JSON-safe LLM pipeline (strict-JSON → parse → cleanup → repair → judge-repair → pydantic validate → graceful degrade, never crash) across a **4-provider LLM gateway** (DeepSeek primary, Mistral fallback, OpenRouter, Gemini as a diverse judge) with key rotation and per-call health-checks
- Self-hosted on a real Ubuntu VPS behind Caddy with automatic HTTPS and DuckDNS — not just a Vercel free-tier deploy.

#### RR Squad — "DRISHTi" — [jaiw1/drishti-msme-early-warning](https://github.com/jaiw1/drishti-msme-early-warning)
- 9,000-business synthetic practice book with a deliberately lifelike deterioration ordering (cash-flow dips → overdraft reliance → bounces → missed payment), sized to mirror IDBI's real book (₹3L–₹5cr loans, ~3% flagged at any time)
- **A "predicted runway"** in months, with its own quoted error bar (median ≈3 months) — an honesty pattern worth noting
- **"Who to call first" — ranked by ₹ at risk**, a network-contagion lens wired for future CRILC/GST graph data, and an interactive provisioning-savings calculator for "what early action is worth"
- **Genuinely validated on real data**: the *same modelling approach* re-run on **~3,200 real Indian MSMEs** (17,000 company-years, FY2018–FY2026, 1,284 real defaults — an actual credit-rating downgrade to 'D') scores an honest **AUC 0.81 (95% CI 0.78–0.84)**, beating a logistic-scorecard baseline (0.70) on the *same real data* — the README states *"almost no other team will have any real number."* This claim now needs re-evaluating given PRAHARI, SAARTHI, and UdyamAI all also validate on real external datasets (see §5).

#### Megalodon — [itikelabhaskar/IDBI-Megalodon](https://github.com/itikelabhaskar/IDBI-Megalodon) — **product/track mismatch, flagged**
This is confirmed to be Megalodon's repo (owner username matches the shortlisted email exactly, and it's the only "Megalodon"+"IDBI" hit on GitHub) — **but the repo itself is titled "IDBI MSME HealthLens" and explicitly states it targets Track 03 (Financial Inclusion / Credit Decisioning)**, not Track 04 where they were actually shortlisted with a product called "DRISHTI." Most likely explanation: like several other teams here, Megalodon submitted multiple track ideas in round 1 (this Track03 HealthLens build being one of them) and got shortlisted under a different, differently-branded Track04 idea that either isn't public yet or lives under a teammate's account (a second contributor, `VA24d`, appears on this repo but their own account has no separate IDBI-named repo). **Treat this repo as directionally representative of the team's build quality, not a confirmed preview of their actual Track04 DRISHTI submission** — but it's still worth reading, because it's genuinely one of the most complete Track03 entries in this whole survey (see §3.5 below — it's a stronger reference point for us than most of the actual Track03 competitors).

#### Barquecon Technologies Pvt Ltd — "MSME Loan Stress Forecasting" — not found (enterprise)
A GitHub org (`barquecontech`) exists but holds only one empty test repo (`testRepoBarquecontech`) — confirms the company exists on GitHub but keeps real work private, consistent with an established fintech vendor rather than a hackathon team.

---

### 3.5 Track 05 — Open Innovation

#### De-Dupe Hunter — "Face Sentinel" — [srijan14/FaceSentinel](https://github.com/srijan14/FaceSentinel)
Real-time **1:N facial de-duplication** to catch the same face enrolling under a different identity at KYC — a direct hit on India's ₹36,014 cr FY25 reported bank fraud and ~1.33M frozen mule accounts.
- Face → 512-d embedding → vector search across the *entire* customer base (pluggable **Pinecone** managed or self-hosted **Redis Stack/RediSearch**, cosine similarity)
- Decision engine: strong face match + **different** government ID number → `FRAUD_ALERT_DIFFERENT_IDENTITY`; same ID → legitimate re-KYC. Full policy engine outputs `CLEAR / REVIEW / DUPLICATE_SAME_IDENTITY / FRAUD_ALERT_DIFFERENT_IDENTITY` plus a 0–100 risk score and reason codes
- CPU-only ONNX serving with a **model-free "demo embedding" mode** so the whole pipeline runs without the ~200MB weights — a nice judge-machine-friendly fallback
- Streamlit review console talking to the FastAPI backend over HTTP; Docker-compose one-command bring-up
- **Relevance to SHROFF:** this is exactly the kind of promoter-identity-fraud check that would strengthen our phoenix-detection story if a face/biometric layer were ever added on top of the PAN-graph — not urgent, but a real adjacent capability to be aware of if IDBI ever asks about biometric dedup across tracks.

#### MessageMe (Arishti Cybertech) — not found (enterprise)
Arishti is a real, IITB-incubated company already recognized/awarded by India's Ministry of Defence, MeitY, and (formerly) HRD for "MessageMe" — a quantum-tech-branded, consent-based secure messaging platform. This is an existing funded product being pitched into the wildcard track, not a fresh build — no public repo expected or found.

#### Fraud Shield Edge (Jocata) — not found (enterprise)
Jocata is an established, real AI-based AML/fraud risk-categorization and suspicious-activity-monitoring analytics company. Same pattern as Arishti — an existing enterprise product entering the wildcard track. No public repo expected or found.

---

## 4. The "not found" list, explained honestly

Two very different situations hide behind "not found" — don't read them the same way:

**Enterprise entrants (7 of 9 misses)** — Knight Fintech (×2 tracks), Ganit, Barquecon, Jocata,
Arishti Cybertech, and (functionally) Modus AI all show real corporate presence — company
websites, LinkedIn pages, in Barquecon's and Modus AI's case an actual (empty) GitHub
org — but zero public product code. This is expected professional behavior for companies with
real IP to protect, not a sign of a weak entry. **If anything, these are the entrants most likely
to already have a production-grade system behind closed doors** — Knight Fintech in particular
claims to power 500+ financial institutions already, per a third-party description found during
this search.

**Genuine unknowns (2 of 9 misses)** — AlphaIQ/Vikram AI and Abhimanyu Gupta/Zenith returned
nothing across extensive GitHub and web search on team name, product name, and (for Zenith) the
`zeyro.in` company domain. These may simply not have pushed public code, may be under a GitHub
username with no discoverable link to the team/product name, or may be genuinely early-stage.

---

## 5. What this survey means for SHROFF — the honest gap analysis

This is the part worth acting on. Reading all 14 confirmed repos together, three real patterns
stand out that SHROFF should reckon with — not because any single competitor beats us outright,
but because each one has found a different, real edge worth naming:

**1. "Real data" is now a crowded claim, and one specific version of it we don't have.**
SHROFF's differentiator has been ~45,000 **real government registry rows** (MahaGST, SEBI/NSE,
CBDT, RBI, OpenSanctions) for screening — genuinely rare and still true; no other team surveyed
appears to have anything close to it for negative-registry screening specifically. But for the
**core financial scoring model itself**, SHROFF trains on synthetic bank/GST data (by design, per
`STACK.md` — judge-proof, no network dependency). Three separate competitors now validate their
*scoring* model against real external data: **UdyamAI** retrains live against 97,106 real
AgamiAI bank transactions in a real Postgres instance; **RR Squad's DRISHTi** re-ran its full
modelling approach on ~3,200 real Indian MSMEs (1,284 real defaults, AUC 0.81 vs a 0.70 baseline);
**SAARTHI** validates end-to-end on real public credit datasets (SBA 899k rows, German Credit,
Taiwan Default). The "no other team will have a real number" claim in DRISHTi's own README is no
longer true across the shortlist — and worth knowing before a jury member who's seen multiple
demos points it out first. **If there's room before Sep 3 Demo Day, a real-external-dataset
side-by-side validation (even a small one, framed exactly like SHROFF's existing LogReg
regulator-baseline comparison) would close this gap cheaply — the benchmark harness in
`ml/train/benchmark.py` already has the right shape for it.**

**2. Trustworthy-AI features beyond SHAP reason codes are becoming the differentiator, not the score itself.**
SAARTHI's **faithfulness judge** (independently verifying that an LLM's plain-English explanation
doesn't contradict the model's own SHAP evidence) and its **counterfactual recourse engine**
("smallest realistic change to raise this score, with before→after PD") are both directly aligned
with RBI's FREE-AI push that SHROFF's own `BUILD-SPEC-track03.md` already cites as a scoring
factor. SHROFF currently has neither — it has signed reason codes but no "what would move this
score" answer for a declined applicant, and (correctly, by design) no LLM narrative to verify in
the first place. A lightweight counterfactual feature (which features, moved by how much, would
flip DECLINE→APPROVE or REFER→APPROVE) would be a cheap, high-signal addition that plays directly
to SHROFF's existing monotonic-model strength — moving a monotonic feature in its known-good
direction is a trivial, always-valid counterfactual to compute.

**3. Officer-workflow maturity is a real, separate axis from the score.**
Megalodon's Track03-branded "HealthLens" repo (even though it's not their actual shortlisted
Track04 entry — see §3.4) ships a **maker-checker decision workflow**, **champion-challenger
model governance**, and **fairness slices** as first-class console features — a credit-officer
workbench, not just an applicant health card. SHROFF's console is strong on the explainability
and phoenix-fraud side but its README doesn't describe a maker-checker approval step or explicit
model-governance screen. Given SHROFF already computes everything needed (score, band, decision,
reasons, screening hits) the missing piece is presentational — an officer approval/override
trail — not a new modeling problem.

**What to *not* chase:** RR Squad's contagion-propagation graph math (PRAHARI, and RR Squad's own
DRISHTi) is genuinely elegant for Track04's problem (predicting *when* an existing loan will go
bad), but SHROFF's PAN-spine phoenix graph already answers the analogous Track03 question
("who is this NEW applicant secretly connected to") better than any Track03 rival found here — no
other Track03 entry surveyed has an equivalent entity-graph fraud check. That remains SHROFF's
clearest, least-contested edge.
