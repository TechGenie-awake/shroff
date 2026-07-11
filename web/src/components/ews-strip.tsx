import { AlertTriangle, CheckCircle2, OctagonAlert } from "lucide-react";
import type { EwsLevel } from "@/lib/types";
import { cn } from "@/lib/utils";

const LEVELS: Record<
  EwsLevel,
  { label: string; icon: typeof CheckCircle2; cls: string; dot: string }
> = {
  green: {
    label: "Green — no triggers",
    icon: CheckCircle2,
    cls: "border-stamp-approve/30 bg-stamp-approve/5 text-stamp-approve",
    dot: "bg-stamp-approve",
  },
  amber: {
    label: "Amber — 1 trigger",
    icon: AlertTriangle,
    cls: "border-stamp-refer/35 bg-stamp-refer/5 text-stamp-refer",
    dot: "bg-stamp-refer",
  },
  red: {
    label: "Red — review now",
    icon: OctagonAlert,
    cls: "border-oxide/35 bg-oxide/5 text-oxide",
    dot: "bg-oxide",
  },
};

/** Early-warning strip: last 3 months vs prior 9 — the "other direction". */
export function EwsStrip({
  level,
  triggers,
}: {
  level: EwsLevel;
  triggers: string[];
}) {
  const meta = LEVELS[level];
  const Icon = meta.icon;
  return (
    <div>
      <div
        className={cn(
          "flex items-center gap-2 rounded-md border px-3 py-2",
          meta.cls
        )}
      >
        <Icon className="size-4 shrink-0" aria-hidden />
        <span className="font-mono text-[11px] font-medium uppercase tracking-[0.14em]">
          {meta.label}
        </span>
        <span className="ml-auto font-mono text-[10px] uppercase tracking-[0.1em] opacity-70">
          last 3mo vs prior 9
        </span>
      </div>
      {triggers.length > 0 ? (
        <ul className="mt-2.5 space-y-2">
          {triggers.map((t) => (
            <li key={t} className="flex gap-2.5 text-[12.5px] leading-snug text-ink-2">
              <span
                className={cn("mt-1.5 size-1.5 shrink-0 rounded-full", meta.dot)}
                aria-hidden
              />
              {t}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-2.5 text-[12.5px] text-ink-3">
          No inflow drops, bounces, GST lapses, or headcount cuts detected in
          the monitoring window.
        </p>
      )}
    </div>
  );
}
