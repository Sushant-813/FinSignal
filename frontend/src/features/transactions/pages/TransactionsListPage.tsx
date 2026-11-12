import { RefreshCw } from "lucide-react";
import { Alert } from "../../../components/ui/Alert.tsx";
import { Button } from "../../../components/ui/Button.tsx";
import { Pagination } from "../../../components/ui/Pagination.tsx";
import {
  getUserFriendlyErrorMessage,
  isApiClientError,
  isForbiddenError,
} from "../../../lib/api/errors.ts";
import { TransactionFiltersBar } from "../components/TransactionFiltersBar.tsx";
import { TransactionTable } from "../components/TransactionTable.tsx";
import { useTransactionFilterParams } from "../hooks/useTransactionFilterParams.ts";
import { useTransactionListQuery } from "../hooks/useTransactionListQuery.ts";

export function TransactionsListPage() {
  const {
    filters,
    formDates,
    activeFilterCount,
    hadInvalidUrlParams,
    applyFilters,
    resetFilters,
    setPage,
    setPageSize,
    toggleSort,
  } = useTransactionFilterParams();

  const listQuery = useTransactionListQuery(filters);

  const err = listQuery.error;
  const requestId = isApiClientError(err) ? err.requestId : undefined;
  const isNamespaceNotFound = isApiClientError(err) && err.code === "NAMESPACE_NOT_FOUND";
  const isForbidden = isForbiddenError(err);

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-[24px] leading-8 font-semibold tracking-tight text-text-primary">
            Transactions
          </h1>
          <p className="text-sm text-text-secondary">
            Server-paginated ledger exploration in namespace{" "}
            <span className="font-mono font-medium text-text-primary">
              {filters.source_namespace}
            </span>
            . Each row preserves its exact decimal amount and currency.
          </p>
        </div>

        {listQuery.isFetching && !listQuery.isLoading ? (
          <span role="status" className="text-xs text-text-muted">
            Refreshing transactions...
          </span>
        ) : null}
      </div>

      <TransactionFiltersBar
        filters={filters}
        formDates={formDates}
        activeFilterCount={activeFilterCount}
        hadInvalidUrlParams={hadInvalidUrlParams}
        isFetching={listQuery.isFetching}
        onApply={applyFilters}
        onReset={resetFilters}
      />

      {listQuery.isError ? (
        <Alert
          variant={isNamespaceNotFound || isForbidden ? "warning" : "danger"}
          role="alert"
          title={
            isNamespaceNotFound
              ? "Namespace not found"
              : isForbidden
                ? "Access denied"
                : "Unable to load transactions"
          }
          requestId={requestId}
          action={
            isNamespaceNotFound ? (
              <Button variant="secondary" size="sm" onClick={resetFilters}>
                Reset filters
              </Button>
            ) : !isForbidden ? (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  void listQuery.refetch();
                }}
              >
                <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
                <span>Retry</span>
              </Button>
            ) : undefined
          }
        >
          {getUserFriendlyErrorMessage(err)}
        </Alert>
      ) : (
        <>
          <TransactionTable
            items={listQuery.data?.items ?? []}
            total={listQuery.data?.total ?? 0}
            page={listQuery.data?.page ?? filters.page}
            isLoading={listQuery.isLoading}
            hasActiveFilters={activeFilterCount > 0}
            sortBy={filters.sort_by}
            sortOrder={filters.sort_order}
            onSort={toggleSort}
            onResetFilters={resetFilters}
            onGoToFirstPage={() => setPage(1)}
          />

          {listQuery.data ? (
            <Pagination
              page={listQuery.data.page}
              pageSize={listQuery.data.page_size}
              total={listQuery.data.total}
              totalPages={listQuery.data.total_pages}
              onPageChange={setPage}
              onPageSizeChange={setPageSize}
              disabled={listQuery.isFetching}
              ariaLabel="Transactions pagination"
            />
          ) : null}
        </>
      )}
    </div>
  );
}
