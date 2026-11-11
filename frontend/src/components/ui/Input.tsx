import { AlertCircle } from "lucide-react";
import { useId, type InputHTMLAttributes, type Ref } from "react";
import { cn } from "../../lib/utils/cn.ts";

export interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "size"> {
  label?: string | undefined;
  hideLabel?: boolean | undefined;
  hint?: string | undefined;
  error?: string | undefined;
  containerClassName?: string | undefined;
  ref?: Ref<HTMLInputElement> | undefined;
}

export function Input({
  id,
  label,
  hideLabel = false,
  hint,
  error,
  required,
  disabled,
  readOnly,
  className,
  containerClassName,
  ref,
  ...props
}: InputProps) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const hintId = `${inputId}-hint`;
  const errorId = `${inputId}-error`;

  const describedByIds = [hint ? hintId : undefined, error ? errorId : undefined]
    .filter(Boolean)
    .join(" ");

  const surfaceTextClasses = disabled
    ? "bg-surface-subtle text-text-disabled cursor-not-allowed opacity-75"
    : readOnly
      ? "bg-surface-subtle text-text-secondary"
      : "bg-surface text-text-primary";

  const borderClasses = error
    ? "border-danger"
    : disabled || readOnly
      ? "border-border"
      : "border-border-strong";

  return (
    <div className={cn("flex flex-col gap-1.5", containerClassName)}>
      {label ? (
        <label
          htmlFor={inputId}
          className={cn(
            "text-[13px] leading-[19px] font-medium text-text-primary",
            hideLabel && "sr-only"
          )}
        >
          {label}
          {required ? (
            <span className="ml-0.5 text-danger" aria-hidden="true">
              *
            </span>
          ) : null}
        </label>
      ) : null}

      <input
        ref={ref}
        id={inputId}
        required={required}
        disabled={disabled}
        readOnly={readOnly}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedByIds || undefined}
        className={cn(
          "h-9 w-full rounded-control border px-3 text-sm placeholder:text-text-muted transition-colors",
          surfaceTextClasses,
          borderClasses,
          className
        )}
        {...props}
      />

      {hint ? (
        <p id={hintId} className="text-xs leading-4 text-text-muted">
          {hint}
        </p>
      ) : null}

      {error ? (
        <p id={errorId} className="flex items-center gap-1.5 text-xs leading-4 text-danger">
          <AlertCircle className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
          <span>{error}</span>
        </p>
      ) : null}
    </div>
  );
}
