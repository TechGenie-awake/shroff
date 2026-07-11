/** Indian-format numerals — always rendered in IBM Plex Mono via .tnum */

const inrFmt = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

const numFmt = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });

/** ₹12,00,000 */
export const inr = (n: number) => inrFmt.format(n);

/** 12,00,000 */
export const num = (n: number) => numFmt.format(n);

/** ₹12.0L / ₹1.2Cr — compact lakh-crore for axes and tiles */
export function inrCompact(n: number): string {
  if (n >= 1_00_00_000) return `₹${(n / 1_00_00_000).toFixed(1)}Cr`;
  if (n >= 1_00_000) return `₹${(n / 1_00_000).toFixed(1)}L`;
  if (n >= 1_000) return `₹${(n / 1_000).toFixed(0)}K`;
  return `₹${n}`;
}

/** 55% */
export const pct = (x: number, digits = 0) => `${(x * 100).toFixed(digits)}%`;

/** "2026-04" → "Apr ’26" */
export function monthLabel(ym: string): string {
  const [y, m] = ym.split("-").map(Number);
  const names = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  return `${names[(m ?? 1) - 1]} ’${String(y).slice(2)}`;
}
