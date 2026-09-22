"""Live intake — score ANY GSTIN/PAN the user types in, not just the 3 fixed
personas, while IDBI's real GSTN / Bank-AA / EPFO sandbox APIs are pending.

Deterministically SIMULATES what those APIs will return (same field shapes as
CONTRACTS.md's monthly schema + profile — see DATA-FIELD-REQUIREMENTS.md for
the exact request/response contracts submitted to IDBI), seeded from the
identifier itself so the same GSTIN/PAN always produces the same numbers
(same input -> same score, every time — a judge can ask twice).

This is intentionally the ONLY thing that changes when real sandbox
credentials arrive: everything downstream (feature engine, 4 sub-models,
meta-combiner, calibration, screening, entity graph, decision policy) is
untouched — `compute_firm_features` / `score_features` / `run_screening` /
`compute_ews` / `decide` / `top_reasons` all already take plain data, not an
msme_id, so this module is a drop-in DataSourceAdapter (BUILD-SPEC-track03.md).
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import date

import numpy as np
import pandas as pd

try:
    from screening.pan import validate_gstin, validate_pan
except ImportError:  # mounted with ml/ on sys.path instead of as a package
    from pan import validate_gstin, validate_pan

LIVE_PREFIX = "LIVE-"


def is_live_id(msme_id: str) -> bool:
    return str(msme_id or "").startswith(LIVE_PREFIX)

MONTHS = pd.period_range("2024-07", "2026-06", freq="M")
MONTH_STRS = [str(p) for p in MONTHS]
N_M = len(MONTH_STRS)

# Trimmed, self-contained copies of datagen's archetype knobs (ml/datagen/generate.py)
# so this module has no import-time side effects (datagen seeds the global `random`
# and Faker modules at import time — unsafe to import into a live API process).
STATES = {
    "27": ("Maharashtra", ["Mumbai", "Pune", "Nagpur", "Nashik"]),
    "07": ("Delhi", ["Delhi", "New Delhi"]),
    "29": ("Karnataka", ["Bengaluru", "Mysuru", "Hubballi"]),
    "33": ("Tamil Nadu", ["Chennai", "Coimbatore", "Madurai"]),
    "09": ("Uttar Pradesh", ["Lucknow", "Kanpur", "Noida"]),
    "24": ("Gujarat", ["Ahmedabad", "Surat", "Rajkot"]),
    "36": ("Telangana", ["Hyderabad", "Warangal"]),
}
DEFAULT_STATE = "27"

# name: (base_inflow_lo, base_inflow_hi, upi_lo, upi_hi, b2b_lo, b2b_hi,
#         top3_lo, top3_hi, emp_lo, emp_hi, wage_lo, wage_hi, sector_words)
ARCHETYPES = {
    "kirana_retail": (1.8e5, 12e5, 0.55, 0.85, 0.05, 0.30, 0.20, 0.60, 1, 6, 9000, 16000,
                       ["Kirana & General Stores", "Provision Stores", "Super Market", "Retail Mart"]),
    "trader": (5.0e5, 40e5, 0.08, 0.35, 0.60, 0.95, 0.45, 0.90, 2, 10, 12000, 22000,
               ["Trading Co.", "Traders", "Distributors", "Agencies"]),
    "light_manufacturer": (8.0e5, 60e5, 0.05, 0.25, 0.70, 0.97, 0.40, 0.85, 8, 40, 11000, 20000,
                            ["Industries", "Engineering Works", "Fabricators", "Manufacturing Co."]),
    "services": (3.0e5, 25e5, 0.30, 0.70, 0.30, 0.80, 0.30, 0.75, 3, 20, 15000, 30000,
                 ["Services", "Solutions", "Consultants", "Logistics"]),
}
ARCHETYPE_NAMES = list(ARCHETYPES.keys())

_FIRST = ["Ramesh", "Suresh", "Anita", "Vikram", "Priya", "Manoj", "Deepak", "Kavita",
          "Rajesh", "Sunita", "Arun", "Meera", "Sanjay", "Pooja", "Rahul", "Neha"]
_LAST = ["Sharma", "Verma", "Patel", "Gupta", "Kumar", "Singh", "Rao", "Mehta",
         "Joshi", "Reddy", "Nair", "Iyer", "Agarwal", "Desai", "Chopra", "Malhotra"]


class LiveIntakeError(ValueError):
    pass


def _seed_from(identifier: str) -> int:
    return int(hashlib.sha256(identifier.encode()).hexdigest()[:8], 16)


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def resolve_identifier(raw: str) -> dict:
    """GSTIN (15 chars) or bare PAN (10 chars). Structural validation only, per contract."""
    v = "".join(str(raw or "").split()).upper()
    if len(v) == 15:
        chk = validate_gstin(v)
        if not chk["valid"]:
            raise LiveIntakeError("Invalid GSTIN: " + "; ".join(chk["errors"]))
        return {"gstin": chk["value"], "pan": chk["pan"], "state_code": chk["state_code"],
                "state": chk["state"], "pan_entity_type": chk["pan_entity_type"]}
    if len(v) == 10:
        chk = validate_pan(v)
        if not chk["valid"]:
            raise LiveIntakeError("Invalid PAN: " + "; ".join(chk["errors"]))
        return {"gstin": None, "pan": chk["value"], "state_code": None, "state": None,
                "pan_entity_type": chk["entity_type"]}
    raise LiveIntakeError(
        f"Expected a 15-character GSTIN or a 10-character PAN, got {len(v)} characters")


def simulate(identifier: str, requested_amount_inr: int | None = None) -> tuple[dict, pd.DataFrame, dict]:
    """Deterministically simulate a profile + 24-month history for ANY GSTIN/PAN.

    Returns (profile_dict, monthly_dataframe, meta). Same identifier -> same
    output, every call (seeded RNG). meta carries the simulation parameters
    for transparency (never hidden from the response).
    """
    resolved = resolve_identifier(identifier)
    seed_key = resolved["pan"] or resolved["gstin"] or identifier
    rng = np.random.default_rng(_seed_from(seed_key))

    archetype_name = rng.choice(ARCHETYPE_NAMES)
    (inflow_lo, inflow_hi, upi_lo, upi_hi, b2b_lo, b2b_hi, top3_lo, top3_hi,
     emp_lo, emp_hi, wage_lo, wage_hi, sector_words) = ARCHETYPES[archetype_name]

    # risk_level in [0,1): 0 = healthiest plausible file, 1 = riskiest. This single
    # knob drives every economically-linked signal below so the simulated business
    # is INTERNALLY CONSISTENT (a risky file is risky across cash flow, GST, and
    # stability together — not independently-random noise on each axis).
    risk_level = float(rng.beta(2.0, 3.0))  # skews toward healthier, long tail of risky

    state_code = resolved["state_code"] or DEFAULT_STATE
    state_name, cities = STATES.get(state_code, STATES[DEFAULT_STATE])
    city = str(rng.choice(cities))

    is_company = resolved["pan_entity_type"] == "Company"
    first, last = str(rng.choice(_FIRST)), str(rng.choice(_LAST))
    sector_word = str(rng.choice(sector_words))
    legal_form = " Pvt Ltd" if is_company else ""
    trade_name = f"{last} {sector_word}"
    legal_name = f"{trade_name}{legal_form}"

    base_inflow = float(rng.uniform(inflow_lo, inflow_hi))
    growth_rate = _lerp(0.015, -0.028, risk_level) + float(rng.normal(0, 0.004))
    bounce_prob = _lerp(0.0, 0.22, risk_level)
    buffer_strength = _lerp(3.2, 0.35, risk_level)  # months of outflow held as balance
    self_transfer_share = _lerp(0.0, 0.14, risk_level)
    ontime_prob = _lerp(0.97, 0.35, risk_level)
    divergence_pull = _lerp(0.03, 0.42, risk_level) * (1 if rng.random() < 0.5 else -1)
    headcount_trend = _lerp(0.10, -0.30, risk_level)
    emp_base = max(1, int(rng.uniform(emp_lo, emp_hi)))
    wage_per_head = float(rng.uniform(wage_lo, wage_hi))
    upi_share = float(np.clip(rng.uniform(upi_lo, upi_hi) - 0.15 * risk_level, 0.02, 0.95))
    b2b_share = float(rng.uniform(b2b_lo, b2b_hi))
    top3_base = float(np.clip(rng.uniform(top3_lo, top3_hi) + 0.10 * risk_level, 0.10, 0.95))

    rows = []
    inflow = base_inflow
    for i, month in enumerate(MONTH_STRS):
        inflow = max(2e4, inflow * (1 + growth_rate + float(rng.normal(0, 0.05))))
        outflow_ratio = _lerp(0.78, 1.08, risk_level) + float(rng.normal(0, 0.03))
        outflow = inflow * max(0.4, outflow_ratio)
        eod_avg = max(1e4, inflow * buffer_strength / 12.0 * (1 + float(rng.normal(0, 0.12))))
        eod_min = max(0.0, eod_avg * _lerp(0.65, 0.10, risk_level))
        days_near_zero = float(np.clip(rng.poisson(_lerp(0.2, 9.0, risk_level)), 0, 30))
        bounce = int(rng.random() < bounce_prob) + int(rng.random() < bounce_prob * 0.3)
        emi = inflow * _lerp(0.02, 0.18, risk_level)
        self_transfer = inflow * self_transfer_share * float(rng.uniform(0.5, 1.5))
        emp = max(1, round(emp_base * (1 + headcount_trend * (i / N_M)) + float(rng.normal(0, 0.3))))
        wage_bill = emp * wage_per_head * float(rng.uniform(0.95, 1.05))
        on_time = int(rng.random() < ontime_prob)
        delay_days = 0 if on_time else int(rng.integers(3, 35))
        nil_return = int((not on_time) and rng.random() < 0.15)
        gst_turnover = max(0.0, inflow * (1 + divergence_pull) * float(rng.uniform(0.92, 1.08)))
        top3 = float(np.clip(top3_base + float(rng.normal(0, 0.03)), 0.05, 0.97))

        rows.append({
            "month": month,
            "bank_inflow_inr": round(inflow, 2),
            "bank_outflow_inr": round(outflow, 2),
            "eod_balance_avg_inr": round(eod_avg, 2),
            "eod_balance_min_inr": round(eod_min, 2),
            "days_near_zero": days_near_zero,
            "upi_txn_count": int(rng.integers(20, 400)),
            "upi_inflow_share": round(upi_share, 4),
            "bounce_count": bounce,
            "emi_debit_inr": round(emi, 2),
            "self_transfer_inr": round(self_transfer, 2),
            "gst_turnover_declared_inr": round(gst_turnover, 2),
            "gst_filed_on_time": on_time,
            "gst_filing_delay_days": delay_days,
            "gst_nil_return": nil_return,
            "b2b_share": round(b2b_share, 4),
            "top3_buyer_share": round(top3, 4),
            "employees_epfo": emp,
            "wage_bill_inr": round(wage_bill, 2),
        })

    monthly = pd.DataFrame(rows)
    cp_top1 = float(np.clip(top3_base * 0.55, 0.05, 0.9))
    cp_count = int(rng.integers(3, 25))

    incorp_year = int(rng.integers(2010, 2025))
    incorporated_on = date(incorp_year, int(rng.integers(1, 13)), int(rng.integers(1, 28))).isoformat()
    udyam = f"UDYAM-{state_code}-{str(incorp_year)[2:]}-{int(rng.integers(1000000, 9999999))}"

    annualized = 12.0 * base_inflow
    default_amount = int(round(np.clip(annualized * 0.25, 3e5, 5e7) / 50000) * 50000)

    canonical_id = resolved["gstin"] or resolved["pan"]  # preserves what the user typed
    profile = {
        "msme_id": f"{LIVE_PREFIX}{canonical_id}",
        "name": trade_name,
        "legal_name": legal_name,
        "entity_type": "company" if is_company else "proprietorship",
        "sector": archetype_name,
        "city": city,
        "state_code": state_code,
        "pan": resolved["pan"],
        "gstin": resolved["gstin"],
        "cin": None,
        "promoter_name": f"{first} {last}",
        "promoter_pan": resolved["pan"] if not is_company else None,
        "promoter_din": None,
        "udyam": udyam,
        "incorporated_on": incorporated_on,
        "requested_amount_inr": int(requested_amount_inr) if requested_amount_inr else default_amount,
        "is_persona": 0,
        "is_simulated": True,
    }
    meta = {
        "archetype": archetype_name, "risk_level": round(risk_level, 3),
        "state": state_name, "simulated": True,
        "note": "Profile + 24-month history are deterministically simulated from the "
                "identifier (same input always reproduces the same output) — IDBI's "
                "GSTN/Bank-AA/EPFO sandbox credentials are pending; this is a drop-in "
                "placeholder behind the same interface, not a stored or real record.",
    }
    return profile, monthly, meta


def simulate_from_msme_id(msme_id: str, requested_amount_inr: int | None = None
                           ) -> tuple[dict, pd.DataFrame, dict]:
    """Reconstruct the exact same simulation from a `LIVE-<GSTIN|PAN>` id — the
    id IS the seed, so this is fully deterministic and needs no stored state.
    Lets every endpoint that takes an msme_id (/api/score, /api/msme/{id},
    /api/ocen/offer/{id}) transparently serve a live-simulated business too."""
    if not is_live_id(msme_id):
        raise LiveIntakeError(f"not a live-intake id: {msme_id}")
    raw_identifier = msme_id[len(LIVE_PREFIX):]
    return simulate(raw_identifier, requested_amount_inr)


def consent_artefact(msme_id: str) -> dict:
    """Same ReBIT v2 shape as Engine.consent()'s generic (non-persona) branch —
    duplicated here so it needs no Engine/parquet lookup for a live-simulated id."""
    cid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"shroff-consent-{msme_id}"))
    return {
        "ver": "2.0.0", "txnid": str(uuid.uuid5(uuid.NAMESPACE_URL, f"txn-{msme_id}")),
        "consentId": cid, "ConsentHandle": str(uuid.uuid5(uuid.NAMESPACE_URL, f"h-{msme_id}")),
        "status": "ACTIVE", "createTimestamp": "2026-06-28T10:15:00.000Z",
        "ConsentDetail": {
            "consentStart": "2026-06-28T10:15:00.000Z",
            "consentExpiry": "2027-06-28T10:15:00.000Z",
            "consentMode": "STORE", "fetchType": "PERIODIC",
            "consentTypes": ["PROFILE", "SUMMARY", "TRANSACTIONS"],
            "fiTypes": ["DEPOSIT", "GSTR1_3B"],
            "DataConsumer": {"id": "FIU-SHROFF-IDBI", "type": "FIU"},
            "Customer": {"id": f"{msme_id.lower()}@aa"},
            "Purpose": {"code": "103",
                        "refUri": "https://api.rebit.org.in/aa/purpose/103.xml",
                        "text": "Aggregated statement information for loan underwriting"},
        },
        "is_sample": True,
        "is_simulated": True,
    }
