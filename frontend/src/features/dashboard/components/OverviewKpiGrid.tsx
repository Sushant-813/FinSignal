import { MoneyValue } from "../../../components/data-display/MoneyValue.tsx";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../../../components/ui/Card.tsx";
import { EmptyState } from "../../../components/ui/EmptyState.tsx";
import { Skeleton } from "../../../components/ui/Skeleton.tsx";
import type { OverviewAnalyticsResponse } from "../../analytics/types/analytics.types.ts";

export interface OverviewKpiGridProps {
  data: OverviewAnalyticsResponse | undefined;
  isLoading: boolean;
}

interface StatTileProps {
  label: string;
  value: string | null | undefined;
  currency?: string | undefined;
  isCount?: boolean | undefined;
  context?: string | undefined;
}

function StatTile({ label, value, currency, isCount = false, context }: StatTileProps) {
  return (
    <Card padding="sm" elevated className="min-w-0">
      <div className="min-w-0 space-y-1.5">
        <p className="text-xs font-medium tracking-wide text-text-muted uppercase">{label}</p>
        <div className="text-2xl leading-8 font-semibold break-words text-text-primary tabular-nums">
          {isCount ? (
            <span className="font-mono">{value ?? "—"}</span>
          ) : (
            <MoneyValue amount={value} currency={currency} currencyClassName="text-sm" />
          )}
        </div>
        {context ? <p className="text-xs text-text-secondary">{context}</p> : null}
      </div>
    </Card>
  );
}

export function OverviewKpiGrid({ data, isLoading }: OverviewKpiGridProps) {
  if (isLoading) {
    return (
      <div className="space-y-4" aria-busy="true" aria-label="Loading dashboard overview metrics">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
          {Array.from({ length: 5 }).map((_, index) => (
            <Card key={index} padding="sm">
              <div className="space-y-2.5">
                <Skeleton variant="text-sm" className="w-24" />
                <Skeleton variant="block" className="h-8 w-36" />
                <Skeleton variant="text-sm" className="w-28" />
              </div>
            </Card>
          ))}
        </div>
        <Card padding="md">
          <Skeleton variant="text" className="mb-3 w-48" />
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {Array.from({ length: 8 }).map((_, index) => (
              <Skeleton key={index} variant="block" className="h-12 w-full" />
            ))}
          </div>
        </Card>
      </div>
    );
  }

  if (!data) {
    return null;
  }

  const isEmptyWindow = data.total_transaction_count === 0;

  return (
    <div className="space-y-4">
      {isEmptyWindow ? (
        <EmptyState
          variant="no-results"
          title="No transactions in selected reporting scope"
          description={`No ${data.currency} transactions were recorded in namespace ${data.source_namespace} during the selected window. Averages, medians, and min/max values are unavailable.`}
        />
      ) : null}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        <StatTile
          label="Total transactions"
          value={data.total_transaction_count.toLocaleString("en-US")}
          isCount
          context={`${data.debit_transaction_count.toLocaleString("en-US")} debit · ${data.credit_transaction_count.toLocaleString("en-US")} credit`}
        />
        <StatTile
          label="Total volume"
          value={data.total_volume_amount}
          currency={data.currency}
          context="Combined debit & credit volume"
        />
        <StatTile
          label="Total debit"
          value={data.total_debit_amount}
          currency={data.currency}
          context={`${data.debit_transaction_count.toLocaleString("en-US")} debit transactions`}
        />
        <StatTile
          label="Total credit"
          value={data.total_credit_amount}
          currency={data.currency}
          context={`${data.credit_transaction_count.toLocaleString("en-US")} credit transactions`}
        />
        <StatTile
          label="Net cash flow"
          value={data.net_cash_flow}
          currency={data.currency}
          context="Total credit minus total debit"
        />
      </div>

      <Card padding="md">
        <CardHeader>
          <CardTitle size="panel">Statistical Distribution Summary</CardTitle>
          <CardDescription>
            Backend-computed central tendency and bounds for {data.source_namespace} (
            {data.currency})
          </CardDescription>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-control border border-border bg-canvas p-3">
              <dt className="text-xs text-text-muted">Overall average</dt>
              <dd className="mt-1 text-base font-semibold text-text-primary">
                <MoneyValue amount={data.average_transaction_amount} currency={data.currency} />
              </dd>
            </div>
            <div className="rounded-control border border-border bg-canvas p-3">
              <dt className="text-xs text-text-muted">Overall median</dt>
              <dd className="mt-1 text-base font-semibold text-text-primary">
                <MoneyValue amount={data.median_transaction_amount} currency={data.currency} />
              </dd>
            </div>
            <div className="rounded-control border border-border bg-canvas p-3">
              <dt className="text-xs text-text-muted">Debit average</dt>
              <dd className="mt-1 text-base font-semibold text-text-primary">
                <MoneyValue amount={data.debit_average_amount} currency={data.currency} />
              </dd>
            </div>
            <div className="rounded-control border border-border bg-canvas p-3">
              <dt className="text-xs text-text-muted">Debit median</dt>
              <dd className="mt-1 text-base font-semibold text-text-primary">
                <MoneyValue amount={data.debit_median_amount} currency={data.currency} />
              </dd>
            </div>
            <div className="rounded-control border border-border bg-canvas p-3">
              <dt className="text-xs text-text-muted">Credit average</dt>
              <dd className="mt-1 text-base font-semibold text-text-primary">
                <MoneyValue amount={data.credit_average_amount} currency={data.currency} />
              </dd>
            </div>
            <div className="rounded-control border border-border bg-canvas p-3">
              <dt className="text-xs text-text-muted">Credit median</dt>
              <dd className="mt-1 text-base font-semibold text-text-primary">
                <MoneyValue amount={data.credit_median_amount} currency={data.currency} />
              </dd>
            </div>
            <div className="rounded-control border border-border bg-canvas p-3">
              <dt className="text-xs text-text-muted">Minimum amount</dt>
              <dd className="mt-1 text-base font-semibold text-text-primary">
                <MoneyValue amount={data.min_transaction_amount} currency={data.currency} />
              </dd>
            </div>
            <div className="rounded-control border border-border bg-canvas p-3">
              <dt className="text-xs text-text-muted">Maximum amount</dt>
              <dd className="mt-1 text-base font-semibold text-text-primary">
                <MoneyValue amount={data.max_transaction_amount} currency={data.currency} />
              </dd>
            </div>
          </dl>
        </CardContent>
      </Card>
    </div>
  );
}
