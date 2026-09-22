# INFRA-AWS.md — what SHROFF actually needs to run in the cloud

**Every number in §1 and §2 was measured on this repo, not estimated.** Method and commands are in
§9 so you can re-run them. Prices in §7 are the only estimated numbers on the page and are labelled
as such.

Context that shapes every choice below: IDBI gives shortlisted teams **AWS + Applied Cloud Computing
(ACC) tooling** (`NOTES-internal.md`), and sandbox access lands ~Aug 4. So AWS isn't a preference
here, it's the sanctioned target. Cloud Run appears in §5 only as the comparison you asked for —
and it wins on exactly one axis that turns out to matter a lot.

---

## 1. Measured baseline — the ML API as it stands today

Ran `uvicorn api.main:app` from `ml/` on an 8-core darwin box, cold venv, real artifacts loaded.

| Measurement | Value |
|---|---|
| Cold start (process → `/api/health` 200) | **3.65 s** |
| RSS after boot, artifacts loaded | **318 MB** (second run peaked **463 MB**) |
| RSS steady-state under load | **200–280 MB** |
| First `/api/score` (SHAP explainer construction) | **762 ms** |
| Warm `/api/score` p50 | **87 ms** |
| `/api/screen` (SQLite exact + fuzzy) | **4.2 ms** |
| `/api/graph/{pan}` (recursive PAN walk) | **3.4 ms** |
| `/api/health` @ 10 concurrent | **195 req/s** |
| `/api/screen` @ 10 concurrent | **189 req/s** |
| `/api/score` @ 1 concurrent | **11.5 req/s** |
| `/api/score` @ 2 concurrent | **6.2 req/s** |
| `/api/score` @ 4 concurrent | **2.9 req/s** |
| `/api/score` @ 8 concurrent | **1.2 req/s** |
| `/api/score` @ 10 concurrent | **0.9 req/s** |

### Storage footprint today

| Artifact | Size | Notes |
|---|---|---|
| `artifacts/model_bundle.joblib` | 2.7 MB | 4 LightGBM sub-models (374–400 trees each) + meta + isotonic |
| `data/monthly.parquet` | 9.6 MB | 192,062 rows → **34 MB resident** in pandas |
| `data/features.parquet` | 2.3 MB | |
| `data/counterparties.parquet` | 2.2 MB | |
| `data/msmes.parquet` | 0.83 MB | |
| `screening/registry.db` | 7.6 MB | ~45k real gov rows; `negreg_name` alone is 21,009 |
| `ml/.venv` | **571 MB** | see §2.2 — ~211 MB of it is training-only |
| Container image (est. from venv + base + data) | ~1.2–1.5 GB | not yet built; this is the one estimate in §1–2 |

**Read on the numbers:** the deterministic parts of this service are genuinely fast — screening and
the graph walk answer in single-digit milliseconds and scale linearly. The scoring endpoint does not,
and §2.1 is why.

---

## 2. Three findings that change the sizing before you provision anything

### 2.1 Fuzzy name screening is 86% of scoring latency, and it holds the GIL

`cProfile` on `_score_payload("RAMESH001")`, 10 iterations:

```
   ncalls  tottime  cumtime  function
       10    0.000    1.729  api/main.py:68(_score_payload)
       10    0.000    1.498  api/decision.py:71(run_screening)        <- 86.6%
       30    0.492    1.451  screening/registry.py:161(_check_name)   <- 48 ms x 3 per request
   124540    0.375    0.619  difflib.py:622(quick_ratio)              <- 12,454 calls per request
```

`_check_name` runs three times per score (business name, promoter name, company name). Each call
takes a **length-band prefilter that returns 9,646 of 21,009 rows (46% of the table)** and then runs
`difflib.SequenceMatcher` over all of them in pure Python. `difflib` never releases the GIL, so
concurrent requests convoy — which is exactly the quadratic collapse in §1 (87 ms at n=1 → 6.75 s at
n=8). I confirmed it isn't BLAS/OpenMP thread thrash: re-running with
`OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=1` gave the identical 0.9 req/s at n=10.

Measured cost breakdown of one `_check_name`, and the fix:

| Variant | Time | Hits found |
|---|---|---|
| Current: `SELECT *` length-band + difflib over 9,646 rows | **20.0 ms** | 3 |
| `SELECT rowid, name_norm` instead of `SELECT *` (same algorithm) | 5.3 ms fetch (was 10.6) | — |
| `negreg_company_status` full scan + `normalize_name()` in Python per row | 2.1 ms | — |
| **In-memory token-blocking index + difflib on survivors** | **0.7 ms** | **3 — identical recall** |

Token blocking = an inverted index from every token ≥3 chars to row ids, built once at boot:
**24 ms to build, ~0.5 MB resident, 14,866 tokens.** For `"Ramesh Kumar"` it cuts candidates from
9,646 to 1,478 (7% of the table) and finds the same 3 hits. **28× faster, verified same output.**

Why this is the first thing to fix: at 20 ms × 3 = 60 ms of GIL-held pure Python per request, no
amount of RAM or vCPU helps. Fix it and the per-request cost drops to ~30 ms with the GIL mostly
free, which is the difference between provisioning one container and provisioning eight.

Two smaller ones in the same path, both one-liners:
- `Engine.monthly_rows()` boolean-masks all 192,062 rows on every request: **0.92 ms**. Setting the
  index at boot (`set_index("msme_id", drop=False).sort_index()`) → **0.40 ms**.
- Precompute `name_norm` on `negreg_company_status` in `seed_db.py` and index it — kills the 2.1 ms
  Python scan per call outright.

For reference, the parts everyone assumes are slow are not: **4× TreeSHAP = 2.42 ms**, and the whole
LightGBM + isotonic scoring path is ~6 ms. The ML is not your bottleneck.

### 2.2 The serving image carries ~211 MB of training-only dependencies

`ml/.venv` top packages, and whether they're imported when `api.main` loads (they are — `shap`
pulls them in eagerly; I verified 2,351 modules load at import):

| Package | Size | Needed to serve? |
|---|---|---|
| `pyarrow` | 125 MB | Yes — parquet reads |
| **`llvmlite`** | **125 MB** | No — numba backend |
| `scipy` | 83 MB | Yes — sklearn/shap |
| `pandas` | 48 MB | Yes |
| `sklearn` | 38 MB | Yes — isotonic calibration |
| **`matplotlib`** | **29 MB** | No — plots are train-time only |
| `numpy` | 25 MB | Yes |
| **`numba`** | **17 MB** | No |
| **`PIL`** | **15 MB** | No — matplotlib dependency |
| **`fontTools`** | **13 MB** | No — matplotlib dependency |
| **`faker`** | **12 MB** | No — `datagen` only |
| `lightgbm` | 8 MB | Yes |
| `shap` | 4 MB | Yes |

Splitting `pyproject.toml` into serving vs training extras removes ~211 MB from the image and cuts
import time. **Caveat worth testing before you commit to it:** `shap/__init__` imports its plotting
module, which imports matplotlib eagerly — so matplotlib may not be droppable without importing
`shap.explainers._tree` directly. Verify with a real container build; don't assume the 211 MB.

### 2.3 Until 2.1 ships, concurrency must be capped at the platform level

This is the finding that decides §5. A platform that lets you say "at most 2 requests per container"
survives today's code. A platform that fans 80 concurrent requests into one container does not — at
n=8 you're already at 6.75 s per request, well past a browser timeout, and the console scores three
personas in parallel on page load.

---

## 3. Complete feature inventory → AWS mapping

Tiered by what actually exists, because that determines what you provision in August versus what's a
slide. Status: **LIVE** = running code · **BATCH** = offline script in repo · **MANUAL** = done once
by hand, not automated · **PLANNED** = designed in `BUILD-SPEC-track03.md`, not built.

### 3.1 Serving path — LIVE today

| # | Feature | Where | Compute shape | AWS service | Sizing note |
|---|---|---|---|---|---|
| 1 | Next.js 16 console, App Router SSR, 3 routes | `web/` | Bursty, stateless, Node | **Amplify Hosting** (closest thing to Vercel; CI from GitHub built in) | 0.25–0.5 vCPU equiv |
| 2 | Fixture fallback when API unreachable | `web/src/lib/fixtures.ts` | None — client-side | *Keep as-is.* This is a circuit breaker; it's why the demo can't die | — |
| 3 | FastAPI scoring service, 8 endpoints | `ml/api/` | Long-lived Python, GIL-bound | **ECS Fargate** (recommended) · App Runner · Lambda container | see §6 |
| 4 | LightGBM 4-submodel ensemble + isotonic PD | `model_bundle.joblib` | 2.7 MB loaded at boot | **S3** (versioned) + **SageMaker Model Registry** for lineage | — |
| 5 | TreeSHAP reason codes | `api/reasons.py` | 2.42 ms, CPU | In-process — keep. **SageMaker Clarify** for batch/regulator attribution reports | — |
| 6 | Negative-registry screening, ~45k gov rows | `screening/registry.db` | Read-only, 4 ms | v1: bake `.db` into image. Prod: **Aurora Serverless v2 Postgres**. Fuzzy names: **AWS Entity Resolution** or **OpenSearch** | 7.6 MB → ~80 MB at full MCA scale |
| 7 | PAN-spine entity graph walk (phoenix detection) | `screening/graph.py` | Recursive, 3.4 ms | Postgres recursive CTE (**recommended** — see §7 on the Neptune trap) · **Neptune Serverless** if the graph grows past 2 hops | — |
| 8 | Parquet feature/monthly store | `ml/data/` | 14 MB disk → 34 MB RAM | **S3** + read at boot. Bank scale: **S3 + Glue/Athena**, hot rows in Aurora | dominates RSS |
| 9 | LLM narrative (env-gated, off by default) | `api/narrative.py` | 1 call/request, optional | **Bedrock** (Claude) — **check ap-south-1 model availability first, see §8** | — |
| 10 | OCEN 4.0 loan-offer rail | `api/rails.py` | Pure compute | In-process. Expose to Loan Agents via **API Gateway** + **WAF** | — |
| 11 | `DataSourceAdapter` registry | `api/rails.py` | Config surface | **AppConfig** or **SSM Parameter Store** | — |
| 12 | ReBIT v2 consent artefact generation | `api/scoring.py` | In-process | Prod needs immutable storage: **S3 Object Lock (WORM)** + **DynamoDB** index | see §8 |
| 13 | `/api/health` | `api/main.py` | Trivial | ALB / ECS health check target. **Add a separate `/api/ready`** — health currently returns `degraded` rather than failing, so a load balancer will route to a container with no model loaded | — |
| 14 | CORS `allow_origins=["*"]` | `api/main.py` | — | **Must change before anything is public.** Lock to the Amplify origin; put **Cognito** in front of the console | — |

### 3.2 Offline batch — BATCH, in repo, not on the serving path

| # | Feature | Runtime today | AWS service |
|---|---|---|---|
| 15 | Synthetic datagen — 8,000 MSMEs, 192k rows | 12 s | **AWS Batch** or **SageMaker Processing** |
| 16 | Feature engine — 45 features | 4 s | **SageMaker Processing**; **Glue** if it outgrows one box |
| 17 | Model training — 4 LightGBM + meta + isotonic, seed 42 | 20 s | **SageMaker Training Job**, orchestrated by **SageMaker Pipelines** |
| 18 | Benchmark harness — AUC/KS, band rank-order, approval sim | seconds | **SageMaker Processing** → results to **S3**; gate model promotion on it in Pipelines |
| 19 | `registry.db` seeding from staged CSVs | seconds, stdlib only | **Lambda** (it has no third-party deps — ideal Lambda candidate) |

The whole train pipeline is 36 seconds and deterministic. Don't over-engineer this: a single
SageMaker Pipeline with three Processing steps and one Training step covers it, and gives you the
model-lineage story the jury will ask about.

### 3.3 Registry scraping — MANUAL, and the biggest infra gap you have

This is the feature you flagged as "live scraping," and right now it isn't live at all: the ~45k real
rows were captured **once, by hand**, via headless-browser network inspection plus `curl_cffi` TLS
fingerprint impersonation, then staged to `seeds/real/*.csv` and loaded offline (`SOURCES.md`). That
was the right call for a demo that must not depend on the network — but a bank POC needs the feed to
refresh, and nothing in the repo does that.

Per-source, what the pipeline has to survive:

| Source | Rows | Transport | Cadence | Why Lambda alone won't do it |
|---|---|---|---|---|
| MahaGST Non-Genuine Taxpayers | 11,410 GSTINs | XLSX linked off homepage, URL changes with the "as on" date | Monthly | URL is not stable — needs a page fetch + link discovery, then openpyxl |
| OpenSanctions India (SEBI/NSE/UAPA/PEP) | 11,631 PANs, 20,853 names | Bulk CSV over plain HTTPS | Weekly | Fine on Lambda. Note the **CC BY-NC licence** — see §8 |
| data.gov.in MCA Company Master | 900 → 129,694 available | OGD REST, paginated, clamps to 10/req on the sample key | Quarterly (dataset frozen ~2021-03) | Fine on Lambda. **Register a free key** to remove the clamp — that's a 144× data increase for zero engineering |
| RBI Alert List | 95 | Static HTML `<table class=tablebg>` | Monthly | Fine on Lambda |
| CBDT arrears defaulters | 79 PANs | Liferay Objects REST, endpoint found in a minified bundle | Quarterly | **Akamai 403s full-header curl and a real browser request stack.** Needed `curl_cffi` Chrome TLS impersonation |

Mapping:

| Concern | AWS |
|---|---|
| Schedule | **EventBridge Scheduler** — per-source cron, not one monolithic job |
| Orchestration + retries + partial failure | **Step Functions** (a source going dark must not fail the run) |
| Fetch: plain HTTP/REST/CSV sources | **Lambda** (RBI, OpenSanctions, data.gov.in) |
| Fetch: Akamai/TLS-fingerprinted + link-discovery sources | **ECS Fargate task** — you need a real Chromium and `curl_cffi`, both of which are awkward in a Lambda zip and fine in a container (MahaGST, CBDT) |
| Outbound IP | Fargate in a **public subnet with a public IP** is cheapest. If a source starts rate-limiting by IP, **NAT Gateway + Elastic IP pool** — but note NAT is a ~$40/mo fixed cost (§7) |
| Raw landing zone | **S3, versioned**, keyed by source + fetch date, alongside the existing `manifest__*.json` — you get a free audit trail and can re-parse history without re-fetching |
| Parse + normalize | **Lambda** (openpyxl, csv) → **Glue** only if a source outgrows 15 min |
| Load | **Lambda** → Aurora upsert, replacing today's `seed_db.py` |
| Schema-drift + row-count alarms | **SNS** → your email. A gov portal changing its column order silently is the realistic failure mode here, not downtime |
| Secrets (data.gov.in key) | **Secrets Manager** |

One design note worth keeping: the fetch and the load are already decoupled in your repo (capture →
CSV → `seed_db.py`). Preserve that seam on AWS. It's what lets the service boot with zero network
dependency, which is the reason the demo has never broken.

### 3.4 PLANNED — cron jobs, agentic loop, and the rest

| # | Feature | Compute shape | AWS mapping |
|---|---|---|---|
| 20 | **Continuous Risk Monitoring / post-disbursal EWS** — monthly AA refresh per borrower, trigger on declining inflows, GST delay, payroll shrinkage | Scheduled fan-out over the whole portfolio | **EventBridge Scheduler** → **Step Functions Distributed Map** → **SQS** → Lambda/Fargate workers → **SNS/SES** alert to the RM. Distributed Map is the right primitive here: it handles 10 borrowers and 100,000 with the same code |
| 21 | **Adverse-media / online credibility scanner** — reuse the `news-module` (Hono + Drizzle + Postgres + Gemini): fetch → dedupe → entity-match → LLM classify → severity-weighted, time-decayed compliance overlay | Scheduled scrape + LLM classify + storage | **EventBridge Scheduler** → Lambda fetchers (RSS/NSE/SEBI/news) → **SQS** → Lambda dedupe/entity-match → **Bedrock** (Claude) classify → **Aurora** + raw in **S3**. Semantic dedupe: **Bedrock embeddings** + **Aurora pgvector** (not OpenSearch — §7) |
| 22 | **"Talk to your Health Card" Q&A agent** — read-only tool-calling loop; tools return computed features / SHAP / registry hits so it cannot invent a number | Agentic loop, bounded, ~3–8 tool calls | Simplest and best: **Bedrock tool use in-process** in the existing FastAPI — your tools are already functions in `api/`. Managed alternative: **Bedrock AgentCore**. Deterministic alternative: **Step Functions** with an explicit iteration cap. Add **Bedrock Guardrails**; trace with **CloudWatch + X-Ray**. Keep the loop off the decision path, which is already your locked architecture |
| 23 | **RAG over ~8 RBI/SIDBI policy PDFs** for regulatory citations on decline reasons | Retrieval | **Don't build vector infra for 8 documents.** `BUILD-SPEC` already concludes stuffed context beats pgvector here, and OpenSearch Serverless has a fixed-cost floor that dwarfs the value. If it grows past ~200 docs: **Bedrock Knowledge Bases** over S3 |
| 24 | **PDF / document upload parse path** | Async, spiky | **S3 presigned upload** → **Textract** (async, tables + forms) → Lambda normalize → **Bedrock** for messy residual fields → **SQS** between stages |
| 25 | **Supply-chain Tier B** — cross-check counterparties against the negative registry | Reuses #6 and #7, heavier walk | Same Aurora/graph path. Cheap to add; it's the "who does the borrower depend on" money shot |
| 26 | **Live Account Aggregator integration** — ReBIT v2 consent lifecycle, PERIODIC fetch, webhook callbacks | Inbound webhooks + scheduled fetch + crypto | **API Gateway** (mTLS webhook receiver) → **SQS** → Lambda → Aurora. Consent artefacts → **S3 Object Lock**. Keys → **Secrets Manager + KMS**. AA rails typically require a **static whitelisted egress IP** → NAT Gateway + EIP. **This is the single biggest prod-readiness item on the list** — everything else is code you control; this one is a counterparty integration with certification steps |
| 27 | **Production data path** — consent logs, portfolio persistence, auth | Relational | **Aurora Serverless v2 Postgres** + **Cognito**. `STACK.md` names Supabase; on AWS this is the equivalent, and it's the same one-connection-string swap you already designed for |
| 28 | **Retrain on IDBI sandbox data** (Aug 2–16) | Batch | **SageMaker Pipelines** inside the sandbox VPC. Same pipeline as #15–18, different input — which is exactly the "adapter seam" claim in `STACK.md`, now load-bearing |

---

## 4. What is *not* needed — and the money this saves

Worth stating explicitly, because a bank-POC architecture diagram invites over-provisioning:

- **No GPU.** LightGBM on 45 tabular features. `BUILD-SPEC` cites the evidence (HKMA/ASTRI: XGBoost 0.937 vs CNN 0.849). A GPU here is a cost with negative returns.
- **No Kubernetes / EKS.** Two services. Fargate is the correct altitude; EKS is a control-plane fee plus an ops burden for no benefit at this scale.
- **No Kafka / MSK.** SQS + EventBridge cover every event path listed above. MSK has a fixed-cost floor.
- **No vector database.** 8 policy PDFs (§3.4 #23). Revisit only when the adverse-media corpus needs semantic dedupe, and then use Aurora pgvector first.
- **No Neptune, initially.** Your graph walk answers in 3.4 ms in SQLite. See §7 for the cost.
- **No SageMaker real-time endpoint.** It's a persistent instance billed hourly to serve a 2.7 MB model that loads into your existing container in 3.65 s. Fargate is cheaper and simpler. SageMaker earns its place for *training, registry, and Clarify* — not for this inference.

---

## 5. Cloud Run vs the AWS options, for this specific workload

You asked about Cloud Run, so here it is honestly — and there's one axis where it genuinely wins.

| Concern | Cloud Run | ECS Fargate | App Runner | Lambda (container) |
|---|---|---|---|---|
| **Per-container concurrency cap** | **`--concurrency=2`, one flag** | No such knob — you control it in-app (uvicorn workers, semaphore) or at the ALB | Has a concurrency setting | **1 request per execution environment, by default** |
| Scale to zero | Yes | No (Fargate runs or it doesn't) | No | Yes |
| Cold start, ~1.5 GB image | Seconds; image streaming helps | N/A once running; task launch ~30–60 s | ~seconds | Slowest of the four with a large image; **Lambda SnapStart supports Python — verify current behaviour, it could change this materially** |
| Max resources | 8 vCPU / 32 GB | 16 vCPU / 120 GB | 4 vCPU / 12 GB | 6 vCPU-equiv / 10 GB, 15 min ceiling |
| Fits the IDBI-provided cloud | No | **Yes** | Yes | Yes |
| VPC / PrivateLink for a bank sandbox | Possible, more friction | **Native** | Limited | Native |

**The verdict, which follows from §2.3:**

- **Today's code, unfixed:** Cloud Run with `--concurrency=2` is the single easiest way to not fall
  over, and **Lambda is the sleeper pick** — one request per execution environment means the GIL
  convoy is structurally impossible, and 88 ms × low demo traffic sits inside the free tier. If you
  weren't targeting AWS for the IDBI sandbox, `--concurrency=2` on Cloud Run would be the answer.
- **After the §2.1 fix:** **ECS Fargate, 1 vCPU / 2 GB, 2–4 uvicorn workers.** This is the
  recommendation. It's on the sanctioned cloud, it goes into a VPC when the bank asks, and it has no
  concurrency cliff once name screening stops holding the GIL.
- **App Runner** is the middle option: closest to Cloud Run's ergonomics on AWS, has the concurrency
  knob, costs more per vCPU-hour than Fargate. Reasonable if you want the fix and the deploy in the
  same afternoon.

---

## 6. Sizing — the direct answer on RAM, vCPU, and storage

Derived from §1, with headroom. **512 MB does not work for the ML API** — boot alone peaked at
318–463 MB.

| Component | vCPU | RAM | Ephemeral storage | Basis |
|---|---|---|---|---|
| ML API — as-is | 1 | **2 GB** | 5 GB | 463 MB boot peak + 34 MB parquet + margin. 1 GB is the floor and it's tight |
| ML API — after §2.1 + §2.2 | 0.5–1 | **1 GB** | 3 GB | Slim image, indexed lookups |
| Web console (Amplify or Fargate) | 0.25–0.5 | 0.5–1 GB | — | Next.js 16 SSR, 3 routes |
| Scraper — Chromium/TLS sources | 1–2 | **2–4 GB** | 10 GB | Headless Chrome needs ~1 GB+ per page; `/tmp` for XLSX downloads |
| Scraper — plain HTTP sources (Lambda) | — | 512 MB–1 GB | 512 MB | I/O bound |
| Parser / loader (Lambda) | — | 1–2 GB | 1 GB | openpyxl over an 875 KB XLSX |
| Training job | 4 | 8–16 GB | 30 GB | 8k × 24 rows today; scale with real portfolio size |
| EWS monthly batch worker | 1–2 | 2–4 GB | — | Same feature pipeline as scoring; Distributed Map fans out |
| Adverse-media worker | 0.25 | 512 MB–1 GB | — | I/O + one Bedrock call |

### Storage plan

| Data | Today | Production | AWS |
|---|---|---|---|
| Model bundle | 2.7 MB | ~5 MB/version × versions | **S3** versioned + Model Registry |
| Parquet feature store | 14 MB | Grows with portfolio | **S3** (Parquet already — Athena reads it as-is) |
| Registry | 7.6 MB / 45k rows | ~80 MB at 129,694 MCA rows | **Aurora Serverless v2** |
| Raw scrape archive | — | ~5 MB per run, monthly | **S3 Standard** → Glacier IR after 90 d. Effectively free, and it's your audit trail |
| Container images | ~1.2–1.5 GB | ~0.8–1.0 GB slim | **ECR** (10 image lifecycle policy) |
| Consent artefacts + decision audit | — | Small, but retained 8–10 yr | **S3 Object Lock (WORM)** + CloudTrail — §8 |
| Adverse-media corpus | — | Grows continuously | Raw in **S3**, structured in **Aurora** |

---

## 7. Cost envelope — **estimates, verify on the AWS calculator**

I could not price these against the live ap-south-1 rate card, so treat every figure as an
order-of-magnitude planning number, not a quote. The *relative* sizes are the useful part.

| Item | Est. monthly (ap-south-1) | Note |
|---|---|---|
| Fargate ML API, 1 vCPU / 2 GB, always on | ~$35–40 | Or **near-zero on Lambda** at demo traffic |
| Amplify Hosting (web) | $0–15 | Free tier covers a demo |
| Aurora Serverless v2, min 0.5 ACU | ~$45 | **RDS `db.t4g.micro` at ~$12 is the better POC choice.** Check whether Aurora auto-pause applies to your config |
| S3 + ECR + CloudWatch | ~$5–15 | |
| EventBridge Scheduler + Step Functions + SQS | ~$1–5 | Effectively free at this scale |
| Bedrock (narrative, on-demand) | Low | Per-token; negligible for narrative. **Adverse-media classification at volume is the real driver** — meter it |
| **NAT Gateway** | **~$40 + data** | A fixed cost that surprises people. Avoid it while you can: public-subnet Fargate for scraping, VPC endpoints for AWS services. You'll need it when AA requires a static egress IP |
| **Neptune Serverless**, min 1 NCU | **~$115** | **The trap.** Your graph answers in 3.4 ms in SQLite. Use a Postgres recursive CTE and spend this money nowhere |
| **OpenSearch Serverless** | **High fixed floor** | The other trap. For 8 policy PDFs this is indefensible. Check the current minimum-OCU pricing before you consider it even for adverse media |
| **POC-grade total** | **~$120–200** | Fargate + Amplify + RDS micro + S3/events |
| **Bank-grade total** | **~$400–700** | Adds VPC + NAT + multi-AZ Aurora + WAF + Cognito + audit retention |

The two line items to defend in review are Neptune and OpenSearch. Both are easy to add to an
architecture diagram because they *sound* correct for "entity graph" and "search," and together they
can cost more than everything else combined while replacing code that already runs in single-digit
milliseconds.

---

## 8. Compliance layer — this is a bank POC, so it's not optional

- **Region: `ap-south-1` (Mumbai) or `ap-south-2` (Hyderabad).** RBI's payment-data localisation
  directive plus the AA/ReBIT framework mean this data does not leave India. No exceptions.
- **Bedrock model availability is a real gotcha.** Confirm which Claude models are served in
  `ap-south-1` before you design around them. If the answer involves a cross-region inference
  profile that routes to a non-Indian region, that is a data-residency problem for features #9, #21,
  and #22 — not a latency footnote. Verify before it's on a slide.
- **Encryption:** KMS CMK at rest (S3, Aurora, EBS), TLS 1.2+ in transit, no plaintext secrets —
  Secrets Manager for the data.gov.in key, AA credentials, and any LLM key.
- **Immutable decision audit:** every score, every reason code, every registry hit that forced a
  verdict. **S3 Object Lock (WORM)** + CloudTrail. Your signed TreeSHAP reason codes already produce
  exactly the artefact RBI's FREE-AI guidance asks for — store it so it's provable, not just
  displayable.
- **Access:** IAM least-privilege per service, Cognito on the console, WAF on public endpoints, and
  **fix the `allow_origins=["*"]` CORS in `api/main.py`** before anything is internet-reachable.
- **Model governance:** SageMaker Model Registry + Model Cards. Monotonic constraints and the
  side-by-side LogReg regulator baseline are already the strong part of this story.
- **OpenSanctions is CC BY-NC.** Fine for the hackathon; a commercial deployment reselling screening
  needs their paid licence. Already flagged in `BUILD-SPEC`; keep it flagged in the POC conversation
  so nobody discovers it late.
- **Retention:** bank credit records typically 8–10 years. S3 lifecycle + Object Lock retention
  periods, set once, at the start.

---

## 9. Sequencing — what to do, and when

**Phase 0 — now, before Jul 13.** Nothing on AWS. Ship Vercel + Render per `STACK.md`, with the
keep-warm ping. The deliverable is the deck; a cloud migration now is a distraction with no
shortlisting value.

**Phase 1 — if shortlisted, Aug 2–4 (~1 day of work).** Land the §2 fixes first, then: ECR image →
**Fargate** (1 vCPU / 2 GB) for the ML API, **Amplify Hosting** for the console, **S3** for
artifacts, **Secrets Manager** for keys, CORS locked, `/api/ready` added. Two services, no VPC
complexity yet. This is the demo the jury sees.

**Phase 2 — Aug 4–16, prototype phase.** **RDS Postgres** (registry + consent + portfolio, replacing
the baked SQLite), **EventBridge Scheduler + Step Functions** for the registry refresh (§3.3) and the
monthly EWS run (§3.4 #20), **SageMaker Pipeline** retraining on the IDBI sandbox data. Register the
data.gov.in key — 900 → 129,694 rows for zero engineering is the highest-leverage item on this whole
page.

**Phase 3 — bank POC, post-Aug 31.** VPC + PrivateLink into the bank's environment, live AA
integration with mTLS and static egress (#26 — start the certification conversation early, it's the
long pole), WAF + Cognito, adverse-media scanner, Q&A agent, audit WORM with real retention.

### Fix list, ordered by measured value

| Fix | Effort | Measured effect |
|---|---|---|
| 1. Token-blocking index for `_check_name` | ~30 lines | **20.0 ms → 0.7 ms per name, ×3 per request, identical recall.** Removes the GIL convoy |
| 2. `SELECT rowid, name_norm` in the fuzzy prefilter | 1 line | 10.6 ms → 5.3 ms on that query |
| 3. Precompute + index `name_norm` on `negreg_company_status` | `seed_db.py` | Kills a 2.1 ms Python scan per call |
| 4. `set_index("msme_id")` on `monthly` at boot | 1 line | 0.92 ms → 0.40 ms per request |
| 5. Split serving vs training dependencies | `pyproject.toml` | ~211 MB image reduction — **test it, `shap` imports matplotlib eagerly** |
| 6. Cap concurrency until fix 1 ships | Config | Prevents the 6.75 s-at-n=8 cliff |
| 7. Lock CORS to the console origin | 1 line | Required before anything is public |
| 8. Add `/api/ready` distinct from `/api/health` | ~5 lines | `/api/health` returns `degraded` instead of failing, so a load balancer will route to a container with no model |

Fixes 1–4 together should take the warm score from **87 ms to roughly 25–30 ms** and make the
endpoint scale with vCPU instead of collapsing. I measured each component in isolation; I have not
yet measured them composed in the live service — do that before quoting the combined number.

---

## Appendix — how to reproduce §1 and §2

```bash
cd ml

# cold start + RSS
.venv/bin/uvicorn api.main:app --port 8077 &
# poll /api/health until 200, then:  ps -o rss= -p <pid>

# latency
curl -s -o /dev/null -w "%{time_total}\n" -X POST localhost:8077/api/score \
     -H 'Content-Type: application/json' -d '{"msme_id":"RAMESH001"}'

# concurrency curve — repeat for n in 1 2 4 8 10
for i in $(seq 1 8); do curl -s -o /dev/null -X POST localhost:8077/api/score \
     -H 'Content-Type: application/json' -d '{"msme_id":"RAMESH001"}' & done; wait

# the profile that found §2.1
.venv/bin/python -c "
import warnings,cProfile,pstats,sys; warnings.filterwarnings('ignore'); sys.path.insert(0,'.')
from api.main import _score_payload
_score_payload('RAMESH001')
cProfile.run(\"[_score_payload('RAMESH001') for _ in range(10)]\",'/tmp/p')
pstats.Stats('/tmp/p').sort_stats('cumulative').print_stats(15)"

# serving-path import check (§2.2)
.venv/bin/python -c "
import sys,warnings; warnings.filterwarnings('ignore'); sys.path.insert(0,'.')
import api.main
print({m: m in sys.modules for m in ('numba','matplotlib','llvmlite')})"
```

Concurrency numbers were also re-run with `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
MKL_NUM_THREADS=1` to rule out BLAS thread contention — identical results, which is what points at
the GIL rather than thread thrash.
