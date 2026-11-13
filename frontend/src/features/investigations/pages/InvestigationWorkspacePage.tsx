import { ArrowLeft, RefreshCw } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router";
import { Alert } from "../../../components/ui/Alert.tsx";
import { Button } from "../../../components/ui/Button.tsx";
import { Skeleton } from "../../../components/ui/Skeleton.tsx";
import {
  getUserFriendlyErrorMessage,
  isApiClientError,
  isForbiddenError,
} from "../../../lib/api/errors.ts";
import {
  canLinkInvestigationTransaction,
  canViewInvestigations,
} from "../../../lib/permissions/capabilities.ts";
import { useAuth } from "../../auth/hooks/useAuth.ts";
import { InvestigationAiSummaryPlaceholderCard } from "../components/InvestigationAiSummaryPlaceholderCard.tsx";
import { InvestigationAssignDialog } from "../components/InvestigationAssignDialog.tsx";
import { InvestigationEvidencePlaceholderCard } from "../components/InvestigationEvidencePlaceholderCard.tsx";
import { InvestigationLatestRiskCard } from "../components/InvestigationLatestRiskCard.tsx";
import { InvestigationLinkTransactionDialog } from "../components/InvestigationLinkTransactionDialog.tsx";
import { InvestigationPrimaryTransactionCard } from "../components/InvestigationPrimaryTransactionCard.tsx";
import { InvestigationPriorityDialog } from "../components/InvestigationPriorityDialog.tsx";
import { InvestigationRelatedTransactionsCard } from "../components/InvestigationRelatedTransactionsCard.tsx";
import { InvestigationResolutionBanner } from "../components/InvestigationResolutionBanner.tsx";
import { InvestigationResolveDialog } from "../components/InvestigationResolveDialog.tsx";
import { InvestigationWorkspaceHeader } from "../components/InvestigationWorkspaceHeader.tsx";
import { useInvestigationDetailQuery } from "../hooks/useInvestigationDetailQuery.ts";
import { UUID_REGEX } from "../schemas/investigation-filter-schema.ts";

export function InvestigationWorkspacePage() {
  const { investigationId = "" } = useParams<{ investigationId: string }>();
  const { user } = useAuth();

  const [isAssignOpen, setIsAssignOpen] = useState(false);
  const [isPriorityOpen, setIsPriorityOpen] = useState(false);
  const [isLinkOpen, setIsLinkOpen] = useState(false);
  const [isResolveOpen, setIsResolveOpen] = useState(false);

  const isValidUuid = UUID_REGEX.test(investigationId);
  const detailQuery = useInvestigationDetailQuery(investigationId, isValidUuid);

  if (!canViewInvestigations(user)) {
    return (
      <div className="mx-auto max-w-7xl space-y-6">
        <Alert variant="warning" role="alert" title="Access restricted">
          Your account does not have permission to view investigation workspaces.
        </Alert>
      </div>
    );
  }

  const err = detailQuery.error;
  const isNotFound = isApiClientError(err) && err.status === 404;
  const isForbidden = isForbiddenError(err);

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      {/* Navigation breadcrumb link */}
      <div>
        <Link
          to="/investigations"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-brand-700 hover:text-brand-800 hover:underline"
          aria-label="Back to investigation queue"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Back to Investigations
        </Link>
      </div>

      {!isValidUuid ? (
        <Alert variant="warning" role="alert" title="Invalid investigation identifier">
          The investigation ID in the URL is not a valid UUID. Please return to the queue and select
          a valid case.
        </Alert>
      ) : detailQuery.isLoading ? (
        <div className="space-y-4" aria-label="Loading investigation workspace">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-64 w-full" />
          <Skeleton className="h-48 w-full" />
        </div>
      ) : detailQuery.isError ? (
        <Alert
          variant={isNotFound || isForbidden ? "warning" : "danger"}
          role="alert"
          title={
            isNotFound
              ? "Investigation case not found"
              : isForbidden
                ? "Access denied"
                : "Unable to load investigation"
          }
          requestId={isApiClientError(err) ? err.requestId : undefined}
          action={
            !isNotFound && !isForbidden ? (
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => void detailQuery.refetch()}
              >
                <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
                Retry
              </Button>
            ) : undefined
          }
        >
          {isNotFound
            ? "The requested investigation case does not exist or may have been deleted."
            : getUserFriendlyErrorMessage(err)}
        </Alert>
      ) : detailQuery.data ? (
        <>
          {/* Header */}
          <InvestigationWorkspaceHeader
            investigation={detailQuery.data}
            onOpenAssignDialog={() => setIsAssignOpen(true)}
            onOpenPriorityDialog={() => setIsPriorityOpen(true)}
            onOpenResolveDialog={() => setIsResolveOpen(true)}
          />

          {/* Resolution Banner for RESOLVED cases */}
          <InvestigationResolutionBanner investigation={detailQuery.data} />

          {/* Primary Transaction & Risk Cards */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <InvestigationPrimaryTransactionCard
              transaction={detailQuery.data.primary_transaction}
            />
            <InvestigationLatestRiskCard riskAnalysis={detailQuery.data.latest_risk_analysis} />
          </div>

          {/* Related Transactions */}
          <InvestigationRelatedTransactionsCard
            transactions={detailQuery.data.related_transactions}
            canLink={canLinkInvestigationTransaction(user, detailQuery.data)}
            onOpenLinkDialog={() => setIsLinkOpen(true)}
          />

          {/* F6 Placeholders */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <InvestigationEvidencePlaceholderCard />
            <InvestigationAiSummaryPlaceholderCard />
          </div>

          {/* Dialogs */}
          {isAssignOpen && (
            <InvestigationAssignDialog
              isOpen={isAssignOpen}
              onClose={() => setIsAssignOpen(false)}
              investigation={detailQuery.data}
            />
          )}

          {isPriorityOpen && (
            <InvestigationPriorityDialog
              isOpen={isPriorityOpen}
              onClose={() => setIsPriorityOpen(false)}
              investigation={detailQuery.data}
            />
          )}

          {isLinkOpen && (
            <InvestigationLinkTransactionDialog
              isOpen={isLinkOpen}
              onClose={() => setIsLinkOpen(false)}
              investigationId={detailQuery.data.id}
            />
          )}

          {isResolveOpen && (
            <InvestigationResolveDialog
              isOpen={isResolveOpen}
              onClose={() => setIsResolveOpen(false)}
              investigation={detailQuery.data}
            />
          )}
        </>
      ) : null}
    </div>
  );
}
