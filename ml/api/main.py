"""SHROFF ML API — FastAPI on :8000. Run from ml/:  uv run uvicorn api.main:app --port 8000"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api import schemas
from api.decision import compute_ews, decide, run_screening, supply_chain_overlay
from api.narrative import maybe_narrative
from api.rails import build_ocen_offer, rails_status
from api.reasons import top_reasons
from api.scoring import get_engine

app = FastAPI(title="SHROFF — MSME Financial Health Card API", version="v1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Guarded screening mount per CONTRACTS.md — boot order never breaks
try:
    from screening.router import router as screening_router
    app.include_router(screening_router)
except Exception:
    pass  # screening lands via Track B; integration agent verifies mounting


@app.on_event("startup")
def _load() -> None:
    get_engine()  # load artifacts + parquet once


@app.get("/api/health")
def health() -> dict:
    try:
        eng = get_engine()
        return {"status": "ok", "model_version": eng.bundle["version"],
                "artifacts_loaded": bool(eng.loaded)}
    except Exception:
        return {"status": "degraded", "model_version": "v1", "artifacts_loaded": False}


@app.get("/api/personas", response_model=list[schemas.PersonaOut])
def personas() -> list[dict]:
    eng = get_engine()
    return [{k: p[k] for k in
             ("id", "name", "business", "city", "segment", "requested_amount_inr", "blurb")}
            for p in eng.personas]


@app.get("/api/msme/{msme_id}", response_model=schemas.MsmeDetail)
def msme_detail(msme_id: str) -> dict:
    eng = get_engine()
    if not eng.has(msme_id):
        raise HTTPException(status_code=404, detail=f"unknown msme_id {msme_id}")
    g = eng.monthly_rows(msme_id)
    return {
        "profile": eng.profile(msme_id),
        "consent": eng.consent(msme_id),
        "monthly": g.drop(columns=["msme_id"]).to_dict(orient="records"),
    }


def _score_payload(msme_id: str, overrides: dict[str, float] | None = None) -> dict:
    eng = get_engine()
    if not eng.has(msme_id):
        raise HTTPException(status_code=404, detail=f"unknown msme_id {msme_id}")
    try:
        x = eng.features_for(msme_id, overrides)
    except KeyError as e:
        raise HTTPException(status_code=422,
                            detail=f"unknown feature in overrides: {e.args[0]}")
    s = eng.score_features(x)
    profile = eng.profile(msme_id)
    g = eng.monthly_rows(msme_id)

    ews = compute_ews(g)
    screening = run_screening(profile)
    supply = supply_chain_overlay(eng, msme_id, g)
    decision, band_eff = decide(profile, g, s["score"], s["band"], screening, ews)
    reasons = top_reasons(x)

    payload = {
        "msme_id": msme_id,
        "name": profile["name"],
        "score": s["score"],
        "band": band_eff,
        "pd_12m": round(s["pd_12m"], 4),
        "sub_scores": s["sub_scores"],
        "decision": decision,
        "reasons": reasons,
        "overlays": {
            "screening": screening,
            "early_warning": ews,
            "supply_chain": supply,
        },
        "model": eng.model_info(),
    }
    narrative = maybe_narrative(payload)  # None unless LLM_API_KEY set
    if narrative:
        payload["narrative"] = narrative
    return payload


@app.post("/api/score", response_model=schemas.ScoreResponse, response_model_exclude_none=True)
def score(req: schemas.ScoreRequest) -> dict:
    return _score_payload(req.msme_id)


@app.post("/api/whatif", response_model=schemas.ScoreResponse, response_model_exclude_none=True)
def whatif(req: schemas.WhatIfRequest) -> dict:
    return _score_payload(req.msme_id, req.overrides or None)


# ---- Lending rails (output side): OCEN loan offer + adapter status ----
@app.get("/api/ocen/offer/{msme_id}")
def ocen_offer(msme_id: str) -> dict:
    """The decision, reshaped as an OCEN 4.0-aligned loan offer (Step 5: plug into the pipes)."""
    payload = _score_payload(msme_id)
    payload["pan"] = get_engine().profile(msme_id).get("pan", "")
    return build_ocen_offer(payload)


@app.get("/api/rails")
def rails() -> dict:
    """DataSourceAdapter registry — AA (live-capable) · OCEN (output) · ULI/EPFO (adapter-ready)."""
    return rails_status()
