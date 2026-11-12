import { ArrowRight, RefreshCw } from "lucide-react";
import { Link } from "react-router";
import { Alert } from "../../../components/ui/Alert.tsx";
import { Badge } from "../../../components/ui/Badge.tsx";
import { Button } from "../../../components/ui/Button.tsx";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../../../components/ui/Card.tsx";
import {
  getUserFriendlyErrorMessage,
  isApiClientError,
  isForbiddenError,
} from "../../../lib/api/errors.ts";
import { canManageDatasets } from "../../../lib/permissions/capabilities.ts";
import { ReportingScopeBar } from "../../analytics/components/ReportingScopeBar.tsx";
import { useOverviewAnalyticsQuery } from "../../analytics/hooks/useAnalyticsQueries.ts";
import { useReportingScopeParams } from "../../analytics/hooks/useReportingScopeParams.ts";
import { useAuth } from "../../auth/hooks/useAuth.ts";
import { OverviewKpiGrid } from "../components/OverviewKpiGrid.tsx";

export function DashboardPage() {
  const { user } = useAuth();
  const managesDatasets = canManageDatasets(user);
  const { scope, hadInvalidUrlParams, setScope, resetScope, buildScopeSearchString } =
    useReportingScopeParams();

  const overviewQuery = useOverviewAnalyticsQuery({
    source_namespace: scope.source_namespace,
    currency: scope.currency,
    from_time: scope.from_time,
    to_time: scope.to_time,
    timezone: scope.timezone,
  });

  const scopeSearch = buildScopeSearchString();
  const txParams = new URLSearchParams({
    source_namespace: scope.source_namespace,
    currency: scope.currency,
    from_time: scope.from_time,
    to_time: scope.to_time,
  });

  const err = overviewQuery.error;
  const requestId = isApiClientError(err) ? err.requestId : undefined;
  const isNamespaceNotFound = isApiClientError(err) && err.code === "NAMESPACE_NOT_FOUND";
  const isForbidden = isForbiddenError(err);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-[24px] leading-8 font-semibold tracking-tight text-text-primary">
            Dashboard Overview
          </h1>
          <p className="text-sm text-text-secondary">
            Backend-authoritative macro financial metrics for the selected namespace, currency, and
            half-open reporting window.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {user ? <Badge variant="brand">{user.role}</Badge> : null}
          {user ? <Badge variant="neutral">{user.email}</Badge> : null}
        </div>
      </div>

      <ReportingScopeBar
        scope={scope}
        hadInvalidUrlParams={hadInvalidUrlParams}
        isFetching={overviewQuery.isFetching}
        timezoneNote="Overview totals aggregate over UTC instants [from_time, to_time)."
        onApply={setScope}
        onReset={resetScope}
      />

      {overviewQuery.isError ? (
        <Alert
          variant={isNamespaceNotFound || isForbidden ? "warning" : "danger"}
          role="alert"
          title={
            isNamespaceNotFound
              ? "Namespace not found"
              : isForbidden
                ? "Access denied"
                : "Unable to load dashboard overview"
          }
          requestId={requestId}
          action={
            isNamespaceNotFound ? (
              <Button variant="secondary" size="sm" onClick={resetScope}>
                Reset to SYNTHETIC
              </Button>
            ) : !isForbidden ? (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  void overviewQuery.refetch();
                }}
              >
                <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
                <span>Retry</span>
              </Button>
            ) : undefined
          }
        >
          {getUserFriendlyErrorMessage(err)}
        </Alert>
      ) : (
        <OverviewKpiGrid data={overviewQuery.data} isLoading={overviewQuery.isLoading} />
      )}

      <div className="grid gap-4 md:grid-cols-3">
        <Card padding="sm">
          <CardHeader className="pb-2">
            <CardTitle size="panel">Transaction Explorer</CardTitle>
            <CardDescription>
              Inspect individual records, filter by risk tier, and run on-demand risk scoring.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild variant="secondary" size="sm">
              <Link to={`/transactions?${txParams.toString()}`}>
                <span>Explore transactions</span>
                <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
              </Link>
            </Button>
          </CardContent>
        </Card>

        <Card padding="sm">
          <CardHeader className="pb-2">
            <CardTitle size="panel">Financial Analytics</CardTitle>
            <CardDescription>
              View daily/monthly trends, category distributions, and top merchant spend.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild variant="secondary" size="sm">
              <Link to={`/analytics${scopeSearch}`}>
                <span>Open analytics</span>
                <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
              </Link>
            </Button>
          </CardContent>
        </Card>

        <Card padding="sm">
          <CardHeader className="pb-2">
            <CardTitle size="panel">Dataset Imports</CardTitle>
            <CardDescription>
              {managesDatasets
                ? "History viewing plus CSV upload and recovery (Admin / Analyst)."
                : "Read-only import history visibility for Investigator role."}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild variant="secondary" size="sm">
              <Link to="/datasets">
                <span>View dataset workspace</span>
                <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
