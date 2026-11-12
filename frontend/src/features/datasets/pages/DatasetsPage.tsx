import { Alert } from "../../../components/ui/Alert.tsx";
import { Pagination } from "../../../components/ui/Pagination.tsx";
import { isApiClientError } from "../../../lib/api/errors.ts";
import { canManageDatasets } from "../../../lib/permissions/capabilities.ts";
import { useAuth } from "../../auth/hooks/useAuth.ts";
import { DatasetFiltersBar } from "../components/DatasetFiltersBar.tsx";
import { DatasetImportTable } from "../components/DatasetImportTable.tsx";
import { DatasetUploadCard } from "../components/DatasetUploadCard.tsx";
import { useDatasetFilterParams } from "../hooks/useDatasetFilterParams.ts";
import { useDatasetImportsListQuery } from "../hooks/useDatasetImportsListQuery.ts";

export function DatasetsPage() {
  const { user } = useAuth();
  const operatorCanManage = canManageDatasets(user);

  const {
    filters,
    setPage,
    setPageSize,
    setNamespace,
    setStatus,
    setDateRange,
    resetFilters,
  } = useDatasetFilterParams();

  const listQuery = useDatasetImportsListQuery(filters);

  const isNamespaceNotFound =
    isApiClientError(listQuery.error) &&
    listQuery.error.status === 404 &&
    listQuery.error.code === "NAMESPACE_NOT_FOUND";

  return (
    <div className="space-y-6">
      {/* Page Title & Mission Header */}
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-[20px] leading-7 font-semibold tracking-tight text-text-primary">
            Datasets
          </h1>
          <p className="text-[13px] text-text-secondary">
            Ingest financial transaction datasets, track streaming ingestion state, and inspect data quality outcomes.
          </p>
        </div>
      </div>

      {/* Role Notice */}
      {operatorCanManage ? (
        <Alert
          variant="info"
          role="region"
          aria-label="Dataset role permissions"
        >
          Your role has full dataset permissions: read-only import history plus CSV upload and recovery workflows (Phase F4).
        </Alert>
      ) : (
        <Alert
          variant="info"
          role="region"
          aria-label="Investigator read-only dataset permissions"
        >
          Read-only dataset import history is permitted for Investigator accounts. Dataset upload and import recovery actions require Administrator or Analyst roles and are disabled for your role.
        </Alert>
      )}

      {/* Upload Card: Accessible strictly to ADMIN and ANALYST */}
      {operatorCanManage ? (
        <DatasetUploadCard
          onUploadSuccess={() => {
            void listQuery.refetch();
          }}
          onRefreshHistory={() => {
            void listQuery.refetch();
          }}
        />
      ) : null}

      {/* Filters Bar */}
      <DatasetFiltersBar
        filters={filters}
        onNamespaceChange={setNamespace}
        onStatusChange={setStatus}
        onDateRangeChange={setDateRange}
        onResetFilters={resetFilters}
        onRefresh={() => {
          void listQuery.refetch();
        }}
        isNamespaceNotFound={isNamespaceNotFound}
        isLoading={listQuery.isFetching}
      />

      {/* Import History Ledger Table */}
      <DatasetImportTable
        items={listQuery.data?.items}
        isLoading={listQuery.isLoading}
        hasCutoffReached={listQuery.hasCutoffReached}
        onRefresh={() => {
          void listQuery.refetch();
        }}
      />

      {/* Server-Side Pagination */}
      {listQuery.data && listQuery.data.total > 0 ? (
        <Pagination
          page={listQuery.data.page}
          totalPages={listQuery.data.total_pages}
          pageSize={listQuery.data.page_size}
          total={listQuery.data.total}
          onPageChange={setPage}
          onPageSizeChange={setPageSize}
        />
      ) : null}
    </div>
  );
}
