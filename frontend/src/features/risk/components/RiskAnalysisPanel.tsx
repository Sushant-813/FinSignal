import { RefreshCw, ShieldAlert, Sparkles } from "lucide-react";
import { RiskBadge } from "../../../components/data-display/RiskBadge.tsx";
import { TimestampDisplay } from "../../../components/data-display/TimestampDisplay.tsx";
import { Alert } from "../../../components/ui/Alert.tsx";
import { Button } from "../../../components/ui/Button.tsx";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../../../components/ui/Card.tsx";
import { Skeleton } from "../../../components/ui/Skeleton.tsx";
import { useAuth } from "../../auth/hooks/useAuth.ts";
import {
  getUserFriendlyErrorMessage,
  isApiClientError,
  isForbiddenError,
} from "../../../lib/api/errors.ts";
import { canAnalyzeActiveRisk } from "../../../lib/permissions/capabilities.ts";
import type { TransactionLatestRiskDTO } from "../../transactions/types/transactions.types.ts";
import { useAnalyzeTransactionRiskMutation } from "../hooks/useAnalyzeTransactionRiskMutation.ts";
import { useTransactionRiskQuery } from "../hooks/useTransactionRiskQuery.ts";
import type { RiskAnalysisResponse } from "../types/risk.types.ts";
import { RiskFactorList } from "./RiskFactorList.tsx";

export interface RiskAnalysisPanelProps {
  transactionId: string;
  latestRiskSnapshot?: TransactionLatestRiskDTO | null | undefined;
  enabled?: boolean | undefined;
}

function formatScoreValue(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(4).replace(/\.?0+$/, "");
}

function getAnalyzeErrorTitle(error: unknown): string {
  if (isForbiddenError(error)) {
    return "Risk analysis forbidden";
  }
  if (isApiClientError(error)) {
    switch (error.code) {
      case "NO_ACTIVE_MODEL":
        return "No active risk model available";
      case "INELIGIBLE_MODEL_STATUS":
        return "Model ineligible for scoring";
      case "TRANSACTION_NOT_FOUND":
        return "Transaction not found";
      case "MODEL_NOT_FOUND":
        return "Risk model not found";
      default:
        break;
    }
  }
  return "Risk analysis failed";
}

function formatNormalizationValue(val: unknown): string {
  if (val === null || val === undefined) {
    return "—";
  }
  if (typeof val === "string" || typeof val === "number" || typeof val === "boolean") {
    return String(val);
  }
  try {
    return JSON.stringify(val);
  } catch {
    return "[Unserializable]";
  }
}

function AnalyzedRiskContent({
  analysis,
  latestRiskSnapshot,
}: {
  analysis: RiskAnalysisResponse;
  latestRiskSnapshot?: TransactionLatestRiskDTO | null | undefined;
}) {
  const normalizationEntries = Object.entries(analysis.normalization_params ?? {});
  const hasSnapshotMismatch =
    latestRiskSnapshot !== null &&
    latestRiskSnapshot !== undefined &&
    latestRiskSnapshot.analysis_id !== analysis.id;

  return (
    <div className="space-y-5">
      {hasSnapshotMismatch ? (
        <Alert variant="info" role="status" title="Synchronized latest evaluation">
          Transaction summary referenced snapshot{" "}
          <code className="font-mono text-xs">{latestRiskSnapshot.analysis_id}</code>; displaying
          the latest persisted risk evaluation{" "}
          <code className="font-mono text-xs">{analysis.id}</code>.
        </Alert>
      ) : null}

      <div className="flex flex-col gap-4 rounded-input border border-border bg-surface-subtle p-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-medium tracking-wide text-text-muted uppercase">
            Prioritization Risk Score (0–100)
          </p>
          <div className="mt-1 flex items-baseline gap-2.5">
            <span className="font-mono text-3xl font-semibold tabular-nums text-text-primary">
              {formatScoreValue(analysis.score)}
            </span>
            <span className="font-mono text-sm text-text-muted">/ 100</span>
            <RiskBadge level={analysis.risk_level} size="md" />
          </div>
        </div>

        <div className="text-xs text-text-secondary sm:text-right">
          <div>
            Evaluated at <TimestampDisplay value={analysis.created_at} timeZone="UTC" />
          </div>
          <div className="mt-1 font-mono text-text-muted">
            Model: <span className="text-text-primary">{analysis.model_version}</span> · Config{" "}
            <span className="text-text-primary">{analysis.config_version}</span>
          </div>
        </div>
      </div>

      <div>
        <h3 className="mb-2.5 text-xs font-semibold tracking-wide text-text-muted uppercase">
          ML & Rule Score Decomposition
        </h3>
        <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="rounded-input border border-border bg-surface p-3">
            <dt className="text-xs text-text-muted">Rule score</dt>
            <dd className="mt-1 font-mono text-base font-semibold tabular-nums text-text-primary">
              {formatScoreValue(analysis.rule_score)}
            </dd>
          </div>
          <div className="rounded-input border border-border bg-surface p-3">
            <dt className="text-xs text-text-muted">Normalized ML score</dt>
            <dd className="mt-1 font-mono text-base font-semibold tabular-nums text-text-primary">
              {formatScoreValue(analysis.normalized_ml_score)}
            </dd>
          </div>
          <div className="rounded-input border border-border bg-surface p-3">
            <dt className="text-xs text-text-muted">Raw ML anomaly score</dt>
            <dd className="mt-1 font-mono text-base font-semibold tabular-nums text-text-primary">
              {formatScoreValue(analysis.ml_anomaly_score)}
            </dd>
          </div>
          <div className="rounded-input border border-border bg-surface p-3">
            <dt className="text-xs text-text-muted">ML threshold</dt>
            <dd className="mt-1 font-mono text-base font-semibold tabular-nums text-text-primary">
              {formatScoreValue(analysis.ml_threshold)}
            </dd>
          </div>
        </dl>
      </div>

      <div>
        <div className="mb-2.5 flex items-center justify-between gap-2">
          <h3 className="text-xs font-semibold tracking-wide text-text-muted uppercase">
            Explainable Risk Factors ({analysis.factors.length})
          </h3>
        </div>
        <RiskFactorList factors={analysis.factors} />
      </div>

      <details className="rounded-input border border-border bg-surface-subtle px-3.5 py-2.5 text-xs">
        <summary className="cursor-pointer font-medium text-text-secondary hover:text-text-primary">
          Model provenance & normalization parameters
        </summary>
        <dl className="mt-3 grid grid-cols-1 gap-x-4 gap-y-2 border-t border-border/70 pt-2.5 sm:grid-cols-2">
          <div>
            <dt className="text-text-muted">Analysis ID</dt>
            <dd className="font-mono break-all text-text-primary">{analysis.id}</dd>
          </div>
          <div>
            <dt className="text-text-muted">Model Version ID</dt>
            <dd className="font-mono break-all text-text-primary">{analysis.model_version_id}</dd>
          </div>
          <div className="sm:col-span-2">
            <dt className="text-text-muted">Feature Vector Hash</dt>
            <dd className="font-mono break-all text-text-primary">
              {analysis.feature_vector_hash}
            </dd>
          </div>
          {normalizationEntries.map(([key, value]) => (
            <div key={key}>
              <dt className="font-mono text-text-muted">{key}</dt>
              <dd className="font-mono break-all text-text-primary">
                {formatNormalizationValue(value)}
              </dd>
            </div>
          ))}
        </dl>
      </details>
    </div>
  );
}

export function RiskAnalysisPanel({
  transactionId,
  latestRiskSnapshot,
  enabled = true,
}: RiskAnalysisPanelProps) {
  const { user } = useAuth();
  const canRunAnalysis = canAnalyzeActiveRisk(user);
  const riskQuery = useTransactionRiskQuery(transactionId, enabled);
  const analyzeMutation = useAnalyzeTransactionRiskMutation();

  const handleRunAnalysis = () => {
    if (!canRunAnalysis || analyzeMutation.isPending) {
      return;
    }
    analyzeMutation.mutate({ transactionId });
  };

  const hasExistingAnalysis = riskQuery.isSuccess && riskQuery.data.kind === "analyzed";

  return (
    <Card as="section" aria-labelledby="risk-intelligence-heading">
      <CardHeader>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <ShieldAlert className="h-4 w-4 text-brand-700" aria-hidden="true" />
              <CardTitle id="risk-intelligence-heading" as="h2" size="section">
                Risk Intelligence
              </CardTitle>
            </div>
            <CardDescription className="mt-1">
              Computed triage prioritization signal from the platform ML & rule engine. This score
              guides investigation priority — it is not an automated fraud verdict and does not
              modify immutable transaction facts.
            </CardDescription>
          </div>

          {canRunAnalysis && !riskQuery.isLoading && !riskQuery.isError ? (
            <Button
              type="button"
              variant={hasExistingAnalysis ? "secondary" : "primary"}
              size="sm"
              isLoading={analyzeMutation.isPending}
              disabled={analyzeMutation.isPending}
              onClick={handleRunAnalysis}
              className="shrink-0"
            >
              <Sparkles className="h-4 w-4" aria-hidden="true" />
              {hasExistingAnalysis ? "Re-run risk analysis" : "Run risk analysis"}
            </Button>
          ) : null}
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {analyzeMutation.isError ? (
          <Alert
            variant={isForbiddenError(analyzeMutation.error) ? "warning" : "danger"}
            role="alert"
            title={getAnalyzeErrorTitle(analyzeMutation.error)}
            requestId={
              isApiClientError(analyzeMutation.error) ? analyzeMutation.error.requestId : undefined
            }
          >
            {getUserFriendlyErrorMessage(analyzeMutation.error)}
          </Alert>
        ) : null}

        {riskQuery.isLoading ? (
          <div className="space-y-3" aria-label="Loading risk evaluation">
            <Skeleton className="h-20 w-full" />
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
            </div>
          </div>
        ) : riskQuery.isError ? (
          <Alert
            variant={isForbiddenError(riskQuery.error) ? "warning" : "danger"}
            role="alert"
            title={
              isForbiddenError(riskQuery.error)
                ? "Risk intelligence access denied"
                : "Unable to load risk evaluation"
            }
            requestId={isApiClientError(riskQuery.error) ? riskQuery.error.requestId : undefined}
            action={
              !isForbiddenError(riskQuery.error) ? (
                <Button
                  type="button"
                  size="sm"
                  variant="secondary"
                  onClick={() => void riskQuery.refetch()}
                >
                  <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
                  Retry
                </Button>
              ) : undefined
            }
          >
            {getUserFriendlyErrorMessage(riskQuery.error)}
          </Alert>
        ) : riskQuery.data?.kind === "not_analyzed" ? (
          <div className="rounded-input border border-dashed border-border bg-surface-subtle p-5 text-sm">
            <p className="font-medium text-text-primary">No risk analysis recorded yet.</p>
            <p className="mt-1 text-text-secondary">
              {canRunAnalysis
                ? "Run on-demand scoring using the workspace's active risk model to inspect factor contributions."
                : "Your current role has read-only access to completed evaluations and cannot trigger new risk scoring runs."}
            </p>
          </div>
        ) : riskQuery.data?.kind === "analyzed" ? (
          <AnalyzedRiskContent
            analysis={riskQuery.data.analysis}
            latestRiskSnapshot={latestRiskSnapshot}
          />
        ) : null}
      </CardContent>
    </Card>
  );
}
