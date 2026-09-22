"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, ArrowUpRight, Search } from "lucide-react";
import { getPersonas, postScore, type DataSource } from "@/lib/api";
import type { Persona, ScoreResponse } from "@/lib/types";
import { inr } from "@/lib/format";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { DataSourceChip } from "@/components/data-source";
import { DocumentUpload } from "@/components/document-upload";
import { Stamp } from "@/components/stamp";

interface RowData {
  persona: Persona;
  score: ScoreResponse | null;
}

const TILE_ORDER = ["Assessed", "Approved", "Referred", "Declined"] as const;

const tileDot: Record<(typeof TILE_ORDER)[number], string> = {
  Assessed: "bg-ink-3",
  Approved: "bg-stamp-approve",
  Referred: "bg-stamp-refer",
  Declined: "bg-oxide",
};

/** GSTIN (15) or bare PAN (10) — structural check only, mirrors the server's
 * validator (ml/screening/pan.py) so bad input is caught before navigating. */
function normalizeIdentifier(raw: string): { value: string; error: string | null } {
  const v = raw.replace(/\s+/g, "").toUpperCase();
  if (v.length === 0) return { value: v, error: "Enter a GSTIN or PAN." };
  if (v.length !== 10 && v.length !== 15) {
    return { value: v, error: `Expected 10 (PAN) or 15 (GSTIN) characters, got ${v.length}.` };
  }
  const panPart = v.length === 15 ? v.slice(2, 12) : v;
  if (!/^[A-Z]{5}[0-9]{4}[A-Z]$/.test(panPart)) {
    return { value: v, error: "Doesn't match the PAN pattern (AAAAA9999A)." };
  }
  return { value: v, error: null };
}

function LiveLookup() {
  const router = useRouter();
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const { value: v, error: err } = normalizeIdentifier(value);
    if (err) {
      setError(err);
      return;
    }
    setError(null);
    setSubmitting(true);
    router.push(`/console/LIVE-${v}`);
  }

  return (
    <div
      className="reveal mt-6 rounded-lg border border-rule bg-panel px-5 py-4"
      style={{ animationDelay: "40ms" }}
    >
      <div className="section-label">Live lookup · any GSTIN or PAN</div>
      <p className="mt-1.5 text-[11.5px] leading-relaxed text-ink-3">
        Not one of the 3 demo personas — score a business by its own
        identifier. Financial history is deterministically simulated pending
        IDBI&rsquo;s GSTN/Bank-AA sandbox (same input always reproduces the
        same score); registry and entity-graph checks run against the real
        negative-registry data.
      </p>
      <form onSubmit={onSubmit} className="mt-3 flex flex-wrap items-start gap-2">
        <div className="min-w-0 flex-1">
          <input
            value={value}
            onChange={(e) => {
              setValue(e.target.value);
              if (error) setError(null);
            }}
            placeholder="e.g. 27ABCPR3456K1Z5 or ABCPR3456K"
            className="tnum w-full min-w-55 rounded-md border border-rule bg-paper px-3 py-2 text-[13px] uppercase text-ink placeholder:text-ink-3/70 placeholder:normal-case focus:border-teal focus:outline-none"
            aria-label="GSTIN or PAN"
          />
          {error && (
            <p className="mt-1 text-[11px] text-oxide">{error}</p>
          )}
        </div>
        <button
          type="submit"
          disabled={submitting}
          className="inline-flex items-center gap-1.5 rounded-md border border-teal/40 bg-teal/5 px-3 py-2 font-mono text-[11px] uppercase tracking-[0.12em] text-teal transition-colors hover:border-teal hover:bg-teal/10 disabled:opacity-50"
        >
          <Search className="size-3.5" aria-hidden />
          {submitting ? "Scoring…" : "Score it"}
          {!submitting && <ArrowRight className="size-3.5" aria-hidden />}
        </button>
      </form>
    </div>
  );
}

export default function ConsolePage() {
  const router = useRouter();
  const [rows, setRows] = useState<RowData[] | null>(null);
  const [source, setSource] = useState<DataSource | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const personas = await getPersonas();
      const scored = await Promise.all(
        personas.data.map(async (p) => {
          try {
            const s = await postScore(p.id);
            return { persona: p, score: s.data, src: s.source };
          } catch {
            return { persona: p, score: null, src: "fixture" as const };
          }
        })
      );
      if (cancelled) return;
      setRows(scored.map(({ persona, score }) => ({ persona, score })));
      setSource(
        personas.source === "live" || scored.some((s) => s.src === "live")
          ? "live"
          : "fixture"
      );
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const counts = {
    Assessed: rows?.filter((r) => r.score).length ?? 0,
    Approved:
      rows?.filter((r) => r.score?.decision.verdict === "APPROVE").length ?? 0,
    Referred:
      rows?.filter((r) => r.score?.decision.verdict === "REFER").length ?? 0,
    Declined:
      rows?.filter((r) => r.score?.decision.verdict === "DECLINE").length ?? 0,
  };

  return (
    <div className="mx-auto min-h-screen max-w-6xl px-6 pb-16">
      {/* header */}
      <header className="reveal flex items-center justify-between pt-8">
        <div>
          <Link href="/" className="font-display text-lg font-semibold tracking-tight text-ink">
            SHROFF
          </Link>
          <span className="ml-3 font-mono text-[10px] uppercase tracking-[0.16em] text-ink-3">
            Underwriter&rsquo;s console
          </span>
        </div>
        <DataSourceChip source={source} />
      </header>

      <LiveLookup />
      <DocumentUpload />

      {/* stat tiles */}
      <div
        className="reveal mt-8 grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-rule bg-rule md:grid-cols-4"
        style={{ animationDelay: "80ms" }}
      >
        {TILE_ORDER.map((label) => (
          <div key={label} className="bg-panel px-5 py-4">
            <div className="flex items-center gap-1.5">
              <span className={`size-1.5 rounded-full ${tileDot[label]}`} aria-hidden />
              <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-2">
                {label}
              </span>
            </div>
            <div className="tnum mt-1.5 text-3xl font-semibold text-ink">
              {rows ? counts[label] : "–"}
            </div>
          </div>
        ))}
      </div>

      {/* portfolio ledger */}
      <div
        className="reveal mt-6 overflow-hidden rounded-lg border border-rule bg-panel"
        style={{ animationDelay: "160ms" }}
      >
        <div className="section-label px-5 pt-4 pb-3">Assessment ledger</div>
        <Table className="ledger-table">
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="pl-5">Borrower</TableHead>
              <TableHead>Segment</TableHead>
              <TableHead className="text-right">Requested</TableHead>
              <TableHead className="text-right">Score</TableHead>
              <TableHead className="text-center">Verdict</TableHead>
              <TableHead className="pr-5 text-right">Health card</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {(rows ?? []).map(({ persona, score }, i) => (
              <TableRow
                key={persona.id}
                onClick={() => router.push(`/console/${persona.id}`)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    router.push(`/console/${persona.id}`);
                  }
                }}
                tabIndex={0}
                role="link"
                aria-label={`Open health card for ${persona.business}`}
                className="reveal group cursor-pointer transition-colors hover:bg-paper focus-visible:outline-2 focus-visible:outline-teal"
                style={{ animationDelay: `${220 + i * 70}ms` }}
              >
                <TableCell className="pl-5">
                  <div className="text-[13px] font-medium text-ink">
                    {persona.business}
                  </div>
                  <div className="tnum mt-0.5 text-[10.5px] text-ink-3">
                    {persona.id} · {persona.city}
                  </div>
                </TableCell>
                <TableCell className="max-w-56">
                  <div className="text-[12px] text-ink-2">{persona.segment}</div>
                  <div className="mt-0.5 line-clamp-2 text-[11px] leading-snug text-ink-3">
                    {persona.blurb}
                  </div>
                </TableCell>
                <TableCell className="tnum text-right text-[12.5px] text-ink">
                  {inr(persona.requested_amount_inr)}
                </TableCell>
                <TableCell className="text-right">
                  {score ? (
                    <>
                      <span className="tnum text-base font-semibold text-ink">
                        {score.score}
                      </span>
                      <span className="tnum ml-1.5 text-[10.5px] text-ink-3">
                        band {score.band}
                      </span>
                    </>
                  ) : (
                    <span className="text-ink-3">—</span>
                  )}
                </TableCell>
                <TableCell className="text-center">
                  {score ? (
                    <Stamp verdict={score.decision.verdict} size="sm" />
                  ) : (
                    <span className="text-ink-3">—</span>
                  )}
                </TableCell>
                <TableCell className="pr-5 text-right">
                  <Link
                    href={`/console/${persona.id}`}
                    onClick={(e) => e.stopPropagation()}
                    className="inline-flex items-center gap-1 rounded-sm border border-rule bg-panel px-2.5 py-1.5 font-mono text-[10px] uppercase tracking-[0.12em] text-ink-2 transition-colors group-hover:border-teal/40 hover:border-teal hover:text-teal"
                  >
                    Run assessment
                    <ArrowUpRight className="size-3" aria-hidden />
                  </Link>
                </TableCell>
              </TableRow>
            ))}
            {!rows &&
              [0, 1, 2].map((i) => (
                <TableRow key={i}>
                  <TableCell colSpan={6} className="px-5">
                    <div className="h-10 animate-pulse rounded bg-muted" />
                  </TableCell>
                </TableRow>
              ))}
          </TableBody>
        </Table>
      </div>

      <p
        className="reveal mt-5 text-[11px] leading-relaxed text-ink-3"
        style={{ animationDelay: "500ms" }}
      >
        Scores are computed by a monotonic LightGBM ensemble with TreeSHAP
        reason codes, calibrated to a 12-month PD. Registry and phoenix overlays
        are deterministic and can only worsen a verdict — never improve it.
        Demo personas run on synthetic consented data.
      </p>
    </div>
  );
}
