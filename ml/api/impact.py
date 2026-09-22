"""Bank operational-impact overlay — what automating THIS assessment saves the bank.

NOT a training feature, NOT part of the credit decision (same overlay pattern as
screening/EWS/supply_chain). Answers the mentor's ask: quantify onboarding cost saved
and the human-in-the-loop field-verification cost saved.

Honesty boundary, deliberately built in: savings are claimed ONLY when the deterministic
overlays came back clean (APPROVE, no high-confidence registry hit, no phoenix flag, EWS
not red). A flagged application correctly still needs a human reviewer — claiming a
savings there would be dishonest, so it reports zero.

The rupee ranges are CITED INDUSTRY BENCHMARKS, not IDBI's own measured cost — that gap
is stated explicitly in the payload, not hidden, and is one of the sandbox-access asks.
"""
from __future__ import annotations

# Physical field/address-verification visit, per check.
# Source: SalaryBox "Background Verification Cost in India 2026" pricing breakdown.
FIELD_VERIFICATION_INR = (500, 1500)

# Traditional MSME onboarding: physical meeting + document collection, per applicant.
# Source: MSME digital-lending acquisition-cost research (The Digital Fifth / Dvara-style).
ONBOARDING_ACQUISITION_USD = (70, 200)
USD_INR = 83.0  # stated conversion rate — not live-fetched, flagged as such below


def compute_bank_impact(verdict: str, screening: dict, ews: dict) -> dict:
    auto_cleared = (
        verdict == "APPROVE"
        and not screening.get("phoenix_flag")
        and not any(h.get("confidence") == "high" for h in screening.get("hits", []))
        and ews.get("level") != "red"
    )
    onboarding_range_inr = [round(ONBOARDING_ACQUISITION_USD[0] * USD_INR),
                             round(ONBOARDING_ACQUISITION_USD[1] * USD_INR)]
    return {
        "auto_cleared": auto_cleared,
        "field_verification_saved_inr": list(FIELD_VERIFICATION_INR) if auto_cleared else [0, 0],
        "onboarding_cost_saved_inr": onboarding_range_inr if auto_cleared else [0, 0],
        "basis": (
            "Deterministic registry screening + AA-consented data cleared this application "
            "without a manual field-verification visit or a physical document-collection "
            "cycle — subject to IDBI's own KYC/compliance policy confirming which case "
            "classes still require an in-person check."
            if auto_cleared else
            "A deterministic overlay flagged this application for manual review — no "
            "automation savings are claimed here; routing this to a human reviewer is the "
            "correct, intended outcome, not a system failure."
        ),
        "sources": [
            {"claim": "Physical field/address-verification visit",
             "range_inr": list(FIELD_VERIFICATION_INR),
             "source": "SalaryBox — Background Verification Cost in India, 2026"},
            {"claim": "Traditional MSME onboarding (physical meeting + document collection)",
             "range_usd": list(ONBOARDING_ACQUISITION_USD),
             "converted_inr_at": USD_INR,
             "source": "MSME digital-lending acquisition-cost research (The Digital Fifth / Dvara)"},
        ],
        "honest_caveat": (
            "These are cited industry-benchmark ranges, not IDBI's own measured cost. "
            "Replacing this with IDBI's real per-application onboarding and field-"
            "verification cost is one of our sandbox-access data asks."
        ),
    }
