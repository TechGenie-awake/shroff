import type { ModelInfoResponse, ScoreResponse } from "@/lib/types";
import { pct } from "@/lib/format";
import { cn } from "@/lib/utils";

const SUB_LABELS: Record<string, string> = {
  cash_flow: "Cash flow", growth: "Growth", stability: "Stability", compliance: "Compliance",
};

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-md border border-rule bg-paper px-3 py-2.5">
      <div className="font-mono text-[9.5px] uppercase tracking-[0.12em] text-ink-3">{label}</div>
      <div className="tnum mt-0.5 text-lg font-semibold text-ink">{value}</div>
      {sub && <div className="mt-0.5 text-[10.5px] text-ink-3">{sub}</div>}
    </div>
  );
}

export function ModelDetail({
  score,
  modelInfo,
}: {
  score: ScoreResponse;
  modelInfo: ModelInfoResponse | null;
}) {
  return (
    <div className="space-y-4">
      {/* current score + population rank */}
      <div className="grid gap-3 sm:grid-cols-4">
        <Stat label="Current score" value={String(score.score)} sub={`Band ${score.band}`} />
        <Stat label="12-month PD" value={pct(score.pd_12m, 1)} />
        <Stat
          label="Rank vs population"
          value={
            score.score_percentile != null ? `${score.score_percentile.toFixed(1)}th pct` : "—"
          }
          sub={
            score.population_n
              ? `healthier than ${score.score_percentile?.toFixed(0)}% of ${score.population_n.toLocaleString("en-IN")} reference MSMEs`
              : undefined
          }
        />
        <Stat
          label="Model version"
          value={modelInfo?.metrics.model_version ?? score.model.version}
          sub={modelInfo?.metrics.trained_on ?? score.model.trained_on}
        />
      </div>

      {/* sub-scores as ranked rows */}
      <div className="rounded-md border border-rule bg-paper p-3">
        <div className="section-label !text-[10px]">Sub-scores · population percentile</div>
        <div className="mt-2 space-y-2">
          {(Object.entries(score.sub_scores) as [string, number][]).map(([k, v]) => (
            <div key={k} className="flex items-center gap-3">
              <span className="w-24 shrink-0 text-[11.5px] text-ink-2">{SUB_LABELS[k] ?? k}</span>
              <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-rule">
                <div
                  className="h-full rounded-full bg-teal"
                  style={{ width: `${Math.max(2, v)}%` }}
                />
              </div>
              <span className="tnum w-10 shrink-0 text-right text-[12px] font-medium text-ink">
                {v}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* the exact formula */}
      {modelInfo && (
        <div className="rounded-md border border-rule bg-paper p-3">
          <div className="section-label !text-[10px]">Scorecard formula</div>
          <p className="tnum mt-2 rounded-sm bg-panel px-3 py-2 text-[12px] text-ink-2">
            {modelInfo.scorecard_formula.description}
          </p>
          <p className="mt-2 text-[11px] leading-relaxed text-ink-3">
            {modelInfo.scorecard_formula.score_ref} points at {pct(modelInfo.scorecard_formula.pd_ref)} PD
            (odds {modelInfo.scorecard_formula.odds_ref}:1) · +{modelInfo.scorecard_formula.points_per_doubling} points per
            halving of default odds · clamped [{modelInfo.scorecard_formula.score_min}, {modelInfo.scorecard_formula.score_max}]
          </p>
          <table className="mt-3 w-full text-[11.5px]">
            <thead>
              <tr className="text-left font-mono text-[9.5px] uppercase tracking-[0.1em] text-ink-3">
                <th className="pb-1.5 font-normal">Band</th>
                <th className="pb-1.5 font-normal">Floor score</th>
                <th className="pb-1.5 font-normal">Amount factor</th>
                <th className="pb-1.5 font-normal">Tenure</th>
              </tr>
            </thead>
            <tbody>
              {modelInfo.scorecard_formula.bands.map((b) => (
                <tr
                  key={b.band}
                  className={cn(
                    "border-t border-rule",
                    b.band === score.band && "bg-teal/5"
                  )}
                >
                  <td className="py-1.5 font-medium text-ink">
                    {b.band}
                    {b.band === score.band && (
                      <span className="ml-1.5 font-mono text-[9px] uppercase text-teal">this score</span>
                    )}
                  </td>
                  <td className="tnum py-1.5 text-ink-2">{b.floor_score ? `≥${b.floor_score}` : "<500"}</td>
                  <td className="tnum py-1.5 text-ink-2">{(b.band_factor * 100).toFixed(0)}% of turnover</td>
                  <td className="tnum py-1.5 text-ink-2">{b.tenure_months || "—"} mo</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* architecture */}
      {modelInfo && (
        <div className="rounded-md border border-rule bg-paper p-3">
          <div className="section-label !text-[10px]">Architecture</div>
          <dl className="mt-2 space-y-2 text-[11.5px]">
            <div>
              <dt className="font-mono text-[9.5px] uppercase tracking-[0.1em] text-ink-3">Per sub-model</dt>
              <dd className="mt-0.5 text-ink-2">{modelInfo.architecture.algorithm}</dd>
            </div>
            <div>
              <dt className="font-mono text-[9.5px] uppercase tracking-[0.1em] text-ink-3">Combiner</dt>
              <dd className="mt-0.5 text-ink-2">{modelInfo.architecture.combiner}</dd>
            </div>
            <div>
              <dt className="font-mono text-[9.5px] uppercase tracking-[0.1em] text-ink-3">Calibration</dt>
              <dd className="mt-0.5 text-ink-2">{modelInfo.architecture.calibration}</dd>
            </div>
            <div>
              <dt className="font-mono text-[9.5px] uppercase tracking-[0.1em] text-ink-3">Explainability</dt>
              <dd className="mt-0.5 text-ink-2">{modelInfo.architecture.explainability}</dd>
            </div>
          </dl>
        </div>
      )}

      {/* validation metrics */}
      {modelInfo && (
        <div className="rounded-md border border-rule bg-paper p-3">
          <div className="section-label !text-[10px]">Validation (untouched holdout)</div>
          <table className="mt-2 w-full text-[11.5px]">
            <thead>
              <tr className="text-left font-mono text-[9.5px] uppercase tracking-[0.1em] text-ink-3">
                <th className="pb-1.5 font-normal">Model</th>
                <th className="pb-1.5 text-right font-normal">AUC</th>
                <th className="pb-1.5 text-right font-normal">KS</th>
                <th className="pb-1.5 text-right font-normal">Combiner weight</th>
              </tr>
            </thead>
            <tbody>
              {modelInfo.architecture.sub_models.map((g) => (
                <tr key={g} className="border-t border-rule">
                  <td className="py-1.5 text-ink-2">{SUB_LABELS[g] ?? g}</td>
                  <td className="tnum py-1.5 text-right text-ink">
                    {modelInfo.metrics.sub_models[g]?.auc.toFixed(3)}
                  </td>
                  <td className="tnum py-1.5 text-right text-ink">
                    {modelInfo.metrics.sub_models[g]?.ks.toFixed(3)}
                  </td>
                  <td className="tnum py-1.5 text-right text-ink">
                    {modelInfo.metrics.meta_coefficients[g]?.toFixed(3)}
                  </td>
                </tr>
              ))}
              <tr className="border-t border-rule bg-teal/5 font-medium">
                <td className="py-1.5 text-ink">Combined (meta)</td>
                <td className="tnum py-1.5 text-right text-teal">{modelInfo.metrics.combined.auc.toFixed(3)}</td>
                <td className="tnum py-1.5 text-right text-teal">{modelInfo.metrics.combined.ks.toFixed(3)}</td>
                <td className="py-1.5 text-right text-ink-3">—</td>
              </tr>
              <tr className="border-t border-rule">
                <td className="py-1.5 text-ink-2">Baseline LogReg (regulator view)</td>
                <td className="tnum py-1.5 text-right text-ink-2">{modelInfo.metrics.baseline_logreg.auc.toFixed(3)}</td>
                <td className="tnum py-1.5 text-right text-ink-2">{modelInfo.metrics.baseline_logreg.ks.toFixed(3)}</td>
                <td className="py-1.5 text-right text-ink-3">—</td>
              </tr>
            </tbody>
          </table>
          <p className="mt-2 text-[10.5px] text-ink-3">
            Trained on {modelInfo.metrics.train_n.toLocaleString("en-IN")} · held out{" "}
            {modelInfo.metrics.holdout_n.toLocaleString("en-IN")} · population default rate{" "}
            {pct(modelInfo.metrics.prevalence, 1)} · seed {modelInfo.metrics.seed} ·{" "}
            {modelInfo.total_features} features across {modelInfo.architecture.sub_models.length} groups.
            Synthetic-v1 data — a pipeline rehearsal, not a production claim.
          </p>
        </div>
      )}

      {/* monotone constraints */}
      {modelInfo && (
        <div className="rounded-md border border-rule bg-paper p-3">
          <div className="section-label !text-[10px]">
            Monotone constraints · direction is fixed, never learned
          </div>
          <div className="mt-2 grid gap-2 sm:grid-cols-2">
            {Object.entries(modelInfo.monotone_constraints).map(([g, m]) => (
              <div key={g} className="rounded-sm border border-rule px-2.5 py-2">
                <div className="text-[11px] font-medium text-ink">{SUB_LABELS[g] ?? g}</div>
                <div className="mt-1 flex gap-3 font-mono text-[10px] text-ink-3">
                  <span className="text-oxide">{m.n_risk_increasing} risk ↑</span>
                  <span className="text-stamp-approve">{m.n_risk_decreasing} risk ↓</span>
                  <span>{m.n_unconstrained} free</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
