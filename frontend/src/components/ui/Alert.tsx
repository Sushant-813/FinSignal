import { AlertCircle, AlertTriangle, CheckCircle2, Info } from "lucide-react";
import { useId, type ReactNode } from "react";
import { cn } from "../../lib/utils/cn.ts";

export type AlertVariant = "info" | "success" | "warning" | "danger";
export type AlertRole = "status" | "alert" | "region";

export interface AlertProps {
  variant?: AlertVariant | undefined;
  title?: string | undefined;
  children: ReactNode;
  requestId?: string | undefined;
  action?: ReactNode | undefined;
  /**
   * Explicit ARIA role override:
   * - "status" (default): polite, non-interruptive announcement
   * - "alert": urgent announcement reserved for immediate errors
   * - "region": static persistent notice landmark
   */
  role?: AlertRole | undefined;
  "aria-label"?: string | undefined;
  className?: string | undefined;
}

const variantClasses: Record<AlertVariant, string> = {
  info: "bg-tint-info border-info/25 text-text-primary",
  success: "bg-tint-success border-success/25 text-text-primary",
  warning: "bg-tint-warning border-warning/30 text-text-primary",
  danger: "bg-tint-danger border-danger/30 text-text-primary",
};

const iconColorClasses: Record<AlertVariant, string> = {
  info: "text-info",
  success: "text-success",
  warning: "text-warning",
  danger: "text-danger",
};

const variantIcons: Record<AlertVariant, typeof Info> = {
  info: Info,
  success: CheckCircle2,
  warning: AlertTriangle,
  danger: AlertCircle,
};

export function Alert({
  variant = "info",
  title,
  children,
  requestId,
  action,
  role = "status",
  "aria-label": ariaLabel,
  className,
}: AlertProps) {
  const titleId = useId();
  const Icon = variantIcons[variant];

  const regionLabelProps =
    role === "region"
      ? title
        ? { "aria-labelledby": titleId }
        : { "aria-label": ariaLabel ?? `${variant} notice` }
      : ariaLabel
        ? { "aria-label": ariaLabel }
        : {};

  return (
    <div
      role={role}
      {...regionLabelProps}
      className={cn(
        "flex items-start gap-3 rounded-panel border px-4 py-3 text-sm",
        variantClasses[variant],
        className
      )}
    >
      <Icon
        className={cn("mt-0.5 h-4 w-4 shrink-0", iconColorClasses[variant])}
        aria-hidden="true"
      />
      <div className="min-w-0 flex-1 space-y-1">
        {title ? (
          <p id={titleId} className="font-semibold leading-5 text-text-primary">
            {title}
          </p>
        ) : null}
        <div className="text-[13px] leading-[19px] text-text-secondary">{children}</div>
        {requestId ? (
          <p className="text-xs text-text-muted font-mono">Request ID: {requestId}</p>
        ) : null}
      </div>
      {action ? <div className="shrink-0 self-center">{action}</div> : null}
    </div>
  );
}
