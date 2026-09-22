"""Pydantic models mirroring the CONTRACTS.md ScoreResponse EXACTLY (field names are law)."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class ScoreRequest(BaseModel):
    msme_id: str
    loan_type: str = "working_capital"  # or "term_loan" — see api/decision.py LOAN_TYPES


class WhatIfRequest(BaseModel):
    msme_id: str
    overrides: dict[str, float] = Field(default_factory=dict)
    loan_type: str = "working_capital"


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
    loan_type: str
    rationale: str


class LoanTypeInfo(BaseModel):
    id: str
    label: str
    implemented: bool
    sizing_rule: str


class LoanTypesResponse(BaseModel):
    loan_types: list[LoanTypeInfo]


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


class ImpactSource(BaseModel):
    claim: str
    source: str
    range_inr: Optional[list[int]] = None
    range_usd: Optional[list[int]] = None
    converted_inr_at: Optional[float] = None


class BankImpact(BaseModel):
    auto_cleared: bool
    field_verification_saved_inr: list[int]
    onboarding_cost_saved_inr: list[int]
    basis: str
    sources: list[ImpactSource]
    honest_caveat: str


class ScoreResponse(BaseModel):
    msme_id: str
    name: str
    score: int
    band: str
    pd_12m: float
    sub_scores: dict[str, int]
    decision: Decision
    reasons: list[Reason]
    overlays: Overlays
    model: ModelInfo
    # optional LLM prose (env-gated; template reasons are the default path) — omitted when None
    narrative: Optional[str] = None
    # operational-impact overlay — onboarding/field-verification cost saved (see api/impact.py)
    bank_impact: Optional[BankImpact] = None


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
