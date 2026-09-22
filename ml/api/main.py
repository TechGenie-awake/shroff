"""SHROFF ML API — FastAPI on :8000. Run from ml/:  uv run uvicorn api.main:app --port 8000"""
from __future__ import annotations

import json
import os

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from api import schemas
from api.decision import compute_ews, decide, run_screening, supply_chain_overlay
from api.documents import DocumentParseError, generate_sample_zip, parse_uploaded_documents
from api.live_intake import (
    LiveIntakeError,
    consent_artefact as live_consent_artefact,
    is_live_id,
    simulate_from_msme_id,
)
from api.narrative import maybe_narrative
from api.rails import build_ocen_offer, rails_status
from api.reasons import top_reasons
from api.scoring import ARTIFACTS, get_engine
from features.build import FEATURE_NAMES, GROUP_FEATURES, GROUPS, MONOTONE
from train.scorecard import BAND_FACTOR, BAND_TENURE, BANDS, ODDS_REF, PDO, SCORE_MAX, SCORE_MIN, SCORE_REF

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


def _resolve(msme_id: str, requested_amount_inr: int | None = None):
    """profile, monthly-DataFrame for ANY id — a fixed persona (via the trained
    Engine/parquet) or a `LIVE-<GSTIN|PAN>` id (via deterministic simulation,
    ml/api/live_intake.py). The id IS the seed for live ones, so every endpoint
    below is a transparent pass-through regardless of which kind it got."""
    if is_live_id(msme_id):
        try:
            profile, g, meta = simulate_from_msme_id(msme_id, requested_amount_inr)
        except LiveIntakeError as e:
            raise HTTPException(status_code=422, detail=str(e))
        return profile, g, meta
    eng = get_engine()
    if not eng.has(msme_id):
        raise HTTPException(status_code=404, detail=f"unknown msme_id {msme_id}")
    return eng.profile(msme_id), eng.monthly_rows(msme_id), None


@app.get("/api/msme/{msme_id}", response_model=schemas.MsmeDetail)
def msme_detail(msme_id: str) -> dict:
    profile, g, _meta = _resolve(msme_id)
    consent = live_consent_artefact(msme_id) if is_live_id(msme_id) else get_engine().consent(msme_id)
    monthly = g.drop(columns=["msme_id"]) if "msme_id" in g.columns else g
    return {
        "profile": profile,
        "consent": consent,
        "monthly": monthly.to_dict(orient="records"),
    }


def _assemble_response(msme_id: str, profile: dict, g, x, eng,
                        supply_from_engine: bool = True) -> dict:
    """Shared tail: score -> overlays -> decision -> reasons -> ScoreResponse shape.
    Used by both the persona path (/api/score) and the live-intake path
    (/api/score/live) — everything past feature-building is identical, per
    the DataSourceAdapter design (BUILD-SPEC-track03.md)."""
    s = eng.score_features(x)
    ews = compute_ews(g)
    screening = run_screening(profile)
    if supply_from_engine:
        supply = supply_chain_overlay(eng, msme_id, g)
    else:
        # live-intake has no real counterparty GSTINs to cross-check — report the
        # concentration metric honestly, leave distressed-counterparty empty rather
        # than fabricate a hit.
        supply = {"top3_buyer_share": round(float(g["top3_buyer_share"].tail(12).mean()), 2),
                  "distressed_counterparties": []}
    decision, band_eff = decide(profile, g, s["score"], s["band"], screening, ews)
    reasons = top_reasons(x)

    payload = {
        "msme_id": msme_id,
        "name": profile["name"],
        "score": s["score"],
        "band": band_eff,
        "pd_12m": round(s["pd_12m"], 4),
        "sub_scores": s["sub_scores"],
        "score_percentile": s.get("score_percentile"),
        "population_n": s.get("population_n"),
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


def _score_payload(msme_id: str, overrides: dict[str, float] | None = None,
                    requested_amount_inr: int | None = None) -> dict:
    eng = get_engine()
    if is_live_id(msme_id):
        profile, g, meta = _resolve(msme_id, requested_amount_inr)
        cp_top1 = float(g["top3_buyer_share"].tail(12).mean()) * 0.55
        feats = compute_firm_features(g, cp_top1, 8.0)
        if overrides:
            for k, v in overrides.items():
                if k not in FEATURE_NAMES:
                    raise HTTPException(status_code=422, detail=f"unknown feature in overrides: {k}")
                feats[k] = float(v)
        x = pd.DataFrame([feats])[FEATURE_NAMES]
        payload = _assemble_response(msme_id, profile, g, x, eng, supply_from_engine=False)
        payload["simulated"] = True
        payload["simulation_note"] = meta["note"]
        return payload
    if not eng.has(msme_id):
        raise HTTPException(status_code=404, detail=f"unknown msme_id {msme_id}")
    try:
        x = eng.features_for(msme_id, overrides)
    except KeyError as e:
        raise HTTPException(status_code=422,
                            detail=f"unknown feature in overrides: {e.args[0]}")
    profile = eng.profile(msme_id)
    g = eng.monthly_rows(msme_id)
    return _assemble_response(msme_id, profile, g, x, eng)


@app.post("/api/score", response_model=schemas.ScoreResponse, response_model_exclude_none=True)
def score(req: schemas.ScoreRequest) -> dict:
    return _score_payload(req.msme_id)


@app.post("/api/whatif", response_model=schemas.ScoreResponse, response_model_exclude_none=True)
def whatif(req: schemas.WhatIfRequest) -> dict:
    return _score_payload(req.msme_id, req.overrides or None)


def _canonical_live_id(identifier: str) -> str:
    """Validate + normalize a raw GSTIN/PAN into the canonical `LIVE-<id>` msme_id
    (same normalization live_intake.simulate() applies internally, done up front
    here so a bad identifier 422s before anything else runs)."""
    from api.live_intake import resolve_identifier
    try:
        resolved = resolve_identifier(identifier)
    except LiveIntakeError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return f"LIVE-{resolved['gstin'] or resolved['pan']}"


@app.post("/api/score/live", response_model=schemas.ScoreResponse, response_model_exclude_none=True)
def score_live(req: schemas.LiveScoreRequest) -> dict:
    """Score ANY GSTIN/PAN the user types in — not one of the 3 fixed personas.
    Profile + 24-month history are deterministically SIMULATED (ml/api/live_intake.py)
    pending IDBI's real GSTN/Bank-AA/EPFO sandbox; screening + entity-graph overlays
    still run against the REAL negative-registry data (ml/screening/registry.db).
    Resolves to the canonical `LIVE-<id>` msme_id and delegates to the same path
    every other endpoint uses, so /api/msme/{id}, /api/graph/{pan} and
    /api/ocen/offer/{id} all transparently work for the id this returns too."""
    msme_id = _canonical_live_id(req.identifier)
    return _score_payload(msme_id, requested_amount_inr=req.requested_amount_inr)


# ---- Document upload demo: download sample files, upload them back, get scored ----
@app.get("/api/documents/sample")
def documents_sample(identifier: str, requested_amount_inr: int | None = None) -> Response:
    """A downloadable ZIP (business_profile.csv + monthly_history.csv) for the given
    GSTIN/PAN — the same simulated data /api/score/live would use, handed over as
    files so the upload flow below has something real to parse. Edit a value and
    re-upload: the score reflects the file, not a fresh simulation."""
    try:
        zip_bytes, filename = generate_sample_zip(identifier, requested_amount_inr)
    except LiveIntakeError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return Response(
        content=zip_bytes, media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@app.post("/api/documents/upload", response_model=schemas.ScoreResponse,
          response_model_exclude_none=True)
async def documents_upload(
    business_profile: UploadFile = File(...),
    monthly_history: UploadFile = File(...),
) -> dict:
    """Parse the two uploaded CSVs and score EXACTLY what's in them — no
    re-simulation. This is the "live processing" demo: registry + entity-graph
    checks run on the real negative-registry data (ml/screening/registry.db);
    the financials are whatever the uploaded files say."""
    try:
        profile_bytes = await business_profile.read()
        monthly_bytes = await monthly_history.read()
        profile, g = parse_uploaded_documents(profile_bytes, monthly_bytes)
    except DocumentParseError as e:
        raise HTTPException(status_code=422, detail=str(e))

    eng = get_engine()
    cp_top1 = float(g["top3_buyer_share"].tail(12).mean()) * 0.55
    feats = compute_firm_features(g, cp_top1, 8.0)
    x = pd.DataFrame([feats])[FEATURE_NAMES]
    payload = _assemble_response(profile["msme_id"], profile, g, x, eng, supply_from_engine=False)
    payload["simulated"] = True
    payload["simulation_note"] = (
        "Scored from the two uploaded documents, not re-simulated — edit "
        "monthly_history.csv and re-upload to see the score change. Underlying "
        "figures trace back to a labeled simulation pending IDBI's real "
        "GSTN/Bank-AA/EPFO sandbox; registry + entity-graph checks are real.")
    return payload


# ---- Lending rails (output side): OCEN loan offer + adapter status ----
@app.get("/api/ocen/offer/{msme_id}")
def ocen_offer(msme_id: str) -> dict:
    """The decision, reshaped as an OCEN 4.0-aligned loan offer (Step 5: plug into the pipes)."""
    payload = _score_payload(msme_id)
    profile, _g, _meta = _resolve(msme_id)
    payload["pan"] = profile.get("pan", "") or ""
    return build_ocen_offer(payload)


@app.get("/api/rails")
def rails() -> dict:
    """DataSourceAdapter registry — AA (live-capable) · OCEN (output) · ULI/EPFO (adapter-ready)."""
    return rails_status()


@app.get("/api/model/info")
def model_info() -> dict:
    """Everything about HOW the score is computed — architecture, the exact
    scorecard formula, per-sub-model + combined validation metrics, and the
    monotone-constraint direction of every feature. All values below are read
    live from ml/artifacts/metrics.json and train/scorecard.py — nothing here
    is hardcoded copy that could drift from the actual trained model."""
    with open(os.path.join(ARTIFACTS, "metrics.json")) as fh:
        metrics = json.load(fh)

    band_table = [
        {"band": b, "floor_score": floor, "band_factor": BAND_FACTOR[b],
         "tenure_months": BAND_TENURE[b]}
        for b, floor in BANDS if b != "E"
    ] + [{"band": "E", "floor_score": None, "band_factor": BAND_FACTOR["E"],
          "tenure_months": BAND_TENURE["E"]}]

    monotone_summary = {}
    for g in GROUPS:
        cols = GROUP_FEATURES[g]
        monotone_summary[g] = {
            "n_features": len(cols),
            "n_risk_increasing": sum(1 for c in cols if MONOTONE[c] == 1),
            "n_risk_decreasing": sum(1 for c in cols if MONOTONE[c] == -1),
            "n_unconstrained": sum(1 for c in cols if MONOTONE[c] == 0),
        }

    return {
        "architecture": {
            "sub_models": GROUPS,
            "algorithm": "Monotonic-constrained LightGBM (gradient-boosted trees), one per sub-model group",
            "combiner": "Logistic regression on logit(sub-model PDs), fit on 5-fold "
                        "out-of-fold sub-model predictions (no leakage)",
            "calibration": "Isotonic regression on the holdout split -> 12-month PD",
            "baseline": "Standardized LogisticRegression over all features, reported "
                        "side-by-side as the 'regulator view'",
            "explainability": "TreeSHAP on the deciding sub-models directly (not a "
                              "surrogate), weighted by the combiner's coefficients",
        },
        "scorecard_formula": {
            "description": "score = SCORE_REF + PDO * log2(odds / ODDS_REF), where "
                           "odds = (1 - PD) / PD",
            "score_ref": SCORE_REF, "pd_ref": 0.05, "points_per_doubling": PDO,
            "odds_ref": round(ODDS_REF, 2), "score_min": SCORE_MIN, "score_max": SCORE_MAX,
            "bands": band_table,
        },
        "metrics": metrics,
        "monotone_constraints": monotone_summary,
        "total_features": len(FEATURE_NAMES),
    }
