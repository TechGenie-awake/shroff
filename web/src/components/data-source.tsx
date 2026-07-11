import type { DataSource } from "@/lib/api";
import { cn } from "@/lib/utils";

/** Honest indicator: is this page fed by the live ML API or bundled fixtures? */
export function DataSourceChip({
  source,
  className,
}: {
  source: DataSource | null;
  className?: string;
}) {
  if (source === null) {
    return (
      <span
        className={cn(
          "inline-flex items-center gap-1.5 rounded-sm border border-rule bg-panel px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.14em] text-ink-3",
          className
        )}
      >
        <span className="size-1.5 rounded-full bg-ink-3 animate-pulse" />
        Connecting
      </span>
    );
  }
  const live = source === "live";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-sm border px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.14em]",
        live
          ? "border-teal/30 bg-teal/5 text-teal"
          : "border-stamp-refer/30 bg-stamp-refer/5 text-stamp-refer",
        className
      )}
      title={
        live
          ? "Data served by the ML API"
          : "ML API unreachable — serving contract-exact bundled fixtures"
      }
    >
      <span
        className={cn(
          "size-1.5 rounded-full",
          live ? "bg-teal" : "bg-stamp-refer"
        )}
      />
      {live ? "Live API" : "Fixture mode"}
    </span>
  );
}
