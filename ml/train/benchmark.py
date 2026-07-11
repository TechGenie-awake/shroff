"""SHROFF benchmark — decision-quality proof on the untouched holdout.

Loads the trained bundle, reproduces the EXACT holdout split (seed=42), scores it
through the real path (sub-models -> meta -> isotonic PD -> scorecard -> band), and
computes what a bank actually underwrites on: rank-ordering, an approval simulation
(approve bands A/B), confusion matrix, bad-loan capture, and the score-cutoff tradeoff.

Run:  cd ml && uv run python -m train.benchmark
Emits ml/artifacts/benchmark.json  (personas I/O is captured separately via the API).
Personas (is_persona=1) are EXCLUDED — same as training.
"""
from __future__ import annotations

import json
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, roc_curve
from sklearn.model_selection import train_test_split

from features.build import FEATURE_NAMES, GROUP_FEATURES, GROUPS
from train.scorecard import band_for_score, pd_to_score

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
ARTIFACTS = os.path.join(ROOT, "artifacts")
SEED = 42
APPROVE_BANDS = {"A", "B"}   # decision engine: A/B APPROVE, C/D REFER, E DECLINE


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def score_matrix(bundle: dict, X: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Return (pd_cal, score, band) via the exact production scoring path."""
    sub = np.zeros((len(X), len(GROUPS)))
    for j, grp in enumerate(GROUPS):
        sub[:, j] = bundle["sub_models"][grp].predict_proba(X[GROUP_FEATURES[grp]])[:, 1]
    p_meta = bundle["meta"].predict_proba(_logit(sub))[:, 1]
    pd_cal = bundle["calibrator"].predict(p_meta)
    scores = np.array([pd_to_score(p) for p in pd_cal])
    bands = [band_for_score(s) for s in scores]
    return pd_cal, scores, bands


def main() -> None:
    bundle = joblib.load(os.path.join(ARTIFACTS, "model_bundle.joblib"))
    feats = pd.read_parquet(os.path.join(DATA, "features.parquet"))
    prof = pd.read_parquet(os.path.join(DATA, "msmes.parquet")).set_index("msme_id")
    pop = prof[prof["is_persona"] == 0]
    X = feats.loc[pop.index, FEATURE_NAMES]
    y = pop["default_12m"].to_numpy()
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.20, stratify=y, random_state=SEED)

    pd_cal, scores, bands = score_matrix(bundle, X_te)
    bands = np.array(bands)
    n = len(y_te)
    prevalence = float(y_te.mean())

    # -- discrimination
    auc = float(roc_auc_score(y_te, pd_cal))
    fpr, tpr, _ = roc_curve(y_te, pd_cal)
    ks = float(np.max(tpr - fpr))

    # -- rank-ordering: observed default rate by band (monotone = the score works)
    band_table = []
    for b in ["A", "B", "C", "D", "E"]:
        m = bands == b
        if m.sum():
            band_table.append({"band": b, "n": int(m.sum()),
                               "observed_default_rate": round(float(y_te[m].mean()), 4),
                               "score_range": [int(scores[m].min()), int(scores[m].max())]})

    # -- decision simulation: APPROVE = band A/B
    approve = np.isin(bands, list(APPROVE_BANDS))
    decline = bands == "E"
    refer = ~approve & ~decline
    approved_bad = int(y_te[approve].sum())
    total_bad = int(y_te.sum())
    decision = {
        "policy": "APPROVE if band A/B · REFER if C/D · DECLINE if E",
        "approve": {"n": int(approve.sum()), "rate": round(float(approve.mean()), 4),
                    "bad_in_book": approved_bad,
                    "bad_rate": round(float(y_te[approve].mean()), 4) if approve.sum() else 0.0},
        "refer":   {"n": int(refer.sum()), "rate": round(float(refer.mean()), 4),
                    "bad_rate": round(float(y_te[refer].mean()), 4) if refer.sum() else 0.0},
        "decline": {"n": int(decline.sum()), "rate": round(float(decline.mean()), 4),
                    "bad_rate": round(float(y_te[decline].mean()), 4) if decline.sum() else 0.0},
        # what share of ALL defaulters the policy keeps OUT of the approved book
        "bad_loans_caught_pct": round(100.0 * (total_bad - approved_bad) / total_bad, 1),
        # approved book is this many x cleaner than approving everyone
        "approved_book_vs_population": round(prevalence / max(y_te[approve].mean(), 1e-9), 1),
    }

    # -- confusion matrix at the approve cutoff (positive class = DEFAULT/"bad")
    #    decline+refer = "flagged" (predicted bad-ish), approve = "cleared"
    flagged = ~approve
    cm = {
        "true_bad_flagged": int((flagged & (y_te == 1)).sum()),      # correctly withheld
        "true_good_flagged": int((flagged & (y_te == 0)).sum()),     # opportunity cost
        "bad_approved": int((approve & (y_te == 1)).sum()),          # leakage
        "good_approved": int((approve & (y_te == 0)).sum()),         # correct approvals
    }
    cm["recall_bad"] = round(cm["true_bad_flagged"] / max(total_bad, 1), 4)
    cm["approval_precision_good"] = round(cm["good_approved"] / max(approve.sum(), 1), 4)

    # -- score-cutoff tradeoff: if we approve the top-k% by score, book bad-rate
    order = np.argsort(-scores)
    y_sorted = y_te[order]
    sweep = []
    for frac in (0.4, 0.5, 0.6, 0.7, 0.8, 0.9):
        k = int(frac * n)
        sweep.append({"approve_rate": frac,
                      "book_bad_rate": round(float(y_sorted[:k].mean()), 4),
                      "score_cutoff": int(scores[order][k - 1])})

    out = {
        "holdout_n": n, "prevalence": round(prevalence, 4),
        "discrimination": {"auc": round(auc, 4), "ks": round(ks, 4)},
        "rank_ordering_by_band": band_table,
        "decision_simulation": decision,
        "confusion_at_approve_cutoff": cm,
        "score_cutoff_tradeoff": sweep,
        "note": "Synthetic-v1 holdout; demonstrates the decisioning pipeline, not production performance.",
    }
    with open(os.path.join(ARTIFACTS, "benchmark.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
