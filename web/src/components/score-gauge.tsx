"use client";

import { useEffect, useState } from "react";
import type { Band } from "@/lib/types";

const MIN = 300;
const MAX = 900;
const START = 210; // degrees, lower-left
const SWEEP = 240; // degrees, clockwise through the top

/** Band boundaries per contract: A ≥750 · B 680–749 · C 600–679 · D 500–599 · E <500 */
const BOUNDARIES = [500, 600, 680, 750];
const BAND_MIDS: Array<{ band: Band; at: number }> = [
  { band: "E", at: 400 },
  { band: "D", at: 550 },
  { band: "C", at: 640 },
  { band: "B", at: 715 },
  { band: "A", at: 825 },
];

const bandColor = (band: Band) =>
  band === "A" || band === "B"
    ? "var(--teal)"
    : band === "C"
      ? "var(--stamp-refer)"
      : "var(--oxide)";

function polar(cx: number, cy: number, r: number, angleDeg: number) {
  const rad = (angleDeg * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy - r * Math.sin(rad) };
}

function arcPath(cx: number, cy: number, r: number, a0: number, a1: number) {
  const p0 = polar(cx, cy, r, a0);
  const p1 = polar(cx, cy, r, a1);
  const large = a0 - a1 > 180 ? 1 : 0;
  return `M ${p0.x.toFixed(2)} ${p0.y.toFixed(2)} A ${r} ${r} 0 ${large} 1 ${p1.x.toFixed(2)} ${p1.y.toFixed(2)}`;
}

const angleFor = (score: number) =>
  START - ((Math.min(Math.max(score, MIN), MAX) - MIN) / (MAX - MIN)) * SWEEP;

/** Single-arc score gauge, 300→900, with band ticks — per the contract dataviz spec. */
export function ScoreGauge({ score, band }: { score: number; band: Band }) {
  const [shown, setShown] = useState(MIN);
  useEffect(() => {
    const raf = requestAnimationFrame(() => setShown(score));
    return () => cancelAnimationFrame(raf);
  }, [score]);

  const cx = 130;
  const cy = 120;
  const r = 96;
  const color = bandColor(band);

  return (
    <div className="flex flex-col items-center">
      <svg viewBox="0 0 260 190" className="w-full max-w-[280px]" role="img"
        aria-label={`Credit score ${score} of 900, band ${band}`}>
        {/* track */}
        <path
          d={arcPath(cx, cy, r, START, START - SWEEP)}
          fill="none"
          stroke="var(--rule)"
          strokeWidth={10}
          strokeLinecap="round"
        />
        {/* value arc */}
        <path
          d={arcPath(cx, cy, r, START, angleFor(shown))}
          fill="none"
          stroke={color}
          strokeWidth={10}
          strokeLinecap="round"
          style={{ transition: "all 0.9s cubic-bezier(0.25, 0.8, 0.3, 1)" }}
        />
        {/* band boundary ticks punch 2px gaps through the arc */}
        {BOUNDARIES.map((b) => {
          const a = angleFor(b);
          const p0 = polar(cx, cy, r - 8, a);
          const p1 = polar(cx, cy, r + 8, a);
          return (
            <line
              key={b}
              x1={p0.x} y1={p0.y} x2={p1.x} y2={p1.y}
              stroke="var(--panel)"
              strokeWidth={3}
            />
          );
        })}
        {/* band letters along the arc */}
        {BAND_MIDS.map(({ band: b, at }) => {
          const p = polar(cx, cy, r + 16, angleFor(at));
          return (
            <text
              key={b}
              x={p.x} y={p.y}
              textAnchor="middle"
              dominantBaseline="middle"
              style={{
                font: "500 9px var(--font-plex-mono), monospace",
                fill: b === band ? "var(--ink)" : "var(--ink-3)",
                letterSpacing: "0.1em",
              }}
            >
              {b}
            </text>
          );
        })}
        {/* endpoints */}
        <text x={polar(cx, cy, r - 22, START).x} y={polar(cx, cy, r - 20, START).y + 12}
          textAnchor="middle" style={{ font: "10px var(--font-plex-mono), monospace", fill: "var(--ink-3)" }}>
          300
        </text>
        <text x={polar(cx, cy, r - 22, START - SWEEP).x} y={polar(cx, cy, r - 20, START - SWEEP).y + 12}
          textAnchor="middle" style={{ font: "10px var(--font-plex-mono), monospace", fill: "var(--ink-3)" }}>
          900
        </text>
        {/* center readout */}
        <text x={cx} y={cy - 4} textAnchor="middle"
          style={{ font: "600 44px var(--font-plex-mono), monospace", fill: "var(--ink)", fontVariantNumeric: "tabular-nums" }}>
          {score}
        </text>
        <text x={cx} y={cy + 20} textAnchor="middle"
          style={{ font: "500 10px var(--font-plex-mono), monospace", fill: "var(--ink-2)", letterSpacing: "0.16em" }}>
          BAND {band}
        </text>
      </svg>
    </div>
  );
}
