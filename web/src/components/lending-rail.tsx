import type { OcenOffer } from "@/lib/types";
import { inr } from "@/lib/format";

const STATUS_STYLE: Record<
  OcenOffer["loanOffer"]["status"],
  { label: string; cls: string }
> = {
  APPROVED: { label: "Approved", cls: "text-stamp-approve border-stamp-approve/40 bg-stamp-approve/10" },
  PENDING_MANUAL_REVIEW: { label: "Pending review", cls: "text-stamp-refer border-stamp-refer/40 bg-stamp-refer/10" },
  REJECTED: { label: "Rejected", cls: "text-oxide border-oxide/40 bg-oxide/10" },
};

/** One node in the origination flow strip. */
function RailNode({
  label,
  chip,
  chipCls,
}: {
  label: string;
  chip: string;
  chipCls: string;
}) {
  return (
    <div className="flex min-w-0 flex-col items-center gap-1 text-center">
      <span className="text-[11px] font-medium text-ink">{label}</span>
      <span
        className={`rounded-sm border px-1.5 py-0.5 font-mono text-[8.5px] uppercase tracking-[0.1em] ${chipCls}`}
      >
        {chip}
      </span>
    </div>
  );
}

function Arrow() {
  return (
    <span className="shrink-0 self-start pt-1 font-mono text-ink-3" aria-hidden>
      →
    </span>
  );
}

function Term({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="font-mono text-[9px] uppercase tracking-[0.12em] text-ink-3">
        {label}
      </span>
      <span className="tnum text-[13px] font-semibold text-ink">{value}</span>
    </div>
  );
}

export function LendingRail({ offer }: { offer: OcenOffer }) {
  const o = offer.loanOffer;
  const st = STATUS_STYLE[o.status];
  const teal = "text-teal border-teal/40 bg-teal/10";
  const amber = "text-stamp-refer border-stamp-refer/40 bg-stamp-refer/10";

  return (
    <div className="flex flex-col gap-5">
      {/* origination flow strip */}
      <div className="flex items-start justify-between gap-2 rounded-md border border-rule bg-paper px-4 py-3">
        <RailNode label="Account Aggregator" chip="● Live" chipCls={teal} />
        <Arrow />
        <RailNode label="SHROFF decision" chip={`Score ${offer.creditAssessment.healthScore}`} chipCls="text-ink-2 border-rule bg-panel" />
        <Arrow />
        <RailNode label="OCEN 4.0" chip="Output" chipCls={teal} />
        <Arrow />
        <RailNode label="Lender · IDBI" chip="Disburse" chipCls="text-ink-2 border-rule bg-panel" />
      </div>

      {/* OCEN loan offer artifact */}
      <div className="rounded-md border border-rule bg-panel p-4">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-rule pb-3">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-2">
              OCEN loan offer
            </span>
            <span
              className={`rounded-sm border px-2 py-0.5 font-mono text-[9px] font-semibold uppercase tracking-[0.1em] ${st.cls}`}
            >
              {st.label}
            </span>
          </div>
          <span className="tnum font-mono text-[10px] text-ink-3">
            {o.offerId}
            {o.validUpto ? ` · valid to ${o.validUpto}` : ""}
          </span>
        </div>

        {o.status === "REJECTED" ? (
          <p className="pt-3 text-[12px] leading-relaxed text-ink-2">
            <span className="font-medium text-oxide">No offer generated. </span>
            {o.rejectionReason}
          </p>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-x-6 gap-y-3.5 pt-3.5 sm:grid-cols-3">
              <Term label="Sanctioned" value={inr(o.sanctionedAmount.value)} />
              <Term
                label="Interest (p.a.)"
                value={o.interestRate ? `${o.interestRate.value}%` : "—"}
              />
              <Term
                label="EMI"
                value={o.emi ? `${inr(o.emi.value)}/mo` : "—"}
              />
              <Term
                label="Tenure"
                value={o.tenure ? `${o.tenure.value} months` : "—"}
              />
              <Term
                label="Processing fee"
                value={o.processingFee ? inr(o.processingFee.value) : "—"}
              />
              <Term
                label="Total interest"
                value={o.totalInterestPayable ? inr(o.totalInterestPayable.value) : "—"}
              />
            </div>
            {o.reviewNote && (
              <p className={`mt-3.5 rounded-sm border px-3 py-2 text-[11.5px] leading-relaxed ${amber}`}>
                {o.reviewNote}
              </p>
            )}
          </>
        )}

        <div className="mt-3.5 flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-rule pt-3 font-mono text-[9.5px] text-ink-3">
          <span>VUA {offer.borrower.vua}</span>
          <span>·</span>
          <span>{offer.creditAssessment.dataSources.join(" + ")}</span>
          <span>·</span>
          <span>consent purpose {offer.creditAssessment.consentPurposeCode}</span>
          <span className="ml-auto uppercase tracking-[0.1em]">
            OCEN {offer.ocenVersion} · ULI adapter-ready
          </span>
        </div>
      </div>
    </div>
  );
}
