import { useMemo } from "react";
import { MoneyValue } from "../../../components/data-display/MoneyValue.tsx";
import { Badge } from "../../../components/ui/Badge.tsx";
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
import { useCategoryAnalyticsQuery } from "../hooks/useAnalyticsQueries.ts";
import type { CategoryDirection, ReportingScope } from "../types/analytics.types.ts";
import { buildCategoryChartOption } from "../utils/chart-options.ts";
import { ChartContainer } from "./ChartContainer.tsx";

export interface CategoryDistributionPanelProps {
  scope: ReportingScope;
  direction: CategoryDirection;
  onDirectionChange: (direction: CategoryDirection) => void;
  reducedMotion?: boolean | undefined;
}

export function CategoryDistributionPanel({
  scope,
  direction,
  onDirectionChange,
  reducedMotion = false,
}: CategoryDistributionPanelProps) {
  const categoryQuery = useCategoryAnalyticsQuery({
    source_namespace: scope.source_namespace,
    currency: scope.currency,
    direction,
    from_time: scope.from_time,
    to_time: scope.to_time,
    timezone: scope.timezone,
  });

  const categories = categoryQuery.data?.categories ?? [];

  const option = useMemo(() => {
    if (!categoryQuery.data || categories.length === 0) {
      return null;
    }
    return buildCategoryChartOption(categoryQuery.data, reducedMotion);
  }, [categories.length, categoryQuery.data, reducedMotion]);

  const tableAlternative = (
    <TableContainer>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Category</TableHead>
            <TableHead align="right">Transactions</TableHead>
            <TableHead align="right">Total amount</TableHead>
            <TableHead align="right">Average amount</TableHead>
            <TableHead align="right">Share</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {categories.map((cat) => (
            <TableRow key={cat.category_name}>
              <TableCell className="font-medium">{cat.category_name}</TableCell>
              <TableCell numeric>{cat.transaction_count.toLocaleString("en-US")}</TableCell>
              <TableCell numeric>
                <MoneyValue amount={cat.total_amount} currency={scope.currency} />
              </TableCell>
              <TableCell numeric>
                <MoneyValue amount={cat.average_amount} currency={scope.currency} />
              </TableCell>
              <TableCell numeric>{formatPercentage(cat.percentage_of_total)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );

  return (
    <ChartContainer
      title="Category Distribution"
      description={`${direction} volume breakdown across transaction categories (${scope.currency})`}
      ariaLabel={`Category ${direction} distribution chart for ${scope.source_namespace}`}
      option={option}
      tableAlternative={tableAlternative}
      isLoading={categoryQuery.isLoading}
      isEmpty={!categoryQuery.isLoading && !categoryQuery.isError && categories.length === 0}
      emptyTitle={`No ${direction.toLowerCase()} category activity`}
      emptyDescription={`No ${direction.toLowerCase()} transactions matched the selected namespace, currency, and window.`}
      error={categoryQuery.error}
      onRetry={() => {
        void categoryQuery.refetch();
      }}
      height={Math.max(280, Math.min(480, categories.length * 36 + 60))}
      summaryStrip={
        categoryQuery.data ? (
          <div className="flex flex-wrap items-center gap-2 text-xs text-text-secondary">
            <Badge variant="neutral">
              Total {categoryQuery.data.direction}:{" "}
              <MoneyValue
                amount={categoryQuery.data.total_directional_amount}
                currency={categoryQuery.data.currency}
                className="ml-1 font-semibold text-text-primary"
              />
            </Badge>
            <span>{categories.length} categories</span>
          </div>
        ) : null
      }
      headerActions={
        <Select
          label="Category direction"
          hideLabel
          value={direction}
          onValueChange={(val) => {
            if (val === "DEBIT" || val === "CREDIT") {
              onDirectionChange(val);
            }
          }}
          options={[
            { value: "DEBIT", label: "DEBIT" },
            { value: "CREDIT", label: "CREDIT" },
          ]}
          containerClassName="w-28"
        />
      }
    />
  );
}
