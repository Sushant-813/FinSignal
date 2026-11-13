import { FolderPlus, RefreshCw } from "lucide-react";
import { useState } from "react";
import { Alert } from "../../../components/ui/Alert.tsx";
import { Button } from "../../../components/ui/Button.tsx";
import { canCreateInvestigation, canViewInvestigations } from "../../../lib/permissions/capabilities.ts";
import { useAuth } from "../../auth/hooks/useAuth.ts";
import { InvestigationCreateDialog } from "../components/InvestigationCreateDialog.tsx";
import { InvestigationFiltersBar } from "../components/InvestigationFiltersBar.tsx";
import { InvestigationQueueTable } from "../components/InvestigationQueueTable.tsx";
import { useInvestigationFilterParams } from "../hooks/useInvestigationFilterParams.ts";
import { useInvestigationListQuery } from "../hooks/useInvestigationListQuery.ts";

export function InvestigationsQueuePage() {
  const { user } = useAuth();
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  const {
    filters,
    assigneeMode,
    setPage,
    setPageSize,
    setStatus,
    setPriority,
    setAssigneeMode,
    resetFilters,
  } = useInvestigationFilterParams(user?.id);

  const queueQuery = useInvestigationListQuery(filters);

  if (!canViewInvestigations(user)) {
    return (
      <div className="mx-auto max-w-7xl space-y-6">
        <Alert variant="warning" role="alert" title="Access restricted">
          Your account does not have permission to view the investigation queue.
        </Alert>
      </div>
    );
  }

  const isFiltered =
    Boolean(filters.status) ||
    Boolean(filters.priority) ||
    filters.unassigned === true ||
    Boolean(filters.assigned_to) ||
    filters.page > 1;

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-[24px] leading-8 font-semibold tracking-tight text-text-primary">
            Investigations
          </h1>
          <p className="text-sm text-text-secondary">
            Manage, triage, and progress financial transaction investigation cases.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => void queueQuery.refetch()}
            disabled={queueQuery.isFetching}
            aria-label="Refresh investigation queue"
          >
            <RefreshCw
              className={`h-4 w-4 ${queueQuery.isFetching ? "animate-spin" : ""}`}
              aria-hidden="true"
            />
            Refresh
          </Button>

          {canCreateInvestigation(user) && (
            <Button
              type="button"
              variant="primary"
              size="sm"
              onClick={() => setIsCreateOpen(true)}
              data-testid="new-investigation-button"
            >
              <FolderPlus className="h-4 w-4" aria-hidden="true" />
              New Investigation
            </Button>
          )}
        </div>
      </div>

      {/* Filters Bar */}
      <InvestigationFiltersBar
        filters={filters}
        assigneeMode={assigneeMode}
        onStatusChange={setStatus}
        onPriorityChange={setPriority}
        onAssigneeModeChange={setAssigneeMode}
        onPageSizeChange={setPageSize}
        onReset={resetFilters}
        currentUserId={user?.id}
        disabled={queueQuery.isLoading && !queueQuery.data}
      />

      {/* Queue Table */}
      <InvestigationQueueTable
        items={queueQuery.data?.items}
        total={queueQuery.data?.total ?? 0}
        totalPages={queueQuery.data?.total_pages ?? 0}
        page={filters.page}
        pageSize={filters.page_size}
        isLoading={queueQuery.isLoading}
        isError={queueQuery.isError}
        error={queueQuery.error}
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
        onRetry={() => void queueQuery.refetch()}
        isFiltered={isFiltered}
      />

      {/* Creation Dialog */}
      {isCreateOpen && (
        <InvestigationCreateDialog
          isOpen={isCreateOpen}
          onClose={() => setIsCreateOpen(false)}
        />
      )}
    </div>
  );
}

