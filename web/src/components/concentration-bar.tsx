import type { DistressedCounterparty } from "@/lib/types";
import { pct } from "@/lib/format";
import { cn } from "@/lib/utils";

/**
 * Supply-chain concentration: one composition bar (2px surface gaps),
 * distressed counterparties carved out in oxide — status, not a series color.
 */
export function ConcentrationBar({
  top3Share,
  distressed,
}: {
  top3Share: number;
  distressed: DistressedCounterparty[];
}) {
  const distressedShare = distressed.reduce((s, d) => s + d.share, 0);
  const cleanTop3 = Math.max(top3Share - distressedShare, 0);
  const others = Math.max(1 - top3Share, 0);

  const segments = [
    ...(distressedShare > 0
      ? [
          {
            key: "distressed",
            share: distressedShare,
            color: "var(--oxide)",
            label: `Distressed buyer${distressed.length > 1 ? "s" : ""} (${distressed
              .map((d) => d.name)
              .join(", ")})`,
          },
        ]
      : []),
    {
      key: "top3",
      share: cleanTop3,
      color: "var(--series-1)",
      label: distressedShare > 0 ? "Rest of top-3 buyers" : "Top-3 buyers",
    },
    { key: "others", share: others, color: "var(--rule)", label: "All other buyers" },
  ].filter((s) => s.share > 0.001);

  const tone =
    top3Share >= 0.7
      ? { text: "Concentrated", cls: "border-oxide/35 bg-oxide/5 text-oxide" }
      : top3Share >= 0.45
        ? { text: "Advisory", cls: "border-stamp-refer/35 bg-stamp-refer/5 text-stamp-refer" }
        : { text: "Diversified", cls: "border-stamp-approve/30 bg-stamp-approve/5 text-stamp-approve" };

  return (
    <div>
      <div className="flex items-baseline gap-2.5">
        <span className="tnum text-3xl font-semibold text-ink">
          {pct(top3Share)}
        </span>
        <span className="text-[12px] text-ink-2">
          of receipts from the top-3 buyers
        </span>
        <span
          className={cn(
            "ml-auto rounded-sm border px-1.5 py-px font-mono text-[9px] uppercase tracking-[0.12em]",
            tone.cls
          )}
        >
          {tone.text}
        </span>
      </div>

      <div
        className="mt-3 flex h-4 w-full overflow-hidden rounded-[3px]"
        role="img"
        aria-label={`Buyer concentration: top-3 share ${pct(top3Share)}`}
      >
        {segments.map((s, i) => (
          <div
            key={s.key}
            style={{
              width: `${s.share * 100}%`,
              background: s.color,
              marginLeft: i > 0 ? 2 : 0, // 2px surface gap between fills
            }}
            title={`${s.label}: ${pct(s.share)}`}
          />
        ))}
      </div>

      <ul className="mt-3 space-y-1.5">
        {segments.map((s) => (
          <li key={s.key} className="flex items-center gap-2">
            <span
              className="inline-block size-2.5 rounded-[2px]"
              style={{ background: s.color }}
              aria-hidden
            />
            <span className="text-[11.5px] text-ink-2">{s.label}</span>
            <span className="tnum ml-auto text-[11.5px] font-medium text-ink">
              {pct(s.share)}
            </span>
          </li>
        ))}
      </ul>

      {distressed.map((d) => (
        <div
          key={d.gstin}
          className="mt-3 rounded-md border border-oxide/35 bg-oxide/5 p-2.5"
        >
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-[12px] font-medium text-oxide">{d.name}</span>
            <span className="tnum text-[10.5px] text-ink-2">{d.gstin}</span>
            <span
              className="ml-auto inline-flex items-center rounded-sm border border-series-3/35 bg-series-3/5 px-1.5 py-px font-mono text-[9px] uppercase tracking-[0.12em] text-series-3"
              title="Synthetic sample row mirroring the real registry schema (is_sample = 1)"
            >
              {d.is_sample ? "sample row" : "govt data"}
            </span>
          </div>
          <p className="mt-1 text-[11.5px] leading-snug text-ink-2">
            {pct(d.share)} of receipts · listed on {d.list_name} ({d.registry})
          </p>
        </div>
      ))}
    </div>
  );
}
