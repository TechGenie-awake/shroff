# SHROFF — Data Field Requirements submission (drafted)

For: "Action Required: Submit Data Field Requirements & Mentor Session Questions"
(`given/round-2/data-field-requirements-mail.txt`). Reference template:
`given/round-2/IDBI Innovate 2026_ Data Field Requirements.pdf`. **The email's "Submit Data
Fields & Mentor Questions" button didn't carry a URL into the pasted text — paste that link here
when you have it and I'll adapt this straight into the form.**

SHROFF needs four data feeds. IDBI's own sample covers GSTN in more granular detail than our
current pipeline consumes — the honest move is to request the fields we actually need (mapped
1:1 to `CONTRACTS.md`'s monthly schema and the 45 features in `ml/features/FEATURES.md`), not to
pad the ask. Three feeds below (AA bank statement, UPI, EPFO) aren't in IDBI's sample at all, so
they're drafted from scratch in the same Request/Response format.

---

## 1. GSTN — largely covered by IDBI's own sample; two additions requested

IDBI's sample response schema already supplies almost everything `cm_*`/`gr_gst_*`/`st_*` need:
`gross_turnover_current_month` → our `gst_turnover_declared_inr`; `gstr1_delay_days` /
`gstr3b_delay_days` → `gst_filing_delay_days`; `nil_return_count_12m` → `gst_nil_return`;
`b2b_taxable_turnover_12m` / `b2c_taxable_turnover_12m` → `b2b_share`; `top_1_customer_sales_pct` /
`top_5_customer_sales_pct` → `top1_buyer_share` / `top3_buyer_share` (need top-3, not top-5 — see
below).

**Confirm as sufficient**, with two specific asks:

| Ask | Why |
|---|---|
| **Per-counterparty breakdown** (`counterparty_gstin`, `counterparty_name`, monthly `share`) — not just the top-1/top-5 aggregate percentages in the sample | Our entity graph and supply-chain-concentration overlay (`ml/screening/graph.py`) walks named counterparty GSTINs against the negative registry — an aggregate percentage alone can't be graphed or screened |
| **`top_3_customer_sales_pct`** (the sample gives top-1 and top-5; we need top-3 specifically) | Matches `st_top3_buyer_share`, the feature actually trained and reported on the Health Card |

Everything else in IDBI's GSTN sample (ITC mismatch, credit-note ratio, invoice-count growth,
turnover-growth at multiple horizons) is **more granular than SHROFF currently models** — noted
as a welcome upgrade path for Pillar 1's feature engine post-sandbox, not a blocking request.

## 2. Account Aggregator — Bank Statement feed (FI Type: DEPOSIT)

Not present in IDBI's sample. Drafted in the same table format, one row per `msme_id` per month
(mirrors `CONTRACTS.md`'s monthly schema exactly — this is the request/response IDBI's sandbox
AA-simulation endpoint would need to return).

### Request

| API Field Name | Field Type | Max Field Length | Mandatory/Optional | Sample Values | Description |
|---|---|---|---|---|---|
| `consent_handle` | String | 50 | Mandatory | `AA-CONSENT-9f2b1e` | Sahamati/ReBIT consent artefact reference authorizing the pull |
| `account_ref` | String | 30 | Mandatory | `HDFC-SAV-77213` | AA-issued linked-account reference (masked account) |
| `period_from` | Date | 10 | Mandatory | `01-08-25` | Statement window start |
| `period_to` | Date | 10 | Mandatory | `31-07-26` | Statement window end |

### Response (one row per month)

| API Response Field Name | Field Type | Max Field Length | Sample Values | Description |
|---|---|---|---|---|
| `msme_id` | String | 20 | `RAMESH001` | Borrower identifier (join key) |
| `month` | String | 7 | `2026-07` | Statement month |
| `bank_inflow_inr` | Integer | 18,2 | 810000 | Total monthly bank credits |
| `bank_outflow_inr` | Integer | 18,2 | 742000 | Total monthly bank debits |
| `eod_balance_avg_inr` | Integer | 18,2 | 145000 | Mean end-of-day balance for the month |
| `eod_balance_min_inr` | Integer | 18,2 | 12000 | Minimum end-of-day balance for the month |
| `days_near_zero` | Integer | 2 | 3 | Days in the month balance stayed below a near-zero threshold |
| `bounce_count` | Integer | 2 | 1 | Count of RTN/NACH-returned debits or bounced cheques in the month |
| `emi_debit_inr` | Integer | 18,2 | 38000 | Total EMI/loan-repayment debits recognized in the statement |
| `self_transfer_inr` | Integer | 18,2 | 15000 | Own-account round-trip transfers (fraud-padding check) |
| `response_status` | String | 20 | `SUCCESS` | API processing result |
| `consent_reference` | String | 50 | `CONS_SYN_982731` | Consent/audit reference (mirrors IDBI's own sample field) |

## 3. UPI transaction feed (via AA transaction narration/channel code, or NPCI switch data)

| API Response Field Name | Field Type | Max Field Length | Sample Values | Description |
|---|---|---|---|---|
| `msme_id` | String | 20 | `RAMESH001` | Borrower identifier |
| `month` | String | 7 | `2026-07` | Transaction month |
| `upi_txn_count` | Integer | 6 | 214 | Count of UPI-channel credit transactions in the month |
| `upi_inflow_share` | Integer | 5,2 | 62.40 | UPI credits as a percentage of total bank inflow for the month |

## 4. EPFO — payroll/headcount feed

| API Field Name | Field Type | Max Field Length | Mandatory/Optional | Sample Values | Description |
|---|---|---|---|---|---|
| `establishment_id` | String | 20 | Mandatory | `MH/12345/001` | EPFO establishment code linked to the business |
| `period_from` | Date | 10 | Mandatory | `01-08-25` | Contribution window start |
| `period_to` | Date | 10 | Mandatory | `31-07-26` | Contribution window end |

| API Response Field Name | Field Type | Max Field Length | Sample Values | Description |
|---|---|---|---|---|
| `msme_id` | String | 20 | `RAMESH001` | Borrower identifier |
| `month` | String | 7 | `2026-07` | Contribution month |
| `employees_epfo` | Integer | 6 | 18 | Active EPFO-contributing headcount for the month |
| `wage_bill_inr` | Integer | 18,2 | 412000 | Aggregate monthly wage bill against which EPFO contributions were computed |
| `establishment_status` | String | 20 | `Active` | EPFO establishment registration status |

---

## Mentor-session questions (3, per the same email's ask)

1. **Real-vs-synthetic GST granularity:** IDBI's own GSTN sample schema (ITC mismatch, credit-note
   ratio, customer-concentration index, multi-horizon turnover growth) is materially richer than
   what our current 45-feature engine consumes. Should we retrain Pillar 1 against this full
   granularity before the sandbox data lands, or is the coarser monthly aggregate (declared
   turnover, filing punctuality, buyer concentration) the intended level for this track?
2. **AA/EPFO sandbox availability and shape:** will the sandbox's Account Aggregator simulation
   and EPFO feed match the FI-type/consent-handle shape in the Sahamati ReBIT spec exactly, or a
   bank-internal simplified schema — and is per-counterparty GSTIN-level detail (not just
   aggregate concentration percentages) available for entity-graph / negative-registry screening?
3. **Negative-registry and PAN/DIN data in the sandbox:** does IDBI's sandbox expose (or plan to
   expose) any internal watchlist, struck-off-company, or director-disqualification feed we could
   validate our own ~45,000-row public-registry screening layer against — or should that layer
   stay sourced entirely from public data (MahaGST, SEBI/NSE, CBDT, RBI, OpenSanctions, MCA) for
   this phase?
