/**
 * SHROFF — contract-exact fixtures for the three demo personas.
 * Used automatically whenever the ML API at NEXT_PUBLIC_ML_API is unreachable,
 * so the demo never breaks. Shapes mirror CONTRACTS.md ScoreResponse EXACTLY.
 */

import type {
  ConsentArtefact,
  GraphResponse,
  HealthResponse,
  LoanTypeInfo,
  MonthlyRow,
  MsmeResponse,
  OcenOffer,
  Persona,
  RailsResponse,
  ScoreResponse,
  ScreenResponse,
  ScreeningHit,
} from "./types";

/* ────────────────────────── helpers ────────────────────────── */

/** i = 0 → 2024-07 … i = 23 → 2026-06 (24 months ending 2026-06). */
function ym24(i: number): string {
  const y = 2024 + Math.floor((6 + i) / 12);
  const m = ((6 + i) % 12) + 1;
  return `${y}-${String(m).padStart(2, "0")}`;
}

/** i = 0 → 2025-05 … i = 13 → 2026-06 (Nexon's 14 months of history). */
function ym14(i: number): string {
  const y = 2025 + Math.floor((4 + i) / 12);
  const m = ((4 + i) % 12) + 1;
  return `${y}-${String(m).padStart(2, "0")}`;
}

const r1k = (n: number) => Math.round(n / 1000) * 1000;

function makeConsent(
  vua: string,
  suffix: string,
  from: string,
  to: string
): ConsentArtefact {
  return {
    ver: "2.0.0",
    txnid: `txn-shroff-${suffix}`,
    consentId: `cons-${suffix}-9f2a`,
    status: "ACTIVE",
    createTimestamp: "2026-06-28T10:15:00.000Z",
    consentStart: "2026-06-28T10:15:00.000Z",
    consentExpiry: "2026-12-28T10:15:00.000Z",
    consentMode: "STORE",
    fetchType: "PERIODIC",
    consentTypes: ["PROFILE", "SUMMARY", "TRANSACTIONS"],
    fiTypes: ["DEPOSIT", "GSTR1_3B"],
    DataConsumer: { id: "IDBI-FIU-SHROFF-001", type: "FIU" },
    Customer: { id: vua },
    Purpose: {
      code: "103",
      refUri: "https://api.rebit.org.in/aa/purpose/103.xml",
      text: "Aggregated statement for MSME loan underwriting",
      Category: { type: "Financial Reporting" },
    },
    FIDataRange: { from: `${from}-01T00:00:00.000Z`, to: `${to}-30T23:59:59.000Z` },
    DataLife: { unit: "MONTH", value: 6 },
    Frequency: { unit: "MONTH", value: 1 },
  };
}

/* ────────────────────────── health ────────────────────────── */

export const healthFixture: HealthResponse = {
  status: "ok",
  model_version: "v1",
  artifacts_loaded: true,
};

export const loanTypesFixture: LoanTypeInfo[] = [
  {
    id: "working_capital",
    label: "Working Capital / Cash Credit",
    implemented: true,
    sizing_rule:
      "20% of annualized bank-verified turnover (Nayak Committee norm) \u00d7 band factor",
  },
  {
    id: "term_loan",
    label: "Term Loan (equipment / expansion)",
    implemented: true,
    sizing_rule:
      "DSCR-based: free cash flow \u00f7 band DSCR requirement \u2192 max EMI \u2192 present-valued over a longer tenure at a band test rate",
  },
  {
    id: "invoice_discounting",
    label: "Invoice / Bill Discounting (TReDS-style)",
    implemented: false,
    sizing_rule:
      "Not yet built \u2014 would size against a specific invoice's value and the buyer's own creditworthiness, not the borrower's turnover",
  },
  {
    id: "trade_finance",
    label: "Trade Finance (import/export)",
    implemented: false,
    sizing_rule: "Not yet built \u2014 would size against LC/shipment value and trade-cycle length",
  },
];

/* ────────────────────────── personas ────────────────────────── */

export const personasFixture: Persona[] = [
  {
    id: "RAMESH001",
    name: "Ramesh Kumar",
    business: "Ramesh Kirana & General Stores",
    city: "Pune",
    segment: "Retail trade · proprietorship",
    requested_amount_inr: 1500000,
    blurb:
      "No credit history, no collateral — but 24 months of clean bank + GST cash flow. The invisible-but-healthy borrower.",
  },
  {
    id: "SURESH002",
    name: "Suresh Mehta",
    business: "Suresh Trading Co.",
    city: "Mumbai",
    segment: "Wholesale trade · proprietorship",
    requested_amount_inr: 1000000,
    blurb:
      "Clean on paper. But declared GST turnover runs 40% above bank inflows, receipts are sliding, and cheques are bouncing.",
  },
  {
    id: "PHOENIX003",
    name: "Vikram Malhotra",
    business: "Nexon Trading Pvt Ltd",
    city: "Delhi",
    segment: "Trading company · 14 months old",
    requested_amount_inr: 2000000,
    blurb:
      "A tidy thin file the score alone would pass. The entity graph walks promoter DIN to a struck-off shell at the same address.",
  },
];

/* ────────────────────────── monthly series ────────────────────────── */

/** RAMESH001 — ~₹8L/mo growing ~1.5%/mo, GST ≈ bank ±5%, spotless conduct. */
const rameshMonthly: MonthlyRow[] = Array.from({ length: 24 }, (_, i) => {
  const festive = i === 3 || i === 4 || i === 15 || i === 16 ? 1.08 : 1; // Oct–Nov
  const inflow = r1k(680000 * Math.pow(1.015, i) * festive * (1 + 0.018 * Math.sin(i * 2.1)));
  const declared = r1k(inflow * (1 + 0.035 * Math.sin(i * 1.3)));
  return {
    msme_id: "RAMESH001",
    month: ym24(i),
    bank_inflow_inr: inflow,
    bank_outflow_inr: r1k(inflow * 0.93),
    eod_balance_avg_inr: r1k(182000 + i * 4200),
    eod_balance_min_inr: r1k(61000 + i * 1500),
    days_near_zero: 0,
    upi_txn_count: 1380 + i * 22,
    upi_inflow_share: Number((0.75 + 0.015 * Math.sin(i)).toFixed(2)),
    bounce_count: 0,
    emi_debit_inr: 18000,
    self_transfer_inr: 0,
    gst_turnover_declared_inr: declared,
    gst_filed_on_time: i === 7 ? 0 : 1, // one late month (2025-02) → 23/24 on time
    gst_filing_delay_days: i === 7 ? 9 : 0,
    gst_nil_return: 0,
    b2b_share: 0.35,
    top3_buyer_share: 0.55,
    employees_epfo: 4,
    wage_bill_inr: 72000,
  };
});

/**
 * SURESH002 — the divergence money-shot. Bank inflows slide ~28% in the last
 * two quarters while GST-declared turnover stays ~₹13.3L/mo (≈40% above bank).
 * 3 bounces in the last quarter, 2 late GST filings, 1 nil return, visible
 * self-transfer round-tripping.
 */
const sureshMonthly: MonthlyRow[] = Array.from({ length: 24 }, (_, i) => {
  const inflow =
    i < 18
      ? r1k(960000 * (1 - 0.004 * i) * (1 + 0.02 * Math.sin(i * 1.7)))
      : r1k(900000 * (1 - 0.055 * (i - 17)));
  const isNil = i === 5; // 2024-12 nil return
  const declared = isNil ? 0 : r1k(1305000 * (1 + 0.02 * Math.sin(i * 0.9)));
  const late = i === 21 || i === 22; // 2026-04, 2026-05
  const lastQ = i >= 21;
  return {
    msme_id: "SURESH002",
    month: ym24(i),
    bank_inflow_inr: inflow,
    bank_outflow_inr: r1k(inflow * (i >= 18 ? 1.02 : 0.97)),
    eod_balance_avg_inr: r1k(Math.max(28000, 142000 - i * 4800)),
    eod_balance_min_inr: r1k(Math.max(1200, 24000 - i * 1000)),
    days_near_zero: i >= 18 ? (i - 17) + 2 : i >= 12 ? 1 : 0,
    upi_txn_count: 430 - i * 6,
    upi_inflow_share: Number((0.31 + 0.01 * Math.sin(i)).toFixed(2)),
    bounce_count: lastQ ? 1 : 0, // 3 bounces in the last quarter
    emi_debit_inr: 42000,
    self_transfer_inr: r1k(185000 * (1 + 0.05 * Math.sin(i * 2.3))),
    gst_turnover_declared_inr: declared,
    gst_filed_on_time: late || isNil ? 0 : 1,
    gst_filing_delay_days: i === 21 ? 18 : i === 22 ? 26 : 0,
    gst_nil_return: isNil ? 1 : 0,
    b2b_share: 0.82,
    top3_buyer_share: 0.78,
    employees_epfo: 5,
    wage_bill_inr: 90000,
  };
});

/** PHOENIX003 — 14 clean, modest months since incorporation (May 2025). */
const phoenixMonthly: MonthlyRow[] = Array.from({ length: 14 }, (_, i) => {
  const inflow = r1k(440000 * Math.pow(1.028, i) * (1 + 0.015 * Math.sin(i * 1.4)));
  const declared = r1k(inflow * (1 + 0.012 * Math.sin(i * 1.1)));
  return {
    msme_id: "PHOENIX003",
    month: ym14(i),
    bank_inflow_inr: inflow,
    bank_outflow_inr: r1k(inflow * 0.9),
    eod_balance_avg_inr: r1k(95000 + i * 7200),
    eod_balance_min_inr: r1k(32000 + i * 2100),
    days_near_zero: i < 2 ? 1 : 0,
    upi_txn_count: 96 + i * 9,
    upi_inflow_share: Number((0.42 + 0.01 * Math.sin(i)).toFixed(2)),
    bounce_count: 0,
    emi_debit_inr: 0,
    self_transfer_inr: 0,
    gst_turnover_declared_inr: declared,
    gst_filed_on_time: 1,
    gst_filing_delay_days: 0,
    gst_nil_return: 0,
    b2b_share: 0.9,
    top3_buyer_share: 0.48,
    employees_epfo: 3,
    wage_bill_inr: 54000,
  };
});

/* ────────────────────────── /api/msme/{id} ────────────────────────── */

export const msmeFixtures: Record<string, MsmeResponse> = {
  RAMESH001: {
    profile: {
      msme_id: "RAMESH001",
      name: "Ramesh Kirana & General Stores",
      legal_name: "Ramesh Kumar (Proprietor)",
      entity_type: "Proprietorship",
      sector: "Retail trade — groceries & general stores",
      city: "Pune",
      state_code: "27",
      pan: "ABCPR3456K",
      gstin: "27ABCPR3456K1Z5",
      cin: null,
      promoter_name: "Ramesh Kumar",
      promoter_pan: "ABCPR3456K",
      promoter_din: null,
      udyam: "UDYAM-MH-26-0012345",
      incorporated_on: "2015-04-11",
      requested_amount_inr: 1500000,
    },
    consent: makeConsent("ramesh.kirana@onemoney", "ramesh001", "2024-07", "2026-06"),
    monthly: rameshMonthly,
  },
  SURESH002: {
    profile: {
      msme_id: "SURESH002",
      name: "Suresh Trading Co.",
      legal_name: "Suresh Mehta (Proprietor)",
      entity_type: "Proprietorship",
      sector: "Wholesale trade — textiles & fabrics",
      city: "Mumbai",
      state_code: "27",
      pan: "AKLPM8765D",
      gstin: "27AKLPM8765D1Z3",
      cin: null,
      promoter_name: "Suresh Mehta",
      promoter_pan: "AKLPM8765D",
      promoter_din: null,
      udyam: "UDYAM-MH-18-0067890",
      incorporated_on: "2012-09-03",
      requested_amount_inr: 1000000,
    },
    consent: makeConsent("suresh.trading@onemoney", "suresh002", "2024-07", "2026-06"),
    monthly: sureshMonthly,
  },
  PHOENIX003: {
    profile: {
      msme_id: "PHOENIX003",
      name: "Nexon Trading Pvt Ltd",
      legal_name: "Nexon Trading Private Limited",
      entity_type: "Private Limited Company",
      sector: "Trading — electronics & components",
      city: "Delhi",
      state_code: "07",
      pan: "AAECN1234F",
      gstin: "07AAECN1234F1Z2",
      cin: "U51909DL2025PTC412345",
      promoter_name: "Vikram Malhotra",
      promoter_pan: "AEXPM4521C",
      promoter_din: "08234567",
      udyam: "UDYAM-DL-06-0098765",
      incorporated_on: "2025-05-02",
      requested_amount_inr: 2000000,
    },
    consent: makeConsent("nexon.trading@onemoney", "phoenix003", "2025-05", "2026-06"),
    monthly: phoenixMonthly,
  },
};

/* ────────────────────────── screening hits ────────────────────────── */

const vertexStruckOffHit: ScreeningHit = {
  registry: "negreg_company_status",
  list_name: "MCA struck-off companies (ROC Delhi)",
  matched_on: "CIN U74999DL2019PTC356789 — Vertex Impex Pvt Ltd, linked via promoter DIN 08234567",
  confidence: "high",
  detail:
    "Vertex Impex Pvt Ltd was struck off in May 2025. Promoter Vikram Malhotra (DIN 08234567) served as its co-director from 2019 until strike-off. Nexon Trading was incorporated the same month at the same normalized registered address.",
  source_url: "https://www.mca.gov.in/",
  is_sample: true,
};

const vertexWilfulHit: ScreeningHit = {
  registry: "negreg_name",
  list_name: "Wilful defaulter list (suit-filed accounts, name match)",
  matched_on: "VERTEX IMPEX PRIVATE LIMITED",
  confidence: "advisory",
  detail:
    "Name-only match: an entity named Vertex Impex Private Limited appears on the wilful-defaulter (suit-filed) list. Advisory strength — name matches are not identifier-verified.",
  source_url: "https://www.watchoutinvestors.com/",
  is_sample: true,
};

const rakeshDinHit: ScreeningHit = {
  registry: "negreg_din",
  list_name: "Directors of struck-off companies",
  matched_on: "DIN 07654321 — Rakesh Sharma, co-director at Vertex Impex Pvt Ltd",
  confidence: "high",
  detail:
    "Rakesh Sharma (DIN 07654321) is listed as a director of a struck-off company. He co-directed Vertex Impex alongside the applicant's promoter Vikram Malhotra.",
  source_url: "https://www.mca.gov.in/",
  is_sample: true,
};

const tridentGstinHit: ScreeningHit = {
  registry: "negreg_gstin",
  list_name: "Maharashtra GST non-genuine taxpayers",
  matched_on: "GSTIN 27AABCT5678Q1Z9 — Trident Textiles",
  confidence: "high",
  detail:
    "The applicant's largest buyer, Trident Textiles (41% of receipts), appears on the Maharashtra GST department's non-genuine taxpayer list.",
  source_url: "https://www.mahagst.gov.in/",
  is_sample: true,
};

/* ────────────────────────── /api/score ────────────────────────── */

const IMPACT_SOURCES = [
  {
    claim: "Physical field/address-verification visit",
    source: "SalaryBox — Background Verification Cost in India, 2026",
    range_inr: [500, 1500],
  },
  {
    claim: "Traditional MSME onboarding (physical meeting + document collection)",
    source: "MSME digital-lending acquisition-cost research (The Digital Fifth / Dvara)",
    range_usd: [70, 200],
    converted_inr_at: 83.0,
  },
];

const IMPACT_CLEARED: ScoreResponse["bank_impact"] = {
  auto_cleared: true,
  field_verification_saved_inr: [500, 1500],
  onboarding_cost_saved_inr: [5810, 16600],
  basis:
    "Deterministic registry screening + AA-consented data cleared this application without a manual field-verification visit or a physical document-collection cycle — subject to IDBI's own KYC/compliance policy confirming which case classes still require an in-person check.",
  sources: IMPACT_SOURCES,
  honest_caveat:
    "These are cited industry-benchmark ranges, not IDBI's own measured cost. Replacing this with IDBI's real per-application onboarding and field-verification cost is one of our sandbox-access data asks.",
};

const IMPACT_FLAGGED: ScoreResponse["bank_impact"] = {
  auto_cleared: false,
  field_verification_saved_inr: [0, 0],
  onboarding_cost_saved_inr: [0, 0],
  basis:
    "A deterministic overlay flagged this application for manual review — no automation savings are claimed here; routing this to a human reviewer is the correct, intended outcome, not a system failure.",
  sources: IMPACT_SOURCES,
  honest_caveat:
    "These are cited industry-benchmark ranges, not IDBI's own measured cost. Replacing this with IDBI's real per-application onboarding and field-verification cost is one of our sandbox-access data asks.",
};

export const scoreFixtures: Record<string, ScoreResponse> = {
  RAMESH001: {
    msme_id: "RAMESH001",
    name: "Ramesh Kirana & General Stores",
    score: 782,
    band: "A",
    pd_12m: 0.021,
    sub_scores: { cash_flow: 84, growth: 71, stability: 76, compliance: 88 },
    decision: {
      verdict: "APPROVE",
      amount_inr: 1200000,
      tenure_months: 24,
      loan_type: "working_capital",
      rationale:
        "20% working-capital norm on ₹92.3L bank-verified annual turnover at band-A factor 0.65 supports ₹12.0L against ₹15.0L requested.",
    },
    reasons: [
      {
        code: "CF-01",
        group: "cash_flow",
        direction: "positive",
        text: "Consistent bank inflows averaging ₹8.1L/month with 24-month history",
        value: "₹8.1L/mo",
        shap: 0.42,
      },
      {
        code: "CO-02",
        group: "compliance",
        direction: "positive",
        text: "GST filed on time 23 of 24 months; declared turnover within 4% of bank inflows",
        value: "23/24 on-time",
        shap: 0.31,
      },
      {
        code: "GR-01",
        group: "growth",
        direction: "positive",
        text: "Steady inflow growth of ~1.5% month-on-month across two festive cycles",
        value: "+1.5%/mo",
        shap: 0.22,
      },
      {
        code: "ST-02",
        group: "stability",
        direction: "positive",
        text: "Zero payment bounces and zero near-zero balance days across 24 months",
        value: "0 bounces",
        shap: 0.18,
      },
      {
        code: "ST-05",
        group: "stability",
        direction: "negative",
        text: "Top-3 buyer concentration at 55% of receipts — mild, advisory only",
        value: "55%",
        shap: -0.12,
      },
    ],
    overlays: {
      screening: { checked: true, hits: [], phoenix_flag: false },
      early_warning: { level: "green", triggers: [] },
      supply_chain: { top3_buyer_share: 0.55, distressed_counterparties: [] },
    },
    model: { version: "v1", auc: 0.874, ks: 0.516, trained_on: "synthetic-v1" },
    bank_impact: IMPACT_CLEARED,
  },

  SURESH002: {
    msme_id: "SURESH002",
    name: "Suresh Trading Co.",
    score: 421,
    band: "D",
    pd_12m: 0.34,
    sub_scores: { cash_flow: 31, growth: 22, stability: 28, compliance: 18 },
    decision: {
      verdict: "DECLINE",
      amount_inr: 0,
      tenure_months: 0,
      loan_type: "working_capital",
      rationale:
        "Band D with red early-warning status falls below the lending threshold; GST-declared turnover diverges +40% from bank-verified inflows, failing the cross-verification check.",
    },
    reasons: [
      {
        code: "CO-03",
        group: "compliance",
        direction: "negative",
        text: "GST-declared turnover runs ~40% above bank-verified inflows — divergence indicates inflated declared sales or undisclosed cash routing",
        value: "+40% divergence",
        shap: -0.58,
      },
      {
        code: "CF-04",
        group: "cash_flow",
        direction: "negative",
        text: "Bank inflows declined 28% over the last two quarters against the trailing baseline",
        value: "−28% / 6mo",
        shap: -0.44,
      },
      {
        code: "ST-03",
        group: "stability",
        direction: "negative",
        text: "3 inward cheque/NACH bounces in the last 90 days",
        value: "3 bounces",
        shap: -0.29,
      },
      {
        code: "CF-06",
        group: "cash_flow",
        direction: "negative",
        text: "Recurring self-transfers averaging ₹1.85L/month suggest round-tripping to pad inflows",
        value: "₹1.85L/mo",
        shap: -0.21,
      },
      {
        code: "CF-09",
        group: "cash_flow",
        direction: "positive",
        text: "UPI collections remain steady at ~₹2.9L/month, showing a genuine retail receipt base",
        value: "₹2.9L/mo",
        shap: 0.09,
      },
    ],
    overlays: {
      screening: { checked: true, hits: [], phoenix_flag: false },
      early_warning: {
        level: "red",
        triggers: [
          "Bank inflows down 28% in the last quarter versus the trailing 9-month average",
          "3 inward cheque/NACH bounces within the last 90 days",
          "GST late-filing streak — 2 consecutive delayed returns (Apr & May 2026), one nil return on record",
        ],
      },
      supply_chain: {
        top3_buyer_share: 0.78,
        distressed_counterparties: [
          {
            gstin: "27AABCT5678Q1Z9",
            name: "Trident Textiles",
            share: 0.41,
            registry: "negreg_gstin",
            list_name: "Maharashtra GST non-genuine taxpayers",
            is_sample: true,
          },
        ],
      },
    },
    model: { version: "v1", auc: 0.874, ks: 0.516, trained_on: "synthetic-v1" },
    bank_impact: IMPACT_FLAGGED,
  },

  PHOENIX003: {
    msme_id: "PHOENIX003",
    name: "Nexon Trading Pvt Ltd",
    score: 656,
    band: "C",
    pd_12m: 0.052,
    sub_scores: { cash_flow: 68, growth: 61, stability: 44, compliance: 79 },
    decision: {
      verdict: "REFER",
      amount_inr: 400000,
      tenure_months: 12,
      loan_type: "working_capital",
      rationale:
        "Registry overlay forces manual referral — promoter DIN links to struck-off Vertex Impex at a shared address (phoenix pattern); eligible exposure capped at ₹4.0L under the 20% working-capital norm at band C pending review.",
    },
    reasons: [
      {
        code: "CO-11",
        group: "compliance",
        direction: "positive",
        text: "GST filed on time in all 14 months since incorporation; declared turnover matches bank inflows",
        value: "14/14 on-time",
        shap: 0.34,
      },
      {
        code: "ST-06",
        group: "stability",
        direction: "negative",
        text: "Thin file — 14 months of operating history against the 24-month underwriting norm",
        value: "14 months",
        shap: -0.31,
      },
      {
        code: "CF-08",
        group: "cash_flow",
        direction: "positive",
        text: "Positive net cash flow in every month since inception, average ₹5.3L/month inflows",
        value: "₹5.3L/mo",
        shap: 0.27,
      },
      {
        code: "GR-04",
        group: "growth",
        direction: "positive",
        text: "Inflows grew ~37% since incorporation on a rising balance base",
        value: "+37% / 14mo",
        shap: 0.19,
      },
    ],
    overlays: {
      screening: {
        checked: true,
        hits: [vertexStruckOffHit, rakeshDinHit, vertexWilfulHit],
        phoenix_flag: true,
      },
      early_warning: { level: "green", triggers: [] },
      supply_chain: { top3_buyer_share: 0.48, distressed_counterparties: [] },
    },
    model: { version: "v1", auc: 0.874, ks: 0.516, trained_on: "synthetic-v1" },
    bank_impact: IMPACT_FLAGGED,
  },
};

/* ────────────────────────── /api/graph/{pan} ────────────────────────── */

export const graphFixtures: Record<string, GraphResponse> = {
  // RAMESH001 — clean proprietorship graph
  ABCPR3456K: {
    nodes: [
      { id: "27ABCPR3456K1Z5", type: "gstin", label: "GSTIN 27ABCPR3456K1Z5", flag: null },
      { id: "ABCPR3456K", type: "pan", label: "PAN ABCPR3456K · Ramesh Kumar", flag: null },
      { id: "ADDR-LAXMI-PUNE", type: "address", label: "Shop 4, Laxmi Road, Pune 411030", flag: null },
    ],
    edges: [
      { source: "27ABCPR3456K1Z5", target: "ABCPR3456K", relation: "embeds PAN (chars 3–12)" },
      { source: "ABCPR3456K", target: "ADDR-LAXMI-PUNE", relation: "principal place of business" },
    ],
    phoenix_flag: false,
    narrative:
      "No adverse linkages found. The GSTIN resolves to proprietor PAN ABCPR3456K with a single registered place of business and no connected companies, directors, or flagged counterparties across the negative registries.",
  },

  // SURESH002 — own identifiers clean; largest buyer flagged non-genuine
  AKLPM8765D: {
    nodes: [
      { id: "27AKLPM8765D1Z3", type: "gstin", label: "GSTIN 27AKLPM8765D1Z3", flag: null },
      { id: "AKLPM8765D", type: "pan", label: "PAN AKLPM8765D · Suresh Mehta", flag: null },
      { id: "27AABCT5678Q1Z9", type: "gstin", label: "GSTIN 27AABCT5678Q1Z9 · Trident Textiles", flag: "non_genuine" },
      { id: "ADDR-KALBADEVI-MUM", type: "address", label: "212 Kalbadevi Road, Mumbai 400002", flag: null },
    ],
    edges: [
      { source: "27AKLPM8765D1Z3", target: "AKLPM8765D", relation: "embeds PAN (chars 3–12)" },
      { source: "AKLPM8765D", target: "ADDR-KALBADEVI-MUM", relation: "principal place of business" },
      { source: "27AKLPM8765D1Z3", target: "27AABCT5678Q1Z9", relation: "largest buyer — 41% of receipts" },
    ],
    phoenix_flag: false,
    narrative:
      "The borrower's own identifiers are clean across all registries. However, his largest buyer — Trident Textiles, 41% of receipts — sits on the Maharashtra GST non-genuine taxpayer list, concentrating collection risk in a distressed counterparty.",
  },

  // PHOENIX003 — the phoenix walk: Nexon → Vikram → Vertex (struck off) + Rakesh + shared address
  AAECN1234F: {
    nodes: [
      { id: "07AAECN1234F1Z2", type: "gstin", label: "GSTIN 07AAECN1234F1Z2", flag: null },
      { id: "AAECN1234F", type: "pan", label: "PAN AAECN1234F · Nexon Trading", flag: null },
      { id: "U51909DL2025PTC412345", type: "company", label: "Nexon Trading Pvt Ltd · inc. May 2025", flag: null },
      { id: "08234567", type: "din", label: "Vikram Malhotra · DIN 08234567", flag: null },
      { id: "U74999DL2019PTC356789", type: "company", label: "Vertex Impex Pvt Ltd · STRUCK OFF May 2025", flag: "struck_off" },
      { id: "07654321", type: "din", label: "Rakesh Sharma · DIN 07654321", flag: "director_of_struck_off" },
      { id: "ADDR-KAROL-BAGH", type: "address", label: "14 Karol Bagh Industrial Area, Delhi 110005 — shared address", flag: null },
    ],
    edges: [
      { source: "07AAECN1234F1Z2", target: "AAECN1234F", relation: "embeds PAN (chars 3–12)" },
      { source: "AAECN1234F", target: "U51909DL2025PTC412345", relation: "PAN of company" },
      { source: "08234567", target: "U51909DL2025PTC412345", relation: "director (2025–)" },
      { source: "08234567", target: "U74999DL2019PTC356789", relation: "director (2019–2025)" },
      { source: "07654321", target: "U74999DL2019PTC356789", relation: "co-director (2019–2025)" },
      { source: "U51909DL2025PTC412345", target: "ADDR-KAROL-BAGH", relation: "registered at" },
      { source: "U74999DL2019PTC356789", target: "ADDR-KAROL-BAGH", relation: "registered at" },
    ],
    phoenix_flag: true,
    narrative:
      "Phoenix pattern: Nexon Trading Pvt Ltd (incorporated May 2025) is promoted by Vikram Malhotra (DIN 08234567), who until May 2025 co-directed Vertex Impex Pvt Ltd with Rakesh Sharma (DIN 07654321). Vertex was struck off that same month, appears on the wilful-defaulter name list, and Rakesh's DIN is flagged as director-of-struck-off. Nexon and Vertex share the same normalized registered address at 14 Karol Bagh Industrial Area, Delhi — the new entity rises exactly where the old one burned down.",
  },
};

/** Map msme_id → the PAN used for the entity-graph walk. */
export const graphPanByMsme: Record<string, string> = {
  RAMESH001: "ABCPR3456K",
  SURESH002: "AKLPM8765D",
  PHOENIX003: "AAECN1234F",
};

/* ────────────────────────── /api/screen ────────────────────────── */

const screenHitMap: Record<string, ScreeningHit[]> = {
  "gstin:27AABCT5678Q1Z9": [tridentGstinHit],
  "cin:U74999DL2019PTC356789": [vertexStruckOffHit],
  "din:07654321": [rakeshDinHit],
  "din:08234567": [vertexStruckOffHit],
  "name:VERTEX IMPEX PRIVATE LIMITED": [vertexWilfulHit],
};

export function screenFixture(type: string, value: string): ScreenResponse {
  const key = `${type}:${value.trim().toUpperCase()}`;
  return {
    query: { type: type as ScreenResponse["query"]["type"], value },
    hits: screenHitMap[key] ?? [],
  };
}

export const ocenFixtures: Record<string, OcenOffer> = {
  "RAMESH001": {
    "ocenVersion": "4.0.0-aligned",
    "rail": "OCEN",
    "generatedAt": "2026-07-11T09:00:00+00:00",
    "loanApplicationId": "LA-RAMESH001",
    "borrower": {
      "vua": "ABCPR3456K@shroff",
      "pan": "ABCPR3456K",
      "name": "Ramesh Kirana & General Stores"
    },
    "creditAssessment": {
      "assessmentProvider": "SHROFF",
      "healthScore": 769,
      "band": "A",
      "pd12m": 0.0182,
      "modelVersion": "v1",
      "dataSources": [
        "AA:DEPOSIT",
        "AA:GSTR1_3B",
        "EPFO:ECR"
      ],
      "consentPurposeCode": "103",
      "reasonCodes": [
        {
          "code": "CM-06",
          "direction": "positive",
          "text": "GST-declared turnover diverges from bank inflows by 1%"
        },
        {
          "code": "CF-06",
          "direction": "positive",
          "text": "Average bank balance grew 48% between first and last six months"
        },
        {
          "code": "CF-10",
          "direction": "positive",
          "text": "Account near zero 0.0 days per month on average"
        }
      ]
    },
    "loanOffer": {
      "offerId": "OFR-RAMESH001-20260711",
      "status": "APPROVED",
      "sanctionedAmount": {
        "value": 1250000,
        "currency": "INR"
      },
      "rationale": "20% working-capital norm (Nayak committee) on ₹96.8L annualized bank-verified turnover × 0.65 band-A factor → eligible ₹12.6L; sanction = min(requested ₹15.0L, eligible) = ₹12.5L over 36 months; 2 advisory name match(es) flagged for manual disposition (not verdict-affecting).",
      "interestRate": {
        "value": 13.77,
        "type": "REDUCING_BALANCE",
        "unit": "PERCENT_PER_ANNUM"
      },
      "tenure": {
        "value": 36,
        "unit": "MONTHS"
      },
      "emi": {
        "value": 42583,
        "currency": "INR"
      },
      "processingFee": {
        "value": 12500,
        "currency": "INR"
      },
      "totalInterestPayable": {
        "value": 282988,
        "currency": "INR"
      },
      "validUpto": "2026-08-10"
    }
  },
  "SURESH002": {
    "ocenVersion": "4.0.0-aligned",
    "rail": "OCEN",
    "generatedAt": "2026-07-11T09:00:00+00:00",
    "loanApplicationId": "LA-SURESH002",
    "borrower": {
      "vua": "AKLPM8765D@shroff",
      "pan": "AKLPM8765D",
      "name": "Suresh Trading Co."
    },
    "creditAssessment": {
      "assessmentProvider": "SHROFF",
      "healthScore": 419,
      "band": "E",
      "pd12m": 0.3485,
      "modelVersion": "v1",
      "dataSources": [
        "AA:DEPOSIT",
        "AA:GSTR1_3B",
        "EPFO:ECR"
      ],
      "consentPurposeCode": "103",
      "reasonCodes": [
        {
          "code": "CM-06",
          "direction": "negative",
          "text": "GST-declared turnover diverges from bank inflows by 37%"
        },
        {
          "code": "CF-05",
          "direction": "negative",
          "text": "Average balance covers 12% of a typical month's outflows"
        },
        {
          "code": "GR-07",
          "direction": "negative",
          "text": "EPFO headcount shrank 22% over the observed period"
        }
      ]
    },
    "loanOffer": {
      "offerId": "OFR-SURESH002-20260711",
      "status": "REJECTED",
      "sanctionedAmount": {
        "value": 0,
        "currency": "INR"
      },
      "rationale": "Band E yields no working-capital eligibility under the 20% turnover norm (Nayak committee): early-warning red.",
      "rejectionReason": "Band E yields no working-capital eligibility under the 20% turnover norm (Nayak committee): early-warning red."
    }
  },
  "PHOENIX003": {
    "ocenVersion": "4.0.0-aligned",
    "rail": "OCEN",
    "generatedAt": "2026-07-11T09:00:00+00:00",
    "loanApplicationId": "LA-PHOENIX003",
    "borrower": {
      "vua": "AAECN1234F@shroff",
      "pan": "AAECN1234F",
      "name": "Nexon Trading Pvt Ltd"
    },
    "creditAssessment": {
      "assessmentProvider": "SHROFF",
      "healthScore": 678,
      "band": "C",
      "pd12m": 0.0425,
      "modelVersion": "v1",
      "dataSources": [
        "AA:DEPOSIT",
        "AA:GSTR1_3B",
        "EPFO:ECR"
      ],
      "consentPurposeCode": "103",
      "reasonCodes": [
        {
          "code": "CF-05",
          "direction": "negative",
          "text": "Average balance covers 9% of a typical month's outflows"
        },
        {
          "code": "CM-06",
          "direction": "positive",
          "text": "GST-declared turnover diverges from bank inflows by 0%"
        },
        {
          "code": "CF-07",
          "direction": "negative",
          "text": "Minimum monthly balance holds at 2% of monthly outflows"
        }
      ]
    },
    "loanOffer": {
      "offerId": "OFR-PHOENIX003-20260711",
      "status": "PENDING_MANUAL_REVIEW",
      "sanctionedAmount": {
        "value": 300000,
        "currency": "INR"
      },
      "rationale": "20% working-capital norm (Nayak committee) on ₹47.8L annualized bank-verified turnover × 0.30 band-C factor → eligible ₹2.9L; sanction = min(requested ₹20.0L, eligible) = ₹3.0L over 12 months; entity-graph phoenix flag — promoter network reaches VERTEX IMPEX PRIVATE LIMITED · U74999DL2019PTC356789 — wilful defaulter on the negative registry; RAKESH SHARMA · DIN 07654321 — director of struck off on the negative registry.",
      "interestRate": {
        "value": 18.14,
        "type": "REDUCING_BALANCE",
        "unit": "PERCENT_PER_ANNUM"
      },
      "tenure": {
        "value": 12,
        "unit": "MONTHS"
      },
      "emi": {
        "value": 27524,
        "currency": "INR"
      },
      "processingFee": {
        "value": 3000,
        "currency": "INR"
      },
      "totalInterestPayable": {
        "value": 30288,
        "currency": "INR"
      },
      "validUpto": "2026-08-10",
      "reviewNote": "Deterministic overlay flagged this application — manual disposition required before disbursal."
    }
  }
};

export const railsFixture: RailsResponse = {
  "rails": [
    {
      "rail": "Account Aggregator (AA)",
      "role": "input",
      "adapter": "SetuAAAdapter",
      "status": "live-capable",
      "detail": "ReBIT consent artefact (purpose 103, PERIODIC) live; Setu/Finvu UAT shape.",
      "fields": [
        "FIP",
        "consentHandle",
        "fiTypes:[DEPOSIT,GSTR1_3B]",
        "dataRange"
      ]
    },
    {
      "rail": "EPFO",
      "role": "input",
      "adapter": "EPFOAdapter",
      "status": "adapter-ready",
      "detail": "Not an AA FIP yet — synthetic ECR on the real establishment-search shape.",
      "fields": [
        "establishmentId",
        "ecrMonth",
        "memberCount",
        "wageBill"
      ]
    },
    {
      "rail": "ULI (Unified Lending Interface)",
      "role": "input / origination",
      "adapter": "ULIConnector",
      "status": "adapter-ready",
      "detail": "RBIH lender onboarding required; connector implements the real service-code contract.",
      "fields": [
        "serviceCode:[gst-returns,bank-statement,kyc]",
        "consentArtefact",
        "lenderId"
      ]
    },
    {
      "rail": "OCEN 4.0",
      "role": "OUTPUT",
      "adapter": "OCENDerivedDataProvider",
      "status": "spec-conformant",
      "endpoint": "/api/ocen/offer/{msme_id}",
      "detail": "Health score exposed as a Loan-Agent-consumable loan offer (GST-Sahay / SIDBI pattern).",
      "fields": [
        "loanApplicationId",
        "creditAssessment",
        "loanOffer:{sanctionedAmount,interestRate,emi}"
      ]
    }
  ],
  "summary": "AA input live-capable · OCEN output spec-conformant · ULI adapter-ready on RBIH onboarding",
  "principle": "One DataSourceAdapter interface — IDBI's sandbox becomes one more adapter, wired in hours."
};
