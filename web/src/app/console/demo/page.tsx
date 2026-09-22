"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Search } from "lucide-react";
import { DocumentUpload } from "@/components/document-upload";

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
    <div className="reveal rounded-lg border border-rule bg-panel px-5 py-4" style={{ animationDelay: "40ms" }}>
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
          {error && <p className="mt-1 text-[11px] text-oxide">{error}</p>}
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

export default function DemoPage() {
  return (
    <div className="mx-auto min-h-screen max-w-7xl px-6 pb-16">
      <div className="reveal pt-6">
        <h1 className="font-display text-2xl font-medium tracking-tight text-ink">
          Live demo
        </h1>
        <p className="mt-0.5 text-[12px] text-ink-3">
          Score any real GSTIN or PAN, or walk the full document-submission
          flow — download, edit, upload, watch it process.
        </p>
      </div>

      <div className="mt-6">
        <LiveLookup />
      </div>
      <div className="mt-4">
        <DocumentUpload />
      </div>
    </div>
  );
}
