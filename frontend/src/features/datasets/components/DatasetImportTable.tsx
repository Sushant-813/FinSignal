import { ArrowRight, Database } from "lucide-react";
import { Link } from "react-router";
import { TimestampDisplay } from "../../../components/data-display/TimestampDisplay.tsx";
import { Alert } from "../../../components/ui/Alert.tsx";
import { Badge } from "../../../components/ui/Badge.tsx";
import { Button } from "../../../components/ui/Button.tsx";
import { EmptyState } from "../../../components/ui/EmptyState.tsx";
import { TableSkeleton } from "../../../components/ui/Skeleton.tsx";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../../components/ui/Table.tsx";
import type { DatasetImportResponse } from "../types/datasets.types.ts";
import { DatasetImportStatusBadge } from "./DatasetImportStatusBadge.tsx";

export interface DatasetImportTableProps {
  items: DatasetImportResponse[] | undefined;
  isLoading?: boolean | undefined;
  hasCutoffReached?: boolean | undefined;
  onRefresh?: (() => void) | undefined;
}

export function DatasetImportTable({
  items,
  isLoading = false,
  hasCutoffReached = false,
  onRefresh,
}: DatasetImportTableProps) {
  if (isLoading && (!items || items.length === 0)) {
    return <TableSkeleton rows={5} columns={8} />;
  }

  return (
    <div className="space-y-3">
      {hasCutoffReached ? (
        <Alert
          variant="warning"
          role="status"
          aria-label="Automatic status monitoring paused"
          action={
            onRefresh ? (
              <Button size="sm" variant="secondary" onClick={onRefresh}>
                Refresh Now
              </Button>
            ) : undefined
          }
        >
          Automatic status monitoring has paused after 5 minutes of observation. Some imports may still be processing on the server or may have been interrupted. Click &ldquo;Refresh Now&rdquo; to pull the latest status.
        </Alert>
      ) : null}

      {!items || items.length === 0 ? (
        <EmptyState
          icon={<Database className="h-5 w-5" />}
          title="No dataset imports found"
          description="No dataset import records match your current filter parameters or namespace scope."
        />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-border-default bg-surface-primary">
          <Table aria-label="Dataset import executions ledger">
            <TableHeader>
              <TableRow>
                <TableHead>Filename</TableHead>
                <TableHead>Namespace</TableHead>
                <TableHead>Status</TableHead>
                <TableHead align="right">Total Rows</TableHead>
                <TableHead align="right">Valid</TableHead>
                <TableHead align="right">Invalid</TableHead>
                <TableHead>Started (UTC)</TableHead>
                <TableHead>Completed (UTC)</TableHead>
                <TableHead align="right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((item) => (
                <TableRow key={item.id} interactive>
                  <TableCell className="max-w-[180px] truncate font-medium text-text-primary">
                    <span title={item.filename || item.id}>
                      {item.filename || `${item.id.slice(0, 8)}...`}
                    </span>
                    {item.is_duplicate ? (
                      <Badge variant="neutral" className="ml-2 text-[10px] tracking-tight">
                        Duplicate
                      </Badge>
                    ) : null}
                  </TableCell>
                  <TableCell>
                    <span className="font-mono text-[12px] text-text-secondary">
                      {item.source_namespace}
                    </span>
                  </TableCell>
                  <TableCell>
                    <DatasetImportStatusBadge status={item.status} />
                  </TableCell>
                  <TableCell align="right" numeric>
                    {item.total_rows.toLocaleString()}
                  </TableCell>
                  <TableCell align="right" numeric className="text-accent-success font-medium">
                    {item.valid_rows.toLocaleString()}
                  </TableCell>
                  <TableCell
                    align="right"
                    numeric
                    className={item.invalid_rows > 0 ? "text-accent-danger font-medium" : "text-text-muted"}
                  >
                    {item.invalid_rows.toLocaleString()}
                  </TableCell>
                  <TableCell>
                    <TimestampDisplay value={item.started_at} />
                  </TableCell>
                  <TableCell>
                    {item.completed_at ? (
                      <TimestampDisplay value={item.completed_at} />
                    ) : (
                      <span className="text-text-muted">—</span>
                    )}
                  </TableCell>
                  <TableCell align="right">
                    <Button asChild variant="tertiary" size="sm">
                      <Link
                        to={`/datasets/imports/${item.id}`}
                        aria-label={`View details for dataset import ${item.filename || item.id}`}
                      >
                        Details
                        <ArrowRight className="h-3.5 w-3.5" />
                      </Link>
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
