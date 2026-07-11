# FEATURES.md — SHROFF feature dictionary (feature engine v1)

45 features in 4 groups (cash_flow 14 · growth 9 · stability 12 · compliance 10), computed per MSME from the CONTRACTS
monthly schema + GSTR-1 counterparties table. Short histories (PHOENIX003: 14 months)
use windows over the AVAILABLE months (first/last window k = min(6, n//2), recent = last
min(3, n)); missing months are pre-incorporation, never imputed as zero activity.
`st_history_months` carries thin-file information explicitly.

Monotone constraint is with respect to the model output **P(default)**: `+1` = predicted
risk may only rise as the feature rises, `-1` = may only fall, `0` = unconstrained.
Constraints guarantee directionally-sane SHAP (more revenue can never raise risk).

| Feature | Group | Direction | Monotone (vs PD) | Rationale |
|---|---|---|---|---|
| `cf_inflow_avg_log` | cash_flow | higher = safer | -1 | log(1+mean monthly bank inflow): scale of bank-verified activity (HKMA/ASTRI core variable). |
| `cf_inflow_amount_cov` | cash_flow | higher = riskier | +1 | Coefficient of variation of monthly inflow amounts: irregular revenue = repayment risk. |
| `cf_inflow_count_cov` | cash_flow | higher = riskier | +1 | CoV of monthly UPI transaction counts: irregular customer traffic (inflow-count regularity). |
| `cf_net_flow_ratio` | cash_flow | higher = safer | -1 | Mean (inflow-outflow)/inflow: operating surplus retained in the account. |
| `cf_balance_buffer` | cash_flow | higher = safer | -1 | Mean EOD avg balance / mean monthly outflow: liquidity runway in months. |
| `cf_log_growth_avg_balance` | cash_flow | higher = safer | -1 | log growth of average balance (last-6m vs first-6m): the #1 IV feature in AI-BAAM (IV=0.484). |
| `cf_min_balance_ratio` | cash_flow | higher = safer | -1 | Mean EOD minimum balance / mean outflow: intramonth cushion level. |
| `cf_min_balance_change` | cash_flow | higher = safer | -1 | Change in min balance (last-6m minus first-6m, scaled by outflow): cushion trajectory. |
| `cf_balance_volatility` | cash_flow | higher = riskier | +1 | CoV of EOD average balance: unstable treasury management. |
| `cf_days_near_zero_avg` | cash_flow | higher = riskier | +1 | Mean days/month with balance near zero: balance-depletion stress (HKMA early-warning signal). |
| `cf_days_near_zero_last3` | cash_flow | higher = riskier | +1 | Days-near-zero in last 3 months: recent depletion stress. |
| `cf_emi_to_inflow` | cash_flow | higher = riskier | +1 | Existing EMI debits / inflows: leverage stacking (FOIR analogue on cash flows). |
| `cf_self_transfer_share` | cash_flow | higher = riskier | +1 | Self-transfers / inflows: circular round-tripping that pads apparent turnover (fraud padding). |
| `cf_outflow_to_inflow` | cash_flow | higher = riskier | +1 | Outflows / inflows: burn ratio; >1 means the account is being drained. |
| `gr_inflow_growth_log` | growth | higher = safer | -1 | log(mean inflow last-6m / first-6m): medium-term revenue trajectory. |
| `gr_inflow_mom_mean` | growth | higher = safer | -1 | Mean month-over-month inflow growth (clipped): short-cycle momentum. |
| `gr_inflow_trend` | growth | higher = safer | -1 | OLS slope of log inflow vs time: robust whole-history trend. |
| `gr_inflow_recent_ratio` | growth | higher = safer | -1 | Mean inflow last-3m / prior months: early-warning collapse detector (both-directions head). |
| `gr_gst_growth_log` | growth | higher = safer | -1 | log growth of GST-declared turnover (last-6m vs first-6m): tax-verified growth. |
| `gr_gst_trend` | growth | higher = safer | -1 | OLS slope of log GST-declared turnover vs time. |
| `gr_headcount_trend` | growth | higher = safer | -1 | EPFO headcount change (last-6m vs first-6m): hiring = expansion, shedding = distress. |
| `gr_balance_recent_ratio` | growth | higher = safer | -1 | Avg balance last-3m / prior months: recent treasury build-up or depletion. |
| `gr_wage_bill_growth_log` | growth | neutral / mix | 0 | log growth of wage bill: expansion signal but also cost strain — left unconstrained. |
| `st_history_months` | stability | higher = safer | -1 | Months of observed banking history: thin files carry estimation risk (PHOENIX003=14). |
| `st_bounce_total` | stability | higher = riskier | +1 | Total bounced/returned payments (RTN/NACH RTN): the classic delinquency precursor. |
| `st_bounce_last3` | stability | higher = riskier | +1 | Bounces in last 3 months: active repayment stress. |
| `st_bounce_rate` | stability | higher = riskier | +1 | Bounces per month (history-normalized so 14-month files compare fairly with 24). |
| `st_upi_share_mean` | stability | higher = safer | -1 | UPI share of inflows: cashless share predicts lower default (Ghosh–Vallée–Zeng, J.Finance). |
| `st_upi_txn_avg_log` | stability | higher = safer | -1 | log(1+mean UPI txns/month): digital footprint depth. |
| `st_top3_buyer_share` | stability | higher = riskier | +1 | Mean top-3 buyer concentration: dependency risk (supply-chain Tier A). |
| `st_top1_buyer_share` | stability | higher = riskier | +1 | Mean largest-buyer share from GSTR-1 counterparties: single-point-of-failure risk. |
| `st_b2b_share` | stability | neutral / mix | 0 | B2B share of sales: mix descriptor, direction ambiguous — unconstrained. |
| `st_counterparty_count` | stability | neutral / mix | 0 | Mean distinct GSTR-1 counterparties per month: diversification breadth. |
| `st_wage_to_inflow` | stability | neutral / mix | 0 | Wage bill / inflows: too high = cost strain, too low = informality — unconstrained. |
| `st_headcount_avg` | stability | neutral / mix | 0 | Mean EPFO headcount: formalization scale descriptor. |
| `cm_gst_ontime_share` | compliance | higher = safer | -1 | Share of GST returns filed on time: filing punctuality (late-fee incidence proxy). |
| `cm_gst_delay_days_avg` | compliance | higher = riskier | +1 | Mean GST filing delay days: severity of late filing. |
| `cm_gst_nil_count` | compliance | higher = riskier | +1 | Count of nil returns: activity going dark while registration stays alive. |
| `cm_gst_nil_streak` | compliance | higher = riskier | +1 | Longest consecutive nil-return streak: sustained non-activity signal. |
| `cm_gst_late_nil_last3` | compliance | higher = riskier | +1 | Late-or-nil months within last 3: current compliance stress (EWS-aligned). |
| `cm_gst_divergence_abs_log` | compliance | higher = riskier | +1 | |log(GST-declared turnover / bank inflows)| — THE killer cross-check: divergence in either direction = inflated turnover or undeclared sales (single strongest MSME fraud check). |
| `cm_gst_declared_to_inflow` | compliance | neutral / mix | 0 | Raw GST-declared / bank-inflow ratio: signed divergence kept for explanation display. |
| `cm_gst_divergence_recent` | compliance | higher = riskier | +1 | |log divergence| over last 6 months: is the mismatch current or historical? |
| `cm_gst_punctuality_trend` | compliance | higher = safer | -1 | On-time share last-6m minus first-6m: compliance improving or decaying. |
| `cm_gst_turnover_avg_log` | compliance | neutral / mix | 0 | log(1+mean GST-declared turnover): declared-scale descriptor. |

## Notes
- `cm_gst_divergence_abs_log` is THE killer cross-check (GST-declared vs bank-verified
  turnover). Datagen injects a benign cash-divergence band for kirana/agri so it is a
  strong signal, not a perfect tell.
- `cf_log_growth_avg_balance` replicates AI-BAAM's top feature (IV = 0.484).
- Ratios are guarded with eps; inf/NaN mapped to 0 after computation.
- The four groups feed four separate monotonic LightGBM sub-models; the sub-scores on the
  Health Card radar are population percentiles of those sub-models (see train/train.py).
