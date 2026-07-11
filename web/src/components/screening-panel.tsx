import { ExternalLink, ShieldCheck } from "lucide-react";
import type { ScreeningHit } from "@/lib/types";
import { cn } from "@/lib/utils";

function SampleChip({ isSample }: { isSample: boolean }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-sm border px-1.5 py-px font-mono text-[9px] uppercase tracking-[0.12em]",
        isSample
          ? "border-series-3/35 bg-series-3/5 text-series-3"
          : "border-teal/35 bg-teal/5 text-teal"
      )}
      title={
        isSample
          ? "Synthetic sample row mirroring the real registry schema (is_sample = 1)"
          : "Sourced from published government data (is_sample = 0)"
      }
    >
      {isSample ? "sample row" : "govt data"}
    </span>
  );
}

/** Negative-registry screening results with honest is_sample provenance chips. */
export function ScreeningPanel({
  hits,
  checked,
}: {
  hits: ScreeningHit[];
  checked: boolean;
}) {
  if (!checked) {
    return (
      <p className="text-[12.5px] text-ink-3">Screening not yet run.</p>
    );
  }
  if (hits.length === 0) {
    return (
      <div className="flex items-start gap-2.5 rounded-md border border-stamp-approve/25 bg-stamp-approve/5 px-3 py-2.5">
        <ShieldCheck className="mt-0.5 size-4 shrink-0 text-stamp-approve" aria-hidden />
        <p className="text-[12.5px] leading-snug text-ink-2">
          <span className="font-medium text-stamp-approve">Clear.</span>{" "}
          No hits across MCA struck-off, GST non-genuine, wilful-defaulter,
          DIN and CIRP registries on the borrower&rsquo;s own identifiers.
        </p>
      </div>
    );
  }
  return (
    <ul className="space-y-3">
      {hits.map((h) => (
        <li
          key={`${h.registry}-${h.matched_on}`}
          className="rounded-md border border-rule bg-panel p-3"
        >
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-ink-2">
              {h.registry}
            </span>
            <span
              className={cn(
                "inline-flex items-center rounded-sm border px-1.5 py-px font-mono text-[9px] uppercase tracking-[0.12em]",
                h.confidence === "high"
                  ? "border-oxide/40 bg-oxide/5 text-oxide"
                  : "border-stamp-refer/40 bg-stamp-refer/5 text-stamp-refer"
              )}
            >
              {h.confidence}
            </span>
            <SampleChip isSample={h.is_sample} />
          </div>
          <div className="mt-1.5 text-[12px] font-medium text-ink">
            {h.list_name}
          </div>
          <div className="tnum mt-0.5 break-all text-[11px] text-oxide">
            {h.matched_on}
          </div>
          <p className="mt-1.5 text-[12px] leading-snug text-ink-2">{h.detail}</p>
          {h.source_url && (
            <a
              href={h.source_url}
              target="_blank"
              rel="noreferrer"
              className="mt-1.5 inline-flex items-center gap-1 font-mono text-[10px] text-ink-3 underline-offset-2 hover:text-teal hover:underline"
            >
              <ExternalLink className="size-3" aria-hidden />
              {h.source_url.replace(/^https?:\/\//, "").replace(/\/$/, "")}
            </a>
          )}
        </li>
      ))}
    </ul>
  );
}
