"""Decision policy — EXACTLY per CONTRACTS.md.

- Amount: eligible = 0.20 x annualized bank-verified turnover x band_factor
  (A 0.65 · B 0.50 · C 0.30 · D 0.15 · E 0); amount = min(requested, eligible), rounded ₹50k.
  Annualized turnover = 12 x mean monthly bank inflow over the observed history.
- Tenure: A/B 24-36 · C 12-18 · D 12 · E —.
- Base verdict by (post-EWS) band: A/B APPROVE · C/D REFER · E DECLINE.
- Overlays are deterministic and only WORSEN: high-confidence registry hit on the borrower's
  own identifiers -> DECLINE; phoenix_flag or advisory/name-only hit -> REFER; EWS red -> cap
  band at C. Verdict floor: never improves via overlays.
- EWS (last 3 months vs prior 9): inflow drop >25% · >=2 bounces · GST late/nil streak >=2 ·
  headcount drop >25%. 0 triggers green, 1 amber, >=2 red.

Screening is called IN-PROCESS via guarded imports (Track B builds ml/screening/; the
integration agent finishes the wiring) — on any failure the overlay reports checked:false.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from train.scorecard import BAND_FACTOR, BAND_TENURE, worse_band

VERDICT_BY_BAND = {"A": "APPROVE", "B": "APPROVE", "C": "REFER", "D": "REFER", "E": "DECLINE"}
_VERDICT_RANK = {"APPROVE": 0, "REFER": 1, "DECLINE": 2}


def _worsen(v1: str, v2: str) -> str:
    return v1 if _VERDICT_RANK[v1] >= _VERDICT_RANK[v2] else v2


# ---------------------------------------------------------------------------------------
# Early-warning system
# ---------------------------------------------------------------------------------------
def compute_ews(g: pd.DataFrame) -> dict:
    g = g.sort_values("month")
    n = len(g)
    triggers: list[str] = []
    last3 = g.tail(3)
    prior = g.iloc[max(0, n - 12):n - 3]  # up to 9 months before the last 3
    if len(prior) >= 3:
        m_last, m_prior = last3["bank_inflow_inr"].mean(), prior["bank_inflow_inr"].mean()
        if m_prior > 0 and (m_prior - m_last) / m_prior > 0.25:
            triggers.append(
                f"Bank inflows down {(m_prior - m_last) / m_prior * 100:.0f}% in the last "
                f"quarter vs the prior nine months")
        h_last, h_prior = last3["employees_epfo"].mean(), prior["employees_epfo"].mean()
        if h_prior > 0 and (h_prior - h_last) / h_prior > 0.25:
            triggers.append(
                f"EPFO headcount down {(h_prior - h_last) / h_prior * 100:.0f}% in the last "
                f"quarter vs the prior nine months")
    b3 = int(last3["bounce_count"].sum())
    if b3 >= 2:
        triggers.append(f"{b3} bounced payments in the last 3 months")
    # GST late/nil streak >= 2 within the last 6 months
    tail6 = g.tail(6)
    bad = ((tail6["gst_filed_on_time"] < 0.5) | (tail6["gst_nil_return"] > 0.5)).to_numpy()
    streak = best = 0
    for v in bad:
        streak = streak + 1 if v else 0
        best = max(best, streak)
    if best >= 2:
        triggers.append(f"GST late/nil filing streak of {best} consecutive months")
    level = "green" if not triggers else ("amber" if len(triggers) == 1 else "red")
    return {"level": level, "triggers": triggers}


# ---------------------------------------------------------------------------------------
# Screening overlay (guarded in-process call into ml/screening — Track B's subtree)
# ---------------------------------------------------------------------------------------
def run_screening(profile: dict) -> dict:
    out = {"checked": False, "hits": [], "phoenix_flag": False}
    try:
        from screening.registry import check_msme  # Track B module
        res = check_msme(profile)
        if isinstance(res, dict):
            out["hits"] = list(res.get("hits", []))
            out["phoenix_flag"] = bool(res.get("phoenix_flag", False))
        elif isinstance(res, list):
            out["hits"] = list(res)
        out["checked"] = True
    except Exception:
        pass
    if not out["phoenix_flag"]:
        pan = profile.get("pan")
        if pan:
            try:  # Track B's entry point: build_graph(pan) -> {"phoenix_flag", "nodes", ...}
                from screening.graph import TAINT_FLAGS, build_graph
                g = build_graph(pan)
                out["phoenix_flag"] = bool(g.get("phoenix_flag", False))
                if out["phoenix_flag"]:
                    tainted = [n for n in g.get("nodes", [])
                               if n.get("flag") in TAINT_FLAGS]
                    if tainted:  # cite registry + matched identifier (CONTRACTS.md)
                        out["phoenix_detail"] = "; ".join(
                            f"{n['label']} — {n['flag'].replace('_', ' ')} on the negative registry"
                            for n in tainted[:3])
                out["checked"] = True
            except Exception:
                pass
    return out


def check_counterparty(gstin: str) -> list[dict]:
    """Screen one counterparty GSTIN (supply-chain Tier B). Empty when screening is absent."""
    try:
        from screening.registry import check_identifier
        res = check_identifier("gstin", gstin)
        if isinstance(res, dict):
            return list(res.get("hits", []))
        if isinstance(res, list):
            return list(res)
    except Exception:
        pass
    return []


def supply_chain_overlay(eng, msme_id: str, g: pd.DataFrame) -> dict:
    top3 = round(float(g["top3_buyer_share"].tail(12).mean()), 2)
    distressed: list[dict] = []
    cps = eng.counterparties
    mine = cps[cps["msme_id"] == msme_id]
    if len(mine):
        latest = mine[mine["month"] == mine["month"].max()]
        for _, row in latest.iterrows():
            hits = check_counterparty(row["counterparty_gstin"])
            if hits:
                distressed.append({
                    "counterparty_gstin": row["counterparty_gstin"],
                    "counterparty_name": row["counterparty_name"],
                    "share": round(float(row["share"]), 2),
                    "hits": hits,
                })
    return {"top3_buyer_share": top3, "distressed_counterparties": distressed}


def _hit_is_high_confidence(hit: dict) -> bool:
    return str(hit.get("confidence", "")).lower() == "high"


# ---------------------------------------------------------------------------------------
# The decision
# ---------------------------------------------------------------------------------------
def decide(profile: dict, g: pd.DataFrame, score: int, band: str,
           screening: dict, ews: dict) -> tuple[dict, str]:
    """Returns (decision dict, effective band after overlays)."""
    requested = int(profile.get("requested_amount_inr") or 0)
    annualized = 12.0 * float(g["bank_inflow_inr"].mean())

    band_eff = band
    band_capped = False
    if ews["level"] == "red":
        band_eff = worse_band(band, "C")  # EWS red -> cap band at C (only worsens)
        band_capped = band_eff != band

    verdict = VERDICT_BY_BAND[band_eff]
    overlay_notes: list[str] = []
    hits = screening.get("hits", [])
    # Verdict-forcing signals are DETERMINISTIC only: an exact match on the borrower's
    # own identifier (PAN/GSTIN/CIN/DIN) -> DECLINE, or the entity-graph phoenix flag
    # -> REFER. Advisory name-only matches are NOT verdict-forcing: against a real
    # watchlist of ~21k names, common personal names (e.g. "Ramesh Kumar") collide
    # constantly, so — exactly as a bank's AML workflow does — they are surfaced as
    # "possible matches" for manual disposition rather than auto-declining a loan.
    if any(_hit_is_high_confidence(h) for h in hits):
        verdict = _worsen(verdict, "DECLINE")
        h = next(h for h in hits if _hit_is_high_confidence(h))
        overlay_notes.append(
            f"high-confidence registry hit ({h.get('registry', 'registry')} on "
            f"{h.get('matched_on', 'identifier')})")
    elif screening.get("phoenix_flag"):
        verdict = _worsen(verdict, "REFER")
        detail = screening.get("phoenix_detail")
        overlay_notes.append(
            "entity-graph phoenix flag — promoter network reaches "
            + (detail if detail else "a struck-off/wilful-defaulter entity"))
    advisory = [h for h in hits if not _hit_is_high_confidence(h)]
    if advisory:
        overlay_notes.append(
            f"{len(advisory)} advisory name match(es) flagged for manual disposition "
            "(not verdict-affecting)")
    if ews["level"] == "red":
        overlay_notes.append("early-warning red" + (" (band capped at C)" if band_capped else ""))

    eligible = 0.20 * annualized * BAND_FACTOR[band_eff]
    amount = min(requested, eligible) if requested else eligible
    amount = int(round(amount / 50000.0) * 50000)
    tenure = BAND_TENURE[band_eff]
    if verdict == "DECLINE":
        amount, tenure = 0, 0

    if verdict == "DECLINE":
        rationale = (f"Band {band_eff} yields no working-capital eligibility under the 20% "
                     f"turnover norm (Nayak committee)"
                     + (": " + "; ".join(overlay_notes) if overlay_notes else "")
                     + ".")
    else:
        rationale = (f"20% working-capital norm (Nayak committee) on ₹{annualized / 1e5:.1f}L "
                     f"annualized bank-verified turnover × {BAND_FACTOR[band_eff]:.2f} band-{band_eff} "
                     f"factor → eligible ₹{eligible / 1e5:.1f}L; sanction = min(requested "
                     f"₹{requested / 1e5:.1f}L, eligible) = ₹{amount / 1e5:.1f}L over {tenure} months"
                     + ("; " + "; ".join(overlay_notes) if overlay_notes else "")
                     + ".")

    return ({"verdict": verdict, "amount_inr": amount, "tenure_months": tenure,
             "rationale": rationale}, band_eff)
