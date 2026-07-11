import type { Reason } from "@/lib/types";
import { cn } from "@/lib/utils";

const GROUP_LABEL: Record<Reason["group"], string> = {
  cash_flow: "Cash flow",
  growth: "Growth",
  stability: "Stability",
  compliance: "Compliance",
};

/** Signed SHAP reason codes — the explainability spine of the card. */
export function ReasonsList({ reasons }: { reasons: Reason[] }) {
  const maxAbs = Math.max(...reasons.map((r) => Math.abs(r.shap)), 0.001);
  const ordered = [...reasons].sort(
    (a, b) => Math.abs(b.shap) - Math.abs(a.shap)
  );

  return (
    <ul>
      {ordered.map((r) => {
        const positive = r.direction === "positive";
        return (
          <li
            key={r.code}
            className="flex items-start gap-3 border-b border-rule py-2.5 last:border-b-0"
          >
            <span className="tnum mt-0.5 w-12 shrink-0 text-[11px] font-medium text-ink-2">
              {r.code}
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-[12.5px] leading-snug text-ink">{r.text}</p>
              <div className="mt-1 flex items-center gap-2">
                <span className="font-mono text-[9.5px] uppercase tracking-[0.12em] text-ink-3">
                  {GROUP_LABEL[r.group]}
                </span>
                <span className="tnum text-[10.5px] text-ink-2">{r.value}</span>
              </div>
            </div>
            {/* signed contribution bar + value */}
            <div className="w-28 shrink-0 pt-0.5">
              <div className="flex h-2 items-center">
                <div className="flex h-1.5 w-1/2 justify-end overflow-hidden rounded-l-[2px] bg-muted">
                  {!positive && (
                    <div
                      className="h-full rounded-l-[2px] bg-oxide"
                      style={{ width: `${(Math.abs(r.shap) / maxAbs) * 100}%` }}
                    />
                  )}
                </div>
                <div className="mx-px h-2.5 w-px bg-ink-3" aria-hidden />
                <div className="h-1.5 w-1/2 overflow-hidden rounded-r-[2px] bg-muted">
                  {positive && (
                    <div
                      className="h-full rounded-r-[2px] bg-teal"
                      style={{ width: `${(Math.abs(r.shap) / maxAbs) * 100}%` }}
                    />
                  )}
                </div>
              </div>
              <div
                className={cn(
                  "tnum mt-1 text-right text-[10.5px] font-medium",
                  positive ? "text-teal" : "text-oxide"
                )}
              >
                {positive ? "+" : "−"}
                {Math.abs(r.shap).toFixed(2)} SHAP
              </div>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
