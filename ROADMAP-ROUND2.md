# ROADMAP-ROUND2.md — Refined Prototype phase (shortlisted)

**Status:** shortlisted (announced Mon Aug 17, 2026). Induction session held Thu Aug 20.
**We are here:** Fri Aug 21, 2026.
**Deadline: Refined Prototype Submission — Wed Sep 02, 2026, 23:59 IST.**
Mentor & Mentee Connects: Mon Aug 24 – Tue Aug 25. Virtual Demo Day: **TBA**.

This is the round-2 counterpart to `TODO.md` (round-1 log, now historical) and
`BUILD-SPEC-track03.md` (architecture bible — still authoritative, don't refork it).
Round 1 shipped a working MVP: `ml/` scoring API + screening/entity-graph + `web/`
console, 3 verified personas, both deployed and **live right now**
(`shroff.vercel.app`, `shroff.onrender.com/api/health` both returned 200 as of
this writing). Round 2 is not "build it" — it's **"make it real, make it survive
a live judge poking at it, and widen the gap over the other 4 shortlisted teams."**

---

## What's actually different about round 2

Round 1 was judged on the idea + a synthetic-data MVP. Round 2 is a **Refined
Prototype** with mentor access and (per the roadmap) a narrower, harder bar:
does the thing hold up when someone who isn't us drives it? Three concrete
implications:

1. **Sandbox data may become available.** IDBI mentors are the first real
   chance to get actual AA/GST/EPFO sandbox credentials or a dataset. `TODO.md`
   already flagged this ("sandbox access arrives ~Aug 4 → swap synthetic for
   real") — that was a round-1-era guess; confirm the real offer on Aug 24–25.
2. **The submission format for round 2 is not yet confirmed.** We don't know
   yet whether it's another deck+link, a live jury demo, or both. Don't guess —
   get this in writing during the mentor connect (see the question list below)
   and update this doc same-day.
3. **Judges will likely click around, not just watch our script.** Three fixed
   personas were fine for a 4-minute pitch; a mentor/juror who types in an
   arbitrary PAN or GSTIN and gets nothing is a bad look. Closing that gap is
   the single highest-leverage build item this round (see Phase 2).

---

## Timeline

### Phase 0 — Now → Sun Aug 23 (prep, before mentors)

Get the repo and the team into a state where the mentor conversation is spent
extracting information, not explaining what we already have.

- [ ] Re-verify both deployments cold (Render free tier sleeps after 15 min —
  confirm the 15s timeout fix from the last commit actually survives a cold
  start end-to-end, not just under warm conditions)
- [ ] Write down the **exact question list for the mentor connect** (below) —
  don't wing it, this is a scheduled 1-2 day window, not office hours
- [ ] Triage the round-1 backlog (`TODO.md` → Optional/stretch section) against
  round-2 value: what-if slider, adverse-media scanner, live single-lookup,
  data.gov.in API key. Rank by judge-visible impact, not build cost.
- [ ] Confirm team registration details are final (solo vs with a second member —
  `APPLICATION.md` left this open; the shortlist table shows Walrus Securitas /
  anshumanatrey@gmail.com as the registered contact — reconcile who's actually
  building this round)

### Phase 1 — Mon Aug 24 – Tue Aug 25 (Mentor & Mentee Connects)

Treat this like the round-1 recon effort (`TODO.md` reverse-engineered the
Hack2skill API for real deadlines) — go in with specific asks, capture answers
in writing same day.

**Questions to get answered:**
- [ ] Is a sandbox (AA / GST / EPFO / core banking) actually being provisioned
  to teams this round, and if so, when and how do we get credentials?
- [ ] What exactly does "Refined Prototype Submission" require — deck again?
  Updated repo/deployment links? A live demo to the mentor/jury? A written
  report? Get the literal checklist.
- [ ] What does Virtual Demo Day look like — synchronous live demo, pre-recorded
  video, Q&A format, how long do we get?
- [ ] What's the judging rubric weight this round — technical depth, business
  viability, compliance/regulatory fit, or UX? (Shapes where we spend the next
  8 days.)
- [ ] Any explicit expectation around IDBI-specific integration (their actual
  systems/branding) vs a generic bank-agnostic prototype?
- [ ] Can the mentor point to other shortlisted teams' round-1 submissions on
  the platform? (We could not find any of the other 4 teams' codebases via
  public search — see `COMPETITORS.md` — the platform itself may expose this.)

### Phase 2 — Wed Aug 26 – Sat Aug 29 (core build)

This is the main build window. Two branches depending on the Phase 1 answer on
sandbox access — **don't block the whole week on it**, start the
judge-can't-break-it work in parallel regardless of the sandbox outcome.

**If sandbox access is granted:**
- [ ] Add a real `SetuAAAdapter`/sandbox implementation behind the existing
  `DataSourceAdapter` interface (`STACK.md` / `BUILD-SPEC-track03.md` already
  designed this seam — it should be a plug-in, not a rewrite)
- [ ] Retrain/recalibrate on whatever real signal the sandbox provides via the
  existing `ml/train` pipeline; keep the synthetic-v1 numbers as the labeled
  baseline, don't overwrite `metrics.json` history
- [ ] Update the deck's validation slide to show both, honestly labeled

**If sandbox access is NOT granted (default assumption until confirmed):**
- [ ] Stay on synthetic-v1, but close the credibility gap another way: expand
  the synthetic population beyond 8,000 MSMEs and/or add 1-2 new archetypes
  that stress-test the "both directions" thesis further
- [ ] Get the **data.gov.in API key** (`TODO.md` stretch item) — removes the
  10-row clamp, scales MCA struck-off coverage 900 → 129,694 rows. Free,
  low-effort, directly strengthens Pillar 3's realism claim.

**Judge-proofing (do regardless of sandbox outcome — highest leverage item this round):**
- [ ] **Live single-lookup / free-text entry** — let a juror type any PAN or
  GSTIN (not just the 3 fixed personas) into the screening + graph views and
  get a real, honest answer (including "no hits found"). This is the single
  biggest gap between "canned demo" and "working tool."
- [ ] Ship the **what-if / counterfactual slider** — BUILD-SPEC's own claim is
  "nobody else has these"; it's an `optbinning`-adjacent feature, not a new
  model, so it's cheap relative to its wow-factor
- [ ] PDF bank-statement upload path (BUILD-SPEC wow-moment #1) — even a
  narrow happy-path (one bank format) is worth more live than three personas
- [ ] Reliability pass: Render cold-start keep-warm ping (`STACK.md` flagged
  this as still-todo), error states in the console when the API is briefly
  down (fixture fallback already exists — verify it's not stale)

### Phase 3 — Sun Aug 30 – Mon Sep 1 (polish, deck, rehearsal)

- [ ] Refresh the deck (`docs/deck/`) with round-2 content: what changed since
  round 1, sandbox status (honest either way), new wow-moments, updated
  benchmark numbers if retrained
- [ ] Re-record or extend the demo video/script (`RUN.md`'s 3-act script) to
  include the new live-lookup and what-if moments
- [ ] Full cold-clone rehearsal: someone who isn't the primary builder runs
  `RUN.md` from a clean checkout and the deployed links, end to end
- [ ] Freeze feature work by end of Aug 31 — last day is for delivery packaging
  and rehearsal only, not new code (this is what BUILD-SPEC's round-1 playbook
  called "freeze code mid-afternoon, rehearse" — same discipline applies)

### Phase 4 — Tue Sep 2 (submit)

- [ ] Submit on the Hack2skill dashboard before **23:59 IST**
- [ ] Confirm both deployment links are live at submission time, not just
  during testing
- [ ] Log the submission in `APPLICATION.md`'s submission table

### Phase 5 — Post-submission → Demo Day (date TBA)

- [ ] Once Demo Day format is announced, block rehearsal time
- [ ] Keep the Render service warm in the days leading up to it (cron-job.org
  ping, per `STACK.md`)

---

## Non-negotiables carried over from round 1 (don't relitigate these)

- **Deterministic core, generative shell** — nothing generative computes a
  number. If sandbox integration or new features tempt a "just have an LLM
  score it" shortcut, don't — this is explicitly the thing that loses juries
  (`BUILD-SPEC-track03.md`, "How teams LOSE this").
- Every registry row keeps its `is_sample` chip — honesty-as-a-feature stays
  even as real data gets added.
- Single light theme ("Underwriter's Ledger") — no new design system.

## Risk / contingency

- **Sandbox access slips or never arrives** → default to the synthetic-v1
  path (Phase 2, second branch) and say so plainly on the deck; judges
  respect the honest-synthetic framing already used in round 1.
- **Render free tier cold-starts during live judging** → keep-warm ping is
  Phase 2, non-optional; have the fixture-mode fallback verified as a backstop.
- **Time collapses before Sep 2** → priority order if it does:
  live single-lookup > reliability/keep-warm > what-if slider > sandbox
  integration > PDF upload > deck polish. (Live-lookup and reliability are
  what stop a judge from hitting a wall; everything after is memorability.)
