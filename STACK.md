# STACK.md — tech stack decision (locked Jul 10, 2026)

## The one-line answer
Next.js on Vercel + server actions is enough for the app shell, **but the scoring brain is
Python** (LightGBM + SHAP have no JS equivalent worth trusting) — so the stack is a two-service
split, all free-tier: **Vercel (web) + one FastAPI service (ML) + embedded SQLite for v1,
Supabase Postgres as the production path.** Firebase rejected.

## Layers

| Layer | Choice | Where | Why |
|-------|--------|-------|-----|
| Web app | Next.js (App Router, TS) + Tailwind + shadcn/ui + Recharts + React Flow | **Vercel free** | Instant deploy link (shortlisting booster), server actions for light mutations |
| Scoring API | Python 3.12 + FastAPI + LightGBM (monotonic) + SHAP + scikit-learn calibration | **Render free** (or HF Spaces backup) | Vercel serverless can't run the Python ML stack; artifacts trained offline, loaded at boot, <100ms/score |
| Screening + graph | Stdlib Python module inside the ML service: SQLite registry tables + PAN-spine graph walk | same service | Deterministic lookups don't need a second service |
| Data (v1) | Synthetic parquet (datagen) + seeded SQLite (registries) — **in-repo, zero external deps** | in service | Demo-proof: no network, no accounts, no cold-start dependency chain |
| Data (prod path) | **Supabase Postgres** (consent logs, portfolio persistence, auth when needed) | Supabase free | One connection string reachable from both Vercel and Render; SQL joins the registry/graph needs. **Not wired in v1** — needs your account; add when we deploy |
| LLM (edges only) | OpenAI-compatible endpoint, env-gated: narrative from SHAP | API | Template fallback default — core demo needs NO API key. Nothing generative touches the number |
| Adverse media | Existing news-module (Hono+Drizzle+Neon+Gemini) as an adapter | later | ½-day wire-up, post-core |

## Why NOT Firebase
Document store fights this product: registry screening is multi-key relational lookup
(PAN/GSTIN/CIN/DIN joins), the entity graph is recursive joins, features are tabular
aggregations. Postgres/SQLite do all three natively; Firestore does none well.

## Why SQLite now, Supabase later
Creating a Supabase project needs your login — can't be agent-provisioned. Embedded SQLite
makes the demo self-contained (judge-proof), and the adapter seam (`registry.py`, one
connection layer) makes the swap a config change, which is itself a good "production path"
slide line.

## Deploy plan (when you say go)
1. `git init` done → push public GitHub repo (submission booster #2).
2. Vercel → import `web/`, set `NEXT_PUBLIC_ML_API`.
3. Render → `ml/` as a uvicorn web service (free). Free tier sleeps after 15 min →
   add a 10-min keep-warm ping (cron-job.org) so it's hot during judging.
4. Deployment link (booster #1) = the Vercel URL.
