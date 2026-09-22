# COMPETITORS.md — IDBI Innovate 2026, "Financial Health Score" shortlist

Track: Financial Health Score. Five teams shortlisted (per the coordinator's
table, Aug 2026):

| Team | Product | Contact | Codebase / live link found? |
|------|---------|---------|------------------|
| Modus AI | Udyam Sehat Card | manav@modussecure.com | Not found (no site behind `modussecure.com` either) |
| Knight Fintech Pvt. Ltd. | MSME Health Card | parthesh@knightfintech.com | No hackathon-specific link found, but the *company* is real — `knightfintech.com` is an operating digital-lending infra platform (see below) |
| ASM FinTech Developer | FinRiskLensAI | abhinavmukwane@gmail.com | Not found |
| **Walrus Securitas (us)** | **SHROFF** | anshumanatrey@gmail.com | **Public** — live at `shroff.vercel.app` / `shroff.onrender.com` |
| Team UdyamAI | UdyamAI | kollurisahan@gmail.com | Not found |

## Research note — be honest about the limits of this

On 2026-08-21 I ran three rounds of search for each team/product name:
1. General web search + `site:github.com` targeted queries — no public
   GitHub repo, deployed demo, or write-up turned up for any of the other
   four teams.
2. `"<product name>" demo OR app OR platform OR live` — same result, nothing.
3. **Guessed-hostname probing** — tried the obvious `vercel.app` /
   `netlify.app` subdomains a team might land on if they named their
   deployment after the product (the way we used `shroff.vercel.app`):
   `udyamai.vercel.app`, `udyam-ai.vercel.app`, `udyamai.netlify.app`,
   `modusai.vercel.app`, `modus-ai.vercel.app`, `modus-ai.netlify.app`.
   All six resolved with HTTP 200 — but fetching each page's actual
   `<title>` showed every one is an **unrelated, coincidentally-named
   project** (a VC-interview-prep tool, a startup-idea generator, a Google
   AI Studio demo, a Russian "Jarvis for your company" pitch, an unrelated
   "Modus IMI" industry-intelligence product). None are IDBI Innovate
   entries. Worth flagging explicitly: a same-name hosting URL is **not**
   evidence on its own — always open and read the page before citing it.

Net result: **no live deployment found for any of the other four teams.**
That's a genuinely useful data point (see the deployment-link section
below), not just an absence of evidence — but it means everything else in
this doc except the "us" row and the Knight Fintech company facts below is
inferred from team/product **names alone**, not actual code or product
decisions. Treat the positioning notes as hypotheses to sharpen once real
submissions are visible, not settled facts.

Two things worth doing to convert more of this from guesswork to fact, both cheap:
- **Ask the mentor** (Aug 24–25 connect, see `ROADMAP-ROUND2.md`) whether
  the platform exposes other shortlisted teams' round-1 decks/repos —
  many hackathon platforms publish shortlisted PoCs.
- **Devfolio MCP is configured but not authorized** in this environment — if
  this hackathon's submissions live on Devfolio, authorizing it (`/mcp` or
  `claude mcp`, interactively) could let a future session look up other
  teams' project pages directly instead of guessing from names.

## One real finding: Knight Fintech Pvt. Ltd. is an established company, not a hackathon-only team

Unlike the other three, `knightfintech.com` resolves to a real, operating
business: **Knight Fintech — "India's leading digital lending infrastructure
platform,"** Mumbai-headquartered, serving 500+ financial institutions
across co-lending, treasury management, and embedded finance since 2019, with
a live client login portal (`strategy.knightfintech.com`). I found no page
on their site specifically naming an "MSME Health Card" product — it's most
likely a hackathon-specific build on top of their existing lending
infrastructure, not a shipped product line — but the company itself is real,
funded, and already has production banking integrations. Treat them as the
one competitor genuinely likely to show polish and infrastructure depth
beyond an 8-day build; see the positioning note below.

---

## What the names tell us (inference, not evidence)

**Modus AI — "Udyam Sehat Card."** "Sehat" (health, Hindi/Urdu) makes this a
near-literal translation of "Financial Health Card" — same category as us.
A generic-sounding "AI" team name suggests they may lean on an LLM-forward
pitch rather than a validated statistical model. If so, that's a real
weakness to exploit (see below) — but this is a guess from the name alone.

**Knight Fintech Pvt. Ltd. — "MSME Health Card."** Almost the identical
product name to our own subtitle ("MSME Financial Health Card") — the
closest naming collision on the list. Confirmed (not inferred, see above):
a real Mumbai digital-lending infra company serving 500+ FIs since 2019.
That cuts two ways. Their risk to us: existing production integrations
(co-lending, treasury, embedded finance) mean their demo could look
noticeably more "banking-grade" polished than an 8-day hackathon build,
and they may already sit inside real lender data pipes we'd have to fake.
Their risk to *them*: an established B2B infra vendor retrofitting a
"Health Card" onto their platform in a week may ship something that's
architecturally their existing product with a new dashboard bolted on,
not a purpose-built two-sided risk engine — worth listening for on Demo
Day whether their pitch is genuinely GST/AA/entity-graph-native or a
relabeled version of what they already sell. Take them most seriously as
a peer either way, and double-check our deck doesn't read as
interchangeable with theirs on a skim.

**ASM FinTech Developer — "FinRiskLensAI."** The "Lens" + "AI" naming leans
toward a diagnostic/visualization angle, possibly LLM- or vision-model-heavy
(e.g., "point a lens at financial documents"). If their scoring path runs
through an LLM rather than a calibrated, monotonic model, that is a
documented, citable weakness — see the "AI-forward pitch" section below.

**Team UdyamAI — "UdyamAI."** Single gmail contact (not an org domain),
generic product name — most likely a smaller or first-time team relative to
Knight Fintech. Lower resourcing risk for them, but also the easiest team to
out-execute on polish and depth.

---

## Where SHROFF is already structurally ahead (facts about our own build, not guesses)

These aren't marketing claims — they're specific, checkable things in this
repo that a name like "Health Card" or "FinRiskLensAI" doesn't tell you the
other teams have:

1. **Deterministic core, generative shell — with the evidence to back it.**
   `BUILD-SPEC-track03.md` cites specific published results (HKMA/ASTRI PoC:
   XGBoost AUC 0.937 vs CNN 0.849; LLM-as-scorer AUROC ~0.52–0.63 vs 0.85–0.89
   for trained ML; RBI FREE-AI committee explainability push) for *why* the
   score is a monotonic LightGBM ensemble, not an LLM. If any competitor's
   "AI" name means "an LLM computes the number," this is a rebuttal we can
   deliver with citations, live, in Q&A.
2. **A real, government-sourced negative registry — not a toy blocklist.**
   ~45,000 real rows (MahaGST non-genuine taxpayers, SEBI/NSE debarred,
   CBDT defaulters, MCA struck-off, RBI/OpenSanctions watchlists), each row
   honestly tagged `is_sample`. This took deliberate `curl_cffi` TLS
   impersonation + offline seeding work (`ml/screening/SOURCES.md`) — not
   something a generic "Health Card" concept gets by default.
3. **The PAN-spine entity graph (phoenix-fraud detection).** No other team
   name suggests anything at this layer — "who's *behind* the borrower," not
   just "is the borrower clean." This is explicitly the hardest-to-copy piece
   (BUILD-SPEC calls it "the winning differentiator") because it requires the
   GSTIN→PAN decode, MCA director-graph walk, and a graph-native UI
   (React Flow) working together.
4. **"Both directions," structurally, not just in copy.** Most "Health Card"
   -style pitches solve one half of the brief — approve the invisible-but-
   healthy borrower. SHROFF's decision policy also actively catches the
   clean-on-paper-but-failing one (GST-vs-bank divergence, EWS, phoenix
   overlay), and the personas (`CONTRACTS.md`) are built to prove both
   halves live, not just described in a slide.
5. **A public, live, judge-pokable deployment right now.** `shroff.vercel.app`
   and `shroff.onrender.com/api/health` both answered 200 as of this writing.
   We actively searched for the other four teams' live links (search engines,
   GitHub, and guessed hosting subdomains — see the research note above) and
   found none; every guessed URL that resolved turned out to be an unrelated
   project once we checked its actual content. That's not proof they have
   nothing deployed, but it's the strongest signal available pre-Demo-Day
   that we're ahead on this specific booster. Keep it true through round 2
   (see `ROADMAP-ROUND2.md` Track D, keep-warm ping).
6. **A validation/benchmark artifact judges can actually check.**
   `docs/pipeline-proof.html` + `ml/artifacts/metrics.json` show holdout
   AUC/KS, PD-by-band monotonicity, and an approval-simulation with bad-rate
   improvement — reproducible from a cold clone (`RUN.md`). Per BUILD-SPEC's
   own research, "almost no team has this."

---

## How to widen the gap in round 2 (concrete, prioritized)

These map onto `ROADMAP-ROUND2.md` Phase 2 / `TASKS-ROUND2.md` — this section
is the "why" behind that prioritization from a competitive-positioning angle.

1. **Kill the "3 canned personas" tell.** The single biggest way a "Health
   Card" concept reads as a real product vs. a hackathon demo is whether a
   juror can type in *their own* PAN/GSTIN and get an honest answer,
   including "no hits." This is `TASKS-ROUND2.md` C.1/B.3 — do it first.
2. **Lead with the entity graph in the first 60 seconds of any pitch or demo,
   not buried in act 3.** If Knight Fintech's "MSME Health Card" name-collides
   with ours on a skim, the PAN-spine phoenix graph is the fastest way to
   show we're not the same product — it's visually distinctive (React Flow,
   flagged nodes) and conceptually hard to fake in 8 days if they don't
   already have it.
3. **If any competitor's demo visibly routes scoring through an LLM
   (inconsistent scores on identical input, or a chatbot-style "explain my
   score" that free-associates), have the citation list ready** — this is
   exactly the "How teams LOSE this" section of `BUILD-SPEC-track03.md`.
   Don't attack another team by name; just make sure our own determinism
   (same input → same score, shown live) is unmissable.
4. **Ship the what-if / counterfactual slider.** BUILD-SPEC's own framing —
   "file your pending GST returns → score +41 points" — is speculated to be
   something "nobody else has." Cheap to build (`optbinning`'s
   `Counterfactual` class is already scoped as the tool for this), high
   demo impact, and directly answers the "why was my limit only ₹8L"
   objection a judge is likely to raise.
5. **Push the "both directions" framing harder in language, not just
   mechanics.** A product literally named "Health Card" invites the reading
   "checks if you're healthy" (one direction). Every slide/demo beat should
   explicitly say the second half out loud — catching the clean-on-paper
   failure case — since that's the half a same-named competitor is least
   likely to have built out.
6. **Make the honesty artifacts (`is_sample` chips, the synthetic-data
   disclosure, the validation page) a visible part of the pitch, not a
   footnote.** For a Pvt. Ltd. competitor (Knight Fintech) who may show
   more UI polish, "we show our work and they might not" is a credibility
   axis that doesn't require out-building their design team.
