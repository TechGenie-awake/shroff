# IDBI Innovate 2026 — SHROFF Data Field Requirements

Submitted against the reference template ("IDBI Innovate 2026: Data Field
Requirements"). Five APIs requested, matching the list posted to the team
group on 2026-08-27:

1. **GSTN Insights** — fields below mirror the sample schema IDBI provided,
   noting which ones SHROFF actually consumes.
2. **Bank / Account Aggregator Statement Insights** — new ask, no sample
   given, specified from SHROFF's existing feature contract in `CONTRACTS.md`.
3. **EPFO Employer Insights** — optional/nice-to-have.
4. **MCA Company & Director Master** — new ask, powers the phoenix-fraud
   entity graph.
5. **PAN/GSTIN Negative Registry / Watchlist** — new ask, for the
   compliance-screening overlay.

Per Anshuman's note in the group: most of these will come back as simulated
data from IDBI's side — 5–10 sample records per API is enough to validate
the field shapes against our pipeline; we don't need live production access
for the prototype phase.

---

## API 1 — GSTN Insights

### Request

| API Field Name | Field Type | Max Field Length | Mandatory/Optional | Sample Values | Description |
|---|---|---|---|---|---|
| GSTN | String | 15 | Mandatory | 29ABCDE1234F1Z5 | Borrower's GSTIN |

### Response — fields SHROFF consumes directly (from the provided sample)

All of the following map 1:1 onto existing SHROFF features
(`ml/features/FEATURES.md`) — no changes needed on our side to consume them
as given:

| API Response Field | Used for |
|---|---|
| `gstin`, `legal_name`, `trade_name`, `constitution_of_business` | Identity header, entity resolution |
| `gst_registration_status`, `registration_date`, `taxpayer_type` | Compliance sub-score, screening cross-check |
| `filing_frequency`, `latest_return_period` | Filing-cadence normalization |
| `gstr1_last_filed_date`, `gstr3b_last_filed_date`, `gstr1_delay_days`, `gstr3b_delay_days` | Compliance sub-score — filing punctuality |
| `late_filing_count_6m`, `late_filing_count_12m`, `nil_return_count_12m`, `missed_return_count_12m` | Compliance sub-score, EWS triggers |
| `gross_turnover_current_month` … `gross_turnover_12m` | Growth sub-score — turnover level + trend |
| `turnover_growth_mom_pct`, `turnover_growth_3m_pct`, `turnover_growth_6m_pct`, `turnover_growth_yoy_pct` | Growth sub-score — direct feature inputs |
| `b2b_taxable_turnover_12m`, `b2c_taxable_turnover_12m`, `export_turnover_12m` | Business-mix features |
| `credit_note_ratio_pct` | Revenue-quality adjustment (inflated-turnover check) |
| `outward_invoice_count_12m`, `avg_monthly_invoice_count`, `invoice_count_growth_6m_pct` | Cash-flow regularity proxy |
| `itc_mismatch_amount_12m`, `itc_mismatch_pct` | Compliance/fraud flag |
| `cash_tax_paid_12m`, `tax_payment_delay_count_12m` | Compliance sub-score |
| `gstr1_3b_turnover_mismatch_pct` | **The killer cross-check** — this is precisely the "GST-declared vs bank-verified turnover divergence" signal SHROFF's decision engine is built around (see `BUILD-SPEC-track03.md`) |
| `active_b2b_customer_count_12m`, `top_1_customer_sales_pct`, `top_5_customer_sales_pct`, `customer_concentration_index`, `customer_count_growth_pct` | Supply-chain concentration sub-feature (buyer-dependency risk) |
| `return_filing_consistency_pct` | Compliance sub-score composite |
| `data_period_from`, `data_period_to`, `data_freshness_date` | Displayed in the consent-artefact / data-freshness chip on the health card |
| `consent_reference`, `response_status` | Audit trail, error handling |

### Response — additional fields requested (not in the sample, needed to complete the model)

| Requested Field | Field Type | Description | Why we need it |
|---|---|---|---|
| `pan` | String(10) | Business PAN (also embeddable from GSTIN chars 3–12, but an explicit field avoids parse errors) | Cross-check against our negative-registry PAN join and the entity graph |
| `cin` | String(21) | Corporate Identification Number, if entity is a company | Feeds the PAN→CIN→director graph walk (phoenix-fraud detection) |
| `promoter_pan` / `promoter_din` | String | Promoter/director identifiers | Same — entity-graph join key |
| `udyam_registration_number` | String(19) | UDYAM registration ID | MSME-status confirmation, displayed on the health card identity header |
| `bounce_count_12m` / NACH-return indicator | Integer | If GSTN feed has any linked payment-instrument signal | Only if available on this API — otherwise covered by API 2 |

---

## API 2 — Bank / Account Aggregator Statement Insights *(new ask — no sample provided yet)*

This is the single biggest gap for round 2: the GSTN schema covers Pillar
1's compliance/growth signals well, but SHROFF's cash-flow sub-score and
the GST-vs-bank divergence check both need actual bank transaction data.
Requesting the same shape IDBI's own AA rails would deliver (`DEPOSIT` FI
type, Sahamati-aligned), monthly-aggregated:

### Request

| API Field Name | Field Type | Max Field Length | Mandatory/Optional | Sample Values | Description |
|---|---|---|---|---|---|
| account_ref / consent_ref | String | 50 | Mandatory | CONS_SYN_982731 | AA consent artefact reference authorizing the fetch |
| pan | String | 10 | Mandatory | ABCPR3456K | Borrower PAN to key the account lookup |

### Response (monthly-aggregated, one row per month — mirrors `CONTRACTS.md`'s existing monthly schema so the feature pipeline needs no rework)

| API Response Field | Field Type | Description |
|---|---|---|
| `month` | String(7) | YYYY-MM |
| `bank_inflow_inr` | Integer | Total monthly credits |
| `bank_outflow_inr` | Integer | Total monthly debits |
| `eod_balance_avg_inr` | Integer | Average end-of-day balance |
| `eod_balance_min_inr` | Integer | Minimum end-of-day balance |
| `days_near_zero` | Integer | Days balance stayed near zero (buffer-risk signal) |
| `upi_txn_count` | Integer | UPI transaction count |
| `upi_inflow_share` | Decimal(5,2) | Share of inflows arriving via UPI |
| `bounce_count` | Integer | Returned/bounced payment count (NACH RTN etc.) |
| `emi_debit_inr` | Integer | Existing EMI debits (leverage-stacking check) |
| `self_transfer_inr` | Integer | Detected self/circular transfers (fraud-padding check) |

---

## API 3 — EPFO Employer Insights *(optional / nice-to-have)*

No public lender-facing EPFO API exists today, so SHROFF currently
synthesizes this signal. If IDBI's sandbox can provide it, the fields we'd
consume are: `employees_epfo` (headcount), `wage_bill_inr`, and
`headcount_growth_pct` — feeding the stability sub-score. Not a blocker for
round 2; flagging in case it's already on IDBI's roadmap.

---

## API 4 — MCA Company & Director Master *(new ask — no sample provided yet)*

Powers SHROFF's PAN-spine entity graph — the check that catches a clean new
company backed by a struck-off/defaulter promoter ("phoenix fraud"). Today
this is seeded offline from public MCA/data.gov.in bulk data
(`ml/screening/`); requesting IDBI's own feed would let us corroborate or
replace that seed with sandbox-fresh data for the prototype demo.

### Request

| API Field Name | Field Type | Max Field Length | Mandatory/Optional | Sample Values | Description |
|---|---|---|---|---|---|
| pan | String | 10 | Mandatory | ABCPR3456K | Business or promoter PAN to resolve |
| cin | String | 21 | Optional | U51909DL2025PTC412345 | Corporate Identification Number, if known |

### Response

| API Response Field | Field Type | Description |
|---|---|---|
| `cin` | String(21) | Corporate Identification Number |
| `company_name` | String(150) | Registered company name |
| `company_status` | String(30) | Active / Struck Off / Under Liquidation / Under Process |
| `incorporated_on` | Date(10) | Date of incorporation |
| `registered_address_norm` | String(200) | Normalized registered address (for shared-address corroboration) |
| `directors` | Array | List of `{din, name, role, from_date, to_date}` for each current/past director |
| `co_director_companies` | Array | Other CINs each director is/was associated with (the graph-walk join) |

---

## API 5 — PAN/GSTIN Negative Registry / Watchlist *(new ask — no sample provided yet)*

Feeds the compliance-screening overlay (hard decline/refer trigger,
independent of the GBM score). SHROFF already has ~45,000 real rows seeded
from public sources (MahaGST, SEBI/NSE, CBDT, RBI, OpenSanctions — see
`ml/screening/SOURCES.md`); requesting IDBI's own watchlist feed keeps our
screening consistent with whatever source the bank considers authoritative
for the prototype/production path.

### Request

| API Field Name | Field Type | Max Field Length | Mandatory/Optional | Sample Values | Description |
|---|---|---|---|---|---|
| identifier_type | String | 10 | Mandatory | PAN, GSTIN, CIN, DIN | Which identifier is being screened |
| identifier_value | String | 21 | Mandatory | ABCPR3456K | The identifier value |

### Response

| API Response Field | Field Type | Description |
|---|---|---|
| `hit` | Boolean | Whether the identifier matched any list |
| `list_name` | String(100) | Which registry matched (e.g. "MahaGST non-genuine taxpayers") |
| `category` | String(50) | defaulter / debarred / struck-off / sanctioned / non-genuine |
| `confidence` | String(20) | high (ID match) / advisory (name-only match) |
| `matched_on` | String(20) | Which identifier field triggered the match |
| `source` | String(100) | Originating authority/list |

---

## Notes for the submission form

- API 1 (GSTN) can be wired in first — it's the closest match to what's
  already been provided and covers 3 of SHROFF's 4 sub-scores (growth,
  compliance, part of stability).
- API 2 (Bank/AA) is the one genuinely open ask that changes the model —
  without it, the cash-flow sub-score and the headline "GST-declared vs
  bank-verified" divergence check (SHROFF's core fraud-catching mechanism)
  stay on synthetic data.
- APIs 4 and 5 don't block the score itself — they upgrade the two
  *overlay* layers (entity graph, registry screening) from our own seeded
  data to IDBI-sourced data, which is a stronger prototype-phase story even
  though the pipeline already works end-to-end without them.
- All fields above already exist as named features in
  `ml/features/FEATURES.md` and the monthly schema in `CONTRACTS.md`, or map
  directly onto the existing screening schema in `CONTRACTS.md`'s registry
  tables — this is a mapping/adapter exercise, not new model design, so
  turnaround once credentials arrive should be fast.
