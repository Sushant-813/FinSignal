import { ArrowUpRight } from "lucide-react";
import { Link, useLocation } from "react-router";
import { MoneyValue } from "../../../components/data-display/MoneyValue.tsx";
import { TimestampDisplay } from "../../../components/data-display/TimestampDisplay.tsx";
import { Badge } from "../../../components/ui/Badge.tsx";
import { Button } from "../../../components/ui/Button.tsx";
import { EmptyState } from "../../../components/ui/EmptyState.tsx";
import { TableSkeleton } from "../../../components/ui/Skeleton.tsx";
import {
  type SortDirection,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableHeader,
  TableRow,
} from "../../../components/ui/Table.tsx";
import type {
  TransactionSortField,
  TransactionSortOrder,
  TransactionSummaryItem,
} from "../types/transactions.types.ts";

export interface TransactionTableProps {
  items: readonly TransactionSummaryItem[];
  total: number;
  page: number;
  isLoading: boolean;
  hasActiveFilters: boolean;
  sortBy: TransactionSortField;
  sortOrder: TransactionSortOrder;
  onSort: (field: TransactionSortField) => void;
  onResetFilters: () => void;
  onGoToFirstPage: () => void;
}

function getSortDirection(
  column: TransactionSortField,
  activeSortBy: TransactionSortField,
  activeOrder: TransactionSortOrder
): SortDirection {
  return activeSortBy === column ? activeOrder : "none";
}

function abbreviateUuid(id: string): string {
  return id.length > 13 ? `${id.slice(0, 8)}…${id.slice(-4)}` : id;
}

export function TransactionTable({
  items,
  total,
  page,
  isLoading,
  hasActiveFilters,
  sortBy,
  sortOrder,
  onSort,
  onResetFilters,
  onGoToFirstPage,
}: TransactionTableProps) {
  const location = useLocation();

  if (isLoading) {
    return <TableSkeleton rows={8} columns={8} />;
  }

  if (items.length === 0) {
    if (total > 0 && page > 1) {
      return (
        <EmptyState
          variant="no-results"
          title={`Page ${page} has no rows`}
          description={`There are ${total} matching transactions across earlier pages.`}
          action={
            <Button variant="secondary" size="sm" onClick={onGoToFirstPage}>
              Go to page 1
            </Button>
          }
        />
      );
    }

    if (hasActiveFilters) {
      return (
        <EmptyState
          variant="no-results"
          title="No transactions match these filters"
          description="Adjust or clear your active filter criteria to inspect transactions in this namespace."
          action={
            <Button variant="secondary" size="sm" onClick={onResetFilters}>
              Clear filters
            </Button>
          }
        />
      );
    }

    return (
      <EmptyState
        variant="empty"
        title="No transactions found"
        description="No transaction records exist in the selected source namespace yet."
      />
    );
  }

  return (
    <TableContainer>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>External TX ID</TableHead>
            <TableHead
              sortDirection={getSortDirection("occurred_at", sortBy, sortOrder)}
              onSort={() => onSort("occurred_at")}
            >
              Occurred at
            </TableHead>
            <TableHead>Direction</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Category</TableHead>
            <TableHead>Channel / Method</TableHead>
            <TableHead
              align="right"
              sortDirection={getSortDirection("amount", sortBy, sortOrder)}
              onSort={() => onSort("amount")}
            >
              Amount
            </TableHead>
            <TableHead>Account</TableHead>
            <TableHead
              sortDirection={getSortDirection("created_at", sortBy, sortOrder)}
              onSort={() => onSort("created_at")}
            >
              Created at
            </TableHead>
            <TableHead align="right">Details</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((tx) => {
            const detailUrl = `/transactions/${encodeURIComponent(tx.id)}?source_namespace=${encodeURIComponent(tx.source_namespace)}`;
            const channelMethod = [tx.payment_method, tx.channel].filter(Boolean).join(" · ");

            return (
              <TableRow key={tx.id} interactive>
                <TableCell className="font-mono text-xs font-medium whitespace-nowrap">
                  <Link
                    to={detailUrl}
                    state={{ fromTransactionsSearch: location.search }}
                    className="text-brand-700 hover:underline"
                  >
                    {tx.external_transaction_id}
                  </Link>
                </TableCell>
                <TableCell className="text-xs">
                  <TimestampDisplay value={tx.occurred_at} timeZone="UTC" />
                </TableCell>
                <TableCell>
                  <Badge variant={tx.direction === "CREDIT" ? "info" : "neutral"}>
                    {tx.direction}
                  </Badge>
                </TableCell>
                <TableCell className="whitespace-nowrap">{tx.transaction_type}</TableCell>
                <TableCell className="whitespace-nowrap text-text-secondary">
                  {tx.category ?? "—"}
                </TableCell>
                <TableCell className="whitespace-nowrap text-xs text-text-secondary">
                  {channelMethod || "—"}
                </TableCell>
                <TableCell numeric>
                  <MoneyValue amount={tx.amount} currency={tx.currency} />
                </TableCell>
                <TableCell
                  className="font-mono text-xs text-text-secondary whitespace-nowrap"
                  title={tx.account_id}
                >
                  {abbreviateUuid(tx.account_id)}
                </TableCell>
                <TableCell className="text-xs text-text-secondary">
                  <TimestampDisplay value={tx.created_at} timeZone="UTC" />
                </TableCell>
                <TableCell align="right">
                  <Button asChild variant="tertiary" size="sm">
                    <Link
                      to={detailUrl}
                      state={{ fromTransactionsSearch: location.search }}
                      aria-label={`Inspect transaction ${tx.external_transaction_id}`}
                    >
                      <span>Inspect</span>
                      <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
                    </Link>
                  </Button>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
