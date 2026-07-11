"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { MonthlyRow } from "@/lib/types";
import { inr, inrCompact, monthLabel, pct } from "@/lib/format";

/**
 * Bank-verified inflows vs GST-declared turnover on ONE shared ₹ axis.
 * Divergence between the two lines is THE cross-verification money-shot.
 * Series colors: validated palette — series-1 teal, series-2 burnt saffron.
 */

const SERIES = [
  { key: "bank", label: "Bank-verified inflows", color: "var(--series-1)" },
  { key: "gst", label: "GST-declared turnover", color: "var(--series-2)" },
] as const;

interface Point {
  month: string;
  bank: number;
  gst: number;
  nil: boolean;
}

function DivergenceTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ dataKey: string; value: number; payload: Point }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  const row = payload[0].payload;
  const gap = row.bank > 0 ? (row.gst - row.bank) / row.bank : 0;
  return (
    <div className="rounded-md border border-rule bg-panel px-3 py-2 shadow-sm">
      <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-3">
        {label ? monthLabel(label) : ""}
      </div>
      {SERIES.map((s) => {
        const p = payload.find((x) => x.dataKey === s.key);
        if (!p) return null;
        return (
          <div key={s.key} className="mt-1 flex items-center gap-2">
            <span
              className="inline-block h-0.5 w-3 rounded-full"
              style={{ background: s.color }}
            />
            <span className="text-[11px] text-ink-2">{s.label}</span>
            <span className="tnum ml-auto pl-3 text-[11px] font-medium text-ink">
              {inr(p.value)}
            </span>
          </div>
        );
      })}
      {row.nil ? (
        <div className="mt-1 font-mono text-[10px] uppercase tracking-[0.1em] text-oxide">
          Nil GST return filed
        </div>
      ) : Math.abs(gap) > 0.1 ? (
        <div className="mt-1 font-mono text-[10px] text-oxide">
          declared {gap > 0 ? "+" : ""}
          {pct(gap)} vs bank
        </div>
      ) : null}
    </div>
  );
}

export function DivergenceChart({ monthly }: { monthly: MonthlyRow[] }) {
  const data: Point[] = monthly.map((m) => ({
    month: m.month,
    bank: m.bank_inflow_inr,
    gst: m.gst_turnover_declared_inr,
    nil: m.gst_nil_return === 1,
  }));

  // divergence across the full consented window — the headline the chart proves
  const bankAvg = data.reduce((s, d) => s + d.bank, 0) / Math.max(data.length, 1);
  const gstAvg = data.reduce((s, d) => s + d.gst, 0) / Math.max(data.length, 1);
  const gap = bankAvg > 0 ? (gstAvg - bankAvg) / bankAvg : 0;

  return (
    <div>
      <div className="mb-2 flex flex-wrap items-center gap-x-5 gap-y-1">
        {/* legend — ≥2 series, always present */}
        {SERIES.map((s) => (
          <span key={s.key} className="inline-flex items-center gap-2">
            <svg width="18" height="4" aria-hidden>
              <line
                x1="0" y1="2" x2="18" y2="2"
                stroke={s.color}
                strokeWidth="2"
                strokeDasharray={s.key === "gst" ? "5 3" : undefined}
              />
            </svg>
            <span className="text-[11px] text-ink-2">{s.label}</span>
          </span>
        ))}
        {Math.abs(gap) > 0.1 && (
          <span className="ml-auto inline-flex items-center gap-1.5 rounded-sm border border-oxide/30 bg-oxide/5 px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.1em] text-oxide">
            declared {gap > 0 ? "+" : ""}
            {pct(gap)} vs bank-verified
          </span>
        )}
      </div>
      <div className="h-[260px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 12, left: 4, bottom: 0 }}>
            <CartesianGrid vertical={false} stroke="var(--rule)" />
            <XAxis
              dataKey="month"
              tickFormatter={monthLabel}
              interval={2}
              tickLine={false}
              axisLine={{ stroke: "var(--rule)" }}
              dy={4}
            />
            <YAxis
              tickFormatter={inrCompact}
              tickLine={false}
              axisLine={false}
              width={52}
              domain={[0, "auto"]}
            />
            <Tooltip
              content={<DivergenceTooltip />}
              cursor={{ stroke: "var(--ink-3)", strokeDasharray: "3 3" }}
            />
            <Line
              type="monotone"
              dataKey="bank"
              stroke="var(--series-1)"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 3.5, strokeWidth: 0 }}
              isAnimationActive={true}
              animationDuration={700}
            />
            <Line
              type="monotone"
              dataKey="gst"
              stroke="var(--series-2)"
              strokeWidth={2}
              strokeDasharray="6 4"
              dot={false}
              activeDot={{ r: 3.5, strokeWidth: 0 }}
              isAnimationActive={true}
              animationDuration={700}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
