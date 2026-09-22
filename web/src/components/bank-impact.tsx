import { CheckCircle2, CircleDashed } from "lucide-react";
import type { BankImpact } from "@/lib/types";
import { inrCompact } from "@/lib/format";
import { cn } from "@/lib/utils";

function rangeLabel(lo: number, hi: number): string {
  if (lo === 0 && hi === 0) return "₹0";
  return `${inrCompact(lo)}–${inrCompact(hi)}`;
}

/** Operational-impact overlay: onboarding + field-verification cost saved.
 * Only claims a saving when the deterministic overlays came back clean —
 * a flagged application correctly still needs a human, so it shows ₹0 there. */
export function BankImpactPanel({ impact }: { impact: BankImpact }) {
  const Icon = impact.auto_cleared ? CheckCircle2 : CircleDashed;
  return (
    <div>
      <div
        className={cn(
          "flex items-center gap-2 rounded-md border px-3 py-2",
          impact.auto_cleared
            ? "border-stamp-approve/30 bg-stamp-approve/5 text-stamp-approve"
            : "border-ink-3/30 bg-paper text-ink-2"
        )}
      >
        <Icon className="size-4 shrink-0" aria-hidden />
        <span className="font-mono text-[11px] font-medium uppercase tracking-[0.14em]">
          {impact.auto_cleared ? "Auto-cleared" : "Routed to manual review"}
        </span>
      </div>

      <dl className="mt-3 grid grid-cols-2 gap-3">
        <div>
          <dt className="font-mono text-[9.5px] uppercase tracking-[0.1em] text-ink-3">
            Field verification saved
          </dt>
          <dd className="tnum mt-0.5 text-lg font-semibold text-ink">
            {rangeLabel(
              impact.field_verification_saved_inr[0],
              impact.field_verification_saved_inr[1]
            )}
          </dd>
        </div>
        <div>
          <dt className="font-mono text-[9.5px] uppercase tracking-[0.1em] text-ink-3">
            Onboarding cost saved
          </dt>
          <dd className="tnum mt-0.5 text-lg font-semibold text-ink">
            {rangeLabel(
              impact.onboarding_cost_saved_inr[0],
              impact.onboarding_cost_saved_inr[1]
            )}
          </dd>
        </div>
      </dl>

      <p className="mt-3 text-[11.5px] leading-relaxed text-ink-2">
        {impact.basis}
      </p>

      <div className="mt-3 border-t border-rule pt-2.5">
        <p className="font-mono text-[9px] uppercase tracking-[0.08em] text-ink-3">
          Sources
        </p>
        <ul className="mt-1 space-y-0.5">
          {impact.sources.map((s) => (
            <li key={s.claim} className="text-[10.5px] leading-snug text-ink-3">
              {s.claim} ({s.range_inr ? rangeLabel(s.range_inr[0], s.range_inr[1]) : `$${s.range_usd?.[0]}–${s.range_usd?.[1]}`}) — {s.source}
            </li>
          ))}
        </ul>
        <p className="mt-2 text-[10.5px] italic leading-snug text-saffron">
          {impact.honest_caveat}
        </p>
      </div>
    </div>
  );
}
