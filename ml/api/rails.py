"""SHROFF lending rails — the OUTPUT side of the plan (explain-3.txt Step 5:
"plug the decision into ULI/OCEN, the pipes banks use to actually issue loans").

Two honest pieces:
  1. build_ocen_offer(): reshapes our decision into an OCEN 4.0-aligned Loan Offer a
     Loan Agent (LSP) can consume — with RISK-BASED PRICING (band/PD -> interest rate)
     so the "priced-for-risk" half of the thesis is concrete, not just approve/decline.
  2. rails_status(): the DataSourceAdapter registry. Like the screening is_sample chips,
     it states plainly what is LIVE-CAPABLE (AA input) vs ADAPTER-READY (ULI/OCEN) —
     these rails have no public sandbox, so we ship the real contract shape, not a
     fake "we're connected". Honesty is the credibility play.

Nothing here re-scores; it consumes the same payload /api/score returns.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

# Risk-based pricing — indicative MSME unsecured rates (% p.a., reducing balance).
# Rate rises with risk band; this is the "lend smaller / priced-for-risk" line made real.
BAND_RATE = {"A": 13.5, "B": 15.0, "C": 17.5, "D": 20.0, "E": None}
PROCESSING_FEE_PCT = 1.0          # of sanctioned amount
OFFER_VALIDITY_DAYS = 30

# OCEN offer status by our verdict
_STATUS = {"APPROVE": "APPROVED", "REFER": "PENDING_MANUAL_REVIEW", "DECLINE": "REJECTED"}


def risk_based_rate(band: str, pd_12m: float) -> float | None:
    """Band base rate + a small PD-linked premium (capped). None if not lendable."""
    base = BAND_RATE.get(band)
    if base is None:
        return None
    premium = min(3.0, round(pd_12m * 100 * 0.15, 2))  # up to +3% for higher PD within band
    return round(base + premium, 2)


def emi(principal: int, annual_rate_pct: float, months: int) -> int:
    """Reducing-balance EMI. EMI = P·r·(1+r)^n / ((1+r)^n − 1)."""
    if principal <= 0 or months <= 0 or annual_rate_pct is None:
        return 0
    r = annual_rate_pct / 12.0 / 100.0
    if r == 0:
        return int(round(principal / months))
    factor = (1 + r) ** months
    return int(round(principal * r * factor / (factor - 1)))


def build_ocen_offer(payload: dict) -> dict:
    """Reshape a /api/score payload into an OCEN 4.0-aligned loan offer."""
    now = datetime.now(timezone.utc)
    d = payload["decision"]
    verdict = d["verdict"]
    band = payload["band"]
    pd12 = payload["pd_12m"]
    amount = int(d.get("amount_inr") or 0)
    tenure = int(d.get("tenure_months") or 0)
    rate = risk_based_rate(band, pd12) if verdict != "DECLINE" else None
    monthly = emi(amount, rate, tenure) if rate else 0
    fee = int(round(amount * PROCESSING_FEE_PCT / 100.0)) if amount else 0
    total_interest = (monthly * tenure - amount) if monthly else 0
    pan = payload.get("pan") or payload.get("borrower_pan") or ""

    offer = {
        "offerId": f"OFR-{payload['msme_id']}-{now.strftime('%Y%m%d')}",
        "status": _STATUS.get(verdict, "PENDING_MANUAL_REVIEW"),
        "sanctionedAmount": {"value": amount, "currency": "INR"},
        "rationale": d.get("rationale", ""),
    }
    if verdict == "DECLINE":
        offer["rejectionReason"] = d.get("rationale", "Below lending threshold on alternate-data assessment")
    else:
        offer.update({
            "interestRate": {"value": rate, "type": "REDUCING_BALANCE", "unit": "PERCENT_PER_ANNUM"},
            "tenure": {"value": tenure, "unit": "MONTHS"},
            "emi": {"value": monthly, "currency": "INR"},
            "processingFee": {"value": fee, "currency": "INR"},
            "totalInterestPayable": {"value": total_interest, "currency": "INR"},
            "validUpto": (now + timedelta(days=OFFER_VALIDITY_DAYS)).date().isoformat(),
        })
    if verdict == "REFER":
        offer["reviewNote"] = "Deterministic overlay flagged this application — manual disposition required before disbursal."

    return {
        "ocenVersion": "4.0.0-aligned",
        "rail": "OCEN",
        "generatedAt": now.isoformat(timespec="seconds"),
        "loanApplicationId": f"LA-{payload['msme_id']}",
        "borrower": {
            "vua": f"{pan or payload['msme_id']}@shroff",   # OCEN Virtual Unique Address
            "pan": pan,
            "name": payload.get("name", ""),
        },
        "creditAssessment": {
            "assessmentProvider": "SHROFF",
            "healthScore": payload["score"],
            "band": band,
            "pd12m": pd12,
            "modelVersion": payload.get("model", {}).get("version", "v1"),
            "dataSources": ["AA:DEPOSIT", "AA:GSTR1_3B", "EPFO:ECR"],
            "consentPurposeCode": "103",
            "reasonCodes": [
                {"code": r["code"], "direction": r["direction"], "text": r["text"]}
                for r in payload.get("reasons", [])[:3]
            ],
        },
        "loanOffer": offer,
    }


def rails_status() -> dict:
    """DataSourceAdapter registry — what is live vs adapter-ready, stated honestly.
    Mirrors the screening is_sample honesty: real contract shapes, no fake connections."""
    rails = [
        {
            "rail": "Account Aggregator (AA)", "role": "input", "adapter": "SetuAAAdapter",
            "status": "live-capable",
            "detail": "ReBIT consent artefact (purpose 103, PERIODIC) live; Setu/Finvu UAT shape.",
            "fields": ["FIP", "consentHandle", "fiTypes:[DEPOSIT,GSTR1_3B]", "dataRange"],
        },
        {
            "rail": "EPFO", "role": "input", "adapter": "EPFOAdapter",
            "status": "adapter-ready",
            "detail": "Not an AA FIP yet — synthetic ECR on the real establishment-search shape.",
            "fields": ["establishmentId", "ecrMonth", "memberCount", "wageBill"],
        },
        {
            "rail": "ULI (Unified Lending Interface)", "role": "input / origination",
            "adapter": "ULIConnector", "status": "adapter-ready",
            "detail": "RBIH lender onboarding required; connector implements the real service-code contract.",
            "fields": ["serviceCode:[gst-returns,bank-statement,kyc]", "consentArtefact", "lenderId"],
        },
        {
            "rail": "OCEN 4.0", "role": "OUTPUT", "adapter": "OCENDerivedDataProvider",
            "status": "spec-conformant", "endpoint": "/api/ocen/offer/{msme_id}",
            "detail": "Health score exposed as a Loan-Agent-consumable loan offer (GST-Sahay / SIDBI pattern).",
            "fields": ["loanApplicationId", "creditAssessment", "loanOffer:{sanctionedAmount,interestRate,emi}"],
        },
    ]
    return {
        "rails": rails,
        "summary": "AA input live-capable · OCEN output spec-conformant · ULI adapter-ready on RBIH onboarding",
        "principle": "One DataSourceAdapter interface — IDBI's sandbox becomes one more adapter, wired in hours.",
    }
