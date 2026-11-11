import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "../../lib/utils/cn.ts";

export type BadgeVariant =
  | "neutral"
  | "brand"
  | "info"
  | "success"
  | "warning"
  | "danger"
  | "risk-low"
  | "risk-medium"
  | "risk-high"
  | "risk-critical";

export type BadgeSize = "sm" | "md";

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant | undefined;
  size?: BadgeSize | undefined;
  icon?: ReactNode | undefined;
}

const variantClasses: Record<BadgeVariant, string> = {
  neutral: "bg-tint-neutral text-text-secondary border-border",
  brand: "bg-brand-100 text-brand-700 border-brand-100",
  info: "bg-tint-info text-info border-border",
  success: "bg-tint-success text-success border-border",
  warning: "bg-tint-warning text-warning border-border",
  danger: "bg-tint-danger text-danger border-border",
  "risk-low": "bg-tint-risk-low text-risk-low border-border",
  "risk-medium": "bg-tint-risk-medium text-risk-medium border-border",
  "risk-high": "bg-tint-risk-high text-risk-high border-border",
  "risk-critical": "bg-tint-risk-critical text-risk-critical border-risk-critical/30 font-semibold",
};

const sizeClasses: Record<BadgeSize, string> = {
  sm: "px-2 py-0.5 text-xs gap-1",
  md: "px-2.5 py-1 text-xs gap-1.5",
};

export function Badge({
  variant = "neutral",
  size = "sm",
  icon,
  className,
  children,
  ...props
}: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-badge border font-medium leading-4 whitespace-nowrap",
        variantClasses[variant],
        sizeClasses[size],
        className
      )}
      {...props}
    >
      {icon ? (
        <span className="inline-flex shrink-0 items-center" aria-hidden="true">
          {icon}
        </span>
      ) : null}
      <span>{children}</span>
    </span>
  );
}
