import { Check, Copy, FileText } from "lucide-react";
import { useState } from "react";
import { TimestampDisplay } from "../../../components/data-display/TimestampDisplay.tsx";
import { Alert } from "../../../components/ui/Alert.tsx";
import { Badge } from "../../../components/ui/Badge.tsx";
import { Button } from "../../../components/ui/Button.tsx";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/Card.tsx";
import type {
  DatasetImportDetailResponse,
  DatasetImportResponse,
} from "../types/datasets.types.ts";
import { DatasetImportStatusBadge } from "./DatasetImportStatusBadge.tsx";

export interface DatasetImportSummaryCardProps {
  importData: DatasetImportResponse | DatasetImportDetailResponse;
  isCutoffReached?: boolean | undefined;
  onRefresh?: (() => void) | undefined;
}

function calculateDuration(startedAt: string, completedAt?: string | null): string {
  if (!completedAt) return "—";
  const start = new Date(startedAt).getTime();
  const end = new Date(completedAt).getTime();
  if (Number.isNaN(start) || Number.isNaN(end) || end < start) return "—";

  const diffMs = end - start;
  const seconds = Math.floor(diffMs / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remSec = seconds % 60;
  return `${minutes}m ${remSec}s`;
}

export function DatasetImportSummaryCard({
  importData,
  isCutoffReached = false,
  onRefresh,
}: DatasetImportSummaryCardProps) {
  const [copiedHash, setCopiedHash] = useState(false);
  const [copiedId, setCopiedId] = useState(false);

  const copyToClipboard = async (text: string, isHash: boolean) => {
    try {
      await navigator.clipboard.writeText(text);
      if (isHash) {
        setCopiedHash(true);
        setTimeout(() => setCopiedHash(false), 2000);
      } else {
        setCopiedId(true);
        setTimeout(() => setCopiedId(false), 2000);
      }
    } catch {
      // Fallback if clipboard API not permitted
    }
  };

  const duration = calculateDuration(importData.started_at, importData.completed_at);

  return (
    <div className="space-y-4">
      {isCutoffReached ? (
        <Alert
          variant="warning"
          role="status"
          aria-label="Automatic monitoring paused for import"
          action={
            onRefresh ? (
              <Button size="sm" variant="secondary" onClick={onRefresh}>
                Refresh Status
              </Button>
            ) : undefined
          }
        >
          Automatic status monitoring has paused after 5 minutes of continuous observation. This
          import may still be processing on the server or may have been interrupted. Click
          &ldquo;Refresh Status&rdquo; to query the latest state.
        </Alert>
      ) : null}

      <Card padding="lg" className="border-border-default">
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-accent-primary" aria-hidden="true" />
              <CardTitle as="h2" size="panel">
                Import Summary Facts
              </CardTitle>
            </div>
            <div className="flex items-center gap-2">
              {importData.is_duplicate ? <Badge variant="neutral">Duplicate File</Badge> : null}
              <DatasetImportStatusBadge status={importData.status} />
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-6">
          {/* Key Metric Facts Grid */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="rounded-lg border border-border-default bg-surface-secondary p-4">
              <div className="text-[12px] font-medium text-text-secondary">
                Total Processed Rows
              </div>
              <div className="mt-1 text-[24px] font-semibold tracking-tight text-text-primary">
                {importData.total_rows.toLocaleString()}
              </div>
            </div>

            <div className="rounded-lg border border-border-default bg-surface-secondary p-4">
              <div className="text-[12px] font-medium text-text-secondary">Valid Ingested Rows</div>
              <div className="mt-1 text-[24px] font-semibold tracking-tight text-accent-success">
                {importData.valid_rows.toLocaleString()}
              </div>
            </div>

            <div className="rounded-lg border border-border-default bg-surface-secondary p-4">
              <div className="text-[12px] font-medium text-text-secondary">
                Invalid / Quarantined Rows
              </div>
              <div
                className={`mt-1 text-[24px] font-semibold tracking-tight ${
                  importData.invalid_rows > 0 ? "text-accent-danger" : "text-text-muted"
                }`}
              >
                {importData.invalid_rows.toLocaleString()}
              </div>
            </div>
          </div>

          {/* Metadata Attribute Pairs */}
          <div className="grid grid-cols-1 gap-y-3 gap-x-6 text-[13px] sm:grid-cols-2">
            <div className="flex flex-col sm:flex-row sm:items-baseline sm:justify-between border-b border-border-subtle pb-2">
              <span className="text-text-secondary">Filename</span>
              <span className="font-medium text-text-primary">{importData.filename || "—"}</span>
            </div>

            <div className="flex flex-col sm:flex-row sm:items-baseline sm:justify-between border-b border-border-subtle pb-2">
              <span className="text-text-secondary">Import Identifier</span>
              <div className="flex items-center gap-1.5 font-mono text-[12px]">
                <span
                  title={importData.id}
                >{`${importData.id.slice(0, 8)}...${importData.id.slice(-4)}`}</span>
                <button
                  type="button"
                  onClick={() => copyToClipboard(importData.id, false)}
                  className="rounded p-1 text-text-muted hover:bg-surface-secondary hover:text-text-primary focus:outline-none"
                  aria-label="Copy full import identifier to clipboard"
                >
                  {copiedId ? (
                    <Check className="h-3.5 w-3.5 text-accent-success" />
                  ) : (
                    <Copy className="h-3.5 w-3.5" />
                  )}
                </button>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row sm:items-baseline sm:justify-between border-b border-border-subtle pb-2">
              <span className="text-text-secondary">Target Namespace</span>
              <span className="font-mono text-text-primary">{importData.source_namespace}</span>
            </div>

            <div className="flex flex-col sm:flex-row sm:items-baseline sm:justify-between border-b border-border-subtle pb-2">
              <span className="text-text-secondary">Source Type</span>
              <span className="font-medium text-text-primary">{importData.source_type}</span>
            </div>

            <div className="flex flex-col sm:flex-row sm:items-baseline sm:justify-between border-b border-border-subtle pb-2">
              <span className="text-text-secondary">Started (UTC)</span>
              <TimestampDisplay value={importData.started_at} />
            </div>

            <div className="flex flex-col sm:flex-row sm:items-baseline sm:justify-between border-b border-border-subtle pb-2">
              <span className="text-text-secondary">Completed (UTC)</span>
              {importData.completed_at ? (
                <TimestampDisplay value={importData.completed_at} />
              ) : (
                <span className="text-text-muted">—</span>
              )}
            </div>

            <div className="flex flex-col sm:flex-row sm:items-baseline sm:justify-between border-b border-border-subtle pb-2">
              <span className="text-text-secondary">Elapsed Duration</span>
              <span className="font-medium text-text-primary">{duration}</span>
            </div>

            <div className="flex flex-col sm:flex-row sm:items-baseline sm:justify-between border-b border-border-subtle pb-2">
              <span className="text-text-secondary">SHA-256 Stream Hash</span>
              {importData.file_hash ? (
                <div className="flex items-center gap-1.5 font-mono text-[11px]">
                  <span title={importData.file_hash}>
                    {`${importData.file_hash.slice(0, 10)}...${importData.file_hash.slice(-8)}`}
                  </span>
                  <button
                    type="button"
                    onClick={() => copyToClipboard(importData.file_hash || "", true)}
                    className="rounded p-1 text-text-muted hover:bg-surface-secondary hover:text-text-primary focus:outline-none"
                    aria-label="Copy full SHA-256 stream hash to clipboard"
                  >
                    {copiedHash ? (
                      <Check className="h-3.5 w-3.5 text-accent-success" />
                    ) : (
                      <Copy className="h-3.5 w-3.5" />
                    )}
                  </button>
                </div>
              ) : (
                <span className="text-text-muted">—</span>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
