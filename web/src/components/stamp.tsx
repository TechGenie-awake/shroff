import type { Verdict } from "@/lib/types";
import { cn } from "@/lib/utils";

const verdictClass: Record<Verdict, string> = {
  APPROVE: "stamp-approve",
  REFER: "stamp-refer",
  DECLINE: "stamp-decline",
};

export function Stamp({
  verdict,
  size = "md",
  animate = false,
  className,
}: {
  verdict: Verdict;
  size?: "sm" | "md" | "lg";
  animate?: boolean;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "stamp",
        size === "sm" && "stamp-sm",
        size === "lg" && "stamp-lg",
        animate && "stamp-animate",
        verdictClass[verdict],
        className
      )}
      role="status"
      aria-label={`Verdict: ${verdict}`}
    >
      {verdict}
    </span>
  );
}
