import { BarChart2, RefreshCw, Table as TableIcon } from "lucide-react";
import { lazy, Suspense, useState, type ReactNode } from "react";
import type { EChartsCoreOption } from "echarts/core";
import { Alert } from "../../../components/ui/Alert.tsx";
import { Button } from "../../../components/ui/Button.tsx";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../../../components/ui/Card.tsx";
import { EmptyState } from "../../../components/ui/EmptyState.tsx";
import { Skeleton } from "../../../components/ui/Skeleton.tsx";
import {
  getUserFriendlyErrorMessage,
  isApiClientError,
  isForbiddenError,
} from "../../../lib/api/errors.ts";

const LazyEChartsCanvas = lazy(() => import("./EChartsCanvas.tsx"));

export interface ChartContainerProps {
  title: string;
  description?: string | undefined;
  ariaLabel: string;
  option: EChartsCoreOption | null;
  tableAlternative: ReactNode;
  headerActions?: ReactNode | undefined;
  summaryStrip?: ReactNode | undefined;
  isLoading: boolean;
  isEmpty: boolean;
  emptyTitle: string;
  emptyDescription: string;
  error?: unknown;
  validationMessage?: string | undefined;
  onRetry?: (() => void) | undefined;
  height?: number | undefined;
}

export function ChartContainer({
  title,
  description,
  ariaLabel,
  option,
  tableAlternative,
  headerActions,
  summaryStrip,
  isLoading,
  isEmpty,
  emptyTitle,
  emptyDescription,
  error,
  validationMessage,
  onRetry,
  height = 320,
}: ChartContainerProps) {
  const [viewMode, setViewMode] = useState<"chart" | "table">("chart");

  const requestId = isApiClientError(error) ? error.requestId : undefined;
  const isForbidden = isForbiddenError(error);

  return (
    <Card padding="md" as="section" aria-label={title} className="min-w-0">
      <CardHeader className="gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <CardTitle size="section">{title}</CardTitle>
          {description ? <CardDescription>{description}</CardDescription> : null}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {headerActions}
          <div className="inline-flex rounded-control border border-border bg-canvas p-0.5">
            <Button
              variant={viewMode === "chart" ? "primary" : "tertiary"}
              size="sm"
              aria-pressed={viewMode === "chart"}
              onClick={() => setViewMode("chart")}
            >
              <BarChart2 className="h-3.5 w-3.5" aria-hidden="true" />
              <span>Chart</span>
            </Button>
            <Button
              variant={viewMode === "table" ? "primary" : "tertiary"}
              size="sm"
              aria-pressed={viewMode === "table"}
              onClick={() => setViewMode("table")}
            >
              <TableIcon className="h-3.5 w-3.5" aria-hidden="true" />
              <span>Table</span>
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {summaryStrip}

        {validationMessage ? (
          <Alert variant="warning" role="status">
            {validationMessage}
          </Alert>
        ) : error ? (
          <Alert
            variant={isForbidden ? "warning" : "danger"}
            role="alert"
            title={isForbidden ? "Access denied" : `Unable to load ${title.toLowerCase()}`}
            requestId={requestId}
            action={
              onRetry && !isForbidden ? (
                <Button variant="secondary" size="sm" onClick={onRetry}>
                  <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
                  <span>Retry</span>
                </Button>
              ) : undefined
            }
          >
            {getUserFriendlyErrorMessage(error)}
          </Alert>
        ) : isLoading ? (
          <div className="space-y-2" aria-busy="true" aria-label={`Loading ${title}`}>
            <Skeleton variant="block" className="h-72 w-full" />
          </div>
        ) : isEmpty ? (
          <EmptyState variant="no-results" title={emptyTitle} description={emptyDescription} />
        ) : viewMode === "table" ? (
          tableAlternative
        ) : option ? (
          <Suspense
            fallback={<Skeleton variant="block" className="h-72 w-full" aria-hidden="true" />}
          >
            <LazyEChartsCanvas option={option} ariaLabel={ariaLabel} height={height} />
          </Suspense>
        ) : null}
      </CardContent>
    </Card>
  );
}
