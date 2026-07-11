"""SHROFF feature engine — ~45 features per MSME in 4 named groups.

Consumes the CONTRACTS monthly schema (ml/data/monthly.parquet) + counterparties table.
Handles short histories (PHOENIX003: 14 months) by computing every feature over the
available window and exposing `st_history_months` explicitly. Missing months are
pre-incorporation, NOT zero activity (see datagen/DATA.md).

Run:  cd ml && uv run python -m features.build
Emits: ml/data/features.parquet + ml/features/FEATURES.md
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import numpy as np
import pandas as pd

EPS = 1e-9
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # ml/
DATA = os.path.join(ROOT, "data")


# --------------------------------------------------------------------------------------
# Feature registry: name | group | direction (of the feature vs credit HEALTH) |
# monotone constraint wrt DEFAULT RISK output (+1 higher feature -> higher PD) | rationale
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class FeatureSpec:
    name: str
    group: str  # cash_flow | growth | stability | compliance
    direction: str  # 'higher_better' | 'higher_worse' | 'neutral'
    monotone: int  # -1 / 0 / +1 wrt P(default)
    rationale: str


FEATURES: list[FeatureSpec] = [
    # ---------------- cash_flow ----------------
    FeatureSpec("cf_inflow_avg_log", "cash_flow", "higher_better", -1,
                "log(1+mean monthly bank inflow): scale of bank-verified activity (HKMA/ASTRI core variable)."),
    FeatureSpec("cf_inflow_amount_cov", "cash_flow", "higher_worse", 1,
                "Coefficient of variation of monthly inflow amounts: irregular revenue = repayment risk."),
    FeatureSpec("cf_inflow_count_cov", "cash_flow", "higher_worse", 1,
                "CoV of monthly UPI transaction counts: irregular customer traffic (inflow-count regularity)."),
    FeatureSpec("cf_net_flow_ratio", "cash_flow", "higher_better", -1,
                "Mean (inflow-outflow)/inflow: operating surplus retained in the account."),
    FeatureSpec("cf_balance_buffer", "cash_flow", "higher_better", -1,
                "Mean EOD avg balance / mean monthly outflow: liquidity runway in months."),
    FeatureSpec("cf_log_growth_avg_balance", "cash_flow", "higher_better", -1,
                "log growth of average balance (last-6m vs first-6m): the #1 IV feature in AI-BAAM (IV=0.484)."),
    FeatureSpec("cf_min_balance_ratio", "cash_flow", "higher_better", -1,
                "Mean EOD minimum balance / mean outflow: intramonth cushion level."),
    FeatureSpec("cf_min_balance_change", "cash_flow", "higher_better", -1,
                "Change in min balance (last-6m minus first-6m, scaled by outflow): cushion trajectory."),
    FeatureSpec("cf_balance_volatility", "cash_flow", "higher_worse", 1,
                "CoV of EOD average balance: unstable treasury management."),
    FeatureSpec("cf_days_near_zero_avg", "cash_flow", "higher_worse", 1,
                "Mean days/month with balance near zero: balance-depletion stress (HKMA early-warning signal)."),
    FeatureSpec("cf_days_near_zero_last3", "cash_flow", "higher_worse", 1,
                "Days-near-zero in last 3 months: recent depletion stress."),
    FeatureSpec("cf_emi_to_inflow", "cash_flow", "higher_worse", 1,
                "Existing EMI debits / inflows: leverage stacking (FOIR analogue on cash flows)."),
    FeatureSpec("cf_self_transfer_share", "cash_flow", "higher_worse", 1,
                "Self-transfers / inflows: circular round-tripping that pads apparent turnover (fraud padding)."),
    FeatureSpec("cf_outflow_to_inflow", "cash_flow", "higher_worse", 1,
                "Outflows / inflows: burn ratio; >1 means the account is being drained."),
    # ---------------- growth ----------------
    FeatureSpec("gr_inflow_growth_log", "growth", "higher_better", -1,
                "log(mean inflow last-6m / first-6m): medium-term revenue trajectory."),
    FeatureSpec("gr_inflow_mom_mean", "growth", "higher_better", -1,
                "Mean month-over-month inflow growth (clipped): short-cycle momentum."),
    FeatureSpec("gr_inflow_trend", "growth", "higher_better", -1,
                "OLS slope of log inflow vs time: robust whole-history trend."),
    FeatureSpec("gr_inflow_recent_ratio", "growth", "higher_better", -1,
                "Mean inflow last-3m / prior months: early-warning collapse detector (both-directions head)."),
    FeatureSpec("gr_gst_growth_log", "growth", "higher_better", -1,
                "log growth of GST-declared turnover (last-6m vs first-6m): tax-verified growth."),
    FeatureSpec("gr_gst_trend", "growth", "higher_better", -1,
                "OLS slope of log GST-declared turnover vs time."),
    FeatureSpec("gr_headcount_trend", "growth", "higher_better", -1,
                "EPFO headcount change (last-6m vs first-6m): hiring = expansion, shedding = distress."),
    FeatureSpec("gr_balance_recent_ratio", "growth", "higher_better", -1,
                "Avg balance last-3m / prior months: recent treasury build-up or depletion."),
    FeatureSpec("gr_wage_bill_growth_log", "growth", "neutral", 0,
                "log growth of wage bill: expansion signal but also cost strain — left unconstrained."),
    # ---------------- stability ----------------
    FeatureSpec("st_history_months", "stability", "higher_better", -1,
                "Months of observed banking history: thin files carry estimation risk (PHOENIX003=14)."),
    FeatureSpec("st_bounce_total", "stability", "higher_worse", 1,
                "Total bounced/returned payments (RTN/NACH RTN): the classic delinquency precursor."),
    FeatureSpec("st_bounce_last3", "stability", "higher_worse", 1,
                "Bounces in last 3 months: active repayment stress."),
    FeatureSpec("st_bounce_rate", "stability", "higher_worse", 1,
                "Bounces per month (history-normalized so 14-month files compare fairly with 24)."),
    FeatureSpec("st_upi_share_mean", "stability", "higher_better", -1,
                "UPI share of inflows: cashless share predicts lower default (Ghosh–Vallée–Zeng, J.Finance)."),
    FeatureSpec("st_upi_txn_avg_log", "stability", "higher_better", -1,
                "log(1+mean UPI txns/month): digital footprint depth."),
    FeatureSpec("st_top3_buyer_share", "stability", "higher_worse", 1,
                "Mean top-3 buyer concentration: dependency risk (supply-chain Tier A)."),
    FeatureSpec("st_top1_buyer_share", "stability", "higher_worse", 1,
                "Mean largest-buyer share from GSTR-1 counterparties: single-point-of-failure risk."),
    FeatureSpec("st_b2b_share", "stability", "neutral", 0,
                "B2B share of sales: mix descriptor, direction ambiguous — unconstrained."),
    FeatureSpec("st_counterparty_count", "stability", "neutral", 0,
                "Mean distinct GSTR-1 counterparties per month: diversification breadth."),
    FeatureSpec("st_wage_to_inflow", "stability", "neutral", 0,
                "Wage bill / inflows: too high = cost strain, too low = informality — unconstrained."),
    FeatureSpec("st_headcount_avg", "stability", "neutral", 0,
                "Mean EPFO headcount: formalization scale descriptor."),
    # ---------------- compliance ----------------
    FeatureSpec("cm_gst_ontime_share", "compliance", "higher_better", -1,
                "Share of GST returns filed on time: filing punctuality (late-fee incidence proxy)."),
    FeatureSpec("cm_gst_delay_days_avg", "compliance", "higher_worse", 1,
                "Mean GST filing delay days: severity of late filing."),
    FeatureSpec("cm_gst_nil_count", "compliance", "higher_worse", 1,
                "Count of nil returns: activity going dark while registration stays alive."),
    FeatureSpec("cm_gst_nil_streak", "compliance", "higher_worse", 1,
                "Longest consecutive nil-return streak: sustained non-activity signal."),
    FeatureSpec("cm_gst_late_nil_last3", "compliance", "higher_worse", 1,
                "Late-or-nil months within last 3: current compliance stress (EWS-aligned)."),
    FeatureSpec("cm_gst_divergence_abs_log", "compliance", "higher_worse", 1,
                "|log(GST-declared turnover / bank inflows)| — THE killer cross-check: divergence in either "
                "direction = inflated turnover or undeclared sales (single strongest MSME fraud check)."),
    FeatureSpec("cm_gst_declared_to_inflow", "compliance", "neutral", 0,
                "Raw GST-declared / bank-inflow ratio: signed divergence kept for explanation display."),
    FeatureSpec("cm_gst_divergence_recent", "compliance", "higher_worse", 1,
                "|log divergence| over last 6 months: is the mismatch current or historical?"),
    FeatureSpec("cm_gst_punctuality_trend", "compliance", "higher_better", -1,
                "On-time share last-6m minus first-6m: compliance improving or decaying."),
    FeatureSpec("cm_gst_turnover_avg_log", "compliance", "neutral", 0,
                "log(1+mean GST-declared turnover): declared-scale descriptor."),
]

FEATURE_NAMES = [f.name for f in FEATURES]
GROUPS = ["cash_flow", "growth", "stability", "compliance"]
GROUP_FEATURES = {g: [f.name for f in FEATURES if f.group == g] for g in GROUPS}
MONOTONE = {f.name: f.monotone for f in FEATURES}
SPEC_BY_NAME = {f.name: f for f in FEATURES}


# --------------------------------------------------------------------------------------
# Per-firm computation
# --------------------------------------------------------------------------------------
def _cov(x: np.ndarray) -> float:
    m = float(np.mean(x))
    if abs(m) < EPS:
        return 0.0
    return float(np.std(x) / (abs(m) + EPS))


def _slope_log(y: np.ndarray) -> float:
    """OLS slope of log(1+y) against month index."""
    n = len(y)
    if n < 3:
        return 0.0
    t = np.arange(n, dtype=float)
    ly = np.log1p(np.maximum(y, 0.0))
    t = t - t.mean()
    denom = float((t * t).sum())
    if denom < EPS:
        return 0.0
    return float((t * (ly - ly.mean())).sum() / denom)


def _max_streak(flags: np.ndarray) -> int:
    best = cur = 0
    for v in flags:
        cur = cur + 1 if v else 0
        best = max(best, cur)
    return best


def compute_firm_features(g: pd.DataFrame, cp_top1: float | None = None,
                          cp_count: float | None = None) -> dict[str, float]:
    """g: monthly rows for ONE msme sorted by month (only the months that exist —
    short histories are handled by windowing over what is available)."""
    g = g.sort_values("month")
    n = len(g)
    k = max(1, min(6, n // 2))  # window for first-vs-last comparisons
    r3 = min(3, n)

    infl = g["bank_inflow_inr"].to_numpy(dtype=float)
    outf = g["bank_outflow_inr"].to_numpy(dtype=float)
    bal = g["eod_balance_avg_inr"].to_numpy(dtype=float)
    bmin = g["eod_balance_min_inr"].to_numpy(dtype=float)
    dnz = g["days_near_zero"].to_numpy(dtype=float)
    ucnt = g["upi_txn_count"].to_numpy(dtype=float)
    ushr = g["upi_inflow_share"].to_numpy(dtype=float)
    bnc = g["bounce_count"].to_numpy(dtype=float)
    emi = g["emi_debit_inr"].to_numpy(dtype=float)
    slf = g["self_transfer_inr"].to_numpy(dtype=float)
    gst = g["gst_turnover_declared_inr"].to_numpy(dtype=float)
    ontime = g["gst_filed_on_time"].to_numpy(dtype=float)
    delay = g["gst_filing_delay_days"].to_numpy(dtype=float)
    nil = g["gst_nil_return"].to_numpy(dtype=float)
    b2b = g["b2b_share"].to_numpy(dtype=float)
    top3 = g["top3_buyer_share"].to_numpy(dtype=float)
    emp = g["employees_epfo"].to_numpy(dtype=float)
    wage = g["wage_bill_inr"].to_numpy(dtype=float)

    mi, mo = float(infl.mean()), float(outf.mean())
    si = float(infl.sum())

    def ratio_log(last: np.ndarray, first: np.ndarray) -> float:
        return float(np.log((last.mean() + EPS) / (first.mean() + EPS)))

    mom = np.diff(infl) / (infl[:-1] + EPS) if n > 1 else np.array([0.0])
    prior = slice(0, n - r3) if n > r3 else slice(0, n)  # months before the last 3

    f: dict[str, float] = {}
    # cash_flow
    f["cf_inflow_avg_log"] = float(np.log1p(mi))
    f["cf_inflow_amount_cov"] = _cov(infl)
    f["cf_inflow_count_cov"] = _cov(ucnt)
    f["cf_net_flow_ratio"] = float((mi - mo) / (mi + EPS))
    f["cf_balance_buffer"] = float(bal.mean() / (mo + EPS))
    f["cf_log_growth_avg_balance"] = ratio_log(bal[-k:], bal[:k])
    f["cf_min_balance_ratio"] = float(bmin.mean() / (mo + EPS))
    f["cf_min_balance_change"] = float((bmin[-k:].mean() - bmin[:k].mean()) / (mo + EPS))
    f["cf_balance_volatility"] = _cov(bal)
    f["cf_days_near_zero_avg"] = float(dnz.mean())
    f["cf_days_near_zero_last3"] = float(dnz[-r3:].mean())
    f["cf_emi_to_inflow"] = float(emi.sum() / (si + EPS))
    f["cf_self_transfer_share"] = float(slf.sum() / (si + EPS))
    f["cf_outflow_to_inflow"] = float(outf.sum() / (si + EPS))
    # growth
    f["gr_inflow_growth_log"] = ratio_log(infl[-k:], infl[:k])
    f["gr_inflow_mom_mean"] = float(np.clip(mom, -1.0, 1.0).mean())
    f["gr_inflow_trend"] = _slope_log(infl)
    f["gr_inflow_recent_ratio"] = float(infl[-r3:].mean() / (infl[prior].mean() + EPS))
    f["gr_gst_growth_log"] = ratio_log(gst[-k:], gst[:k])
    f["gr_gst_trend"] = _slope_log(gst)
    f["gr_headcount_trend"] = float((emp[-k:].mean() - emp[:k].mean()) / max(emp[:k].mean(), 1.0))
    f["gr_balance_recent_ratio"] = float(bal[-r3:].mean() / (bal[prior].mean() + EPS))
    f["gr_wage_bill_growth_log"] = ratio_log(wage[-k:] + 1.0, wage[:k] + 1.0)
    # stability
    f["st_history_months"] = float(n)
    f["st_bounce_total"] = float(bnc.sum())
    f["st_bounce_last3"] = float(bnc[-r3:].sum())
    f["st_bounce_rate"] = float(bnc.sum() / n)
    f["st_upi_share_mean"] = float(ushr.mean())
    f["st_upi_txn_avg_log"] = float(np.log1p(ucnt.mean()))
    f["st_top3_buyer_share"] = float(top3.mean())
    f["st_top1_buyer_share"] = float(cp_top1) if cp_top1 is not None else float(top3.mean() / 2.0)
    f["st_b2b_share"] = float(b2b.mean())
    f["st_counterparty_count"] = float(cp_count) if cp_count is not None else 5.0
    f["st_wage_to_inflow"] = float(wage.sum() / (si + EPS))
    f["st_headcount_avg"] = float(emp.mean())
    # compliance
    f["cm_gst_ontime_share"] = float(ontime.mean())
    f["cm_gst_delay_days_avg"] = float(delay.mean())
    f["cm_gst_nil_count"] = float(nil.sum())
    f["cm_gst_nil_streak"] = float(_max_streak(nil > 0.5))
    f["cm_gst_late_nil_last3"] = float(((ontime[-r3:] < 0.5) | (nil[-r3:] > 0.5)).sum())
    div = float(np.log((gst.sum() + EPS) / (si + EPS)))
    f["cm_gst_divergence_abs_log"] = abs(div)
    f["cm_gst_declared_to_inflow"] = float(gst.sum() / (si + EPS))
    k6 = min(6, n)
    f["cm_gst_divergence_recent"] = abs(float(np.log((gst[-k6:].sum() + EPS) / (infl[-k6:].sum() + EPS))))
    f["cm_gst_punctuality_trend"] = float(ontime[-k:].mean() - ontime[:k].mean())
    f["cm_gst_turnover_avg_log"] = float(np.log1p(gst.mean()))
    return f


def counterparty_aggregates(cps: pd.DataFrame) -> pd.DataFrame:
    """Per msme: mean of monthly max buyer share, mean distinct counterparties/month."""
    bym = cps.groupby(["msme_id", "month"], sort=False).agg(
        top1=("share", "max"), cnt=("counterparty_gstin", "nunique"))
    agg = bym.groupby(level="msme_id").mean()
    agg.columns = ["cp_top1", "cp_count"]
    return agg


def build_features(monthly: pd.DataFrame, cps: pd.DataFrame | None = None) -> pd.DataFrame:
    cp_agg = counterparty_aggregates(cps) if cps is not None and len(cps) else None
    rows, ids = [], []
    for msme_id, g in monthly.groupby("msme_id", sort=False):
        t1 = c1 = None
        if cp_agg is not None and msme_id in cp_agg.index:
            t1 = cp_agg.loc[msme_id, "cp_top1"]
            c1 = cp_agg.loc[msme_id, "cp_count"]
        rows.append(compute_firm_features(g, t1, c1))
        ids.append(msme_id)
    out = pd.DataFrame(rows, index=pd.Index(ids, name="msme_id"))[FEATURE_NAMES]
    return out.replace([np.inf, -np.inf], 0.0).fillna(0.0)


# --------------------------------------------------------------------------------------
# FEATURES.md generation
# --------------------------------------------------------------------------------------
def write_features_md(path: str) -> None:
    dir_label = {"higher_better": "higher = safer", "higher_worse": "higher = riskier",
                 "neutral": "neutral / mix"}
    lines = [
        "# FEATURES.md — SHROFF feature dictionary (feature engine v1)",
        "",
        f"{len(FEATURES)} features in 4 groups (cash_flow {len(GROUP_FEATURES['cash_flow'])} · "
        f"growth {len(GROUP_FEATURES['growth'])} · stability {len(GROUP_FEATURES['stability'])} · "
        f"compliance {len(GROUP_FEATURES['compliance'])}), computed per MSME from the CONTRACTS",
        "monthly schema + GSTR-1 counterparties table. Short histories (PHOENIX003: 14 months)",
        "use windows over the AVAILABLE months (first/last window k = min(6, n//2), recent = last",
        "min(3, n)); missing months are pre-incorporation, never imputed as zero activity.",
        "`st_history_months` carries thin-file information explicitly.",
        "",
        "Monotone constraint is with respect to the model output **P(default)**: `+1` = predicted",
        "risk may only rise as the feature rises, `-1` = may only fall, `0` = unconstrained.",
        "Constraints guarantee directionally-sane SHAP (more revenue can never raise risk).",
        "",
        "| Feature | Group | Direction | Monotone (vs PD) | Rationale |",
        "|---|---|---|---|---|",
    ]
    for f in FEATURES:
        mono = {1: "+1", -1: "-1", 0: "0"}[f.monotone]
        lines.append(f"| `{f.name}` | {f.group} | {dir_label[f.direction]} | {mono} | {f.rationale} |")
    lines += [
        "",
        "## Notes",
        "- `cm_gst_divergence_abs_log` is THE killer cross-check (GST-declared vs bank-verified",
        "  turnover). Datagen injects a benign cash-divergence band for kirana/agri so it is a",
        "  strong signal, not a perfect tell.",
        "- `cf_log_growth_avg_balance` replicates AI-BAAM's top feature (IV = 0.484).",
        "- Ratios are guarded with eps; inf/NaN mapped to 0 after computation.",
        "- The four groups feed four separate monotonic LightGBM sub-models; the sub-scores on the",
        "  Health Card radar are population percentiles of those sub-models (see train/train.py).",
    ]
    with open(path, "w") as fh:
        fh.write("\n".join(lines) + "\n")


def main() -> None:
    monthly = pd.read_parquet(os.path.join(DATA, "monthly.parquet"))
    cps = pd.read_parquet(os.path.join(DATA, "counterparties.parquet"))
    feats = build_features(monthly, cps)
    out = os.path.join(DATA, "features.parquet")
    feats.to_parquet(out)
    write_features_md(os.path.join(os.path.dirname(os.path.abspath(__file__)), "FEATURES.md"))
    print(f"features: {feats.shape[0]} firms x {feats.shape[1]} features -> {out}")
    for pid in ["RAMESH001", "SURESH002", "PHOENIX003"]:
        r = feats.loc[pid]
        print(f"  {pid}: history={r.st_history_months:.0f} divergence_ratio="
              f"{r.cm_gst_declared_to_inflow:.2f} bounces={r.st_bounce_total:.0f} "
              f"growth={r.gr_inflow_growth_log:+.3f} buffer={r.cf_balance_buffer:.2f}")


if __name__ == "__main__":
    main()
