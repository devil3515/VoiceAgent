import type { ReactNode } from "react";
import clsx from "clsx";

type Tone = "neutral" | "good" | "warn" | "bad" | "accent";

const tones: Record<Tone, string> = {
  neutral: "bg-bg-2 text-text-1 border-border",
  good: "bg-good/15 text-good border-good/30",
  warn: "bg-warn/15 text-warn border-warn/30",
  bad: "bg-bad/15 text-bad border-bad/30",
  accent: "bg-accent/15 text-accent border-accent/30",
};

export function Badge({
  children,
  tone = "neutral",
  className,
}: {
  children: ReactNode;
  tone?: Tone;
  className?: string;
}) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium",
        tones[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}
