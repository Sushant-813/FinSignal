import type { HTMLAttributes } from "react";
import { Badge, type BadgeSize, type BadgeVariant } from "../../../components/ui/Badge.tsx";
import type { InvestigationResolution } from "../types/investigations.types.ts";

export interface InvestigationResolutionBadgeProps extends HTMLAttributes<HTMLSpanElement> {
  readonly resolution: InvestigationResolution;
  readonly size?: BadgeSize | undefined;
}

const resolutionDisplayMap: Record<
  InvestigationResolution,
  { label: string; variant: BadgeVariant }
> = {
  LEGITIMATE: {
    label: "Legitimate",
    variant: "success",
  },
  SUSPICIOUS: {
    label: "Suspicious",
    variant: "warning",
  },
  CONFIRMED_FRAUD: {
    label: "Confirmed Fraud",
    variant: "danger",
  },
  INCONCLUSIVE: {
    label: "Inconclusive",
    variant: "neutral",
  },
};

export function InvestigationResolutionBadge({
  resolution,
  size = "sm",
  className,
  ...props
}: InvestigationResolutionBadgeProps) {
  const config = resolutionDisplayMap[resolution] ?? {
    label: resolution,
    variant: "neutral" as const,
  };

  return (
    <Badge
      variant={config.variant}
      size={size}
      className={className}
      data-testid={`investigation-resolution-badge-${resolution.toLowerCase()}`}
      {...props}
    >
      {config.label}
    </Badge>
  );
}
