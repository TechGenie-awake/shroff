import Link from "next/link";
import {
  ArrowRight,
  GitFork,
  Landmark,
  LineChart,
  Radar,
  ShieldAlert,
} from "lucide-react";
import { Stamp } from "@/components/stamp";
import { personasFixture, scoreFixtures } from "@/lib/fixtures";

const PILLARS = [
  {
    n: "01",
    icon: LineChart,
    title: "Cash-flow truth, consented",
    body: "24 months of bank inflows, GST filings and EPFO payrolls fetched over Account Aggregator rails under a purpose-bound ReBIT consent. The borrower's real ledger — not a credit bureau's silence.",
  },
  {
    n: "02",
    icon: Radar,
    title: "Deterministic score, signed reasons",
    body: "Four monotonic gradient-boosted sub-models — cash flow, growth, stability, compliance — calibrated to a 12-month PD, each decision carrying TreeSHAP reason codes. Nothing generative ever computes a number.",
  },
  {
    n: "03",
    icon: GitFork,
    title: "Registry screening & the entity graph",
    body: "Every identifier walked through MCA struck-off, GST non-genuine, wilful-defaulter and DIN registries — then along the promoter graph, where phoenix operators hide behind fresh CINs at old addresses.",
  },
];

export default function LandingPage() {
  return (
    <main className="min-h-screen">
      {/* ── top bar ── */}
      <nav className="border-b border-rule">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <span className="font-display text-xl font-semibold tracking-tight text-ink">
            SHROFF
          </span>
          <div className="flex items-center gap-5">
            <span className="hidden font-mono text-[10px] uppercase tracking-[0.16em] text-ink-3 sm:block">
              IDBI Innovate 2026 · Track 03
            </span>
            <Link
              href="/console"
              className="inline-flex items-center gap-1.5 rounded-md bg-teal px-3.5 py-1.5 font-mono text-[11px] font-medium uppercase tracking-[0.12em] text-primary-foreground transition-opacity hover:opacity-90"
            >
              Open console
              <ArrowRight className="size-3.5" aria-hidden />
            </Link>
          </div>
        </div>
      </nav>

      {/* ── hero on ruled ledger paper ── */}
      <section className="ledger-ruling border-b border-rule">
        <div className="mx-auto max-w-6xl px-6 py-20 md:py-28">
          <p className="reveal font-mono text-[11px] uppercase tracking-[0.2em] text-saffron">
            The MSME Financial Health Card
          </p>
          <h1
            className="reveal font-display mt-5 max-w-4xl text-5xl font-medium leading-[1.04] tracking-tight text-ink md:text-7xl"
            style={{ animationDelay: "80ms" }}
          >
            Sees the invisible borrower&nbsp;—
            <em className="text-teal"> in both directions.</em>
          </h1>
          <p
            className="reveal mt-7 max-w-2xl text-[15px] leading-relaxed text-ink-2"
            style={{ animationDelay: "160ms" }}
          >
            Six crore MSMEs run real businesses that credit bureaus cannot see;
            others look clean on paper while their cash flow quietly burns.
            SHROFF reads the consented ledger — bank, GST, EPFO — scores it with
            an explainable model, and screens every identifier against the
            public negative registries. One card. Both failure modes.
          </p>
          <div
            className="reveal mt-9 flex flex-wrap items-center gap-3"
            style={{ animationDelay: "240ms" }}
          >
            <Link
              href="/console"
              className="inline-flex items-center gap-2 rounded-md bg-teal px-5 py-2.5 font-mono text-xs font-medium uppercase tracking-[0.12em] text-primary-foreground transition-opacity hover:opacity-90"
            >
              Open the underwriter&rsquo;s console
              <ArrowRight className="size-4" aria-hidden />
            </Link>
            <Link
              href="/console/RAMESH001"
              className="inline-flex items-center gap-2 rounded-md border border-rule bg-panel px-5 py-2.5 font-mono text-xs uppercase tracking-[0.12em] text-ink-2 transition-colors hover:border-teal hover:text-teal"
            >
              View a live health card
            </Link>
          </div>

          {/* stat strip */}
          <dl
            className="reveal mt-16 grid max-w-3xl grid-cols-2 gap-x-8 gap-y-6 md:grid-cols-4"
            style={{ animationDelay: "320ms" }}
          >
            {[
              ["6.3 Cr", "registered MSMEs in India"],
              ["₹25L Cr", "estimated formal credit gap"],
              ["24 mo", "consented cash-flow window"],
              ["< 60 s", "score, reasons & sanction"],
            ].map(([v, l]) => (
              <div key={l}>
                <dt className="tnum text-2xl font-semibold text-ink">{v}</dt>
                <dd className="mt-1 text-[11.5px] leading-snug text-ink-3">{l}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      {/* ── three pillars ── */}
      <section className="mx-auto max-w-6xl px-6 py-16 md:py-20">
        <div className="section-label">How the card is written</div>
        <div className="mt-8 grid gap-px overflow-hidden rounded-lg border border-rule bg-rule md:grid-cols-3">
          {PILLARS.map((p) => (
            <article key={p.n} className="bg-panel p-7">
              <div className="flex items-center justify-between">
                <span className="font-display text-4xl font-light text-rule">
                  {p.n}
                </span>
                <p.icon className="size-5 text-teal" aria-hidden />
              </div>
              <h2 className="font-display mt-5 text-xl font-medium text-ink">
                {p.title}
              </h2>
              <p className="mt-3 text-[13px] leading-relaxed text-ink-2">
                {p.body}
              </p>
            </article>
          ))}
        </div>
      </section>

      {/* ── both directions ── */}
      <section className="border-y border-rule bg-panel">
        <div className="mx-auto max-w-6xl px-6 py-16">
          <div className="section-label">The both-directions thesis</div>
          <div className="mt-8 grid gap-10 md:grid-cols-2">
            <div className="flex gap-4">
              <Landmark className="mt-1 size-5 shrink-0 text-teal" aria-hidden />
              <div>
                <h3 className="font-display text-lg font-medium text-ink">
                  Direction one — the deserving invisible
                </h3>
                <p className="mt-2 text-[13px] leading-relaxed text-ink-2">
                  A kirana store with no credit history but two years of clean,
                  growing, GST-consistent cash flow deserves working capital.
                  The onboarding head prices it: score, band, sanction amount
                  under the 20% working-capital norm, tenure — with every reason
                  signed.
                </p>
              </div>
            </div>
            <div className="flex gap-4">
              <ShieldAlert className="mt-1 size-5 shrink-0 text-oxide" aria-hidden />
              <div>
                <h3 className="font-display text-lg font-medium text-ink">
                  Direction two — the clean-on-paper risk
                </h3>
                <p className="mt-2 text-[13px] leading-relaxed text-ink-2">
                  Declared turnover 40% above bank receipts. Bounces stacking
                  up. A promoter whose last company was struck off in May and
                  reborn in June at the same address. The early-warning head and
                  the entity graph catch what a bureau score never will.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── the three demo dossiers ── */}
      <section className="mx-auto max-w-6xl px-6 py-16 md:py-20">
        <div className="section-label">Three borrowers, three verdicts</div>
        <div className="mt-8 grid gap-4 md:grid-cols-3">
          {personasFixture.map((p) => {
            const s = scoreFixtures[p.id];
            return (
              <Link
                key={p.id}
                href={`/console/${p.id}`}
                className="group rounded-lg border border-rule bg-panel p-6 transition-colors hover:border-teal/50"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="tnum text-[10px] uppercase tracking-[0.14em] text-ink-3">
                      {p.id}
                    </div>
                    <h3 className="font-display mt-1 text-lg font-medium leading-tight text-ink">
                      {p.business}
                    </h3>
                  </div>
                  <Stamp verdict={s.decision.verdict} size="sm" />
                </div>
                <p className="mt-3 text-[12.5px] leading-relaxed text-ink-2">
                  {p.blurb}
                </p>
                <div className="mt-4 flex items-center justify-between border-t border-rule pt-3">
                  <span className="tnum text-sm font-semibold text-ink">
                    {s.score}
                    <span className="ml-1 text-[10px] font-normal text-ink-3">
                      band {s.band}
                    </span>
                  </span>
                  <span className="inline-flex items-center gap-1 font-mono text-[10px] uppercase tracking-[0.12em] text-ink-3 transition-colors group-hover:text-teal">
                    Open card <ArrowRight className="size-3" aria-hidden />
                  </span>
                </div>
              </Link>
            );
          })}
        </div>
      </section>

      {/* ── honesty footer ── */}
      <footer className="border-t border-rule">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-6 py-6">
          <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-3">
            Deterministic core · generative shell — no LLM ever computes a number
          </span>
          <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-3">
            Synthetic demo data · sample registry rows carry is_sample chips
          </span>
        </div>
      </footer>
    </main>
  );
}
