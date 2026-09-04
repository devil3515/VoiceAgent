import { forwardRef, type InputHTMLAttributes, type TextareaHTMLAttributes, type ReactNode } from "react";
import clsx from "clsx";

const baseField =
  "w-full rounded-lg border border-border bg-bg-2 px-3 py-2 text-sm text-text-0 " +
  "placeholder:text-text-2 outline-none transition-colors " +
  "focus:border-accent/70 focus:ring-2 focus:ring-accent/30 " +
  "disabled:opacity-60 disabled:cursor-not-allowed";

type FieldProps = {
  label?: ReactNode;
  hint?: ReactNode;
  error?: ReactNode;
};

export const Input = forwardRef<
  HTMLInputElement,
  InputHTMLAttributes<HTMLInputElement> & FieldProps
>(function Input({ label, hint, error, className, id, ...rest }, ref) {
  const inputId = id ?? rest.name;
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label htmlFor={inputId} className="text-xs font-medium text-text-1">
          {label}
        </label>
      )}
      <input
        ref={ref}
        id={inputId}
        className={clsx(baseField, className)}
        {...rest}
      />
      {error ? (
        <p className="text-xs text-bad">{error}</p>
      ) : hint ? (
        <p className="text-xs text-text-2">{hint}</p>
      ) : null}
    </div>
  );
});

export const Textarea = forwardRef<
  HTMLTextAreaElement,
  TextareaHTMLAttributes<HTMLTextAreaElement> & FieldProps
>(function Textarea({ label, hint, error, className, id, ...rest }, ref) {
  const tid = id ?? rest.name;
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label htmlFor={tid} className="text-xs font-medium text-text-1">
          {label}
        </label>
      )}
      <textarea
        ref={ref}
        id={tid}
        className={clsx(baseField, "min-h-[88px] resize-y", className)}
        {...rest}
      />
      {error ? (
        <p className="text-xs text-bad">{error}</p>
      ) : hint ? (
        <p className="text-xs text-text-2">{hint}</p>
      ) : null}
    </div>
  );
});

export const Checkbox = forwardRef<
  HTMLInputElement,
  InputHTMLAttributes<HTMLInputElement> & { label?: ReactNode }
>(function Checkbox({ label, className, id, ...rest }, ref) {
  const cid = id ?? rest.name;
  return (
    <label
      htmlFor={cid}
      className="inline-flex items-center gap-2 text-sm text-text-1 select-none cursor-pointer"
    >
      <input
        ref={ref}
        id={cid}
        type="checkbox"
        className={clsx(
          "h-4 w-4 rounded border border-border bg-bg-2",
          "accent-accent",
          className,
        )}
        {...rest}
      />
      {label}
    </label>
  );
});
