import { Slot } from "@radix-ui/react-slot";
import { Loader2 } from "lucide-react";
import type { ButtonHTMLAttributes, HTMLAttributes, ReactElement, Ref } from "react";
import { cn } from "../../lib/utils/cn.ts";

export type ButtonVariant = "primary" | "secondary" | "tertiary" | "danger";
export type ButtonSize = "sm" | "md" | "lg" | "icon";

interface ButtonCommonProps {
  variant?: ButtonVariant | undefined;
  size?: ButtonSize | undefined;
  className?: string | undefined;
}

export interface ButtonNativeProps
  extends ButtonCommonProps, Omit<ButtonHTMLAttributes<HTMLButtonElement>, "disabled"> {
  asChild?: false | undefined;
  disabled?: boolean | undefined;
  isLoading?: boolean | undefined;
  ref?: Ref<HTMLButtonElement> | undefined;
}

export interface ButtonSlotProps
  extends ButtonCommonProps, Omit<HTMLAttributes<HTMLElement>, "children"> {
  asChild: true;
  children: ReactElement;
  disabled?: never;
  isLoading?: never;
}

export type ButtonProps = ButtonNativeProps | ButtonSlotProps;

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "bg-brand-700 text-text-inverse border border-transparent hover:bg-brand-800 active:bg-brand-800",
  secondary:
    "bg-surface text-text-primary border border-border-strong hover:bg-surface-hover active:bg-surface-subtle",
  tertiary:
    "bg-transparent text-text-primary border border-transparent hover:bg-surface-subtle active:bg-border",
  danger:
    "bg-danger text-text-inverse border border-transparent hover:opacity-90 active:opacity-85",
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: "h-8 px-3 text-[13px] gap-1.5",
  md: "h-9 px-4 text-sm gap-2",
  lg: "h-10 px-5 text-sm gap-2",
  icon: "h-9 w-9 p-0",
};

const baseClasses =
  "inline-flex items-center justify-center rounded-control font-medium transition-colors whitespace-nowrap select-none cursor-pointer disabled:pointer-events-none disabled:opacity-50";

export function Button(props: ButtonProps) {
  if (props.asChild) {
    const rawProps = props as ButtonSlotProps & { disabled?: unknown; isLoading?: unknown };
    if (
      import.meta.env.DEV &&
      (rawProps.disabled !== undefined || rawProps.isLoading !== undefined)
    ) {
      throw new Error(
        "Button: 'disabled' and 'isLoading' cannot be used with 'asChild'. Render a disabled <button> instead."
      );
    }

    const {
      asChild,
      variant = "primary",
      size = "md",
      className,
      children,
      disabled,
      isLoading,
      ...slotRest
    } = rawProps;
    void asChild;
    void disabled;
    void isLoading;
    const classes = cn(baseClasses, variantClasses[variant], sizeClasses[size], className);

    return (
      <Slot className={classes} {...slotRest}>
        {children}
      </Slot>
    );
  }

  const {
    asChild,
    variant = "primary",
    size = "md",
    className,
    disabled = false,
    isLoading = false,
    type = "button",
    children,
    ref,
    ...nativeRest
  } = props;
  void asChild;

  const classes = cn(baseClasses, variantClasses[variant], sizeClasses[size], className);
  const isDisabled = Boolean(disabled || isLoading);

  return (
    <button
      ref={ref}
      type={type}
      disabled={isDisabled}
      aria-busy={isLoading ? true : undefined}
      className={classes}
      {...nativeRest}
    >
      {isLoading ? <Loader2 className="h-4 w-4 animate-spin shrink-0" aria-hidden="true" /> : null}
      {children}
    </button>
  );
}
