import type { HTMLAttributes } from "react";
import { Badge, type BadgeSize } from "../../../components/ui/Badge.tsx";
import type { InvestigationStatus } from "../types/investigations.types.ts";

export interface InvestigationStatusBadgeProps extends HTMLAttributes<HTMLSpanElement> {
  readonly status: InvestigationStatus;
  readonly size?: BadgeSize | undefined;
}

const statusDisplayMap: Record<
  InvestigationStatus,
  { label: string; variant: "info" | "warning" | "success" }
> = {
  OPEN: {
    label: "Open",
    variant: "info",
  },
  UNDER_REVIEW: {
    label: "Under Review",
    variant: "warning",
  },
  RESOLVED: {
    label: "Resolved",
    variant: "success",
  },
};

export function InvestigationStatusBadge({
  status,
  size = "sm",
  className,
  ...props
}: InvestigationStatusBadgeProps) {
  const config = statusDisplayMap[status] ?? {
    label: status,
    variant: "info" as const,
  };

  return (
    <Badge
      variant={config.variant}
      size={size}
      className={className}
      data-testid={`investigation-status-badge-${status.toLowerCase()}`}
      {...props}
    >
      {config.label}
    </Badge>
  );
}
