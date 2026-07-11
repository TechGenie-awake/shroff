"use client";

import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
} from "recharts";
import type { ScoreResponse } from "@/lib/types";

const LABELS: Record<string, string> = {
  cash_flow: "Cash flow",
  growth: "Growth",
  stability: "Stability",
  compliance: "Compliance",
};

/** One-series radar: teal fill @15%, 2px stroke, values direct-labeled below. */
export function SubScoreRadar({
  subScores,
}: {
  subScores: ScoreResponse["sub_scores"];
}) {
  const data = (
    ["cash_flow", "growth", "stability", "compliance"] as const
  ).map((k) => ({ axis: LABELS[k], value: subScores[k] }));

  return (
    <div>
      <div className="h-[190px]">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={data} cx="50%" cy="52%" outerRadius="78%">
            <PolarGrid stroke="var(--rule)" />
            <PolarAngleAxis
              dataKey="axis"
              tick={{ fontSize: 10.5, fill: "var(--ink-2)" }}
            />
            <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
            <Radar
              dataKey="value"
              stroke="var(--teal)"
              strokeWidth={2}
              fill="var(--teal)"
              fillOpacity={0.15}
              isAnimationActive={true}
              animationDuration={700}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>
      {/* direct-labeled values — identity never carried by shape alone */}
      <div className="mt-1 grid grid-cols-2 gap-x-4 gap-y-1 border-t border-rule pt-2">
        {data.map((d) => (
          <div key={d.axis} className="flex items-baseline justify-between">
            <span className="text-[11px] text-ink-2">{d.axis}</span>
            <span className="tnum text-xs font-medium text-ink">
              {d.value}
              <span className="text-ink-3">/100</span>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
