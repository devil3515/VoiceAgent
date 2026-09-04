import type { HTMLAttributes, ReactNode } from "react";
import clsx from "clsx";

type Props = HTMLAttributes<HTMLDivElement> & {
  children: ReactNode;
  /** Adds a subtle inner glow at the top edge. */
  glow?: boolean;
  /** Reduces padding to 12px instead of 20px. */
  dense?: boolean;
};

export function Card({ children, className, glow, dense, ...rest }: Props) {
  return (
    <div
      className={clsx(
        "relative rounded-xl border border-border bg-bg-1/70 backdrop-blur-md",
        dense ? "p-3" : "p-5",
        "transition-colors duration-150 hover:border-[#2e3454]",
        className,
      )}
      {...rest}
    >
      {glow && (
        <div
          aria-hidden
          className="pointer-events-none absolute inset-x-0 -top-px h-px bg-gradient-to-r from-transparent via-accent/60 to-transparent"
        />
      )}
      {children}
    </div>
  );
}

export function CardHeader({
  title,
  subtitle,
  right,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  right?: ReactNode;
}) {
  return (
    <div className="mb-4 flex items-start justify-between gap-3">
      <div>
        <h3 className="text-[15px] font-semibold tracking-tight text-text-0">
          {title}
        </h3>
        {subtitle && (
          <p className="mt-0.5 text-xs text-text-2">{subtitle}</p>
        )}
      </div>
      {right}
    </div>
  );
}
