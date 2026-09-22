"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import {
  getGraph,
  getLoanTypes,
  getMsme,
  getOcenOffer,
  panForMsme,
  postScore,
  type DataSource,
} from "@/lib/api";
import type {
  GraphResponse,
  LoanTypeId,
  LoanTypeInfo,
  MsmeResponse,
  OcenOffer,
  ScoreResponse,
} from "@/lib/types";
import { inr } from "@/lib/format";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BankImpactPanel } from "@/components/bank-impact";
import { ConcentrationBar } from "@/components/concentration-bar";
import { LendingRail } from "@/components/lending-rail";
import { ConsentPopover } from "@/components/consent-popover";
import { DataSourceChip } from "@/components/data-source";
import { DivergenceChart } from "@/components/divergence-chart";
import { EntityGraph } from "@/components/entity-graph";
import { EwsStrip } from "@/components/ews-strip";
import { LoanTypeSelector } from "@/components/loan-type-selector";
import { ReasonsList } from "@/components/reasons-list";
import { ScoreGauge } from "@/components/score-gauge";
import { ScreeningPanel } from "@/components/screening-panel";
import { Stamp } from "@/components/stamp";
import { SubScoreRadar } from "@/components/sub-score-radar";

function IdChip({ kind, value }: { kind: string; value: string }) {
  return (
    <span className="id-chip">
      <span className="id-kind">{kind}</span>
      {value}
    </span>
  );
}

function PanelTitle({ children }: { children: React.ReactNode }) {
  return (
    <CardTitle className="section-label !text-[0.6875rem] font-medium">
      {children}
    </CardTitle>
  );
}

export function HealthCard({ id }: { id: string }) {
  const [msme, setMsme] = useState<MsmeResponse | null>(null);
  const [score, setScore] = useState<ScoreResponse | null>(null);
  const [graph, setGraph] = useState<GraphResponse | null>(null);
  const [offer, setOffer] = useState<OcenOffer | null>(null);
  const [loanTypes, setLoanTypes] = useState<LoanTypeInfo[]>([]);
  const [loanType, setLoanType] = useState<LoanTypeId>("working_capital");
  const [source, setSource] = useState<DataSource | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Fixed borrower data — fetched once per id, independent of loan type.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [m, o, lt] = await Promise.all([
          getMsme(id),
          getOcenOffer(id),
          getLoanTypes(),
        ]);
        if (cancelled) return;
        setMsme(m.data);
        setOffer(o.data);
        setLoanTypes(lt.data);
        const g = await getGraph(panForMsme(id, m.data.profile.pan));
        if (!cancelled) setGraph(g.data);
      } catch {
        if (!cancelled) setError(`No borrower found for id "${id}".`);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  // The decision itself — re-run against the real sizing formula whenever the
  // loan type changes, so switching the selector calls the live API, not a
  // client-side relabel of the same number.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const s = await postScore(id, loanType);
        if (!cancelled) {
          setScore(s.data);
          setSource(s.source);
        }
      } catch {
        if (!cancelled) setError(`No borrower found for id "${id}".`);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id, loanType]);

  if (error) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-24 text-center">
        <p className="font-display text-2xl text-ink">{error}</p>
        <Link
          href="/console"
          className="mt-4 inline-block font-mono text-xs uppercase tracking-[0.14em] text-teal underline-offset-4 hover:underline"
        >
          ← Back to the console
        </Link>
      </div>
    );
  }

  if (!msme || !score) {
    return (
      <div className="mx-auto max-w-7xl px-6 py-24">
        <div className="section-label">Preparing health card</div>
        <div className="mt-8 grid gap-4 md:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="h-64 animate-pulse rounded-lg border border-rule bg-panel"
            />
          ))}
        </div>
      </div>
    );
  }

  const { profile, consent, monthly } = msme;
  const d = score.decision;

  return (
    <div className="mx-auto max-w-7xl px-6 pb-16">
      {/* ── identity header ── */}
      <header className="reveal pt-8" style={{ animationDelay: "0ms" }}>
        <div className="flex items-center justify-between gap-4">
          <Link
            href="/console"
            className="inline-flex items-center gap-1.5 font-mono text-[10.5px] uppercase tracking-[0.14em] text-ink-3 transition-colors hover:text-teal"
          >
            <ArrowLeft className="size-3.5" aria-hidden />
            Console
          </Link>
          <DataSourceChip source={source} />
        </div>
        <div className="mt-4 flex flex-wrap items-end justify-between gap-4 border-b border-rule pb-5 double-rule">
          <div>
            <div className="font-mono text-[10.5px] uppercase tracking-[0.16em] text-ink-3">
              {profile.msme_id} · {profile.entity_type} · {profile.city}
            </div>
            <h1 className="font-display mt-1 text-3xl font-medium tracking-tight text-ink md:text-4xl">
              {profile.name}
            </h1>
            <div className="mt-3 flex flex-wrap items-center gap-1.5">
              <IdChip kind="PAN" value={profile.pan} />
              <IdChip kind="GSTIN" value={profile.gstin} />
              {profile.cin && <IdChip kind="CIN" value={profile.cin} />}
              {profile.promoter_din && (
                <IdChip kind="DIN" value={profile.promoter_din} />
              )}
              {profile.udyam && <IdChip kind="UDYAM" value={profile.udyam} />}
              <ConsentPopover consent={consent} />
            </div>
          </div>
          <div className="text-right">
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-3">
              Requested
            </div>
            <div className="tnum text-xl font-semibold text-ink">
              {inr(profile.requested_amount_inr)}
            </div>
            <div className="mt-0.5 text-[11px] text-ink-3">{profile.sector}</div>
          </div>
        </div>
        {loanTypes.length > 0 && (
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-3">
              Loan type
            </span>
            <LoanTypeSelector
              loanTypes={loanTypes}
              value={loanType}
              onChange={setLoanType}
            />
          </div>
        )}
      </header>

      {/* ── row 1: gauge · radar · decision ── */}
      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        <Card className="reveal" style={{ animationDelay: "60ms" }}>
          <CardHeader>
            <PanelTitle>Health score</PanelTitle>
          </CardHeader>
          <CardContent>
            <ScoreGauge score={score.score} band={score.band} />
            <div className="mt-1 flex items-center justify-between border-t border-rule pt-2.5">
              <span className="text-[11px] text-ink-2">12-month PD</span>
              <span className="tnum text-xs font-medium text-ink">
                {(score.pd_12m * 100).toFixed(1)}%
              </span>
            </div>
          </CardContent>
        </Card>

        <Card className="reveal" style={{ animationDelay: "120ms" }}>
          <CardHeader>
            <PanelTitle>Sub-scores</PanelTitle>
          </CardHeader>
          <CardContent>
            <SubScoreRadar subScores={score.sub_scores} />
          </CardContent>
        </Card>

        <Card className="reveal" style={{ animationDelay: "180ms" }}>
          <CardHeader>
            <PanelTitle>Decision</PanelTitle>
          </CardHeader>
          <CardContent className="flex h-full flex-col">
            <div className="flex items-center justify-center py-3">
              <Stamp verdict={d.verdict} size="lg" animate />
            </div>
            <dl className="mt-2 space-y-2 border-t border-rule pt-3">
              <div className="flex items-baseline justify-between">
                <dt className="text-[11.5px] text-ink-2">Sanction amount</dt>
                <dd className="tnum text-base font-semibold text-ink">
                  {d.amount_inr > 0 ? inr(d.amount_inr) : "—"}
                </dd>
              </div>
              <div className="flex items-baseline justify-between">
                <dt className="text-[11.5px] text-ink-2">Tenure</dt>
                <dd className="tnum text-sm font-medium text-ink">
                  {d.tenure_months > 0 ? `${d.tenure_months} months` : "—"}
                </dd>
              </div>
            </dl>
            <p className="mt-3 border-t border-rule pt-3 text-[12px] leading-relaxed text-ink-2">
              {d.rationale}
            </p>
            <div className="mt-auto pt-3 font-mono text-[9.5px] uppercase tracking-[0.1em] text-ink-3">
              model {score.model.version} · AUC {score.model.auc.toFixed(2)} · KS{" "}
              {score.model.ks.toFixed(2)} · {score.model.trained_on}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* ── row 2: reasons · overlays ── */}
      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <Card className="reveal lg:col-span-2" style={{ animationDelay: "240ms" }}>
          <CardHeader>
            <PanelTitle>Signed reason codes · TreeSHAP</PanelTitle>
          </CardHeader>
          <CardContent>
            <ReasonsList reasons={score.reasons} />
          </CardContent>
        </Card>

        <div className="flex flex-col gap-4">
          <Card className="reveal" style={{ animationDelay: "300ms" }}>
            <CardHeader>
              <PanelTitle>Early-warning signals</PanelTitle>
            </CardHeader>
            <CardContent>
              <EwsStrip
                level={score.overlays.early_warning.level}
                triggers={score.overlays.early_warning.triggers}
              />
            </CardContent>
          </Card>
          <Card className="reveal grow" style={{ animationDelay: "360ms" }}>
            <CardHeader>
              <PanelTitle>Registry screening</PanelTitle>
            </CardHeader>
            <CardContent>
              <ScreeningPanel
                checked={score.overlays.screening.checked}
                hits={score.overlays.screening.hits}
              />
            </CardContent>
          </Card>
        </div>
      </div>

      {/* ── row 3: the divergence view ── */}
      <Card className="reveal mt-4" style={{ animationDelay: "420ms" }}>
        <CardHeader>
          <PanelTitle>
            Bank-verified inflows vs GST-declared turnover · monthly
          </PanelTitle>
        </CardHeader>
        <CardContent>
          <DivergenceChart monthly={monthly} />
        </CardContent>
      </Card>

      {/* ── row 4: entity graph · concentration ── */}
      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <Card className="reveal lg:col-span-2" style={{ animationDelay: "480ms" }}>
          <CardHeader>
            <PanelTitle>Entity graph · registry walk</PanelTitle>
          </CardHeader>
          <CardContent>
            {graph ? (
              <EntityGraph graph={graph} />
            ) : (
              <div className="h-[380px] animate-pulse rounded-md border border-rule bg-paper" />
            )}
          </CardContent>
        </Card>
        <Card className="reveal" style={{ animationDelay: "540ms" }}>
          <CardHeader>
            <PanelTitle>Supply-chain concentration</PanelTitle>
          </CardHeader>
          <CardContent>
            <ConcentrationBar
              top3Share={score.overlays.supply_chain.top3_buyer_share}
              distressed={score.overlays.supply_chain.distressed_counterparties}
            />
          </CardContent>
        </Card>
      </div>

      {/* ── row 5: lending rail (OCEN output) · bank impact ── */}
      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        {offer && (
          <Card className="reveal lg:col-span-2" style={{ animationDelay: "600ms" }}>
            <CardHeader>
              <PanelTitle>Lending rail · OCEN 4.0 output</PanelTitle>
            </CardHeader>
            <CardContent>
              <LendingRail offer={offer} />
            </CardContent>
          </Card>
        )}
        {score.bank_impact && (
          <Card className="reveal" style={{ animationDelay: "660ms" }}>
            <CardHeader>
              <PanelTitle>Bank impact · cost saved</PanelTitle>
            </CardHeader>
            <CardContent>
              <BankImpactPanel impact={score.bank_impact} />
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
