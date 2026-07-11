# VALIDATION.md — SHROFF scoring model v1 (synthetic-v1 data)

Population: 8000 synthetic MSMEs (personas excluded), 12-mo default prevalence 10.24%. Stratified 80/20 split (train 6400 / holdout 1600, seed 42). All metrics below are on the untouched holdout.

## Architecture
4 monotonic LightGBM sub-models (cash_flow, growth, stability, compliance — constraints
per features/FEATURES.md) → logistic meta-combiner fit on 5-fold out-of-fold sub-model
outputs (no leakage) → isotonic calibration on holdout → 12-month PD → scorecard scaling
(660 @ 5% PD, +72 per halving of odds, clamped 300–900; bands A ≥750 · B 680–749 ·
C 600–679 · D 500–599 · E <500). A plain standardized LogisticRegression over all
45 features is reported side-by-side as the regulator view.

## Discrimination (holdout)

| Model | AUC | KS |
|---|---|---|
| sub-model: cash_flow | 0.8137 | 0.5169 |
| sub-model: growth | 0.7864 | 0.4354 |
| sub-model: stability | 0.7878 | 0.4660 |
| sub-model: compliance | 0.8155 | 0.5150 |
| **combined (meta-LR of 4 sub-models)** | **0.8560** | **0.5751** |
| baseline: LogisticRegression, all features (regulator view) | 0.8671 | 0.5935 |

Calibrated Brier score: 0.0648. Calibration curve: `../artifacts/calibration_plot.png`; score separation: `../artifacts/score_distribution.png`.

Meta-combiner coefficients (on logit sub-model PDs): cash_flow +0.389, growth +0.149, stability +0.262, compliance +0.227.

## Observed default rate by band (holdout)

| Band | Holdout N | Observed default rate |
|---|---|---|
| A | 637 | 1.26% |
| B | 26 | 3.85% |
| C | 436 | 4.36% |
| D | 199 | 11.56% |
| E | 302 | 37.42% |

## Honest caveats (read before quoting these numbers)

- **This is synthetic data.** The generator encodes known MSME risk economics
  (cash-flow buffers, bounce history, GST punctuality, GST-vs-bank divergence, buyer
  concentration, headcount trend) and draws the default label from those same economics
  plus irreducible noise (datagen/DATA.md: oracle AUC ≈ 0.86, achievable ≈ 0.88). The
  numbers above therefore demonstrate the *pipeline* — feature engine, monotone
  constraints, calibration, scorecard — not production performance.
- Isotonic calibration is fit on the same holdout used for reporting (a 4-day-build
  compromise; AUC/KS are unaffected as isotonic is monotone, but Brier is optimistic).
  Production: separate calibration fold or cross-fitted calibration.
- `st_history_months` is constant (24) across the training population, so the model
  cannot learn a thin-file penalty from data; short-history treatment for PHOENIX003-type
  files comes from windowed features, not from a learned history effect.
- **In production the model must be retrained and recalibrated on IDBI's own MSME
  portfolio outcomes** through the bank's model-risk-management process (RBI FREE-AI
  aligned). The synthetic AUC is a ceiling-shaped rehearsal, not a claim.
