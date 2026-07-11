"use client";

import { FileCheck2 } from "lucide-react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import type { ConsentArtefact } from "@/lib/types";

/** ReBIT-style consent artefact — proof the data is consented, not scraped. */
export function ConsentPopover({ consent }: { consent: ConsentArtefact }) {
  return (
    <Popover>
      <PopoverTrigger className="inline-flex items-center gap-1.5 rounded-sm border border-rule bg-panel px-2 py-1 font-mono text-[10px] uppercase tracking-[0.12em] text-ink-2 transition-colors hover:border-teal/40 hover:text-teal">
        <FileCheck2 className="size-3" aria-hidden />
        AA consent artefact
      </PopoverTrigger>
      <PopoverContent align="end" className="w-[26rem] max-w-[90vw] gap-0 p-0">
        <div className="border-b border-rule px-3.5 py-2.5">
          <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-2">
            ReBIT consent artefact
          </div>
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            <span className="rounded-sm border border-teal/30 bg-teal/5 px-1.5 py-px font-mono text-[9px] text-teal">
              purpose {consent.Purpose?.code ?? "103"}
            </span>
            <span className="rounded-sm border border-rule px-1.5 py-px font-mono text-[9px] text-ink-2">
              {consent.fetchType}
            </span>
            {(consent.fiTypes ?? []).map((t) => (
              <span
                key={t}
                className="rounded-sm border border-rule px-1.5 py-px font-mono text-[9px] text-ink-2"
              >
                {t}
              </span>
            ))}
            <span className="rounded-sm border border-rule px-1.5 py-px font-mono text-[9px] text-ink-2">
              {consent.status}
            </span>
          </div>
        </div>
        <pre className="max-h-72 overflow-auto px-3.5 py-3 font-mono text-[10px] leading-relaxed text-ink-2">
          {JSON.stringify(consent, null, 2)}
        </pre>
        <div className="border-t border-rule px-3.5 py-2 text-[10.5px] text-ink-3">
          Every field on this card is fetched under this consent — purpose-bound,
          time-bound, revocable. Demo artefact mirrors the ReBIT v2 schema.
        </div>
      </PopoverContent>
    </Popover>
  );
}
