import { CheckCircle2, Lock } from "lucide-react";
import { TimestampDisplay } from "../../../components/data-display/TimestampDisplay.tsx";
import type { InvestigationDetailResponse } from "../types/investigations.types.ts";
import { InvestigationResolutionBadge } from "./InvestigationResolutionBadge.tsx";

export interface InvestigationResolutionBannerProps {
  readonly investigation: InvestigationDetailResponse;
}

export function InvestigationResolutionBanner({
  investigation,
}: InvestigationResolutionBannerProps) {
  if (investigation.status !== "RESOLVED") {
    return null;
  }

  return (
    <div
      className="rounded-panel border border-emerald-500/30 bg-emerald-50/50 p-5 shadow-card dark:bg-emerald-950/20"
      data-testid="investigation-resolution-banner"
    >
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-emerald-600" aria-hidden="true" />
            <h2 className="text-base font-semibold text-text-primary">
              Investigation Formally Resolved
            </h2>
            {investigation.resolution && (
              <InvestigationResolutionBadge resolution={investigation.resolution} size="md" />
            )}
          </div>

          {investigation.resolution_notes && (
            <div className="rounded-card border border-border bg-surface p-3 text-sm text-text-primary">
              <p className="text-xs font-medium text-text-secondary">Resolution Notes:</p>
              <p className="mt-1 whitespace-pre-wrap">{investigation.resolution_notes}</p>
            </div>
          )}

          <div className="flex flex-wrap items-center gap-4 text-xs text-text-secondary">
            {investigation.assigned_user_email && (
              <span>
                Resolved by:{" "}
                <strong className="text-text-primary">{investigation.assigned_user_email}</strong>
              </span>
            )}
            <span>
              Updated at: <TimestampDisplay value={investigation.updated_at} />
            </span>
          </div>
        </div>

        <div className="flex items-center gap-1.5 self-start rounded-full border border-border bg-surface px-3 py-1 text-xs font-medium text-text-muted">
          <Lock className="h-3.5 w-3.5" aria-hidden="true" />
          <span>Case Read-Only</span>
        </div>
      </div>
    </div>
  );
}
