/**
 * SHROFF — contract types. Mirror CONTRACTS.md "ML API contract" EXACTLY.
 * Field names are law; do not rename.
 */

export type Verdict = "APPROVE" | "REFER" | "DECLINE";
export type LoanTypeId =
  | "working_capital"
  | "term_loan"
  | "invoice_discounting"
  | "trade_finance";

/** GET /api/loan-types — one entry */
export interface LoanTypeInfo {
  id: LoanTypeId;
  label: string;
  implemented: boolean;
  sizing_rule: string;
}
export type Band = "A" | "B" | "C" | "D" | "E";
export type EwsLevel = "green" | "amber" | "red";
export type ReasonGroup = "cash_flow" | "growth" | "stability" | "compliance";
export type Confidence = "high" | "advisory";
export type NodeFlag =
  | null
  | "struck_off"
  | "wilful_defaulter"
  | "director_of_struck_off"
  | "non_genuine";
export type NodeType = "pan" | "company" | "din" | "gstin" | "address";
export type ScreenType =
  | "pan"
  | "gstin"
  | "cin"
  | "din"
  | "name"
  | "account"
  | "vpa";

/** GET /api/health */
export interface HealthResponse {
  status: string;
  model_version: string;
  artifacts_loaded: boolean;
}

/** GET /api/personas — one entry */
export interface Persona {
  id: string;
  name: string;
  business: string;
  city: string;
  segment: string;
  requested_amount_inr: number;
  blurb: string;
}

/** Monthly schema — one row per msme per month (24 months ending 2026-06) */
export interface MonthlyRow {
  msme_id: string;
  month: string; // YYYY-MM
  bank_inflow_inr: number;
  bank_outflow_inr: number;
  eod_balance_avg_inr: number;
  eod_balance_min_inr: number;
  days_near_zero: number;
  upi_txn_count: number;
  upi_inflow_share: number;
  bounce_count: number;
  emi_debit_inr: number;
  self_transfer_inr: number;
  gst_turnover_declared_inr: number;
  gst_filed_on_time: 0 | 1;
  gst_filing_delay_days: number;
  gst_nil_return: 0 | 1;
  b2b_share: number;
  top3_buyer_share: number;
  employees_epfo: number;
  wage_bill_inr: number;
}

/** Profile table fields */
export interface MsmeProfile {
  msme_id: string;
  name: string;
  legal_name: string;
  entity_type: string;
  sector: string;
  city: string;
  state_code: string;
  pan: string;
  gstin: string;
  cin: string | null;
  promoter_name: string;
  promoter_pan: string;
  promoter_din: string | null;
  udyam: string | null;
  incorporated_on: string;
  requested_amount_inr: number;
}

/** ReBIT-style consent artefact (purpose 103, PERIODIC, DEPOSIT + GSTR1_3B) */
export interface ConsentArtefact {
  ver: string;
  txnid: string;
  consentId: string;
  status: string;
  createTimestamp: string;
  consentStart: string;
  consentExpiry: string;
  consentMode: string;
  fetchType: string;
  consentTypes: string[];
  fiTypes: string[];
  DataConsumer: { id: string; type: string };
  Customer: { id: string };
  Purpose: {
    code: string;
    refUri: string;
    text: string;
    Category: { type: string };
  };
  FIDataRange: { from: string; to: string };
  DataLife: { unit: string; value: number };
  Frequency: { unit: string; value: number };
}

/** GET /api/msme/{id} */
export interface MsmeResponse {
  profile: MsmeProfile;
  consent: ConsentArtefact;
  monthly: MonthlyRow[];
}

export interface Reason {
  code: string;
  group: ReasonGroup;
  direction: "positive" | "negative";
  text: string;
  value: string;
  shap: number;
}

export interface ScreeningHit {
  registry: string;
  list_name: string;
  matched_on: string;
  confidence: Confidence;
  detail: string;
  source_url: string;
  is_sample: boolean;
}

export interface DistressedCounterparty {
  gstin: string;
  name: string;
  share: number;
  registry: string;
  list_name: string;
  is_sample: boolean;
}

export interface ImpactSource {
  claim: string;
  source: string;
  range_inr?: number[];
  range_usd?: number[];
  converted_inr_at?: number;
}

/** Operational-impact overlay — onboarding/field-verification cost saved (see ml/api/impact.py) */
export interface BankImpact {
  auto_cleared: boolean;
  field_verification_saved_inr: number[];
  onboarding_cost_saved_inr: number[];
  basis: string;
  sources: ImpactSource[];
  honest_caveat: string;
}

/** POST /api/score → ScoreResponse (exact field names per CONTRACTS.md) */
export interface ScoreResponse {
  msme_id: string;
  name: string;
  score: number;
  band: Band;
  pd_12m: number;
  sub_scores: {
    cash_flow: number;
    growth: number;
    stability: number;
    compliance: number;
  };
  decision: {
    verdict: Verdict;
    amount_inr: number;
    tenure_months: number;
    loan_type: LoanTypeId;
    rationale: string;
  };
  reasons: Reason[];
  overlays: {
    screening: {
      checked: boolean;
      hits: ScreeningHit[];
      phoenix_flag: boolean;
    };
    early_warning: {
      level: EwsLevel;
      triggers: string[];
    };
    supply_chain: {
      top3_buyer_share: number;
      distressed_counterparties: DistressedCounterparty[];
    };
  };
  model: {
    version: string;
    auc: number;
    ks: number;
    trained_on: string;
  };
  bank_impact?: BankImpact;
}

/** GET /api/screen */
export interface ScreenResponse {
  query: { type: ScreenType; value: string };
  hits: ScreeningHit[];
}

/** GET /api/graph/{pan} */
export interface GraphNode {
  id: string;
  type: NodeType;
  label: string;
  flag: NodeFlag;
}

export interface GraphEdge {
  source: string;
  target: string;
  relation: string;
}

export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
  phoenix_flag: boolean;
  narrative: string;
}

/** GET /api/ocen/offer/{id} — the lending-rail output (OCEN 4.0-aligned) */
export interface Money {
  value: number;
  currency: string;
}

export interface OcenOffer {
  ocenVersion: string;
  rail: string;
  generatedAt: string;
  loanApplicationId: string;
  borrower: { vua: string; pan: string; name: string };
  creditAssessment: {
    assessmentProvider: string;
    healthScore: number;
    band: string;
    pd12m: number;
    modelVersion: string;
    dataSources: string[];
    consentPurposeCode: string;
    reasonCodes: { code: string; direction: string; text: string }[];
  };
  loanOffer: {
    offerId: string;
    status: "APPROVED" | "REJECTED" | "PENDING_MANUAL_REVIEW";
    sanctionedAmount: Money;
    rationale: string;
    interestRate?: { value: number; type: string; unit: string };
    tenure?: { value: number; unit: string };
    emi?: Money;
    processingFee?: Money;
    totalInterestPayable?: Money;
    validUpto?: string;
    rejectionReason?: string;
    reviewNote?: string;
  };
}

/** GET /api/rails — DataSourceAdapter registry (honest live/adapter-ready status) */
export interface RailStatus {
  rail: string;
  role: string;
  adapter: string;
  status: string;
  detail: string;
  fields: string[];
  endpoint?: string;
}

export interface RailsResponse {
  rails: RailStatus[];
  summary: string;
  principle: string;
}
