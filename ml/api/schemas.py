"""Pydantic models mirroring the CONTRACTS.md ScoreResponse EXACTLY (field names are law)."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class ScoreRequest(BaseModel):
    msme_id: str


class WhatIfRequest(BaseModel):
    msme_id: str
    overrides: dict[str, float] = Field(default_factory=dict)


class LiveScoreRequest(BaseModel):
    """Score an arbitrary GSTIN/PAN the user types in — not one of the fixed
    personas. See ml/api/live_intake.py: response is clearly marked `simulated`."""
    identifier: str
    requested_amount_inr: Optional[int] = None


class Reason(BaseModel):
    code: str
    group: str
    direction: str  # "positive" | "negative"
    text: str
    value: str
    shap: float


class Decision(BaseModel):
    verdict: str  # APPROVE | REFER | DECLINE
    amount_inr: int
    tenure_months: int
    rationale: str


class ScreeningOverlay(BaseModel):
    checked: bool
    hits: list[dict[str, Any]] = Field(default_factory=list)
    phoenix_flag: bool = False


class EarlyWarning(BaseModel):
    level: str  # green | amber | red
    triggers: list[str] = Field(default_factory=list)


class SupplyChain(BaseModel):
    top3_buyer_share: float
    distressed_counterparties: list[dict[str, Any]] = Field(default_factory=list)


class Overlays(BaseModel):
    screening: ScreeningOverlay
    early_warning: EarlyWarning
    supply_chain: SupplyChain


class ModelInfo(BaseModel):
    version: str
    auc: float
    ks: float
    trained_on: str


class ScoreResponse(BaseModel):
    msme_id: str
    name: str
    score: int
    band: str
    pd_12m: float
    sub_scores: dict[str, int]
    # this borrower's combined score vs the reference population, e.g. 87.3
    # means "healthier (lower PD) than 87.3% of the population" — computed
    # once at startup from the trained bundle, not hardcoded (ml/api/scoring.py)
    score_percentile: Optional[float] = None
    population_n: Optional[int] = None
    decision: Decision
    reasons: list[Reason]
    overlays: Overlays
    model: ModelInfo
    # optional LLM prose (env-gated; template reasons are the default path) — omitted when None
    narrative: Optional[str] = None
    # set only for /api/score/live — honesty marker per CONTRACTS.md's is_sample pattern
    simulated: Optional[bool] = None
    simulation_note: Optional[str] = None


class PersonaOut(BaseModel):
    id: str
    name: str
    business: str
    city: str
    segment: str
    requested_amount_inr: int
    blurb: str


class MsmeDetail(BaseModel):
    profile: dict[str, Any]
    consent: dict[str, Any]
    monthly: list[dict[str, Any]]
