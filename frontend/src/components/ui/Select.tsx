import * as SelectPrimitive from "@radix-ui/react-select";
import { AlertCircle, Check, ChevronDown } from "lucide-react";
import { useId } from "react";
import { cn } from "../../lib/utils/cn.ts";

export interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean | undefined;
}

export interface SelectProps {
  id?: string | undefined;
  name?: string | undefined;
  label?: string | undefined;
  hideLabel?: boolean | undefined;
  placeholder?: string | undefined;
  value?: string | undefined;
  defaultValue?: string | undefined;
  onValueChange?: ((value: string) => void) | undefined;
  options: ReadonlyArray<SelectOption>;
  disabled?: boolean | undefined;
  required?: boolean | undefined;
  hint?: string | undefined;
  error?: string | undefined;
  className?: string | undefined;
  containerClassName?: string | undefined;
}

export function Select({
  id,
  name,
  label,
  hideLabel = false,
  placeholder = "Select an option",
  value,
  defaultValue,
  onValueChange,
  options,
  disabled = false,
  required = false,
  hint,
  error,
  className,
  containerClassName,
}: SelectProps) {
  if (options.some((opt) => opt.value === "")) {
    throw new Error(
      "Select: option values must be non-empty strings because Radix Select reserves '' for placeholder state."
    );
  }

  const generatedId = useId();
  const triggerId = id ?? generatedId;
  const labelId = `${triggerId}-label`;
  const hintId = `${triggerId}-hint`;
  const errorId = `${triggerId}-error`;

  const describedByIds = [hint ? hintId : undefined, error ? errorId : undefined]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={cn("flex flex-col gap-1.5", containerClassName)}>
      {label ? (
        <label
          id={labelId}
          htmlFor={triggerId}
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

      <SelectPrimitive.Root
        {...(value !== undefined ? { value } : {})}
        {...(defaultValue !== undefined ? { defaultValue } : {})}
        {...(onValueChange !== undefined ? { onValueChange } : {})}
        {...(name !== undefined ? { name } : {})}
        disabled={disabled}
        required={required}
      >
        <SelectPrimitive.Trigger
          id={triggerId}
          aria-labelledby={label ? labelId : undefined}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedByIds || undefined}
          className={cn(
            "inline-flex h-9 w-full items-center justify-between gap-2 rounded-control border border-border-strong bg-surface px-3 text-sm text-text-primary transition-colors cursor-pointer data-[placeholder]:text-text-muted disabled:bg-surface-subtle disabled:text-text-disabled disabled:cursor-not-allowed",
            error && "border-danger",
            className
          )}
        >
          <SelectPrimitive.Value placeholder={placeholder} />
          <SelectPrimitive.Icon asChild>
            <ChevronDown className="h-4 w-4 shrink-0 text-text-muted" aria-hidden="true" />
          </SelectPrimitive.Icon>
        </SelectPrimitive.Trigger>

        <SelectPrimitive.Portal>
          <SelectPrimitive.Content
            position="popper"
            sideOffset={4}
            className="z-50 min-w-[var(--radix-select-trigger-width)] max-h-60 overflow-hidden rounded-control border border-border bg-surface text-text-primary shadow-overlay"
          >
            <SelectPrimitive.Viewport className="p-1">
              {options.map((option) => (
                <SelectPrimitive.Item
                  key={option.value}
                  value={option.value}
                  disabled={Boolean(option.disabled)}
                  className="relative flex w-full cursor-pointer select-none items-center rounded-badge py-1.5 pl-8 pr-3 text-sm text-text-primary outline-none data-[highlighted]:bg-surface-hover data-[state=checked]:bg-brand-50 data-[state=checked]:text-brand-700 data-[disabled]:pointer-events-none data-[disabled]:text-text-disabled"
                >
                  <span className="absolute left-2.5 flex h-3.5 w-3.5 items-center justify-center">
                    <SelectPrimitive.ItemIndicator>
                      <Check className="h-3.5 w-3.5 text-brand-700" aria-hidden="true" />
                    </SelectPrimitive.ItemIndicator>
                  </span>
                  <SelectPrimitive.ItemText>{option.label}</SelectPrimitive.ItemText>
                </SelectPrimitive.Item>
              ))}
            </SelectPrimitive.Viewport>
          </SelectPrimitive.Content>
        </SelectPrimitive.Portal>
      </SelectPrimitive.Root>

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
