"""SHROFF — synthetic MSME data generator (Track A, step 1).

Emits (all under ml/data/):
  msmes.parquet           one row per MSME (profile + default_12m label + is_persona)
  monthly.parquet         24 monthly rows per MSME ending 2026-06 (14 for PHOENIX003)
  counterparties.parquet  top-5 buyer GSTINs + shares per msme per month (quarterly-stable)
  personas.json           3 demo personas + ReBIT-style consent artefacts

Deterministic: SEED=42 everywhere (numpy, random, Faker, uuid5).
Label design: latent health index = weighted, economically-motivated signals + noise
-> logistic -> Bernoulli. Target prevalence ~10%, achievable AUC ~0.85-0.92 (NOT 1.0).
See DATA.md for assumptions and weights.
"""
from __future__ import annotations

import json
import random
import string
import uuid
import zlib
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

# ----------------------------------------------------------------------------- config
SEED = 42
N_POP = 8000                       # non-persona synthetic MSMEs
MONTHS = pd.period_range("2024-07", "2026-06", freq="M")   # 24 months
MONTH_STRS = [str(p) for p in MONTHS]                      # 'YYYY-MM'
N_M = len(MONTHS)
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# label calibration knobs (tuned so oracle AUC ~0.90, trainable AUC ~0.85-0.92)
LABEL_SLOPE = 1.9        # weight on the standardized risk signal
LABEL_NOISE_SD = 1.15    # irreducible noise in the latent index
TARGET_PREVALENCE = 0.10

# signal -> risk weights (positive = riskier). Documented in DATA.md.
W = {
    "inflow_growth": -0.90,   # log(mean inflow last-6m / first-6m)
    "buffer": -0.70,          # mean(eod_balance_avg) / mean(bank_outflow)
    "bounce_rate": +0.85,     # bounces per month
    "gst_ontime": -0.60,      # share of months GST filed on time
    "divergence": +0.75,      # |log(sum GST declared / sum bank inflow)|
    "concentration": +0.35,   # mean top3_buyer_share
    "headcount_trend": -0.40, # (emp last-6m mean - first-6m mean) / first-6m mean
    "days_near_zero": +0.50,  # mean days-near-zero per month
    "self_transfer": +0.45,   # self-transfer share of inflows (round-tripping)
}

STATES = {  # gst state code -> (abbr, cities, weight)
    "27": ("MH", ["Mumbai", "Pune", "Nagpur", "Nashik"], 0.26),
    "07": ("DL", ["Delhi", "New Delhi"], 0.14),
    "29": ("KA", ["Bengaluru", "Mysuru", "Hubballi"], 0.16),
    "33": ("TN", ["Chennai", "Coimbatore", "Madurai"], 0.14),
    "09": ("UP", ["Lucknow", "Kanpur", "Noida"], 0.12),
    "24": ("GJ", ["Ahmedabad", "Surat", "Rajkot"], 0.10),
    "36": ("TS", ["Hyderabad", "Warangal"], 0.08),
}

ARCHETYPES = {
    #                     weight  base inflow ₹/mo     upi share    b2b share    top3 share   emp     ticket ₹      season amp   benign cash-divergence
    "kirana_retail":      (0.30, (1.8e5, 12e5),  (0.55, 0.85), (0.05, 0.30), (0.20, 0.60), (1, 6),   (250, 700),    (0.04, 0.12), (0.00, 0.12)),
    "trader":             (0.22, (5.0e5, 40e5),  (0.08, 0.35), (0.60, 0.95), (0.45, 0.90), (2, 10),  (5000, 60000), (0.05, 0.15), (0.00, 0.04)),
    "light_manufacturer": (0.18, (8.0e5, 60e5),  (0.05, 0.25), (0.70, 0.97), (0.40, 0.85), (8, 40),  (8000, 80000), (0.05, 0.18), (0.00, 0.03)),
    "services":           (0.18, (3.0e5, 25e5),  (0.30, 0.70), (0.30, 0.80), (0.30, 0.75), (3, 20),  (1500, 15000), (0.03, 0.10), (0.00, 0.05)),
    "seasonal_agri":      (0.12, (2.0e5, 20e5),  (0.20, 0.60), (0.40, 0.85), (0.35, 0.80), (1, 8),   (1000, 12000), (0.35, 0.60), (0.00, 0.10)),
}
WAGE_RANGE = {
    "kirana_retail": (9000, 16000), "trader": (12000, 22000),
    "light_manufacturer": (11000, 20000), "services": (15000, 30000),
    "seasonal_agri": (8000, 14000),
}
SECTOR_WORDS = {
    "kirana_retail": ["Kirana & General Stores", "Provision Stores", "Super Market", "Retail Mart", "General Trading"],
    "trader": ["Trading Co.", "Traders", "Distributors", "Exim", "Agencies"],
    "light_manufacturer": ["Industries", "Engineering Works", "Fabricators", "Products", "Manufacturing Co."],
    "services": ["Services", "Solutions", "Consultants", "Logistics", "Enterprises"],
    "seasonal_agri": ["Agro Traders", "Agro Industries", "Cold Storage", "Commodities", "Agri Enterprises"],
}

MONTHLY_COLS = [
    "msme_id", "month", "bank_inflow_inr", "bank_outflow_inr", "eod_balance_avg_inr",
    "eod_balance_min_inr", "days_near_zero", "upi_txn_count", "upi_inflow_share",
    "bounce_count", "emi_debit_inr", "self_transfer_inr", "gst_turnover_declared_inr",
    "gst_filed_on_time", "gst_filing_delay_days", "gst_nil_return", "b2b_share",
    "top3_buyer_share", "employees_epfo", "wage_bill_inr",
]
PROFILE_COLS = [
    "msme_id", "name", "legal_name", "entity_type", "sector", "city", "state_code",
    "pan", "gstin", "cin", "promoter_name", "promoter_pan", "promoter_din", "udyam",
    "incorporated_on", "requested_amount_inr", "default_12m", "is_persona",
]

rng = np.random.default_rng(SEED)
random.seed(SEED)
Faker.seed(SEED)
fake = Faker("en_IN")
NS = uuid.UUID("d51e5f1e-9d4a-4b6f-9c1a-000000000042")  # deterministic uuid5 namespace

_used_pans: set[str] = set()


# ----------------------------------------------------------------------- id generators
def make_pan(entity_type: str) -> str:
    """Format-valid PAN: 5 letters (4th = holder type), 4 digits, 1 letter. No checksum."""
    fourth = "P" if entity_type == "proprietorship" else "C"
    while True:
        pan = (
            "".join(random.choices(string.ascii_uppercase, k=3))
            + fourth
            + random.choice(string.ascii_uppercase)
            + f"{random.randint(0, 9999):04d}"
            + random.choice(string.ascii_uppercase)
        )
        if pan not in _used_pans:
            _used_pans.add(pan)
            return pan


def make_gstin(state_code: str, pan: str) -> str:
    """GSTIN chars 3-12 embed the PAN. Checksum char NOT enforced (structure only)."""
    return f"{state_code}{pan}{random.choice('123')}Z{random.choice(string.ascii_uppercase + string.digits)}"


def make_cin(state_abbr: str, year: int) -> str:
    return f"U{random.randint(10000, 79999)}{state_abbr}{year}PTC{random.randint(100000, 999999):06d}"


def make_udyam(state_abbr: str) -> str:
    return f"UDYAM-{state_abbr}-{random.randint(0, 26):02d}-{random.randint(1, 9999999):07d}"


def make_din() -> str:
    return f"{random.randint(1000000, 9999999):08d}"


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


# ------------------------------------------------------------------------- buyer pool
def build_buyer_pool(n=600):
    suffixes = ["Textiles", "Traders", "Enterprises", "Agro", "Industries", "Distributors",
                "Marketing", "Exim", "& Sons", "Steels", "Polymers", "Foods", "Electricals"]
    pool = []
    for _ in range(n):
        surname = fake.last_name().split()[-1]
        name = f"{surname} {random.choice(suffixes)}"
        state = random.choice(list(STATES.keys()))
        pan = make_pan("pvt_ltd")
        pool.append({"gstin": make_gstin(state, pan), "name": name})
    # fixed distressed counterparty for the Suresh demo (Track B seeds this GSTIN)
    pool.append({"gstin": "27AABCT5678Q1Z9", "name": "Trident Textiles"})
    return pool


# -------------------------------------------------------------------- population firms
def draw_profile(i: int):
    arch = rng.choice(list(ARCHETYPES.keys()), p=[a[0] for a in ARCHETYPES.values()])
    entity_type = "pvt_ltd" if rng.random() < 0.25 else "proprietorship"
    state_code = rng.choice(list(STATES.keys()), p=[s[2] for s in STATES.values()])
    abbr, cities, _ = STATES[state_code]
    city = random.choice(cities)
    promoter = fake.name()
    surname = promoter.split()[-1]
    biz = f"{surname} {random.choice(SECTOR_WORDS[arch])}"
    pan = make_pan(entity_type)
    inc_year = random.randint(2005, 2023)
    cin = make_cin(abbr, inc_year) if entity_type == "pvt_ltd" else None
    return {
        "msme_id": f"MSME{i:05d}",
        "name": biz,
        "legal_name": biz + (" Pvt Ltd" if entity_type == "pvt_ltd" and "Pvt" not in biz else "") if entity_type == "pvt_ltd" else promoter,
        "entity_type": entity_type,
        "sector": arch,
        "city": city,
        "state_code": state_code,
        "pan": pan,
        "gstin": make_gstin(state_code, pan),
        "cin": cin,
        "promoter_name": promoter,
        "promoter_pan": pan if entity_type == "proprietorship" else make_pan("proprietorship"),
        "promoter_din": make_din() if entity_type == "pvt_ltd" else None,
        "udyam": make_udyam(abbr),
        "incorporated_on": f"{inc_year}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
        "requested_amount_inr": int(rng.choice([5, 7.5, 10, 15, 20, 25, 30, 50]) * 1e5),
        "is_persona": 0,
    }


def gen_firm_monthlies(arch: str, q: float):
    """24 months of monthly rows for one population firm. q = latent quality N(0,1)."""
    _, base_rng, upi_r, b2b_r, top3_r, emp_r, ticket_r, amp_r, cash_r = ARCHETYPES[arch]

    base = np.exp(rng.uniform(np.log(base_rng[0]), np.log(base_rng[1])))
    trend = np.clip(0.004 + 0.007 * q + rng.normal(0, 0.006), -0.045, 0.04)
    amp = rng.uniform(*amp_r)
    phase = rng.uniform(0, 12)
    vol = rng.uniform(0.07, 0.18)
    t = np.arange(N_M)

    season = 1 + amp * np.sin(2 * np.pi * (t + phase) / 12)
    inflow = base * (1 + trend) ** t * season * np.exp(rng.normal(0, vol, N_M))

    margin = np.clip(0.05 + 0.03 * q + rng.normal(0, 0.02), -0.06, 0.16)
    outflow = inflow * (1 - margin) * np.exp(rng.normal(0, 0.05, N_M))

    buffer_ratio = np.exp(-1.25 + 0.38 * q + rng.normal(0, 0.30))       # ~0.29 median
    avg_bal = buffer_ratio * inflow * np.exp(rng.normal(0, 0.22, N_M))
    min_frac = rng.uniform(0.12, 0.5)
    min_bal = avg_bal * min_frac * np.exp(rng.normal(0, 0.2, N_M))

    dnz_lambda = np.clip(5.5 * np.exp(-3.2 * buffer_ratio) - 1.2, 0, 12)
    dnz = np.minimum(rng.poisson(dnz_lambda, N_M), 26)

    upi_share = np.clip(rng.uniform(*upi_r) + rng.normal(0, 0.04, N_M), 0.01, 0.98)
    ticket = rng.uniform(*ticket_r)
    upi_txn = np.maximum((inflow * upi_share / ticket).round(), 0)

    bounce_lambda = np.clip(0.05 * np.exp(-1.1 * q + rng.normal(0, 0.55)), 0, 1.6)
    bounce = rng.poisson(bounce_lambda, N_M)

    emi = int(rng.uniform(0.02, 0.12) * base) if rng.random() < 0.55 else 0

    self_share = np.clip(rng.beta(1.2, 22) + np.maximum(0, -q) * 0.04 * rng.random(), 0, 0.35)
    self_transfer = self_share * inflow * np.exp(rng.normal(0, 0.25, N_M))

    # GST declared vs banked: fraud inflation for weak firms + benign cash divergence
    inflate_p = sigmoid(-1.8 - 1.3 * q)
    log_ratio_mu = rng.normal(-0.02, 0.05) + rng.uniform(*cash_r)
    if rng.random() < inflate_p:
        log_ratio_mu += rng.uniform(0.14, 0.42)   # inflated turnover (Suresh pattern)
    gst_declared = inflow * np.exp(log_ratio_mu + rng.normal(0, 0.06, N_M))

    punctual_p = np.clip(sigmoid(2.1 + 1.1 * q + rng.normal(0, 0.7)), 0.35, 0.995)
    on_time = (rng.random(N_M) < punctual_p).astype(int)
    delay = np.where(on_time == 1, 0, rng.integers(3, 46, N_M))
    nil_p = 0.002 + (0.025 if q < -1.0 else 0.0)
    nil = (rng.random(N_M) < nil_p).astype(int)
    gst_declared = np.where(nil == 1, 0.0, gst_declared)

    b2b = np.clip(rng.uniform(*b2b_r) + rng.normal(0, 0.02, N_M), 0.0, 1.0)
    top3_base = np.clip(rng.uniform(*top3_r) - 0.05 * q + rng.normal(0, 0.03), 0.10, 0.95)

    emp0 = rng.integers(emp_r[0], emp_r[1] + 1)
    emp_trend = np.clip(0.002 + 0.005 * q + rng.normal(0, 0.004), -0.05, 0.05)
    emp = np.maximum((emp0 * (1 + emp_trend) ** t + rng.normal(0, 0.3, N_M)).round(), 0).astype(int)
    wage = rng.uniform(*WAGE_RANGE[arch])
    wage_bill = emp * wage * np.exp(rng.normal(0, 0.05, N_M))

    return {
        "bank_inflow_inr": inflow.round(0), "bank_outflow_inr": outflow.round(0),
        "eod_balance_avg_inr": avg_bal.round(0), "eod_balance_min_inr": min_bal.round(0),
        "days_near_zero": dnz.astype(int), "upi_txn_count": upi_txn.astype(int),
        "upi_inflow_share": upi_share.round(3), "bounce_count": bounce.astype(int),
        "emi_debit_inr": np.full(N_M, emi, dtype=float), "self_transfer_inr": self_transfer.round(0),
        "gst_turnover_declared_inr": gst_declared.round(0), "gst_filed_on_time": on_time,
        "gst_filing_delay_days": delay.astype(int), "gst_nil_return": nil,
        "b2b_share": b2b.round(3), "top3_buyer_share": np.full(N_M, top3_base),  # refined by counterparties
        "employees_epfo": emp, "wage_bill_inr": wage_bill.round(0),
    }


# ------------------------------------------------------------------ persona monthlies
def persona_ramesh():
    """RAMESH001: ~8.1L/mo avg, +1.5%/mo, UPI 0.75, 23/24 GST on time, GST≈bank, healthy."""
    t = np.arange(N_M)
    r = np.random.default_rng(SEED + 1)
    inflow = 810000 * 1.015 ** (t - 11.5) * np.exp(r.normal(0, 0.12, N_M))
    outflow = inflow * 0.96 * np.exp(r.normal(0, 0.03, N_M))
    # healthy but human: a real kirana keeps a lean float (~0.25-0.30x monthly outflow),
    # not a corporate treasury — keeps him a strong A without gaming the top of the band
    avg_bal = np.linspace(100000, 145000, N_M) * np.exp(r.normal(0, 0.22, N_M))
    on_time = np.ones(N_M, dtype=int)
    delay = np.zeros(N_M, dtype=int)
    on_time[7] = 0            # 2025-02: the single late filing -> 23/24
    delay[7] = 11
    upi = np.clip(0.75 + r.normal(0, 0.015, N_M), 0, 1)
    return {
        "bank_inflow_inr": inflow.round(0), "bank_outflow_inr": outflow.round(0),
        "eod_balance_avg_inr": avg_bal.round(0),
        "eod_balance_min_inr": (avg_bal * 0.32 * np.exp(r.normal(0, 0.08, N_M))).round(0),
        "days_near_zero": np.zeros(N_M, dtype=int),
        "upi_txn_count": (inflow * upi / 420).round().astype(int),
        "upi_inflow_share": upi.round(3), "bounce_count": np.zeros(N_M, dtype=int),
        "emi_debit_inr": np.zeros(N_M), "self_transfer_inr": (inflow * 0.01).round(0),
        "gst_turnover_declared_inr": (inflow * r.uniform(0.97, 1.04, N_M)).round(0),
        "gst_filed_on_time": on_time, "gst_filing_delay_days": delay,
        "gst_nil_return": np.zeros(N_M, dtype=int),
        "b2b_share": np.clip(0.18 + r.normal(0, 0.015, N_M), 0, 1).round(3),
        "top3_buyer_share": np.full(N_M, 0.55), "employees_epfo": np.full(N_M, 4, dtype=int),
        "wage_bill_inr": (4 * 15000 * np.exp(r.normal(0, 0.03, N_M))).round(0),
    }


def persona_suresh():
    """SURESH002: -20% inflow over last 6m, 3 bounces last quarter, GST ~1.4x bank,
    2 late filings + 1 nil return, self-transfer round-tripping, top3 0.78."""
    t = np.arange(N_M)
    r = np.random.default_rng(SEED + 2)
    inflow = 1150000 * np.exp(r.normal(0, 0.03, N_M))
    decline = 0.9563 ** np.maximum(t - 18, 0)        # -20% from 2026-01 to 2026-06
    inflow = inflow * decline
    outflow = inflow * np.where(t < 18, 0.97, 1.03) * np.exp(r.normal(0, 0.03, N_M))
    avg_bal = np.linspace(190000, 72000, N_M) * np.exp(r.normal(0, 0.10, N_M))
    bounce = np.zeros(N_M, dtype=int)
    bounce[10] = 1                       # one early stress marker
    bounce[[21, 22, 23]] = 1             # 3 bounces in the last quarter
    on_time = np.ones(N_M, dtype=int)
    delay = np.zeros(N_M, dtype=int)
    on_time[[19, 22]] = 0                # filed late twice
    delay[19], delay[22] = 28, 34
    nil = np.zeros(N_M, dtype=int)
    nil[21] = 1                          # one nil return
    gst = inflow * 1.42 * np.exp(r.normal(0, 0.03, N_M))   # declared ~40% ABOVE bank
    gst = np.where(nil == 1, 0.0, gst)
    dnz = np.concatenate([np.zeros(16), np.array([0, 1, 1, 2, 2, 3, 4, 5])]).astype(int)
    emp = np.where(t < 20, 3, 2)
    return {
        "bank_inflow_inr": inflow.round(0), "bank_outflow_inr": outflow.round(0),
        "eod_balance_avg_inr": avg_bal.round(0),
        "eod_balance_min_inr": (avg_bal * np.linspace(0.35, 0.07, N_M)).round(0),
        "days_near_zero": dnz,
        "upi_txn_count": (inflow * 0.22 / 18000).round().astype(int),
        "upi_inflow_share": np.clip(0.22 + r.normal(0, 0.02, N_M), 0, 1).round(3),
        "bounce_count": bounce, "emi_debit_inr": np.full(N_M, 65000.0),
        "self_transfer_inr": (inflow * 0.18 * np.exp(r.normal(0, 0.1, N_M))).round(0),
        "gst_turnover_declared_inr": gst.round(0),
        "gst_filed_on_time": on_time, "gst_filing_delay_days": delay, "gst_nil_return": nil,
        "b2b_share": np.clip(0.85 + r.normal(0, 0.01, N_M), 0, 1).round(3),
        "top3_buyer_share": np.full(N_M, 0.78),
        "employees_epfo": emp.astype(int),
        "wage_bill_inr": (emp * 14000 * np.exp(r.normal(0, 0.03, N_M))).round(0),
    }


def persona_phoenix():
    """PHOENIX003 (Nexon Trading Pvt Ltd): SHORT HISTORY — only 14 months (2025-05..2026-06).
    Earlier months are NOT emitted (no zero/NaN padding rows); downstream feature code must
    treat missing months as 'not yet active'. Documented in DATA.md. Clean thin financials."""
    n = 14
    t = np.arange(n)
    r = np.random.default_rng(SEED + 3)
    # THIN, not pristine: modest growth, volatile young-firm inflows, lean float running
    # close to zero — clean compliance (GST 14/14, zero bounces, GST≈bank) so the model
    # says "maybe" (B/C) and the risk genuinely lives in the entity graph (Track B).
    inflow = 390000 * 1.004 ** t * np.exp(r.normal(0, 0.16, n))
    outflow = inflow * 0.975 * np.exp(r.normal(0, 0.05, n))
    avg_bal = 0.085 * inflow * np.exp(r.normal(0, 0.20, n))
    dnz = np.zeros(n, dtype=int)
    dnz[[2, 5, 7, 10, 12]] = [1, 2, 1, 3, 2]   # near-zero days: lean, not delinquent
    return {
        "bank_inflow_inr": inflow.round(0), "bank_outflow_inr": outflow.round(0),
        "eod_balance_avg_inr": avg_bal.round(0),
        "eod_balance_min_inr": (avg_bal * 0.18).round(0),
        "days_near_zero": dnz,
        "upi_txn_count": (inflow * 0.45 / 9000).round().astype(int),
        "upi_inflow_share": np.clip(0.45 + r.normal(0, 0.02, n), 0, 1).round(3),
        "bounce_count": np.zeros(n, dtype=int), "emi_debit_inr": np.zeros(n),
        "self_transfer_inr": (inflow * 0.015).round(0),
        "gst_turnover_declared_inr": (inflow * r.uniform(0.98, 1.03, n)).round(0),
        "gst_filed_on_time": np.ones(n, dtype=int),
        "gst_filing_delay_days": np.zeros(n, dtype=int),
        "gst_nil_return": np.zeros(n, dtype=int),
        "b2b_share": np.clip(0.60 + r.normal(0, 0.02, n), 0, 1).round(3),
        "top3_buyer_share": np.full(n, 0.62), "employees_epfo": np.full(n, 3, dtype=int),
        "wage_bill_inr": (3 * 16000 * np.exp(r.normal(0, 0.03, n))).round(0),
    }


PERSONA_PROFILES = [
    {
        "msme_id": "RAMESH001", "name": "Ramesh Kirana & General Stores",
        "legal_name": "Ramesh Kumar", "entity_type": "proprietorship",
        "sector": "kirana_retail", "city": "Pune", "state_code": "27",
        "pan": "ABCPR3456K", "gstin": "27ABCPR3456K1Z5", "cin": None,
        "promoter_name": "Ramesh Kumar", "promoter_pan": "ABCPR3456K", "promoter_din": None,
        "udyam": "UDYAM-MH-26-0012345", "incorporated_on": "2016-04-11",
        "requested_amount_inr": 1500000, "default_12m": 0, "is_persona": 1,
    },
    {
        "msme_id": "SURESH002", "name": "Suresh Trading Co.",
        "legal_name": "Suresh Mehta", "entity_type": "proprietorship",
        "sector": "trader", "city": "Mumbai", "state_code": "27",
        "pan": "AKLPM8765D", "gstin": "27AKLPM8765D1Z3", "cin": None,
        "promoter_name": "Suresh Mehta", "promoter_pan": "AKLPM8765D", "promoter_din": None,
        "udyam": "UDYAM-MH-19-0045678", "incorporated_on": "2014-08-20",
        "requested_amount_inr": 1000000, "default_12m": 1, "is_persona": 1,
    },
    {
        "msme_id": "PHOENIX003", "name": "Nexon Trading Pvt Ltd",
        "legal_name": "Nexon Trading Private Limited", "entity_type": "pvt_ltd",
        "sector": "trader", "city": "Delhi", "state_code": "07",
        "pan": "AAECN1234F", "gstin": "07AAECN1234F1Z2", "cin": "U51909DL2025PTC412345",
        "promoter_name": "Vikram Malhotra", "promoter_pan": "AEXPM4521C",
        "promoter_din": "08234567", "udyam": "UDYAM-DL-25-0067890",
        "incorporated_on": "2025-05-02", "requested_amount_inr": 2000000,
        "default_12m": 0, "is_persona": 1,
    },
]

PERSONA_META = {
    "RAMESH001": {
        "blurb": ("The invisible-but-healthy borrower: growing kirana store, ~₹8L/mo bank "
                  "inflows (+1.5%/mo), UPI-heavy, 23/24 on-time GST, GST≈bank. No credit "
                  "history — but the cash flows say APPROVE."),
        "customer_vpa": "ramesh.kumar@okaxis",
    },
    "SURESH002": {
        "blurb": ("Clean-on-paper-but-risky: inflows down ~20% in 6 months, 3 bounces last "
                  "quarter, GST declared ~1.4x bank inflows, self-transfer round-tripping, "
                  "78% sales to top-3 buyers incl. a distressed counterparty."),
        "customer_vpa": "suresh.mehta@okhdfcbank",
    },
    "PHOENIX003": {
        "blurb": ("The phoenix borrower: 14-month-old company, clean thin financials — but the "
                  "entity graph links its promoter to a struck-off, wilful-defaulter shell. "
                  "Score says maybe; graph says REFER."),
        "customer_vpa": "accounts.nexon@icici",
    },
}


def consent_artefact(p: dict) -> dict:
    """ReBIT-style AA consent artefact (structure only, sample data)."""
    handle = str(uuid.uuid5(NS, p["msme_id"] + ":handle"))
    cid = str(uuid.uuid5(NS, p["msme_id"] + ":consent"))
    return {
        "ver": "2.0.0",
        "txnid": str(uuid.uuid5(NS, p["msme_id"] + ":txn")),
        "consentId": cid,
        "ConsentHandle": handle,
        "status": "ACTIVE",
        "createTimestamp": "2026-06-28T10:15:00.000Z",
        "ConsentDetail": {
            "consentStart": "2026-06-28T10:15:00.000Z",
            "consentExpiry": "2027-06-28T10:15:00.000Z",
            "consentMode": "STORE",
            "fetchType": "PERIODIC",
            "consentTypes": ["PROFILE", "SUMMARY", "TRANSACTIONS"],
            "fiTypes": ["DEPOSIT", "GSTR1_3B"],
            "DataConsumer": {"id": "FIU-SHROFF-IDBI", "type": "FIU"},
            "Customer": {"id": PERSONA_META[p["msme_id"]]["customer_vpa"]},
            "Purpose": {
                "code": "103",
                "refUri": "https://api.rebit.org.in/aa/purpose/103.xml",
                "text": "Aggregated statement for loan underwriting",
                "Category": {"type": "Personal Finance"},
            },
            "FIDataRange": {"from": "2024-07-01T00:00:00.000Z", "to": "2026-06-30T23:59:59.000Z"},
            "DataLife": {"unit": "MONTH", "value": 12},
            "Frequency": {"unit": "MONTH", "value": 1},
            "DataFilter": [],
        },
        "is_sample": True,
    }


# ---------------------------------------------------------------------- counterparties
def firm_counterparties(msme_id, months, top3_series, pool, fixed=None, rj=None):
    """Quarterly-stable top-5 buyers; monthly top3_buyer_share = sum of top-3 shares."""
    # NOTE: zlib.crc32, not hash() — Python's str hash is salted per process and
    # would silently break the fixed-seed determinism guarantee.
    rj = rj or np.random.default_rng(zlib.crc32(msme_id.encode()))
    if fixed is None:
        idx = rj.choice(len(pool), 5, replace=False)
        buyers = [pool[i] for i in idx]
        raw = np.sort(rj.dirichlet(np.ones(5) * 1.2))[::-1]
        c = float(np.clip(top3_series[0], 0.10, 0.95))
        rest = rj.uniform(0.04, min(0.18, max(0.05, 1 - c)))
        shares = np.concatenate([raw[:3] / raw[:3].sum() * c, raw[3:] / raw[3:].sum() * rest])
    else:
        buyers, shares = fixed
        shares = np.asarray(shares, dtype=float)
    rows, top3_out = [], np.empty(len(months))
    for mi, m in enumerate(months):
        qi = mi // 3
        rq = np.random.default_rng(zlib.crc32(f"{msme_id}:q{qi}".encode()))
        s = np.clip(shares * (1 + rq.normal(0, 0.015, 5)), 0.005, 0.97)
        top3_out[mi] = np.sort(s)[::-1][:3].sum()
        for b, sh in zip(buyers, s):
            rows.append((msme_id, m, b["gstin"], b["name"], round(float(sh), 4)))
    return rows, top3_out.round(3)


# --------------------------------------------------------------------------- label calc
def firm_signals(g: pd.DataFrame) -> dict:
    inflow = g["bank_inflow_inr"].to_numpy(dtype=float)
    n = len(inflow)
    h = min(6, max(2, n // 4))
    growth = np.log((inflow[-h:].mean() + 1) / (inflow[:h].mean() + 1))
    buffer = g["eod_balance_avg_inr"].mean() / (g["bank_outflow_inr"].mean() + 1)
    bounce = g["bounce_count"].sum() / n
    gst_ontime = g["gst_filed_on_time"].mean()
    declared = g["gst_turnover_declared_inr"].sum()
    div = abs(np.log((declared + 1) / (inflow.sum() + 1)))
    conc = g["top3_buyer_share"].mean()
    emp = g["employees_epfo"].to_numpy(dtype=float)
    head = (emp[-h:].mean() - emp[:h].mean()) / (emp[:h].mean() + 0.5)
    dnz = g["days_near_zero"].mean()
    selfsh = g["self_transfer_inr"].sum() / (inflow.sum() + 1)
    return dict(inflow_growth=growth, buffer=buffer, bounce_rate=bounce, gst_ontime=gst_ontime,
                divergence=div, concentration=conc, headcount_trend=head,
                days_near_zero=dnz, self_transfer=selfsh)


def auc_score(y: np.ndarray, s: np.ndarray) -> float:
    order = np.argsort(s)
    ranks = np.empty(len(s), dtype=float)
    ranks[order] = np.arange(1, len(s) + 1)
    # midranks for ties
    df = pd.DataFrame({"s": s, "r": ranks})
    ranks = df.groupby("s")["r"].transform("mean").to_numpy()
    n1 = y.sum()
    n0 = len(y) - n1
    return float((ranks[y == 1].sum() - n1 * (n1 + 1) / 2) / (n0 * n1))


def numpy_logit_auc(X: np.ndarray, y: np.ndarray, seed=SEED) -> float:
    """Tiny logistic regression (GD) on firm-level signals, 70/30 split -> test AUC.
    This estimates the ACHIEVABLE model AUC on this data (sanity: 0.85-0.92)."""
    r = np.random.default_rng(seed)
    mu, sd = X.mean(0), X.std(0) + 1e-9
    Xs = np.hstack([(X - mu) / sd, np.ones((len(X), 1))])
    idx = r.permutation(len(y))
    cut = int(0.7 * len(y))
    tr, te = idx[:cut], idx[cut:]
    w = np.zeros(Xs.shape[1])
    for _ in range(3000):
        p = sigmoid(Xs[tr] @ w)
        w -= 0.5 * Xs[tr].T @ (p - y[tr]) / len(tr)
    return auc_score(y[te], sigmoid(Xs[te] @ w))


# --------------------------------------------------------------------------------- main
def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    pool = build_buyer_pool()

    profiles, monthly_frames, cp_rows = [], [], []

    # -- population
    qs = rng.normal(0, 1, N_POP)
    for i in range(N_POP):
        prof = draw_profile(i)
        m = gen_firm_monthlies(prof["sector"], qs[i])
        rows, top3 = firm_counterparties(prof["msme_id"], MONTH_STRS, m["top3_buyer_share"], pool)
        m["top3_buyer_share"] = top3
        cp_rows.extend(rows)
        dfm = pd.DataFrame(m)
        dfm.insert(0, "month", MONTH_STRS)
        dfm.insert(0, "msme_id", prof["msme_id"])
        monthly_frames.append(dfm)
        profiles.append(prof)

    # -- personas (fixed stories; EXCLUDED from training via is_persona=1)
    persona_monthlies = {
        "RAMESH001": (persona_ramesh(), MONTH_STRS),
        "SURESH002": (persona_suresh(), MONTH_STRS),
        "PHOENIX003": (persona_phoenix(), MONTH_STRS[-14:]),   # short history: 2025-05..2026-06
    }
    persona_cp_fixed = {
        "RAMESH001": None,   # generic pool buyers @ top3=0.55
        "SURESH002": (
            [{"gstin": "27AABCT5678Q1Z9", "name": "Trident Textiles"},
             {"gstin": pool[10]["gstin"], "name": pool[10]["name"]},
             {"gstin": pool[45]["gstin"], "name": pool[45]["name"]},
             {"gstin": pool[99]["gstin"], "name": pool[99]["name"]},
             {"gstin": pool[150]["gstin"], "name": pool[150]["name"]}],
            [0.45, 0.20, 0.13, 0.08, 0.05],                    # top3 = 0.78
        ),
        "PHOENIX003": None,
    }
    for p in PERSONA_PROFILES:
        mid = p["msme_id"]
        m, months = persona_monthlies[mid]
        rows, top3 = firm_counterparties(mid, months, m["top3_buyer_share"], pool,
                                         fixed=persona_cp_fixed[mid])
        if mid == "RAMESH001":
            m["top3_buyer_share"] = top3           # keep table & column consistent
        elif mid == "SURESH002":
            m["top3_buyer_share"] = top3           # ≈0.78 from fixed shares
        cp_rows.extend(rows)
        dfm = pd.DataFrame(m)
        dfm.insert(0, "month", months)
        dfm.insert(0, "msme_id", mid)
        monthly_frames.append(dfm)
        profiles.append(dict(p))

    monthly = pd.concat(monthly_frames, ignore_index=True)[MONTHLY_COLS]
    msmes = pd.DataFrame(profiles)

    # -- label: latent health index -> logistic -> Bernoulli (population only)
    sig_rows = []
    for mid, g in monthly.groupby("msme_id", sort=False):
        s = firm_signals(g)
        s["msme_id"] = mid
        sig_rows.append(s)
    sig = pd.DataFrame(sig_rows).set_index("msme_id")
    pop_ids = msmes.loc[msmes["is_persona"] == 0, "msme_id"]
    S = sig.loc[pop_ids]
    Z = (S - S.mean()) / (S.std() + 1e-9)
    risk = sum(W[k] * Z[k] for k in W)
    risk_z = ((risk - risk.mean()) / risk.std()).to_numpy()
    noise = rng.normal(0, LABEL_NOISE_SD, len(risk_z))
    lo, hi = -12.0, 6.0
    for _ in range(60):                                   # bisect intercept -> prevalence 10%
        c = (lo + hi) / 2
        if sigmoid(LABEL_SLOPE * risk_z + noise + c).mean() > TARGET_PREVALENCE:
            hi = c
        else:
            lo = c
    p_default = sigmoid(LABEL_SLOPE * risk_z + noise + c)
    y = (rng.random(len(p_default)) < p_default).astype(int)
    label_map = dict(zip(pop_ids, y))
    msmes["default_12m"] = msmes.apply(
        lambda r: r.get("default_12m") if r["is_persona"] == 1 else label_map[r["msme_id"]], axis=1
    ).astype(int)
    msmes = msmes[PROFILE_COLS]

    counterparties = pd.DataFrame(
        cp_rows, columns=["msme_id", "month", "counterparty_gstin", "counterparty_name", "share"]
    )

    # -- personas.json (API blurbs + ReBIT consent artefacts)
    personas_json = []
    for p in PERSONA_PROFILES:
        meta = PERSONA_META[p["msme_id"]]
        personas_json.append({
            "id": p["msme_id"], "name": p["promoter_name"], "business": p["name"],
            "city": p["city"], "segment": p["sector"],
            "requested_amount_inr": p["requested_amount_inr"], "blurb": meta["blurb"],
            "profile": {k: p[k] for k in PROFILE_COLS if k != "msme_id"} | {"msme_id": p["msme_id"]},
            "consent_artefact": consent_artefact(p),
            "history_months": 14 if p["msme_id"] == "PHOENIX003" else 24,
        })

    # -- write outputs
    msmes.to_parquet(DATA_DIR / "msmes.parquet", index=False)
    monthly.to_parquet(DATA_DIR / "monthly.parquet", index=False)
    counterparties.to_parquet(DATA_DIR / "counterparties.parquet", index=False)
    (DATA_DIR / "personas.json").write_text(json.dumps(personas_json, indent=2))

    # ------------------------------------------------------------------- verification
    print("=" * 76)
    print("SHROFF datagen — verification (seed=42)")
    print("=" * 76)
    print(f"msmes.parquet          rows={len(msmes):>7,}  (population {N_POP:,} + 3 personas)")
    print(f"monthly.parquet        rows={len(monthly):>7,}  (= {N_POP}*24 + 24 + 24 + 14)")
    print(f"counterparties.parquet rows={len(counterparties):>7,}")
    prev = msmes.loc[msmes["is_persona"] == 0, "default_12m"].mean()
    print(f"\nlabel prevalence (population, personas excluded): {prev:.4f}  (target ~0.10)")
    oracle = auc_score(y, LABEL_SLOPE * risk_z)
    print(f"oracle AUC (noiseless risk index vs sampled label): {oracle:.4f}")
    ach = numpy_logit_auc(S.to_numpy(dtype=float), y)
    print(f"achievable AUC (logreg on firm-level signals, 70/30 test): {ach:.4f}  (target 0.85-0.92)")

    print("\n--- persona checks ---")
    for mid in ["RAMESH001", "SURESH002", "PHOENIX003"]:
        g = monthly[monthly["msme_id"] == mid]
        prof = msmes[msmes["msme_id"] == mid].iloc[0]
        print(f"{mid}: {len(g)} monthly rows | PAN {prof['pan']} | GSTIN {prof['gstin']}"
              f" | PAN embedded in GSTIN[2:12]: {prof['gstin'][2:12] == prof['pan']}")

    su = monthly[monthly["msme_id"] == "SURESH002"].reset_index(drop=True)
    trend = su["bank_inflow_inr"].iloc[23] / su["bank_inflow_inr"].iloc[18] - 1
    nn = su[su["gst_nil_return"] == 0]
    ratio = (nn["gst_turnover_declared_inr"] / nn["bank_inflow_inr"]).mean()
    lastq_bounces = int(su["bounce_count"].iloc[21:24].sum())
    print(f"\nSURESH002  last-6mo inflow trend (2026-06 vs 2026-01): {trend:+.1%}  (target ~-20%)")
    print(f"SURESH002  GST-declared / bank-inflow (non-nil months): {ratio:.2f}x  (target ~1.4x)")
    print(f"SURESH002  bounces in last quarter: {lastq_bounces}  | nil returns: {int(su['gst_nil_return'].sum())}"
          f" | late filings: {int((su['gst_filed_on_time'] == 0).sum())}"
          f" | top3_buyer_share mean: {su['top3_buyer_share'].mean():.3f}")
    sc = counterparties[(counterparties["msme_id"] == "SURESH002")
                        & (counterparties["month"] == "2026-06")]
    print("SURESH002  2026-06 counterparties:",
          ", ".join(f"{r.counterparty_name}({r.counterparty_gstin})={r.share:.2f}"
                    for r in sc.itertuples()))

    ra = monthly[monthly["msme_id"] == "RAMESH001"]
    print(f"\nRAMESH001  GST filed on time: {int(ra['gst_filed_on_time'].sum())}/24  (target 23/24)"
          f" | mean inflow: ₹{ra['bank_inflow_inr'].mean()/1e5:.1f}L/mo"
          f" | UPI share: {ra['upi_inflow_share'].mean():.2f}"
          f" | GST/bank: {(ra['gst_turnover_declared_inr']/ra['bank_inflow_inr']).mean():.2f}"
          f" | bounces: {int(ra['bounce_count'].sum())}")

    ph = monthly[monthly["msme_id"] == "PHOENIX003"]
    print(f"\nPHOENIX003 history months: {len(ph)} ({ph['month'].min()}..{ph['month'].max()})"
          f" — SHORT HISTORY, no padded rows (see DATA.md)"
          f" | GST on time: {int(ph['gst_filed_on_time'].sum())}/{len(ph)}"
          f" | bounces: {int(ph['bounce_count'].sum())}")

    print(f"\nmonthly columns == contract schema: {list(monthly.columns) == MONTHLY_COLS}")
    pj = json.loads((DATA_DIR / "personas.json").read_text())
    ca = pj[0]["consent_artefact"]["ConsentDetail"]
    print(f"personas.json: {len(pj)} personas | consent purpose={pj[0]['consent_artefact']['ConsentDetail']['Purpose']['code']}"
          f" fetchType={ca['fetchType']} fiTypes={ca['fiTypes']} consentTypes={ca['consentTypes']}")
    print("\nwrote:", ", ".join(str(DATA_DIR / f) for f in
          ["msmes.parquet", "monthly.parquet", "counterparties.parquet", "personas.json"]))


if __name__ == "__main__":
    main()
