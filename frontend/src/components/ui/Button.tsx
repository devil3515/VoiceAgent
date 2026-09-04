import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";
import { motion } from "framer-motion";
import clsx from "clsx";
import { Loader2 } from "lucide-react";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

type Props = Omit<ButtonHTMLAttributes<HTMLButtonElement>, "ref"> & {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  iconLeft?: ReactNode;
  iconRight?: ReactNode;
};

const variants: Record<Variant, string> = {
  primary:
    "bg-gradient-to-br from-accent to-accent-2 text-white shadow-[0_8px_30px_-12px_rgba(124,92,255,0.6)] hover:from-[#8a6dff] hover:to-[#3ddcec]",
  secondary:
    "bg-bg-2 text-text-0 border border-border hover:border-[#2e3454] hover:bg-[#1d2034]",
  ghost: "text-text-1 hover:text-text-0 hover:bg-bg-2",
  danger:
    "bg-bad/15 text-bad border border-bad/30 hover:bg-bad/25",
};

const sizes: Record<Size, string> = {
  sm: "h-8 px-3 text-xs gap-1.5 rounded-md",
  md: "h-10 px-4 text-sm gap-2 rounded-lg",
  lg: "h-12 px-5 text-[15px] gap-2 rounded-xl",
};

export const Button = forwardRef<HTMLButtonElement, Props>(function Button(
  {
    variant = "primary",
    size = "md",
    loading = false,
    disabled,
    className,
    children,
    iconLeft,
    iconRight,
    type = "button",
    onClick,
    name,
    value,
    form,
    autoFocus,
    title,
    "aria-label": ariaLabel,
  },
  ref,
) {
  return (
    <motion.button
      ref={ref}
      type={type}
      whileTap={{ scale: 0.98 }}
      whileHover={{ scale: 1.02 }}
      transition={{ duration: 0.12 }}
      disabled={disabled || loading}
      onClick={onClick}
      name={name}
      value={value}
      form={form}
      autoFocus={autoFocus}
      title={title}
      aria-label={ariaLabel}
      className={clsx(
        "inline-flex items-center justify-center font-medium select-none transition-colors",
        "focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 focus-visible:ring-offset-0",
        "disabled:opacity-50 disabled:cursor-not-allowed",
        variants[variant],
        sizes[size],
        className,
      )}
    >
      {loading ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : (
        iconLeft
      )}
      <span>{children}</span>
      {!loading && iconRight}
    </motion.button>
  );
});
