import { ChevronLeft, ChevronRight } from "lucide-react";
import { useMemo } from "react";
import { MoneyValue } from "../../../components/data-display/MoneyValue.tsx";
import { Badge } from "../../../components/ui/Badge.tsx";
import { Button } from "../../../components/ui/Button.tsx";
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
import { formatPercentage } from "../../../lib/formatting/money.ts";
import { useMerchantAnalyticsQuery } from "../hooks/useAnalyticsQueries.ts";
import type { MerchantSortBy, ReportingScope } from "../types/analytics.types.ts";
import { buildMerchantChartOption } from "../utils/chart-options.ts";
import { ChartContainer } from "./ChartContainer.tsx";

export interface MerchantAnalyticsPanelProps {
  scope: ReportingScope;
  sortBy: MerchantSortBy;
  limit: number;
  offset: number;
  onSortByChange: (sortBy: MerchantSortBy) => void;
  onLimitChange: (limit: number) => void;
  onOffsetChange: (offset: number) => void;
  reducedMotion?: boolean | undefined;
}

export function MerchantAnalyticsPanel({
  scope,
  sortBy,
  limit,
  offset,
  onSortByChange,
  onLimitChange,
  onOffsetChange,
  reducedMotion = false,
}: MerchantAnalyticsPanelProps) {
  const merchantQuery = useMerchantAnalyticsQuery({
    source_namespace: scope.source_namespace,
    currency: scope.currency,
    from_time: scope.from_time,
    to_time: scope.to_time,
    sort_by: sortBy,
    limit,
    offset,
    timezone: scope.timezone,
  });

  const data = merchantQuery.data;
  const merchants = data?.merchants ?? [];
  const hasPrev = offset > 0;
  const hasNext = Boolean(data && data.returned_merchant_count >= limit);

  const option = useMemo(() => {
    if (!data || merchants.length === 0) {
      return null;
    }
    return buildMerchantChartOption(data, sortBy, reducedMotion);
  }, [data, merchants.length, reducedMotion, sortBy]);

  const tableAlternative = (
    <TableContainer>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Merchant</TableHead>
            <TableHead>Category</TableHead>
            <TableHead align="right">Transactions</TableHead>
            <TableHead align="right">Total spend</TableHead>
            <TableHead align="right">Average</TableHead>
            <TableHead align="right">% of total debit</TableHead>
            <TableHead align="right">% of merchant spend</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {merchants.map((merchant) => (
            <TableRow key={merchant.merchant_id}>
              <TableCell className="font-medium">{merchant.merchant_name}</TableCell>
              <TableCell>
                <Badge variant="neutral">{merchant.merchant_category}</Badge>
              </TableCell>
              <TableCell numeric>{merchant.transaction_count.toLocaleString("en-US")}</TableCell>
              <TableCell numeric>
                <MoneyValue amount={merchant.total_amount} currency={scope.currency} />
              </TableCell>
              <TableCell numeric>
                <MoneyValue amount={merchant.average_amount} currency={scope.currency} />
              </TableCell>
              <TableCell numeric>{formatPercentage(merchant.percentage_of_total_debit)}</TableCell>
              <TableCell numeric>
                {formatPercentage(merchant.percentage_of_merchant_spend)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );

  return (
    <div className="space-y-3">
      <ChartContainer
        title="Merchant Analytics"
        description={`Top debit merchants ranked by ${sortBy === "amount" ? "spend volume" : "transaction count"} (${scope.currency})`}
        ariaLabel={`Merchant debit analytics chart ranked by ${sortBy}`}
        option={option}
        tableAlternative={tableAlternative}
        isLoading={merchantQuery.isLoading}
        isEmpty={!merchantQuery.isLoading && !merchantQuery.isError && merchants.length === 0}
        emptyTitle="No merchant debit activity"
        emptyDescription={
          offset > 0
            ? "No further merchants at this offset."
            : "No merchant-linked debit transactions matched the selected scope."
        }
        error={merchantQuery.error}
        onRetry={() => {
          void merchantQuery.refetch();
        }}
        height={Math.max(280, Math.min(520, merchants.length * 36 + 60))}
        summaryStrip={
          data ? (
            <div className="flex flex-wrap items-center gap-2 text-xs text-text-secondary">
              <Badge variant="neutral">
                Total debit:{" "}
                <MoneyValue
                  amount={data.total_debit_amount}
                  currency={data.currency}
                  className="ml-1 font-semibold text-text-primary"
                />
              </Badge>
              <Badge variant="neutral">
                Merchant debit:{" "}
                <MoneyValue
                  amount={data.total_merchant_debit_amount}
                  currency={data.currency}
                  className="ml-1 font-semibold text-text-primary"
                />
              </Badge>
              <Badge variant="neutral">
                Non-merchant debit:{" "}
                <MoneyValue
                  amount={data.non_merchant_debit_amount}
                  currency={data.currency}
                  className="ml-1 font-semibold text-text-primary"
                />
              </Badge>
            </div>
          ) : null
        }
        headerActions={
          <div className="flex flex-wrap items-center gap-2">
            <Select
              label="Sort merchants by"
              hideLabel
              value={sortBy}
              onValueChange={(val) => {
                if (val === "amount" || val === "count") {
                  onSortByChange(val);
                }
              }}
              options={[
                { value: "amount", label: "By amount" },
                { value: "count", label: "By count" },
              ]}
              containerClassName="w-32"
            />
            <Select
              label="Merchants per page"
              hideLabel
              value={String(limit)}
              onValueChange={(val) => {
                const parsed = Number.parseInt(val, 10);
                if (Number.isInteger(parsed) && parsed >= 1 && parsed <= 100) {
                  onLimitChange(parsed);
                }
              }}
              options={[
                { value: "10", label: "Top 10" },
                { value: "20", label: "Top 20" },
                { value: "50", label: "Top 50" },
                { value: "100", label: "Top 100" },
              ]}
              containerClassName="w-28"
            />
          </div>
        }
      />

      {data && (hasPrev || hasNext) ? (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-panel border border-border bg-surface px-4 py-2.5 text-xs text-text-secondary">
          <span className="tabular-nums">
            Offset {offset} · Returned {data.returned_merchant_count} merchants
          </span>
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              disabled={!hasPrev || merchantQuery.isFetching}
              onClick={() => onOffsetChange(Math.max(0, offset - limit))}
            >
              <ChevronLeft className="h-3.5 w-3.5" aria-hidden="true" />
              <span>Previous</span>
            </Button>
            <Button
              variant="secondary"
              size="sm"
              disabled={!hasNext || merchantQuery.isFetching}
              onClick={() => onOffsetChange(offset + limit)}
            >
              <span>Next</span>
              <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
