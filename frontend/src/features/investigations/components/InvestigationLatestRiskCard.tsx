import { ShieldAlert } from "lucide-react";
import { RiskBadge } from "../../../components/data-display/RiskBadge.tsx";
import { TimestampDisplay } from "../../../components/data-display/TimestampDisplay.tsx";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../../../components/ui/Card.tsx";
import type { InvestigationLatestRiskDTO } from "../types/investigations.types.ts";

export interface InvestigationLatestRiskCardProps {
  readonly riskAnalysis?: InvestigationLatestRiskDTO | null | undefined;
}

export function InvestigationLatestRiskCard({
  riskAnalysis,
}: InvestigationLatestRiskCardProps) {
  return (
    <Card elevated className="space-y-4" data-testid="investigation-latest-risk-card">
      <CardHeader className="pb-2">
        <div className="flex items-center gap-2">
          <ShieldAlert className="h-5 w-5 text-amber-600" aria-hidden="true" />
          <CardTitle size="panel">Latest Risk Intelligence Snapshot</CardTitle>
        </div>
        <CardDescription>
          Authoritative ML risk score and evaluation snapshot recorded for this investigation.
        </CardDescription>
      </CardHeader>

      {!riskAnalysis ? (
        <div className="rounded-card border border-dashed border-border bg-surface-muted/20 p-6 text-center">
          <p className="text-sm text-text-secondary">
            No risk analysis has been scored for the primary transaction.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {/* Risk Level */}
          <div className="rounded-card border border-border bg-surface-muted/30 p-3">
            <p className="text-xs font-medium text-text-secondary">Risk Level</p>
            <div className="mt-1 flex items-center gap-2">
              <RiskBadge level={riskAnalysis.risk_level} size="md" />
            </div>
          </div>

          {/* Risk Score */}
          <div className="rounded-card border border-border bg-surface-muted/30 p-3">
            <p className="text-xs font-medium text-text-secondary">Risk Score</p>
            <p className="mt-1 font-mono text-xl font-bold tabular-nums text-text-primary">
              {riskAnalysis.score.toFixed(4)}
            </p>
          </div>

          {/* Model Version */}
          <div className="rounded-card border border-border bg-surface-muted/30 p-3">
            <p className="text-xs font-medium text-text-secondary">Model Version</p>
            <p className="mt-1 font-mono text-sm font-medium text-text-primary">
              {riskAnalysis.model_version}
            </p>
          </div>

          {/* Scored Timestamp */}
          <div className="rounded-card border border-border bg-surface-muted/30 p-3">
            <p className="text-xs font-medium text-text-secondary">Scored At (UTC)</p>
            <div className="mt-1 text-sm font-medium text-text-primary">
              <TimestampDisplay value={riskAnalysis.created_at} />
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}
