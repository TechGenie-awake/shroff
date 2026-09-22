# IDBI Innovate 2026 — Sandbox Access Request, drafted answers

Form: https://docs.google.com/forms/d/e/1FAIpQLSfpLH_20KELsytpYKf2br8lNkFEVYxfhhS8Q4f41ao03RTPCQ/viewform

Reference copy of the cleaned blank form: [`given/round-2/sandbox-form.txt`](../given/round-2/sandbox-form.txt).
Sizing/cost figures below are sourced from [`docs/INFRA-AWS.md`](INFRA-AWS.md). This is a drafted
answer sheet for manual copy-paste into the live Google Form — not auto-submitted.

---

**Email\*** — checkbox: record `anshumanatrey@gmail.com`

**Team Name\*** — `Walrus Securitas`

**Track\*** — `Track 03 — Financial Inclusion (Digital Lending / Credit Decisioning) — MSME Financial Health Card`

**Use case\*** —
> SHROFF is a live, working MSME Financial Health Card: a monotonic-constrained LightGBM ensemble (4 sub-models) + TreeSHAP reason codes scoring 300–900 on alternate data (GST, AA bank, UPI, EPFO), a PAN-spine entity graph that catches phoenix-fraud promoters, and an OCEN 4.0 output rail — currently running on synthetic data + ~45,000 real government registry rows (MahaGST, SEBI/NSE, CBDT, RBI, OpenSanctions). Sandbox access lets us retrain and validate this pipeline against IDBI's real MSME/transaction data, and extend it into a fully agentic risk mesh: an orchestration layer of read-only, tool-calling agents that continuously monitor a borrower's credit health, digital/cyber exposure (breach and dark-web exposure of the MSME's PAN/GSTIN/promoter identity, phishing-domain squatting on the business's brand — the same entity-graph and screening infrastructure already built for phoenix-fraud detection, extended to fraud vectors originating outside the bank), and regulatory compliance posture (RBI FREE-AI explainability, DPDP consent lifecycle, AML/KYC/PMLA screening, ULI/OCEN protocol conformance) — all as advisory overlays feeding a single audit-grade decision, never as autonomous decision-makers themselves.

**AWS Services Required\*** — check: `EC2` `S3` `RDS` `Lambda` `VPC`
`Other:` `ECS Fargate (scoring API), SageMaker (training/registry), Bedrock (agent orchestration + narrative), EventBridge Scheduler + Step Functions (registry refresh, continuous monitoring), Secrets Manager, Aurora Serverless v2 Postgres`

**Region Preference\*** — `Mumbai`

**Estimated Compute or Storage Size\*** —
> ML scoring API: 1 vCPU / 2GB RAM (measured — see `docs/INFRA-AWS.md`). Web console: 0.25–0.5 vCPU / 1GB. Training/batch jobs: 4 vCPU / 8–16GB. Storage: 20–50GB initial (parquet feature store + registry DB + model artifacts), scaling with real MCA/GST/AA data volume.

**Required Duration — Start Date\*** — `21/08/2026`

**Required Duration — End Date\*** — `30/09/2026` (covers Prototype Refinement through Demo Day Sep 3 and Winner Felicitation Sep 19, with buffer for a POC transition if selected)

**Estimated Cost (if known)** —
> ~₹10,000–17,000/month (POC-grade: Fargate + Amplify/S3 + RDS micro + light event infra) at prototype scale, per the cost model in `docs/INFRA-AWS.md`.

**Business or Technical Justification\*** —
> Track 03's brief asks for a unified alternate-data framework that includes credit-invisible MSMEs while catching those that look clean on paper — SHROFF already does both, deterministically, with signed reason codes (no LLM ever on the decision path). Real sandbox data closes our one honest gap: our core scoring model is currently trained on synthetic data, while the entity-graph and registry-screening layers already run on ~45,000 real government rows. Beyond that, sandbox access lets us build the next layer we've architected but not yet wired: a bounded, tool-calling agent mesh where each agent (screening, continuous EWS monitoring, adverse-media/cyber-exposure scanning, compliance-citation retrieval) only returns computed facts to a deterministic decision engine — extending one health-card score into a continuously-monitored, cyber-aware, compliance-audited risk posture for the borrower, without ever letting a generative model compute a number itself.

**Point of Contact Name\*** — `Anshuman Atrey`

**Point of Contact Email\*** — `anshumanatrey@gmail.com`

**Point of Contact Phone Number\*** — *(fill in)*

**Which city do you belong to?\*** — *(fill in)*

---

## Why "truly agentic" reaches into cyber ops and compliance without scope creep

`BUILD-SPEC-track03.md` already locked the architecture that makes this safe: **deterministic
core, generative shell.** Agents sit at the edges as read-only tools, never on the score. That
shape is exactly what lets a cyber-exposure agent (dark-web/breach/phishing-domain monitoring on
the borrower's identity — reusing the PAN-graph already built, and directly Walrus Securitas's
own thesis) and a compliance-citation agent (RBI/DPDP/AML) bolt on as additional *overlays* — the
same pattern as the negative-registry screening already shipped — without touching the scoring
engine itself.
