import { AlertTriangle, CheckCircle } from "lucide-react";
import { Badge } from "../../../components/ui/Badge.tsx";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../../../components/ui/Card.tsx";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../../components/ui/Table.tsx";
import type { DatasetImportErrorItem } from "../types/datasets.types.ts";

export interface DatasetImportErrorTableProps {
  errors: DatasetImportErrorItem[] | undefined;
}

export function DatasetImportErrorTable({ errors }: DatasetImportErrorTableProps) {
  const errorList = errors ?? [];
  const hasErrors = errorList.length > 0;

  return (
    <Card padding="lg" className="border-border-default">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle
              className={`h-5 w-5 ${hasErrors ? "text-accent-danger" : "text-text-muted"}`}
              aria-hidden="true"
            />
            <CardTitle as="h2" size="panel">
              Validation & Quarantine Errors
            </CardTitle>
          </div>
          {hasErrors ? (
            <Badge variant="danger">
              {errorList.length >= 100 ? "100+ Errors" : `${errorList.length} Errors`}
            </Badge>
          ) : (
            <Badge variant="success">Zero Errors</Badge>
          )}
        </div>
        <CardDescription>
          {hasErrors
            ? "Record-level validation failures, formatting errors, and schema violations logged during ingestion (capped at 100 items)."
            : "All processed rows satisfied canonical schema constraints and reference entity requirements."}
        </CardDescription>
      </CardHeader>

      <CardContent>
        {!hasErrors ? (
          <div className="flex items-center gap-3 rounded-lg border border-border-default bg-surface-secondary p-4 text-[13px] text-text-secondary">
            <CheckCircle className="h-5 w-5 text-accent-success shrink-0" aria-hidden="true" />
            <span>
              No validation, formatting, or quarantine errors were recorded for this import
              execution.
            </span>
          </div>
        ) : (
          <div className="space-y-2">
            <div className="max-h-[400px] overflow-y-auto rounded-lg border border-border-default">
              <Table aria-label="Dataset import validation error log">
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-20">Row #</TableHead>
                    <TableHead className="w-36">Field</TableHead>
                    <TableHead className="w-44">Code</TableHead>
                    <TableHead>Error Message</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {errorList.map((err, idx) => (
                    <TableRow key={`${err.row_number ?? "none"}-${err.error_code}-${idx}`}>
                      <TableCell className="font-mono text-[12px] text-text-secondary">
                        {err.row_number !== null && err.row_number !== undefined
                          ? err.row_number
                          : "—"}
                      </TableCell>
                      <TableCell className="font-mono text-[12px] text-text-primary">
                        {err.field_name || "—"}
                      </TableCell>
                      <TableCell>
                        <Badge variant="danger" className="text-[11px] font-mono">
                          {err.error_code}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-[13px] text-text-primary">{err.message}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            {errorList.length >= 100 ? (
              <p className="text-[11px] text-text-muted italic">
                Showing the first 100 recorded errors. Additional row-level quarantine errors are
                stored in server logs.
              </p>
            ) : null}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
