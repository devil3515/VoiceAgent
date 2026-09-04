import { motion } from "framer-motion";
import clsx from "clsx";

type Tone = "good" | "bad" | "warn" | "accent" | "neutral";

const dotColors: Record<Tone, string> = {
  good: "bg-good shadow-[0_0_8px_2px_rgba(52,211,153,0.45)]",
  bad: "bg-bad shadow-[0_0_8px_2px_rgba(248,113,113,0.45)]",
  warn: "bg-warn shadow-[0_0_8px_2px_rgba(251,191,36,0.45)]",
  accent: "bg-accent shadow-[0_0_8px_2px_rgba(124,92,255,0.45)]",
  neutral: "bg-text-2",
};

const ringColors: Record<Tone, string> = {
  good: "bg-good/60",
  bad: "bg-bad/60",
  warn: "bg-warn/60",
  accent: "bg-accent/60",
  neutral: "bg-text-2/40",
};

export function PulseDot({
  active = true,
  tone = "good",
  size = 8,
  className,
}: {
  active?: boolean;
  tone?: Tone;
  size?: number;
  className?: string;
}) {
  return (
    <span
      className={clsx("relative inline-flex items-center justify-center", className)}
      style={{ width: size, height: size }}
      aria-hidden
    >
      {active && (
        <>
          <motion.span
            className={clsx("absolute inset-0 rounded-full", ringColors[tone])}
            initial={{ scale: 1, opacity: 0.6 }}
            animate={{ scale: 2.6, opacity: 0 }}
            transition={{ duration: 1.4, repeat: Infinity, ease: "easeOut" }}
          />
          <motion.span
            className={clsx("absolute inset-0 rounded-full", ringColors[tone])}
            initial={{ scale: 1, opacity: 0.5 }}
            animate={{ scale: 2.2, opacity: 0 }}
            transition={{
              duration: 1.4,
              repeat: Infinity,
              ease: "easeOut",
              delay: 0.7,
            }}
          />
        </>
      )}
      <span
        className={clsx("relative rounded-full", dotColors[tone])}
        style={{ width: size, height: size }}
      />
    </span>
  );
}
