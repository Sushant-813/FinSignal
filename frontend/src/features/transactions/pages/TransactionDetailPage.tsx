import { ArrowLeft, FolderSearch, RefreshCw } from "lucide-react";
import { useState } from "react";
import { Link, useLocation, useParams, useSearchParams } from "react-router";
import { Alert } from "../../../components/ui/Alert.tsx";
import { Button } from "../../../components/ui/Button.tsx";
import { Skeleton } from "../../../components/ui/Skeleton.tsx";
import {
  getUserFriendlyErrorMessage,
  isApiClientError,
  isForbiddenError,
} from "../../../lib/api/errors.ts";
import { canCreateInvestigation } from "../../../lib/permissions/capabilities.ts";
import { useAuth } from "../../auth/hooks/useAuth.ts";
import { InvestigationCreateDialog } from "../../investigations/components/InvestigationCreateDialog.tsx";
import { RiskAnalysisPanel } from "../../risk/components/RiskAnalysisPanel.tsx";
import { TransactionFactsCard } from "../components/TransactionFactsCard.tsx";
import { TransactionRelationsCard } from "../components/TransactionRelationsCard.tsx";
import { useTransactionDetailQuery } from "../hooks/useTransactionDetailQuery.ts";
import { UUID_REGEX } from "../schemas/transaction-filters-schema.ts";

interface DetailNavigationState {
  readonly fromTransactionsSearch?: string | undefined;
}

export function TransactionDetailPage() {
  const { user } = useAuth();
  const [isInvestigateOpen, setIsInvestigateOpen] = useState(false);
  const { transactionId = "" } = useParams<{ transactionId: string }>();
  const [searchParams] = useSearchParams();
  const location = useLocation();

  const sourceNamespace = searchParams.get("source_namespace")?.trim() || null;
  const isValidUuid = UUID_REGEX.test(transactionId);

  const navState = location.state as DetailNavigationState | null;
  const backToTransactionsHref = navState?.fromTransactionsSearch
    ? `/transactions${navState.fromTransactionsSearch}`
    : sourceNamespace
      ? `/transactions?source_namespace=${encodeURIComponent(sourceNamespace)}`
      : "/transactions";

  const detailQuery = useTransactionDetailQuery(transactionId, sourceNamespace, isValidUuid);

  const err = detailQuery.error;
  const isNotFound = isApiClientError(err) && err.status === 404;
  const isForbidden = isForbiddenError(err);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-1">
          <Link
            to={backToTransactionsHref}
            className="inline-flex items-center gap-1.5 text-sm font-medium text-brand-700 hover:underline"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            Back to Transactions
          </Link>
          <h1 className="text-[24px] leading-8 font-semibold tracking-tight text-text-primary">
            Transaction Detail
          </h1>
          <p className="font-mono text-xs text-text-muted">{transactionId || "Missing ID"}</p>
        </div>
        {canCreateInvestigation(user) && detailQuery.data && (
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setIsInvestigateOpen(true)}
              data-testid="investigate-transaction-button"
            >
              <FolderSearch className="h-4 w-4" aria-hidden="true" />
              Investigate Transaction
            </Button>
          </div>
        )}
      </div>

      {!isValidUuid ? (
        <Alert variant="warning" role="alert" title="Invalid transaction identifier">
          The transaction identifier in the URL is not a valid UUID. Return to the transaction
          explorer to select an authoritative record.
        </Alert>
      ) : detailQuery.isLoading ? (
        <div className="space-y-4" aria-label="Loading transaction details">
          <Skeleton className="h-56 w-full" />
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      ) : detailQuery.isError ? (
        <Alert
          variant={isNotFound || isForbidden ? "warning" : "danger"}
          role="alert"
          title={
            isNotFound
              ? "Transaction not found"
              : isForbidden
                ? "Access denied"
                : "Unable to load transaction"
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
          {getUserFriendlyErrorMessage(err)}
        </Alert>
      ) : detailQuery.data ? (
        <>
          <TransactionFactsCard transaction={detailQuery.data} />
          <TransactionRelationsCard transaction={detailQuery.data} />
          <RiskAnalysisPanel
            transactionId={detailQuery.data.id}
            latestRiskSnapshot={detailQuery.data.latest_risk}
          />
        </>
      ) : null}
      {isInvestigateOpen && (
        <InvestigationCreateDialog
          isOpen={isInvestigateOpen}
          onClose={() => setIsInvestigateOpen(false)}
          defaultTransactionId={transactionId}
          isTransactionIdFixed
        />
      )}
    </div>
  );
}
