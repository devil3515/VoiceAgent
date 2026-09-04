import { motion } from "framer-motion";
import clsx from "clsx";

export type SegmentedTab = {
  id: string;
  label: string;
  icon?: React.ComponentType<{ className?: string }>;
};

type Props = {
  tabs: SegmentedTab[];
  value: string;
  onChange: (id: string) => void;
  disabled?: boolean;
  /** Shared framer layoutId for the active pill — keep consistent across all uses. */
  layoutId?: string;
  className?: string;
  ariaLabel?: string;
};

export function SegmentedTabs({
  tabs,
  value,
  onChange,
  disabled = false,
  layoutId = "segmented-tabs-pill",
  className,
  ariaLabel,
}: Props) {
  return (
    <div
      role="tablist"
      aria-label={ariaLabel}
      className={clsx(
        "inline-flex rounded-lg border border-border bg-bg-1 p-1",
        className,
      )}
    >
      {tabs.map((t) => {
        const active = value === t.id;
        const Icon = t.icon;
        return (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={active}
            aria-controls={`tabpanel-${t.id}`}
            disabled={disabled}
            onClick={() => onChange(t.id)}
            className={clsx(
              "relative inline-flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium",
              "transition-colors",
              "focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 focus-visible:ring-offset-0",
              "disabled:cursor-not-allowed disabled:opacity-60",
              active ? "text-text-0" : "text-text-1 hover:text-text-0",
            )}
          >
            {active && (
              <motion.span
                layoutId={layoutId}
                className="absolute inset-0 rounded-md bg-bg-2"
                transition={{ type: "spring", stiffness: 350, damping: 30 }}
              />
            )}
            {Icon && <Icon className="relative z-10 h-3.5 w-3.5" />}
            <span className="relative z-10">{t.label}</span>
          </button>
        );
      })}
    </div>
  );
}
