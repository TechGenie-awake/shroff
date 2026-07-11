"""Scorecard scaling + bands + decision constants — EXACTLY per CONTRACTS.md.

- score 660 at PD 5%, +72 points per halving of odds, clamped [300, 900]
- Bands: A >=750 · B 680-749 · C 600-679 · D 500-599 · E <500
"""
from __future__ import annotations

import math

SCORE_REF = 660.0
PD_REF = 0.05
PDO = 72.0  # points per doubling (halving of default odds)
ODDS_REF = (1.0 - PD_REF) / PD_REF  # 19:1 good:bad odds at 660
SCORE_MIN, SCORE_MAX = 300, 900

PD_FLOOR, PD_CEIL = 1e-4, 0.999

BANDS = [("A", 750), ("B", 680), ("C", 600), ("D", 500), ("E", -10**9)]
BAND_FACTOR = {"A": 0.65, "B": 0.50, "C": 0.30, "D": 0.15, "E": 0.0}
BAND_TENURE = {"A": 36, "B": 24, "C": 12, "D": 12, "E": 0}  # A/B 24-36 · C 12-18 · D 12 · E —
BAND_ORDER = ["A", "B", "C", "D", "E"]


def pd_to_score(pd_12m: float) -> int:
    p = min(max(float(pd_12m), PD_FLOOR), PD_CEIL)
    odds = (1.0 - p) / p
    score = SCORE_REF + PDO * math.log2(odds / ODDS_REF)
    return int(round(min(max(score, SCORE_MIN), SCORE_MAX)))


def band_for_score(score: float) -> str:
    for band, floor in BANDS:
        if score >= floor:
            return band
    return "E"


def worse_band(a: str, b: str) -> str:
    """Return the riskier of two bands (used for overlay caps — only ever worsens)."""
    return a if BAND_ORDER.index(a) >= BAND_ORDER.index(b) else b
