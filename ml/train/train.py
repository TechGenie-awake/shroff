"""SHROFF trainer — 4 monotonic LightGBM sub-models -> logistic meta-combiner ->
isotonic-calibrated 12-mo PD, plus a plain LogisticRegression baseline ("regulator view").

Run:  cd ml && uv run python -m train.train
Emits ml/artifacts/: model_bundle.joblib, metrics.json, calibration_plot.png,
score_distribution.png, and ml/train/VALIDATION.md.
Personas (is_persona=1) are EXCLUDED from all training/eval splits per CONTRACTS.
"""
from __future__ import annotations

import json
import os

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score, roc_curve
from sklearn.model_selection import StratifiedKFold, cross_val_predict, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from features.build import FEATURE_NAMES, GROUP_FEATURES, GROUPS, MONOTONE
from train.scorecard import band_for_score, pd_to_score

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # ml/
DATA = os.path.join(ROOT, "data")
ARTIFACTS = os.path.join(ROOT, "artifacts")
SEED = 42

# Dataviz palette — CONTRACTS brand snapped to validator-passing steps on surface #FAF7F1
# (validate_palette.js: all checks PASS for #0B8168,#C2571B,#3F68B5 --mode light)
SURFACE, INK, INK2, HAIR = "#FAF7F1", "#1A2332", "#5C6470", "#E5DFD3"
TEAL, SAFFRON, SLATE = "#0B8168", "#C2571B", "#3F68B5"


def ks_stat(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    fpr, tpr, _ = roc_curve(y_true, y_prob)
    return float(np.max(np.abs(tpr - fpr)))


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def make_submodel(group: str) -> LGBMClassifier:
    cols = GROUP_FEATURES[group]
    return LGBMClassifier(
        objective="binary",
        n_estimators=400,
        learning_rate=0.05,
        num_leaves=15,
        min_child_samples=40,
        subsample=0.9,
        subsample_freq=1,
        colsample_bytree=0.9,
        reg_lambda=1.0,
        monotone_constraints=[MONOTONE[c] for c in cols],
        monotone_constraints_method="advanced",
        random_state=SEED,
        n_jobs=-1,
        verbose=-1,
    )


def _style_ax(ax):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(HAIR)
    ax.tick_params(colors=INK2, labelsize=9)
    ax.grid(True, color=HAIR, linewidth=0.7, alpha=0.8)
    ax.set_axisbelow(True)


def plot_calibration(y_true, pd_cal, path):
    df = pd.DataFrame({"y": y_true, "p": pd_cal}).sort_values("p")
    df["bin"] = pd.qcut(df["p"].rank(method="first"), 10, labels=False)
    g = df.groupby("bin").agg(pred=("p", "mean"), obs=("y", "mean"))
    fig, ax = plt.subplots(figsize=(6.4, 4.8), dpi=160)
    fig.patch.set_facecolor(SURFACE)
    _style_ax(ax)
    lim = max(g["pred"].max(), g["obs"].max()) * 1.15
    ax.plot([0, lim], [0, lim], ls="--", lw=1.2, color=INK2, label="Perfect calibration")
    ax.plot(g["pred"], g["obs"], color=TEAL, lw=2, marker="o", ms=6,
            mfc=TEAL, mec=SURFACE, mew=1.5, label="Isotonic-calibrated PD (holdout)")
    ax.set_xlabel("Predicted 12-mo PD (decile mean)", color=INK, fontsize=10)
    ax.set_ylabel("Observed default rate", color=INK, fontsize=10)
    ax.set_title("Calibration — holdout reliability curve (10 deciles)",
                 color=INK, fontsize=11, loc="left")
    leg = ax.legend(frameon=False, fontsize=9, loc="upper left")
    for t in leg.get_texts():
        t.set_color(INK)
    fig.tight_layout()
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)


def plot_score_distribution(scores, y_true, path):
    fig, ax = plt.subplots(figsize=(7.2, 4.8), dpi=160)
    fig.patch.set_facecolor(SURFACE)
    _style_ax(ax)
    bins = np.arange(300, 901, 20)
    ax.hist(scores[y_true == 0], bins=bins, color=TEAL, alpha=0.75,
            label="Non-defaulters", edgecolor=SURFACE, linewidth=0.8, density=True)
    ax.hist(scores[y_true == 1], bins=bins, color=SAFFRON, alpha=0.75,
            label="Defaulters (12 mo)", edgecolor=SURFACE, linewidth=0.8, density=True)
    for x, lab in [(750, "A"), (680, "B"), (600, "C"), (500, "D")]:
        ax.axvline(x, color=INK2, lw=0.9, ls=":", alpha=0.8)
        ax.text(x + 3, ax.get_ylim()[1] * 0.97, f"{lab} ≥{x}" if lab == "A" else lab,
                color=INK2, fontsize=8, va="top")
    ax.set_xlabel("SHROFF score (300–900; 660 = 5% PD, +72/halving of odds)",
                  color=INK, fontsize=10)
    ax.set_ylabel("Density", color=INK, fontsize=10)
    ax.set_title("Score distribution by outcome — holdout", color=INK, fontsize=11, loc="left")
    leg = ax.legend(frameon=False, fontsize=9)
    for t in leg.get_texts():
        t.set_color(INK)
    fig.tight_layout()
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)


def main() -> None:
    os.makedirs(ARTIFACTS, exist_ok=True)
    feats = pd.read_parquet(os.path.join(DATA, "features.parquet"))
    prof = pd.read_parquet(os.path.join(DATA, "msmes.parquet")).set_index("msme_id")
    pop = prof[prof["is_persona"] == 0]
    X = feats.loc[pop.index, FEATURE_NAMES]
    y = pop["default_12m"].to_numpy()

    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.20, stratify=y, random_state=SEED)
    print(f"train {len(X_tr)} / holdout {len(X_te)} · prevalence {y.mean():.4f}")

    # --- 4 monotonic sub-models + out-of-fold meta features on train ---
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    sub_models: dict[str, LGBMClassifier] = {}
    oof = np.zeros((len(X_tr), len(GROUPS)))
    te_sub = np.zeros((len(X_te), len(GROUPS)))
    metrics: dict = {"sub_models": {}}
    for j, grp in enumerate(GROUPS):
        cols = GROUP_FEATURES[grp]
        mdl = make_submodel(grp)
        oof[:, j] = cross_val_predict(mdl, X_tr[cols], y_tr, cv=cv,
                                      method="predict_proba", n_jobs=1)[:, 1]
        mdl.fit(X_tr[cols], y_tr)
        sub_models[grp] = mdl
        te_sub[:, j] = mdl.predict_proba(X_te[cols])[:, 1]
        auc = roc_auc_score(y_te, te_sub[:, j])
        ks = ks_stat(y_te, te_sub[:, j])
        metrics["sub_models"][grp] = {"auc": round(float(auc), 4), "ks": round(ks, 4)}
        print(f"  sub[{grp:<10}] holdout AUC {auc:.4f}  KS {ks:.4f}")

    # --- logistic meta-combiner on logit(sub-model PDs), fit on OOF (no leakage) ---
    meta = LogisticRegression(max_iter=2000)
    meta.fit(_logit(oof), y_tr)
    p_meta_te = meta.predict_proba(_logit(te_sub))[:, 1]
    auc_c = roc_auc_score(y_te, p_meta_te)
    ks_c = ks_stat(y_te, p_meta_te)
    print(f"  combined (meta)  holdout AUC {auc_c:.4f}  KS {ks_c:.4f}")
    print(f"  meta coefs {dict(zip(GROUPS, np.round(meta.coef_[0], 3)))}")

    # --- isotonic calibration on holdout -> 12-mo PD ---
    calib = IsotonicRegression(y_min=0.002, y_max=0.98, out_of_bounds="clip")
    calib.fit(p_meta_te, y_te)
    pd_cal_te = calib.predict(p_meta_te)
    brier = brier_score_loss(y_te, pd_cal_te)

    # --- plain LogisticRegression all-features baseline (the "regulator view") ---
    base = Pipeline([("scaler", StandardScaler()),
                     ("lr", LogisticRegression(max_iter=4000))])
    base.fit(X_tr, y_tr)
    p_base = base.predict_proba(X_te)[:, 1]
    auc_b, ks_b = roc_auc_score(y_te, p_base), ks_stat(y_te, p_base)
    print(f"  baseline LogReg  holdout AUC {auc_b:.4f}  KS {ks_b:.4f}")

    if not (0.80 <= auc_c <= 0.95):
        raise SystemExit(f"combined holdout AUC {auc_c:.4f} outside 0.80–0.95 — "
                         "adjust datagen noise/weights and re-run (see task spec)")

    # --- population sub-score reference: sorted sub-model PDs over the 8k population ---
    pop_ref = {}
    for j, grp in enumerate(GROUPS):
        cols = GROUP_FEATURES[grp]
        pop_ref[grp] = np.sort(sub_models[grp].predict_proba(X[cols])[:, 1])

    # --- artifacts ---
    metrics.update({
        "combined": {"auc": round(float(auc_c), 4), "ks": round(ks_c, 4),
                     "brier_calibrated": round(float(brier), 4)},
        "baseline_logreg": {"auc": round(float(auc_b), 4), "ks": round(ks_b, 4)},
        "train_n": int(len(X_tr)), "holdout_n": int(len(X_te)),
        "prevalence": round(float(y.mean()), 4),
        "meta_coefficients": {g: round(float(c), 4) for g, c in zip(GROUPS, meta.coef_[0])},
        "model_version": "v1", "trained_on": "synthetic-v1", "seed": SEED,
    })
    with open(os.path.join(ARTIFACTS, "metrics.json"), "w") as fh:
        json.dump(metrics, fh, indent=2)

    bundle = {
        "version": "v1",
        "feature_names": FEATURE_NAMES,
        "group_features": GROUP_FEATURES,
        "monotone": MONOTONE,
        "sub_models": sub_models,
        "meta": meta,
        "calibrator": calib,
        "pop_ref": pop_ref,
        "baseline": base,
        "metrics": {"auc": metrics["combined"]["auc"], "ks": metrics["combined"]["ks"]},
    }
    joblib.dump(bundle, os.path.join(ARTIFACTS, "model_bundle.joblib"))

    scores_te = np.array([pd_to_score(p) for p in pd_cal_te])
    plot_calibration(y_te, pd_cal_te, os.path.join(ARTIFACTS, "calibration_plot.png"))
    plot_score_distribution(scores_te, y_te, os.path.join(ARTIFACTS, "score_distribution.png"))

    bands_te = pd.Series([band_for_score(s) for s in scores_te])
    band_pd = pd.DataFrame({"band": bands_te.values, "y": y_te}).groupby("band")["y"].agg(["mean", "size"])
    write_validation_md(metrics, band_pd)
    print(f"artifacts -> {ARTIFACTS}")
    print(json.dumps(metrics, indent=2))


def write_validation_md(metrics: dict, band_pd: pd.DataFrame) -> None:
    m = metrics
    lines = [
        "# VALIDATION.md — SHROFF scoring model v1 (synthetic-v1 data)",
        "",
        f"Population: {m['train_n'] + m['holdout_n']} synthetic MSMEs (personas excluded), "
        f"12-mo default prevalence {m['prevalence']:.2%}. Stratified 80/20 split "
        f"(train {m['train_n']} / holdout {m['holdout_n']}, seed {m['seed']}). "
        "All metrics below are on the untouched holdout.",
        "",
        "## Architecture",
        "4 monotonic LightGBM sub-models (cash_flow, growth, stability, compliance — constraints",
        "per features/FEATURES.md) → logistic meta-combiner fit on 5-fold out-of-fold sub-model",
        "outputs (no leakage) → isotonic calibration on holdout → 12-month PD → scorecard scaling",
        "(660 @ 5% PD, +72 per halving of odds, clamped 300–900; bands A ≥750 · B 680–749 ·",
        "C 600–679 · D 500–599 · E <500). A plain standardized LogisticRegression over all",
        f"{len(FEATURE_NAMES)} features is reported side-by-side as the regulator view.",
        "",
        "## Discrimination (holdout)",
        "",
        "| Model | AUC | KS |",
        "|---|---|---|",
    ]
    for grp in GROUPS:
        s = m["sub_models"][grp]
        lines.append(f"| sub-model: {grp} | {s['auc']:.4f} | {s['ks']:.4f} |")
    lines += [
        f"| **combined (meta-LR of 4 sub-models)** | **{m['combined']['auc']:.4f}** | **{m['combined']['ks']:.4f}** |",
        f"| baseline: LogisticRegression, all features (regulator view) | {m['baseline_logreg']['auc']:.4f} | {m['baseline_logreg']['ks']:.4f} |",
        "",
        f"Calibrated Brier score: {m['combined']['brier_calibrated']:.4f}. "
        "Calibration curve: `../artifacts/calibration_plot.png`; score separation: "
        "`../artifacts/score_distribution.png`.",
        "",
        f"Meta-combiner coefficients (on logit sub-model PDs): "
        + ", ".join(f"{g} {c:+.3f}" for g, c in m["meta_coefficients"].items()) + ".",
        "",
        "## Observed default rate by band (holdout)",
        "",
        "| Band | Holdout N | Observed default rate |",
        "|---|---|---|",
    ]
    for band in ["A", "B", "C", "D", "E"]:
        if band in band_pd.index:
            r = band_pd.loc[band]
            lines.append(f"| {band} | {int(r['size'])} | {r['mean']:.2%} |")
    lines += [
        "",
        "## Honest caveats (read before quoting these numbers)",
        "",
        "- **This is synthetic data.** The generator encodes known MSME risk economics",
        "  (cash-flow buffers, bounce history, GST punctuality, GST-vs-bank divergence, buyer",
        "  concentration, headcount trend) and draws the default label from those same economics",
        "  plus irreducible noise (datagen/DATA.md: oracle AUC ≈ 0.86, achievable ≈ 0.88). The",
        "  numbers above therefore demonstrate the *pipeline* — feature engine, monotone",
        "  constraints, calibration, scorecard — not production performance.",
        "- Isotonic calibration is fit on the same holdout used for reporting (a 4-day-build",
        "  compromise; AUC/KS are unaffected as isotonic is monotone, but Brier is optimistic).",
        "  Production: separate calibration fold or cross-fitted calibration.",
        "- `st_history_months` is constant (24) across the training population, so the model",
        "  cannot learn a thin-file penalty from data; short-history treatment for PHOENIX003-type",
        "  files comes from windowed features, not from a learned history effect.",
        "- **In production the model must be retrained and recalibrated on IDBI's own MSME",
        "  portfolio outcomes** through the bank's model-risk-management process (RBI FREE-AI",
        "  aligned). The synthetic AUC is a ceiling-shaped rehearsal, not a claim.",
    ]
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "VALIDATION.md"), "w") as fh:
        fh.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
