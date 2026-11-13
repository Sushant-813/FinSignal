import { RotateCcw } from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "../../../components/ui/Button.tsx";
import { Input } from "../../../components/ui/Input.tsx";
import { Select } from "../../../components/ui/Select.tsx";
import type { AssigneeFilterMode } from "../hooks/useInvestigationFilterParams.ts";
import { UUID_REGEX } from "../schemas/investigation-filter-schema.ts";
import type {
  InvestigationListParams,
  InvestigationPriority,
  InvestigationStatus,
} from "../types/investigations.types.ts";

export interface InvestigationFiltersBarProps {
  readonly filters: InvestigationListParams;
  readonly assigneeMode: AssigneeFilterMode;
  readonly onStatusChange: (status?: InvestigationStatus | null) => void;
  readonly onPriorityChange: (priority?: InvestigationPriority | null) => void;
  readonly onAssigneeModeChange: (mode: AssigneeFilterMode, customUserId?: string) => void;
  readonly onPageSizeChange: (pageSize: number) => void;
  readonly onReset: () => void;
  readonly currentUserId?: string | null | undefined;
  readonly disabled?: boolean | undefined;
}

const STATUS_OPTIONS = [
  { value: "ALL", label: "All Statuses" },
  { value: "OPEN", label: "Open" },
  { value: "UNDER_REVIEW", label: "Under Review" },
  { value: "RESOLVED", label: "Resolved" },
] as const;

const PRIORITY_OPTIONS = [
  { value: "ALL", label: "All Priorities" },
  { value: "LOW", label: "Low" },
  { value: "MEDIUM", label: "Medium" },
  { value: "HIGH", label: "High" },
  { value: "CRITICAL", label: "Critical" },
] as const;

const PAGE_SIZE_OPTIONS = [
  { value: "10", label: "10 per page" },
  { value: "25", label: "25 per page" },
  { value: "50", label: "50 per page" },
  { value: "100", label: "100 per page" },
] as const;

export function InvestigationFiltersBar({
  filters,
  assigneeMode,
  onStatusChange,
  onPriorityChange,
  onAssigneeModeChange,
  onPageSizeChange,
  onReset,
  currentUserId,
  disabled = false,
}: InvestigationFiltersBarProps) {
  const [customAssigneeInput, setCustomAssigneeInput] = useState(
    assigneeMode === "OTHER" ? filters.assigned_to ?? "" : ""
  );

  useEffect(() => {
    if (assigneeMode === "OTHER") {
      setCustomAssigneeInput(filters.assigned_to ?? "");
    } else {
      setCustomAssigneeInput("");
    }
  }, [assigneeMode, filters.assigned_to]);

  const assigneeOptions = [
    { value: "ALL", label: "All Assignees" },
    ...(currentUserId ? [{ value: "MINE", label: "Assigned to Me" }] : []),
    { value: "UNASSIGNED", label: "Unassigned" },
    { value: "OTHER", label: "Specific User ID" },
  ];

  const handleCustomAssigneeCommit = () => {
    const trimmed = customAssigneeInput.trim();
    if (trimmed === "") {
      onAssigneeModeChange("ALL");
    } else if (UUID_REGEX.test(trimmed)) {
      onAssigneeModeChange("OTHER", trimmed);
    }
  };

  const hasActiveFilters =
    Boolean(filters.status) ||
    Boolean(filters.priority) ||
    filters.unassigned === true ||
    Boolean(filters.assigned_to);

  return (
    <div
      className="space-y-4 rounded-card border border-border bg-surface p-4 shadow-card"
      data-testid="investigation-filters-bar"
    >
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-4 lg:flex lg:flex-wrap lg:items-end">
        {/* Status */}
        <div className="w-full sm:w-44">
          <Select
            label="Status"
            value={filters.status ?? "ALL"}
            onValueChange={(val) => {
              onStatusChange(val === "ALL" ? undefined : (val as InvestigationStatus));
            }}
            options={STATUS_OPTIONS}
            disabled={disabled}
          />
        </div>

        {/* Priority */}
        <div className="w-full sm:w-44">
          <Select
            label="Priority"
            value={filters.priority ?? "ALL"}
            onValueChange={(val) => {
              onPriorityChange(val === "ALL" ? undefined : (val as InvestigationPriority));
            }}
            options={PRIORITY_OPTIONS}
            disabled={disabled}
          />
        </div>

        {/* Assignee Filter */}
        <div className="w-full sm:w-48">
          <Select
            label="Assignee"
            value={assigneeMode}
            onValueChange={(val) => {
              const mode = val as AssigneeFilterMode;
              if (mode === "OTHER") {
                onAssigneeModeChange("OTHER", customAssigneeInput);
              } else {
                onAssigneeModeChange(mode);
              }
            }}
            options={assigneeOptions}
            disabled={disabled}
          />
        </div>

        {/* Custom Assignee UUID Input when OTHER selected */}
        {assigneeMode === "OTHER" && (
          <div className="w-full sm:w-64">
            <Input
              label="User UUID"
              placeholder="00000000-0000-4000-8000-000000000000"
              value={customAssigneeInput}
              onChange={(e) => setCustomAssigneeInput(e.target.value)}
              onBlur={handleCustomAssigneeCommit}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  handleCustomAssigneeCommit();
                }
              }}
              disabled={disabled}
              error={
                customAssigneeInput.trim() !== "" && !UUID_REGEX.test(customAssigneeInput.trim())
                  ? "Invalid UUID format"
                  : undefined
              }
              aria-label="Custom assignee UUID"
            />
          </div>
        )}

        {/* Page Size */}
        <div className="w-full sm:w-36">
          <Select
            label="Page Size"
            value={String(filters.page_size)}
            onValueChange={(val) => onPageSizeChange(Number(val))}
            options={PAGE_SIZE_OPTIONS}
            disabled={disabled}
          />
        </div>

        {/* Reset */}
        {hasActiveFilters && (
          <div>
            <Button
              type="button"
              variant="tertiary"
              size="sm"
              onClick={onReset}
              disabled={disabled}
              className="text-text-secondary hover:text-text-primary"
              aria-label="Reset all filters"
            >
              <RotateCcw className="h-4 w-4" aria-hidden="true" />
              Reset Filters
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
