import { ArrowLeft, RefreshCw, RotateCcw } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router";
import { Alert } from "../../../components/ui/Alert.tsx";
import { Button } from "../../../components/ui/Button.tsx";
import { Skeleton } from "../../../components/ui/Skeleton.tsx";
import { isApiClientError } from "../../../lib/api/errors.ts";
import { canManageDatasets } from "../../../lib/permissions/capabilities.ts";
import { useAuth } from "../../auth/hooks/useAuth.ts";
import { DatasetImportErrorTable } from "../components/DatasetImportErrorTable.tsx";
import { DatasetImportSummaryCard } from "../components/DatasetImportSummaryCard.tsx";
import { DatasetRecoveryDialog } from "../components/DatasetRecoveryDialog.tsx";
import { useDatasetImportDetailQuery } from "../hooks/useDatasetImportDetailQuery.ts";

export function DatasetImportDetailPage() {
  const { importId } = useParams<{ importId: string }>();
  const { user } = useAuth();
  const operatorCanManage = canManageDatasets(user);

  const [recoveryOpen, setRecoveryOpen] = useState(false);

  const detailQuery = useDatasetImportDetailQuery(importId || "");
  const importData = detailQuery.data;

  const isNotFound =
    isApiClientError(detailQuery.error) &&
    (detailQuery.error.status === 404 || detailQuery.error.code === "RESOURCE_NOT_FOUND");

  return (
    <div className="space-y-6">
      {/* Back Link & Header Navigation */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <Button asChild variant="tertiary" size="sm">
            <Link to="/datasets">
              <ArrowLeft className="h-4 w-4" />
              Back to Datasets
            </Link>
          </Button>
          <div className="h-4 w-[1px] bg-border-default" aria-hidden="true" />
          <h1 className="text-[20px] leading-7 font-semibold tracking-tight text-text-primary">
            Import Details
          </h1>
        </div>

        {importData ? (
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                void detailQuery.refetch();
              }}
              isLoading={detailQuery.isFetching}
            >
              <RotateCcw className="h-4 w-4" />
              Refresh
            </Button>

            {/* Recover Action: Gated strictly to FAILED status and ADMIN/ANALYST roles */}
            {importData.status === "FAILED" && operatorCanManage ? (
              <Button variant="primary" size="sm" onClick={() => setRecoveryOpen(true)}>
                <RefreshCw className="h-4 w-4" />
                Recover Import
              </Button>
            ) : null}
          </div>
        ) : null}
      </div>

      {/* Loading Skeleton */}
      {detailQuery.isLoading ? (
        <div className="space-y-4">
          <Skeleton variant="block" className="h-48" />
          <Skeleton variant="block" className="h-64" />
        </div>
      ) : null}

      {/* 404 Not Found State */}
      {isNotFound ? (
        <Alert
          variant="danger"
          role="alert"
          aria-label="Dataset import not found"
          action={
            <Button asChild size="sm" variant="secondary">
              <Link to="/datasets">Return to History</Link>
            </Button>
          }
        >
          Dataset import execution &ldquo;{importId}&rdquo; was not found in the system of record.
        </Alert>
      ) : null}

      {/* Other Error State */}
      {detailQuery.error && !isNotFound ? (
        <Alert
          variant="danger"
          role="alert"
          action={
            <Button size="sm" variant="secondary" onClick={() => detailQuery.refetch()}>
              Retry Query
            </Button>
          }
        >
          {detailQuery.error instanceof Error
            ? detailQuery.error.message
            : "Failed to load import execution details."}
        </Alert>
      ) : null}

      {/* Content Rendering */}
      {importData ? (
        <>
          <DatasetImportSummaryCard
            importData={importData}
            isCutoffReached={detailQuery.isCutoffReached}
            onRefresh={() => {
              void detailQuery.refetch();
            }}
          />

          <DatasetImportErrorTable errors={importData.errors} />

          {/* Recovery Dialog Modal */}
          {importData.status === "FAILED" && operatorCanManage ? (
            <DatasetRecoveryDialog
              importData={importData}
              open={recoveryOpen}
              onOpenChange={setRecoveryOpen}
              onRecoverySuccess={() => {
                void detailQuery.refetch();
              }}
            />
          ) : null}
        </>
      ) : null}
    </div>
  );
}
