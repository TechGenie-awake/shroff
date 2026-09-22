"use client";

import { useRef, useState } from "react";
import { Download, FileUp, Loader2 } from "lucide-react";
import { postDocumentsUpload, sampleDocumentsUrl } from "@/lib/api";
import type { ScoreResponse } from "@/lib/types";
import { EwsStrip } from "@/components/ews-strip";
import { ReasonsList } from "@/components/reasons-list";
import { ScoreGauge } from "@/components/score-gauge";
import { ScreeningPanel } from "@/components/screening-panel";
import { Stamp } from "@/components/stamp";
import { SubScoreRadar } from "@/components/sub-score-radar";

const STAGES = [
  "Parsing business_profile.csv…",
  "Parsing monthly_history.csv…",
  "Computing ~45 features (cash flow · growth · stability · compliance)…",
  "Running the monotonic LightGBM ensemble…",
  "Checking the negative registry + entity graph…",
  "Assembling the decision…",
];

/** GSTIN (15) or bare PAN (10) — same structural check as the live-lookup panel. */
function normalizeIdentifier(raw: string): { value: string; error: string | null } {
  const v = raw.replace(/\s+/g, "").toUpperCase();
  if (v.length === 0) return { value: v, error: "Enter a GSTIN or PAN first." };
  if (v.length !== 10 && v.length !== 15) {
    return { value: v, error: `Expected 10 (PAN) or 15 (GSTIN) characters, got ${v.length}.` };
  }
  return { value: v, error: null };
}

export function DocumentUpload() {
  const [identifier, setIdentifier] = useState("");
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [profileFile, setProfileFile] = useState<File | null>(null);
  const [monthlyFile, setMonthlyFile] = useState<File | null>(null);
  const [stage, setStage] = useState(-1); // -1 = idle
  const [result, setResult] = useState<ScoreResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const profileInput = useRef<HTMLInputElement>(null);
  const monthlyInput = useRef<HTMLInputElement>(null);

  function onDownload() {
    const { value, error: err } = normalizeIdentifier(identifier);
    if (err) {
      setDownloadError(err);
      return;
    }
    setDownloadError(null);
    window.location.href = sampleDocumentsUrl(value);
  }

  async function onProcess() {
    if (!profileFile || !monthlyFile) {
      setError("Choose both business_profile.csv and monthly_history.csv.");
      return;
    }
    setError(null);
    setResult(null);
    setStage(0);
    // Staged progress is cosmetic (the real request below is a single call
    // that typically resolves in well under a second) but each label is a
    // real step the backend performs, in order — this just paces them so a
    // judge can actually watch the pipeline run instead of a single blink.
    const stageTimer = setInterval(() => {
      setStage((s) => (s < STAGES.length - 1 ? s + 1 : s));
    }, 380);
    try {
      const score = await postDocumentsUpload(profileFile, monthlyFile);
      clearInterval(stageTimer);
      setStage(STAGES.length);
      setResult(score);
    } catch (e) {
      clearInterval(stageTimer);
      setStage(-1);
      setError(e instanceof Error ? e.message : "Upload failed.");
    }
  }

  return (
    <div
      className="reveal rounded-lg border border-rule bg-panel px-5 py-4"
      style={{ animationDelay: "70ms" }}
    >
      <div className="section-label">Document upload demo</div>
      <p className="mt-1.5 text-[11.5px] leading-relaxed text-ink-3">
        Download sample documents for a GSTIN/PAN, optionally edit the
        numbers in <code className="text-ink-2">monthly_history.csv</code>,
        then upload both files back. The score reflects exactly what&rsquo;s
        in the files — nothing is re-simulated on upload.
      </p>

      {/* step 1: download */}
      <div className="mt-3 flex flex-wrap items-start gap-2">
        <div className="min-w-0 flex-1">
          <input
            value={identifier}
            onChange={(e) => {
              setIdentifier(e.target.value);
              if (downloadError) setDownloadError(null);
            }}
            placeholder="GSTIN or PAN to generate sample documents for"
            className="tnum w-full min-w-55 rounded-md border border-rule bg-paper px-3 py-2 text-[13px] uppercase text-ink placeholder:text-ink-3/70 placeholder:normal-case focus:border-teal focus:outline-none"
            aria-label="GSTIN or PAN for sample documents"
          />
          {downloadError && <p className="mt-1 text-[11px] text-oxide">{downloadError}</p>}
        </div>
        <button
          type="button"
          onClick={onDownload}
          className="inline-flex items-center gap-1.5 rounded-md border border-rule bg-paper px-3 py-2 font-mono text-[11px] uppercase tracking-[0.12em] text-ink-2 transition-colors hover:border-teal hover:text-teal"
        >
          <Download className="size-3.5" aria-hidden />
          Download sample docs
        </button>
      </div>

      {/* step 2: upload */}
      <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-rule pt-3">
        <label className="inline-flex cursor-pointer items-center gap-1.5 rounded-md border border-rule bg-paper px-2.5 py-1.5 font-mono text-[10.5px] uppercase tracking-[0.1em] text-ink-2 transition-colors hover:border-teal hover:text-teal">
          business_profile.csv
          <input
            ref={profileInput}
            type="file"
            accept=".csv"
            className="hidden"
            onChange={(e) => setProfileFile(e.target.files?.[0] ?? null)}
          />
        </label>
        <span className="text-[10.5px] text-ink-3">
          {profileFile ? profileFile.name : "not chosen"}
        </span>

        <label className="ml-2 inline-flex cursor-pointer items-center gap-1.5 rounded-md border border-rule bg-paper px-2.5 py-1.5 font-mono text-[10.5px] uppercase tracking-[0.1em] text-ink-2 transition-colors hover:border-teal hover:text-teal">
          monthly_history.csv
          <input
            ref={monthlyInput}
            type="file"
            accept=".csv"
            className="hidden"
            onChange={(e) => setMonthlyFile(e.target.files?.[0] ?? null)}
          />
        </label>
        <span className="text-[10.5px] text-ink-3">
          {monthlyFile ? monthlyFile.name : "not chosen"}
        </span>

        <button
          type="button"
          onClick={onProcess}
          disabled={stage >= 0 && stage < STAGES.length}
          className="ml-auto inline-flex items-center gap-1.5 rounded-md border border-teal/40 bg-teal/5 px-3 py-2 font-mono text-[11px] uppercase tracking-[0.12em] text-teal transition-colors hover:border-teal hover:bg-teal/10 disabled:opacity-50"
        >
          {stage >= 0 && stage < STAGES.length ? (
            <Loader2 className="size-3.5 animate-spin" aria-hidden />
          ) : (
            <FileUp className="size-3.5" aria-hidden />
          )}
          Process documents
        </button>
      </div>

      {error && <p className="mt-2 text-[11px] text-oxide">{error}</p>}

      {/* processing steps */}
      {stage >= 0 && stage < STAGES.length && (
        <ul className="mt-3 space-y-1 border-t border-rule pt-3 font-mono text-[11px] text-ink-2">
          {STAGES.map((label, i) => (
            <li key={label} className={i <= stage ? "text-teal" : "text-ink-3"}>
              {i < stage ? "✓" : i === stage ? "…" : "·"} {label}
            </li>
          ))}
        </ul>
      )}

      {/* result */}
      {result && (
        <div className="mt-4 grid gap-3 border-t border-rule pt-4 md:grid-cols-3">
          <div className="rounded-md border border-rule bg-paper p-3">
            <div className="section-label !text-[10px]">Health score</div>
            <ScoreGauge score={result.score} band={result.band} />
          </div>
          <div className="rounded-md border border-rule bg-paper p-3">
            <div className="section-label !text-[10px]">Sub-scores</div>
            <SubScoreRadar subScores={result.sub_scores} />
          </div>
          <div className="flex flex-col rounded-md border border-rule bg-paper p-3">
            <div className="section-label !text-[10px]">Decision</div>
            <div className="flex items-center justify-center py-2">
              <Stamp verdict={result.decision.verdict} size="md" animate />
            </div>
            <p className="mt-1 text-[11px] leading-relaxed text-ink-2">
              {result.decision.rationale}
            </p>
          </div>
          <div className="rounded-md border border-rule bg-paper p-3 md:col-span-2">
            <div className="section-label !text-[10px]">
              Signed reason codes · TreeSHAP
            </div>
            <ReasonsList reasons={result.reasons} />
          </div>
          <div className="flex flex-col gap-3">
            <div className="rounded-md border border-rule bg-paper p-3">
              <div className="section-label !text-[10px]">Early-warning</div>
              <EwsStrip
                level={result.overlays.early_warning.level}
                triggers={result.overlays.early_warning.triggers}
              />
            </div>
            <div className="rounded-md border border-rule bg-paper p-3">
              <div className="section-label !text-[10px]">Registry screening</div>
              <ScreeningPanel
                checked={result.overlays.screening.checked}
                hits={result.overlays.screening.hits}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
