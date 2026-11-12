import { useMemo, useState } from "react";
import { MoneyValue } from "../../../components/data-display/MoneyValue.tsx";
import { Select } from "../../../components/ui/Select.tsx";
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableHeader,
  TableRow,
} from "../../../components/ui/Table.tsx";
import {
  countCalendarBuckets,
  formatShortDate,
  getTrendBucketLimit,
} from "../../../lib/formatting/datetime.ts";
import { useTrendAnalyticsQuery } from "../hooks/useAnalyticsQueries.ts";
import type { ReportingScope, TrendInterval } from "../types/analytics.types.ts";
import { buildTrendsChartOption, type TrendChartMetric } from "../utils/chart-options.ts";
import { ChartContainer } from "./ChartContainer.tsx";

export interface TrendsChartPanelProps {
  scope: ReportingScope;
  interval: TrendInterval;
  onIntervalChange: (interval: TrendInterval) => void;
  reducedMotion?: boolean | undefined;
}

export function TrendsChartPanel({
  scope,
  interval,
  onIntervalChange,
  reducedMotion = false,
}: TrendsChartPanelProps) {
  const [metric, setMetric] = useState<TrendChartMetric>("amounts");

  const bucketCount = useMemo(
    () => countCalendarBuckets(scope.from_time, scope.to_time, scope.timezone, interval),
    [interval, scope.from_time, scope.timezone, scope.to_time]
  );
  const bucketLimit = getTrendBucketLimit(interval);
  const exceedsLimit = bucketCount > bucketLimit;

  const trendsQuery = useTrendAnalyticsQuery(
    {
      source_namespace: scope.source_namespace,
      currency: scope.currency,
      from_time: scope.from_time,
      to_time: scope.to_time,
      interval,
      timezone: scope.timezone,
    },
    !exceedsLimit
  );

  const option = useMemo(() => {
    if (!trendsQuery.data || trendsQuery.data.buckets.length === 0) {
      return null;
    }
    return buildTrendsChartOption(trendsQuery.data, metric, reducedMotion);
  }, [metric, reducedMotion, trendsQuery.data]);

  const validationMessage = exceedsLimit
    ? `Selected date range produces ${bucketCount} ${interval} buckets, exceeding the backend limit of ${bucketLimit}. Narrow the date window or switch interval to monthly.`
    : undefined;

  const buckets = trendsQuery.data?.buckets ?? [];

  const tableAlternative = (
    <TableContainer>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Bucket ({scope.timezone})</TableHead>
            <TableHead align="right">Transactions</TableHead>
            <TableHead align="right">Debit count</TableHead>
            <TableHead align="right">Credit count</TableHead>
            <TableHead align="right">Total debit</TableHead>
            <TableHead align="right">Total credit</TableHead>
            <TableHead align="right">Net cash flow</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {buckets.map((bucket) => (
            <TableRow key={bucket.bucket_start}>
              <TableCell className="font-mono tabular-nums">
                {formatShortDate(bucket.bucket_start, scope.timezone)}
              </TableCell>
              <TableCell numeric>{bucket.transaction_count.toLocaleString("en-US")}</TableCell>
              <TableCell numeric>{bucket.debit_count.toLocaleString("en-US")}</TableCell>
              <TableCell numeric>{bucket.credit_count.toLocaleString("en-US")}</TableCell>
              <TableCell numeric>
                <MoneyValue amount={bucket.total_debit_amount} currency={scope.currency} />
              </TableCell>
              <TableCell numeric>
                <MoneyValue amount={bucket.total_credit_amount} currency={scope.currency} />
              </TableCell>
              <TableCell numeric>
                <MoneyValue amount={bucket.net_cash_flow} currency={scope.currency} />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );

  return (
    <ChartContainer
      title="Financial Trends"
      description={`Zero-filled ${interval === "day" ? "daily" : "monthly"} buckets in ${scope.timezone} (${scope.currency})`}
      ariaLabel={`Financial trends ${interval} chart for ${scope.source_namespace} in ${scope.currency}`}
      option={option}
      tableAlternative={tableAlternative}
      isLoading={trendsQuery.isLoading}
      isEmpty={
        !exceedsLimit && !trendsQuery.isLoading && !trendsQuery.isError && buckets.length === 0
      }
      emptyTitle="No trend buckets returned"
      emptyDescription="No trend buckets were returned for the selected reporting window."
      error={trendsQuery.error}
      validationMessage={validationMessage}
      onRetry={() => {
        void trendsQuery.refetch();
      }}
      headerActions={
        <div className="flex flex-wrap items-center gap-2">
          <Select
            label="Trend interval"
            hideLabel
            value={interval}
            onValueChange={(val) => {
              if (val === "day" || val === "month") {
                onIntervalChange(val);
              }
            }}
            options={[
              { value: "day", label: "Daily" },
              { value: "month", label: "Monthly" },
            ]}
            containerClassName="w-28"
          />
          <Select
            label="Trend series metric"
            hideLabel
            value={metric}
            onValueChange={(val) => {
              if (val === "amounts" || val === "counts") {
                setMetric(val);
              }
            }}
            options={[
              { value: "amounts", label: "Amounts" },
              { value: "counts", label: "Counts" },
            ]}
            containerClassName="w-28"
          />
        </div>
      }
    />
  );
}
