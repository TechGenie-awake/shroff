# RUN.md — SHROFF, MSME Financial Health Card (cold-clone to demo)

Two services. ML API (FastAPI) on **:8000**, web console (Next.js) on **:3000**.
The web console auto-falls back to contract-exact fixtures if the API is down
(a "FIXTURE MODE" chip appears instead of "LIVE API") — the demo never dies.

## Prerequisites

- Python 3.12 + [`uv`](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Node 20+ and npm

## 1. ML API (from repo root)

```bash
cd ml
uv sync                                       # installs everything from uv.lock

# one-time (only if the generated artifacts are missing from the clone):
uv run python datagen/generate.py             # -> ml/data/*.parquet + personas.json
uv run python train/train.py                  # -> ml/artifacts/model_bundle.joblib + metrics.json
python3 screening/seed_db.py                  # -> ml/screening/registry.db (stdlib-only, any py3)

uv run uvicorn api.main:app --port 8000       # serve
```

Smoke check:

```bash
curl -s localhost:8000/api/health
# {"status":"ok","model_version":"v1","artifacts_loaded":true}
curl -s -X POST localhost:8000/api/score -H 'Content-Type: application/json' \
     -d '{"msme_id":"RAMESH001"}' | python3 -m json.tool | head
```

## 2. Web console (second terminal, from repo root)

```bash
cd web
npm install
cp .env.local.example .env.local              # NEXT_PUBLIC_ML_API=http://localhost:8000
npm run dev                                   # http://localhost:3000
```

Production mode instead: `npm run build && npm run start`.

## Environment variables

| Var | Where | Default | Purpose |
|-----|-------|---------|---------|
| `NEXT_PUBLIC_ML_API` | `web/.env.local` | `http://localhost:8000` | Base URL the console calls; unreachable → fixture mode |
| `LLM_API_KEY` | ML API shell env | unset | OPTIONAL. Enables the LLM narrative paragraph on `/api/score` (any OpenAI-compatible endpoint via `LLM_BASE_URL` / `LLM_MODEL`). Template reasons are the default — no number is ever LLM-computed |

## 3. The 3-persona demo script (~4 minutes)

Open `http://localhost:3000` → one line on the thesis ("sees the invisible
borrower — in both directions") → click **Open Console**. The portfolio ledger
scores all three personas live (stat tiles: 1 approved / 1 referred / 1 declined).

**Act 1 — RAMESH001 (invisible-but-healthy → APPROVE).** Click his Run
Assessment / health card. Say: *"No credit history, so bureaus see nothing. We
read his consented bank + GST + EPFO trail instead."* Show: score ~769 band A,
APPROVE stamp, ₹12.5L over 36 months (20% Nayak working-capital norm in the
rationale), the AA consent-artefact chip (ReBIT v2 JSON — consented, not
scraped), and the monthly chart where GST-declared ≈ bank inflows. Point at the
signed TreeSHAP reason codes: every point on the score has a reason.

**Act 2 — SURESH002 (clean-on-paper-but-risky → DECLINE).** Show: score ~419
band E, DECLINE stamp, **EWS red** strip (bounces, headcount drop, GST late/nil
streak), and THE money-shot chart — GST-declared turnover running ~40% above
bank inflows (same ₹ axis, two lines: declared vs verified). Then the
supply-chain panel: his top buyer "Trident Textiles" sits on the Maharashtra
GST non-genuine list (distressed counterparty, 78% top-3 concentration).
*"On paper he's fine. The ledger says the business is burning."*

**Act 3 — PHOENIX003 (the phoenix borrower → score says maybe, graph says
REFER).** Show: score ~678 band C — a lendable thin-file. But the verdict stamp
is REFER and the rationale cites the registry hit by name: promoter's
co-director network reaches **Vertex Impex Pvt Ltd (CIN U74999DL2019PTC356789,
Struck Off + wilful-defaulter)** via co-director **Rakesh Sharma (DIN
07654321)**, plus a shared registered address. Open the entity graph — flagged
nodes in oxide red, phoenix banner on. *"Deterministic screening beats the
probabilistic score — the overlay can only worsen a verdict, never rescue one."*

Close: every registry row carries an `is_sample` chip (honest synthetic
mirrors of the real government schemas), metrics.json is shipped (holdout AUC
0.856 / KS 0.575, LogReg regulator-view baseline side-by-side), and nothing
generative ever computes a number.

## Ports & endpoints quick reference

- `GET :8000/api/health` · `GET :8000/api/personas` · `GET :8000/api/msme/{id}`
- `POST :8000/api/score` `{"msme_id":"RAMESH001|SURESH002|PHOENIX003"}`
- `GET :8000/api/screen?type=pan|gstin|cin|din|name&value=...`
- `GET :8000/api/graph/{pan}` (try `AAECN1234F`)
- Web: `:3000/` (story) · `:3000/console` (portfolio) · `:3000/console/{id}` (health card)
