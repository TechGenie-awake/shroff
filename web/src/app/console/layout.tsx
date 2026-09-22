"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const SECTIONS = [
  { href: "/console", label: "Portfolio" },
  { href: "/console/demo", label: "Live demo" },
] as const;

export default function ConsoleLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isDetail = /^\/console\/[^/]+$/.test(pathname) && pathname !== "/console/demo";

  return (
    <div className="min-h-screen bg-paper">
      <div className="sticky top-0 z-20 border-b border-rule bg-paper/95 backdrop-blur supports-[backdrop-filter]:bg-paper/80">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-6 px-6 py-3.5">
          <Link
            href="/"
            className="font-display flex items-baseline gap-2.5 text-lg font-semibold tracking-tight text-ink"
          >
            SHROFF
            <span className="font-mono text-[10px] font-normal uppercase tracking-[0.16em] text-ink-3">
              Underwriter&rsquo;s console
            </span>
          </Link>

          {!isDetail && (
            <nav className="flex items-center gap-1 rounded-lg border border-rule bg-panel p-1">
              {SECTIONS.map((s) => {
                const active = pathname === s.href;
                return (
                  <Link
                    key={s.href}
                    href={s.href}
                    className={cn(
                      "rounded-md px-3.5 py-1.5 font-mono text-[11px] uppercase tracking-[0.12em] transition-colors",
                      active
                        ? "bg-teal/10 text-teal"
                        : "text-ink-2 hover:text-ink"
                    )}
                  >
                    {s.label}
                  </Link>
                );
              })}
            </nav>
          )}
        </div>
      </div>
      {children}
    </div>
  );
}
