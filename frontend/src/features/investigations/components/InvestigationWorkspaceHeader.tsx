import { CheckCircle, Play, SlidersHorizontal, UserCheck, UserPlus, UserX } from "lucide-react";
import { TimestampDisplay } from "../../../components/data-display/TimestampDisplay.tsx";
import { Alert } from "../../../components/ui/Alert.tsx";
import { Button } from "../../../components/ui/Button.tsx";
import { getUserFriendlyErrorMessage, isApiClientError } from "../../../lib/api/errors.ts";
import {
  canAdminAssignInvestigation,
  canResolveInvestigation,
  canSelfAssignInvestigation,
  canSelfUnassignInvestigation,
  canTransitionInvestigation,
  canUpdateInvestigationPriority,
} from "../../../lib/permissions/capabilities.ts";
import { useAuth } from "../../auth/hooks/useAuth.ts";
import { usePatchInvestigationMutation } from "../hooks/usePatchInvestigationMutation.ts";
import type { InvestigationDetailResponse } from "../types/investigations.types.ts";
import { InvestigationPriorityBadge } from "./InvestigationPriorityBadge.tsx";
import { InvestigationStatusBadge } from "./InvestigationStatusBadge.tsx";

export interface InvestigationWorkspaceHeaderProps {
  readonly investigation: InvestigationDetailResponse;
  readonly onOpenAssignDialog: () => void;
  readonly onOpenPriorityDialog: () => void;
  readonly onOpenResolveDialog: () => void;
}

export function InvestigationWorkspaceHeader({
  investigation,
  onOpenAssignDialog,
  onOpenPriorityDialog,
  onOpenResolveDialog,
}: InvestigationWorkspaceHeaderProps) {
  const { user } = useAuth();

  const patchMutation = usePatchInvestigationMutation(investigation.id);

  const canSelfAssign = canSelfAssignInvestigation(user, investigation);
  const canSelfUnassign = canSelfUnassignInvestigation(user, investigation);
  const canAdminAssign = canAdminAssignInvestigation(user, investigation);
  const canUpdatePriority = canUpdateInvestigationPriority(user, investigation);
  const canTransition = canTransitionInvestigation(user, investigation);
  const canResolve = canResolveInvestigation(user, investigation);

  const handleSelfAssign = () => {
    if (user?.id) {
      patchMutation.mutate({ assigned_to: user.id });
    }
  };

  const handleSelfUnassign = () => {
    patchMutation.mutate({ assigned_to: null });
  };

  const handleBeginReview = () => {
    patchMutation.mutate({ status: "UNDER_REVIEW" });
  };

  const isPending = patchMutation.isPending;
  const err = patchMutation.error;
  const isClientErr = isApiClientError(err);
  let conflictMessage: string | null = null;
  if (isClientErr && (err.status === 409 || err.code === "CASE_ALREADY_ASSIGNED")) {
    conflictMessage =
      "State conflict: this investigation was modified or claimed concurrently. Authoritative state has been reloaded.";
  }

  return (
    <div className="space-y-4 rounded-panel border border-border bg-surface p-5 shadow-card">
      {conflictMessage && (
        <Alert variant="warning" role="alert" title="Concurrency Conflict">
          {conflictMessage}
        </Alert>
      )}

      {patchMutation.isError && !conflictMessage && (
        <Alert
          variant="danger"
          role="alert"
          title="Action failed"
          requestId={isClientErr ? err.requestId : undefined}
        >
          {getUserFriendlyErrorMessage(err)}
        </Alert>
      )}

      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        {/* Title and metadata */}
        <div className="space-y-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-[22px] font-bold tracking-tight text-text-primary">
              Investigation Case
            </h1>
            <span className="font-mono text-sm text-text-muted" title={investigation.id}>
              #{investigation.id.slice(0, 8)}
            </span>
            <InvestigationStatusBadge status={investigation.status} size="md" />
            <InvestigationPriorityBadge priority={investigation.priority} size="md" />
          </div>

          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-text-secondary">
            <div>
              Assignee:{" "}
              {investigation.assigned_to ? (
                <strong className="text-text-primary">
                  {investigation.assigned_user_email ?? investigation.assigned_to.slice(0, 8)}
                </strong>
              ) : (
                <span className="italic text-text-muted">Unassigned</span>
              )}
            </div>
            <div>
              Created: <TimestampDisplay value={investigation.created_at} />
            </div>
            <div>
              Updated: <TimestampDisplay value={investigation.updated_at} />
            </div>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Self-Assign (Take Case) */}
          {canSelfAssign && (
            <Button
              type="button"
              variant="primary"
              size="sm"
              onClick={handleSelfAssign}
              disabled={isPending}
              data-testid="take-case-button"
            >
              <UserCheck className="h-4 w-4" aria-hidden="true" />
              {isPending ? "Claiming…" : "Take Case"}
            </Button>
          )}

          {/* Self-Unassign (Release Case) */}
          {canSelfUnassign && (
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={handleSelfUnassign}
              disabled={isPending}
              data-testid="release-case-button"
            >
              <UserX className="h-4 w-4" aria-hidden="true" />
              {isPending ? "Releasing…" : "Release Case"}
            </Button>
          )}

          {/* Admin Assign / Reassign */}
          {canAdminAssign && (
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={onOpenAssignDialog}
              disabled={isPending}
              data-testid="admin-assign-button"
            >
              <UserPlus className="h-4 w-4" aria-hidden="true" />
              Assign Case
            </Button>
          )}

          {/* Priority */}
          {canUpdatePriority && (
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={onOpenPriorityDialog}
              disabled={isPending}
              data-testid="change-priority-button"
            >
              <SlidersHorizontal className="h-4 w-4" aria-hidden="true" />
              Priority
            </Button>
          )}

          {/* Transition: OPEN -> UNDER_REVIEW */}
          {canTransition && (
            <Button
              type="button"
              variant="primary"
              size="sm"
              onClick={handleBeginReview}
              disabled={isPending}
              data-testid="begin-review-button"
            >
              <Play className="h-4 w-4" aria-hidden="true" />
              {isPending ? "Starting…" : "Begin Review"}
            </Button>
          )}

          {/* Resolve Case */}
          {canResolve && (
            <Button
              type="button"
              variant="primary"
              size="sm"
              onClick={onOpenResolveDialog}
              disabled={isPending}
              data-testid="resolve-case-button"
            >
              <CheckCircle className="h-4 w-4" aria-hidden="true" />
              Resolve Case
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
