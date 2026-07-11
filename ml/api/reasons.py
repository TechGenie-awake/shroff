"""TreeSHAP reason codes: per-applicant top contributors -> curated dictionary ->
human sentences filled with the ACTUAL feature values. 3-5 signed reasons per response.

SHAP is computed on the DECIDING sub-models (not a surrogate), in log-odds space, and each
sub-model's contributions are weighted by its logistic meta-combiner coefficient so the
ranking reflects the combined model. Sign convention matches the CONTRACTS example:
positive shap = pushes the score UP (good for the borrower).
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np
import pandas as pd
import shap

from features.build import FEATURE_NAMES, GROUP_FEATURES, GROUPS

# ---------------------------------------------------------------------------------------
# Curated reason-code dictionary — feature -> (code, sentence template with {value})
# Codes: CF (cash_flow) · GR (growth) · ST (stability) · CM (compliance)
# ---------------------------------------------------------------------------------------
REASON_CODES: dict[str, tuple[str, str]] = {
    # cash_flow
    "cf_inflow_avg_log": ("CF-01", "Bank inflows averaging {value} over the observed history"),
    "cf_inflow_amount_cov": ("CF-02", "Month-to-month inflow variability of {value} (coefficient of variation)"),
    "cf_inflow_count_cov": ("CF-03", "Transaction-count regularity at {value} variability across months"),
    "cf_net_flow_ratio": ("CF-04", "Operating surplus of {value} of inflows retained in the account"),
    "cf_balance_buffer": ("CF-05", "Average balance covers {value} of a typical month's outflows"),
    "cf_log_growth_avg_balance": ("CF-06", "Average bank balance {value} between first and last six months"),
    "cf_min_balance_ratio": ("CF-07", "Minimum monthly balance holds at {value} of monthly outflows"),
    "cf_min_balance_change": ("CF-08", "Minimum-balance cushion {value} over the observed period"),
    "cf_balance_volatility": ("CF-09", "Balance volatility of {value} (coefficient of variation)"),
    "cf_days_near_zero_avg": ("CF-10", "Account near zero {value} days per month on average"),
    "cf_days_near_zero_last3": ("CF-11", "{value} near-zero balance days per month in the last quarter"),
    "cf_emi_to_inflow": ("CF-12", "Existing EMI obligations consume {value} of bank inflows"),
    "cf_self_transfer_share": ("CF-13", "Self-transfers (own-account round-tripping) at {value} of inflows"),
    "cf_outflow_to_inflow": ("CF-14", "Outflows running at {value} of inflows"),
    # growth
    "gr_inflow_growth_log": ("GR-01", "Bank inflows {value} from the first six months to the last six"),
    "gr_inflow_mom_mean": ("GR-02", "Average month-over-month inflow growth of {value}"),
    "gr_inflow_trend": ("GR-03", "Whole-history inflow trend of {value} per month"),
    "gr_inflow_recent_ratio": ("GR-04", "Last-quarter inflows at {value} of the preceding months' level"),
    "gr_gst_growth_log": ("GR-05", "GST-declared turnover {value} first-half to second-half"),
    "gr_gst_trend": ("GR-06", "GST-declared turnover trend of {value} per month"),
    "gr_headcount_trend": ("GR-07", "EPFO headcount {value} over the observed period"),
    "gr_balance_recent_ratio": ("GR-08", "Recent average balance at {value} of the earlier level"),
    "gr_wage_bill_growth_log": ("GR-09", "Wage bill {value} first-half to second-half"),
    # stability
    "st_history_months": ("ST-01", "{value} of observed banking history"),
    "st_bounce_total": ("ST-02", "{value} bounced/returned payments in the observed history"),
    "st_bounce_last3": ("ST-03", "{value} bounced payments in the last quarter"),
    "st_bounce_rate": ("ST-04", "Bounce frequency of {value} per month"),
    "st_upi_share_mean": ("ST-05", "UPI/digital share of inflows at {value}"),
    "st_upi_txn_avg_log": ("ST-06", "Digital footprint of {value} UPI transactions per month"),
    "st_top3_buyer_share": ("ST-07", "Top-3 buyers account for {value} of sales (concentration)"),
    "st_top1_buyer_share": ("ST-08", "Largest buyer alone accounts for {value} of sales"),
    "st_b2b_share": ("ST-09", "B2B share of sales at {value}"),
    "st_counterparty_count": ("ST-10", "{value} distinct GSTR-1 counterparties per month"),
    "st_wage_to_inflow": ("ST-11", "Wage bill at {value} of bank inflows"),
    "st_headcount_avg": ("ST-12", "{value} EPFO-registered employees on average"),
    # compliance
    "cm_gst_ontime_share": ("CM-01", "GST returns filed on time in {value} of months"),
    "cm_gst_delay_days_avg": ("CM-02", "Average GST filing delay of {value}"),
    "cm_gst_nil_count": ("CM-03", "{value} nil GST return(s) filed"),
    "cm_gst_nil_streak": ("CM-04", "Longest consecutive nil-return streak of {value} month(s)"),
    "cm_gst_late_nil_last3": ("CM-05", "{value} late-or-nil GST month(s) within the last quarter"),
    "cm_gst_divergence_abs_log": ("CM-06", "GST-declared turnover diverges from bank inflows by {value}"),
    "cm_gst_declared_to_inflow": ("CM-07", "GST-declared turnover is {value} of bank-verified inflows"),
    "cm_gst_divergence_recent": ("CM-08", "GST-vs-bank divergence over the last six months at {value}"),
    "cm_gst_punctuality_trend": ("CM-09", "GST filing punctuality {value} over the period"),
    "cm_gst_turnover_avg_log": ("CM-10", "GST-declared turnover averaging {value} per month"),
}

GROUP_OF = {f: g for g in GROUPS for f in GROUP_FEATURES[g]}


# ---------------------------------------------------------------------------------------
# Value formatters — fill {value} with the ACTUAL quantity behind the feature
# ---------------------------------------------------------------------------------------
def _lakh(v: float) -> str:
    return f"₹{v / 1e5:.1f}L"


def _pct(v: float) -> str:
    return f"{v * 100:.0f}%"


def _grew(vlog: float) -> str:
    change = np.expm1(vlog)
    return f"grew {change * 100:.0f}%" if change >= 0 else f"fell {abs(change) * 100:.0f}%"


def format_value(feat: str, v: float) -> str:
    if feat == "cf_inflow_avg_log":
        return f"{_lakh(np.expm1(v))}/month"
    if feat == "cm_gst_turnover_avg_log":
        return f"{_lakh(np.expm1(v))}"
    if feat in ("cf_log_growth_avg_balance", "gr_inflow_growth_log", "gr_gst_growth_log",
                "gr_wage_bill_growth_log"):
        return _grew(v)
    if feat == "gr_headcount_trend":
        return "grew " + _pct(v) if v >= 0 else "shrank " + _pct(abs(v))
    if feat == "cm_gst_punctuality_trend":
        return ("improved " + _pct(v)) if v >= 0 else ("deteriorated " + _pct(abs(v)))
    if feat in ("gr_inflow_mom_mean", "gr_inflow_trend", "gr_gst_trend"):
        return f"{v * 100:+.1f}%"
    if feat in ("cf_net_flow_ratio", "cf_balance_buffer", "cf_min_balance_ratio",
                "cf_emi_to_inflow", "cf_self_transfer_share", "cf_outflow_to_inflow",
                "st_upi_share_mean", "st_top3_buyer_share", "st_top1_buyer_share",
                "st_b2b_share", "st_wage_to_inflow", "cm_gst_ontime_share"):
        return _pct(v)
    if feat == "cf_min_balance_change":
        return ("strengthened by " + _pct(v)) if v >= 0 else ("eroded by " + _pct(abs(v)))
    if feat in ("gr_inflow_recent_ratio", "gr_balance_recent_ratio"):
        return _pct(v)
    if feat in ("cf_inflow_amount_cov", "cf_inflow_count_cov", "cf_balance_volatility",
                "st_bounce_rate"):
        return f"{v:.2f}"
    if feat == "cm_gst_declared_to_inflow":
        return f"{v:.2f}×"
    if feat in ("cm_gst_divergence_abs_log", "cm_gst_divergence_recent"):
        return _pct(np.expm1(v))
    if feat == "st_history_months":
        return f"{v:.0f} months"
    if feat == "cm_gst_delay_days_avg":
        return f"{v:.1f} days"
    if feat == "st_upi_txn_avg_log":
        return f"{np.expm1(v):.0f}"
    if feat in ("st_bounce_total", "st_bounce_last3", "cm_gst_nil_count", "cm_gst_nil_streak",
                "cm_gst_late_nil_last3", "st_headcount_avg", "st_counterparty_count"):
        return f"{v:.0f}"
    if feat in ("cf_days_near_zero_avg", "cf_days_near_zero_last3"):
        return f"{v:.1f}"
    return f"{v:.2f}"


# ---------------------------------------------------------------------------------------
# TreeSHAP on the deciding sub-models, weighted by meta coefficients
# ---------------------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _explainers():
    from api.scoring import get_engine
    eng = get_engine()
    return {g: shap.TreeExplainer(eng.bundle["sub_models"][g]) for g in GROUPS}


def top_reasons(x: pd.DataFrame, n_max: int = 5, n_min: int = 3) -> list[dict]:
    from api.scoring import get_engine
    eng = get_engine()
    meta_coef = dict(zip(GROUPS, eng.bundle["meta"].coef_[0]))
    contribs: dict[str, float] = {}
    for g in GROUPS:
        cols = eng.bundle["group_features"][g]
        sv = _explainers()[g].shap_values(x[cols])
        sv = np.asarray(sv)
        if sv.ndim == 3:  # (n, features, classes)
            sv = sv[:, :, 1]
        for feat, v in zip(cols, sv[0]):
            # risk-direction log-odds contribution, weighted by the combiner
            contribs[feat] = float(meta_coef[g] * v)

    # display-only exclusion: the raw signed ratio duplicates CM-06's |divergence| story and
    # reads contradictory next to it ("1.01x" flagged while "1% divergence" praised)
    contribs.pop("cm_gst_declared_to_inflow", None)
    ranked = sorted(contribs.items(), key=lambda kv: abs(kv[1]), reverse=True)
    chosen = ranked[:n_max]
    # ensure both directions are represented when both exist (contract: "both directions")
    signs = {np.sign(v) for _, v in chosen if v != 0}
    if len(signs) < 2:
        for feat, v in ranked[n_max:]:
            if v != 0 and np.sign(v) not in signs:
                chosen[-1] = (feat, v)
                break
    chosen = chosen[:max(n_min, min(n_max, len(chosen)))]

    out = []
    for feat, risk_contrib in chosen:
        code, template = REASON_CODES[feat]
        val = format_value(feat, float(x[feat].iloc[0]))
        out.append({
            "code": code,
            "group": GROUP_OF[feat],
            "direction": "positive" if risk_contrib < 0 else "negative",
            "text": template.format(value=val),
            "value": val,
            "shap": round(-risk_contrib, 3),  # positive = pushes score up (contract example)
        })
    # keep ordering by |shap| after any direction swap
    out.sort(key=lambda r: abs(r["shap"]), reverse=True)
    return out
