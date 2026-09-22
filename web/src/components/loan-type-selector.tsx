import type { LoanTypeId, LoanTypeInfo } from "@/lib/types";
import { cn } from "@/lib/utils";

/** Loan-type picker: switching re-runs the real sizing formula on the live API —
 * not a relabeled copy. Unimplemented products (invoice discounting, trade finance)
 * are shown, not hidden, but disabled with the honest reason instead of pretending
 * to work. */
export function LoanTypeSelector({
  loanTypes,
  value,
  onChange,
}: {
  loanTypes: LoanTypeInfo[];
  value: LoanTypeId;
  onChange: (id: LoanTypeId) => void;
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {loanTypes.map((lt) => {
        const active = lt.id === value;
        return (
          <button
            key={lt.id}
            type="button"
            disabled={!lt.implemented}
            title={lt.implemented ? lt.sizing_rule : `Not yet built — ${lt.sizing_rule}`}
            onClick={() => lt.implemented && onChange(lt.id)}
            className={cn(
              "rounded-md border px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.1em] transition-colors",
              active
                ? "border-teal bg-teal text-primary-foreground"
                : lt.implemented
                ? "border-rule bg-panel text-ink-2 hover:border-teal hover:text-teal"
                : "cursor-not-allowed border-rule bg-paper text-ink-3 opacity-50"
            )}
          >
            {lt.label}
            {!lt.implemented && " · soon"}
          </button>
        );
      })}
    </div>
  );
}
