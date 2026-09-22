# TASKS-ROUND2.md — round-2 task list

Companion to `ROADMAP-ROUND2.md` (the "why/when") and `CONTRACTS.md` (the
directory-ownership rules — still in force, don't cross the `ml/` / `web/`
/ `screening/` boundaries defined there). This is the "who does what" list.
Assign owners in the `Owner` column before Phase 1 starts (Aug 24) so mentor
time isn't spent figuring out logistics.

Legend: 🔴 must-have for Sep 2 · 🟡 strong-should · ⚪ stretch if time allows

---

## Track 0 — Logistics (either owner, do first)

| # | Task | Priority | Owner | Done |
|---|------|----------|-------|------|
| 0.1 | Confirm who's actually building this round (solo vs 2-person) and register accordingly | 🔴 | | ☐ |
| 0.2 | Write the mentor-connect question list into a shared doc/notes (see `ROADMAP-ROUND2.md` Phase 1) | 🔴 | | ☐ |
| 0.3 | Cold-verify `shroff.vercel.app` and `shroff.onrender.com/api/health` both respond | 🔴 | | ☐ |
| 0.4 | After Aug 25 mentor connect: update `ROADMAP-ROUND2.md` with the real submission-format answer | 🔴 | | ☐ |

## Track A — Data & sandbox (`ml/datagen`, `ml/features`)

| # | Task | Priority | Owner | Done |
|---|------|----------|-------|------|
| A.1 | Get sandbox status confirmed from mentors (blocks A.2–A.4) | 🔴 | | ☐ |
| A.2 | If granted: implement sandbox adapter behind `DataSourceAdapter`, don't touch existing synthetic path | 🟡 | | ☐ |
| A.3 | If granted: retrain via `ml/train/train.py` on new signal, diff against existing `metrics.json` before overwriting | 🟡 | | ☐ |
| A.4 | If not granted: register for a free data.gov.in API key, re-run MCA struck-off ingestion at full scale (900 → 129,694 rows) | 🟡 | | ☐ |
| A.5 | Expand synthetic population / archetypes if sandbox doesn't land (stress-test "both directions" further) | ⚪ | | ☐ |

## Track B — Scoring & decisioning (`ml/api`, `ml/train`)

| # | Task | Priority | Owner | Done |
|---|------|----------|-------|------|
| B.1 | Build the what-if / counterfactual endpoint + wire to `POST /api/whatif` (contract already defines this — currently optional/stretch, promote it) | 🟡 | | ☐ |
| B.2 | If retrained on new data: re-run `ml/train/benchmark.py`, refresh `artifacts/benchmark.json` and `proof_data.json` | 🟡 | | ☐ |
| B.3 | Add a "no hits found" honest-negative response path for live lookups (screening + graph) so arbitrary input doesn't error | 🔴 | | ☐ |
| B.4 | Wire the adverse-media/news-module overlay if time allows (½-day cap per `BUILD-SPEC-track03.md`) | ⚪ | | ☐ |

## Track C — Web console (`web/`)

| # | Task | Priority | Owner | Done |
|---|------|----------|-------|------|
| C.1 | **Live single-lookup UI** — free-text PAN/GSTIN entry point (console or a new `/console/lookup`), not just the 3 fixed personas | 🔴 | | ☐ |
| C.2 | What-if slider UI on the health card, wired to B.1 | 🟡 | | ☐ |
| C.3 | PDF bank-statement upload happy-path (one bank format is enough) | ⚪ | | ☐ |
| C.4 | Verify fixture-mode fallback still mirrors the exact `ScoreResponse` shape after any API changes | 🔴 | | ☐ |
| C.5 | Error/empty states for the new lookup flow (no hits, malformed ID, API down) | 🔴 | | ☐ |

## Track D — Reliability & deploy (`web/`, `ml/`, hosting)

| # | Task | Priority | Owner | Done |
|---|------|----------|-------|------|
| D.1 | Set up a keep-warm ping (cron-job.org, ~10 min) against `shroff.onrender.com/api/health` | 🔴 | | ☐ |
| D.2 | End-to-end cold-start test: kill local servers, hit deployed URLs fresh, confirm the 15s timeout actually covers Render's wake-up latency | 🔴 | | ☐ |
| D.3 | Re-run the full `RUN.md` cold-clone from a clean checkout — someone other than the primary builder drives it | 🔴 | | ☐ |

## Track E — Screening / entity graph (`ml/screening`)

| # | Task | Priority | Owner | Done |
|---|------|----------|-------|------|
| E.1 | Re-verify all registry sources still resolve after any data refresh (A.4) — rerun `seed_db.py`, spot-check real vs `is_sample` counts | 🟡 | | ☐ |
| E.2 | Supply-chain Tier B — cross-check counterparty GSTINs against the negative registry (distressed-buyer flag), extend from the existing Tier A concentration metric | ⚪ | | ☐ |

## Track F — Deck, video, submission

| # | Task | Priority | Owner | Done |
|---|------|----------|-------|------|
| F.1 | Refresh `docs/deck/` with round-2 delta: sandbox status, new features, updated numbers if retrained | 🔴 | | ☐ |
| F.2 | Extend `RUN.md`'s 3-act demo script with the live-lookup + what-if moments | 🔴 | | ☐ |
| F.3 | Re-record demo video/walkthrough | 🟡 | | ☐ |
| F.4 | Full rehearsal against `ROADMAP-ROUND2.md` Phase 3 freeze date (Aug 31) | 🔴 | | ☐ |
| F.5 | Submit on Hack2skill before Sep 2, 23:59 IST; log in `APPLICATION.md` | 🔴 | | ☐ |

---

## Daily standup prompt (use this, don't reinvent it each day)

Each day between now and Sep 2, answer three things in the team chat:
1. What did I finish yesterday (link the task # above)?
2. What am I doing today?
3. What's blocking me — and does it need the other person, or a mentor answer?

If Track A is blocked on the mentor's sandbox answer, work Track C/D in the
meantime — don't let the sandbox uncertainty stall the whole week (see
`ROADMAP-ROUND2.md` Phase 2).
