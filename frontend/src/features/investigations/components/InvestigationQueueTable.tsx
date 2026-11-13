import { ArrowRight, FolderSearch, RefreshCw } from "lucide-react";
import { Link, useNavigate } from "react-router";
import { TimestampDisplay } from "../../../components/data-display/TimestampDisplay.tsx";
import { Alert } from "../../../components/ui/Alert.tsx";
import { Button } from "../../../components/ui/Button.tsx";
import { EmptyState } from "../../../components/ui/EmptyState.tsx";
import { Pagination } from "../../../components/ui/Pagination.tsx";
import { TableSkeleton } from "../../../components/ui/Skeleton.tsx";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../../components/ui/Table.tsx";
import { getUserFriendlyErrorMessage, isApiClientError } from "../../../lib/api/errors.ts";
import type { InvestigationSummaryItem } from "../types/investigations.types.ts";
import { InvestigationPriorityBadge } from "./InvestigationPriorityBadge.tsx";
import { InvestigationResolutionBadge } from "./InvestigationResolutionBadge.tsx";
import { InvestigationStatusBadge } from "./InvestigationStatusBadge.tsx";

export interface InvestigationQueueTableProps {
  readonly items: InvestigationSummaryItem[] | undefined;
  readonly total: number;
  readonly totalPages: number;
  readonly page: number;
  readonly pageSize: number;
  readonly isLoading?: boolean | undefined;
  readonly isError?: boolean | undefined;
  readonly error?: unknown | undefined;
  readonly onPageChange: (page: number) => void;
  readonly onPageSizeChange: (pageSize: number) => void;
  readonly onRetry?: (() => void) | undefined;
  readonly isFiltered?: boolean | undefined;
}

export function InvestigationQueueTable({
  items,
  total,
  totalPages,
  page,
  pageSize,
  isLoading = false,
  isError = false,
  error,
  onPageChange,
  onPageSizeChange,
  onRetry,
  isFiltered = false,
}: InvestigationQueueTableProps) {
  const navigate = useNavigate();

  if (isLoading && (!items || items.length === 0)) {
    return <TableSkeleton rows={8} columns={7} aria-label="Loading investigation cases" />;
  }

  if (isError) {
    const isClientErr = isApiClientError(error);
    return (
      <Alert
        variant="danger"
        role="alert"
        title="Failed to load investigations"
        requestId={isClientErr ? error.requestId : undefined}
        action={
          onRetry ? (
            <Button type="button" size="sm" variant="secondary" onClick={onRetry}>
              <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
              Retry
            </Button>
          ) : undefined
        }
      >
        {getUserFriendlyErrorMessage(error)}
      </Alert>
    );
  }

  if (!items || items.length === 0) {
    return (
      <EmptyState
        icon={<FolderSearch className="h-6 w-6" aria-hidden="true" />}
        title={isFiltered ? "No matching investigations" : "No investigations recorded"}
        description={
          isFiltered
            ? "No investigation cases match your selected filter criteria. Try adjusting your filters."
            : "No investigation cases have been created yet. You can create an investigation from the transaction explorer or using the button above."
        }
      />
    );
  }

  return (
    <div className="space-y-4" data-testid="investigation-queue-table">
      <div className="overflow-x-auto rounded-card border border-border bg-surface shadow-card">
        <Table aria-label="Investigation cases queue">
          <TableHeader>
            <TableRow>
              <TableHead className="w-32">Case ID</TableHead>
              <TableHead className="w-32">Status</TableHead>
              <TableHead className="w-28">Priority</TableHead>
              <TableHead>Primary Transaction</TableHead>
              <TableHead className="w-44">Assignee</TableHead>
              <TableHead className="w-40">Created (UTC)</TableHead>
              <TableHead className="w-40">Updated (UTC)</TableHead>
              <TableHead className="w-28 text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((item) => {
              const shortId = item.id.slice(0, 8);
              const shortTxId = item.primary_transaction_id.slice(0, 8);

              return (
                <TableRow
                  key={item.id}
                  interactive
                  onClick={() => navigate(`/investigations/${item.id}`)}
                  data-testid={`investigation-row-${item.id}`}
                >
                  <TableCell className="font-mono text-xs font-medium text-text-primary">
                    <span title={item.id}>{shortId}…</span>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-col gap-1 items-start">
                      <InvestigationStatusBadge status={item.status} />
                      {item.resolution && (
                        <InvestigationResolutionBadge resolution={item.resolution} size="sm" />
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <InvestigationPriorityBadge priority={item.priority} />
                  </TableCell>
                  <TableCell className="font-mono text-xs text-text-secondary">
                    <span title={item.primary_transaction_id}>{shortTxId}…</span>
                  </TableCell>
                  <TableCell className="text-xs text-text-secondary">
                    {item.assigned_to ? (
                      <span className="font-mono" title={item.assigned_to}>
                        {item.assigned_to.slice(0, 8)}…
                      </span>
                    ) : (
                      <span className="italic text-text-muted">Unassigned</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <TimestampDisplay value={item.created_at} />
                  </TableCell>
                  <TableCell>
                    <TimestampDisplay value={item.updated_at} />
                  </TableCell>
                  <TableCell className="text-right">
                    <Link
                      to={`/investigations/${item.id}`}
                      className="inline-flex items-center gap-1 text-xs font-medium text-brand-700 hover:text-brand-800 hover:underline"
                      onClick={(e) => e.stopPropagation()}
                      aria-label={`Open workspace for investigation ${item.id}`}
                    >
                      Workspace
                      <ArrowRight className="h-3 w-3" aria-hidden="true" />
                    </Link>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      <Pagination
        page={page}
        pageSize={pageSize}
        total={total}
        totalPages={totalPages}
        onPageChange={onPageChange}
        onPageSizeChange={onPageSizeChange}
        ariaLabel="Investigation queue pagination"
      />
    </div>
  );
}
