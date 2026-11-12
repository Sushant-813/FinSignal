import { AlertOctagon, AlertTriangle, Flame, HelpCircle, ShieldCheck } from "lucide-react";
import type { ReactNode } from "react";
import { Badge, type BadgeSize, type BadgeVariant } from "../ui/Badge.tsx";

export type KnownRiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface RiskBadgeProps {
  level: string | null | undefined;
  size?: BadgeSize | undefined;
  unlabeledFallback?: string | undefined;
  className?: string | undefined;
}

interface RiskPresentation {
  readonly variant: BadgeVariant;
  readonly label: string;
  readonly icon: ReactNode;
}

const RISK_PRESENTATION: Record<KnownRiskLevel, RiskPresentation> = {
  LOW: {
    variant: "risk-low",
    label: "LOW RISK",
    icon: <ShieldCheck className="h-3.5 w-3.5" />,
  },
  MEDIUM: {
    variant: "risk-medium",
    label: "MEDIUM RISK",
    icon: <AlertTriangle className="h-3.5 w-3.5" />,
  },
  HIGH: {
    variant: "risk-high",
    label: "HIGH RISK",
    icon: <AlertOctagon className="h-3.5 w-3.5" />,
  },
  CRITICAL: {
    variant: "risk-critical",
    label: "CRITICAL RISK",
    icon: <Flame className="h-3.5 w-3.5" />,
  },
};

export function RiskBadge({
  level,
  size = "sm",
  unlabeledFallback = "Not analyzed",
  className,
}: RiskBadgeProps) {
  const normalized = typeof level === "string" ? level.trim().toUpperCase() : "";
  if (
    normalized === "LOW" ||
    normalized === "MEDIUM" ||
    normalized === "HIGH" ||
    normalized === "CRITICAL"
  ) {
    const config = RISK_PRESENTATION[normalized];
    return (
      <Badge variant={config.variant} size={size} icon={config.icon} className={className}>
        {config.label}
      </Badge>
    );
  }

  return (
    <Badge
      variant="neutral"
      size={size}
      icon={<HelpCircle className="h-3.5 w-3.5" />}
      className={className}
    >
      {unlabeledFallback}
    </Badge>
  );
}
