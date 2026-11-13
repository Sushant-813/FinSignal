import type { HTMLAttributes } from "react";
import { Badge, type BadgeSize, type BadgeVariant } from "../../../components/ui/Badge.tsx";
import type { InvestigationPriority } from "../types/investigations.types.ts";

export interface InvestigationPriorityBadgeProps extends HTMLAttributes<HTMLSpanElement> {
  readonly priority: InvestigationPriority;
  readonly size?: BadgeSize | undefined;
}

const priorityDisplayMap: Record<InvestigationPriority, { label: string; variant: BadgeVariant }> =
  {
    LOW: {
      label: "Low",
      variant: "neutral",
    },
    MEDIUM: {
      label: "Medium",
      variant: "info",
    },
    HIGH: {
      label: "High",
      variant: "warning",
    },
    CRITICAL: {
      label: "Critical",
      variant: "danger",
    },
  };

export function InvestigationPriorityBadge({
  priority,
  size = "sm",
  className,
  ...props
}: InvestigationPriorityBadgeProps) {
  const config = priorityDisplayMap[priority] ?? {
    label: priority,
    variant: "neutral" as const,
  };

  return (
    <Badge
      variant={config.variant}
      size={size}
      className={className}
      data-testid={`investigation-priority-badge-${priority.toLowerCase()}`}
      {...props}
    >
      {config.label}
    </Badge>
  );
}
