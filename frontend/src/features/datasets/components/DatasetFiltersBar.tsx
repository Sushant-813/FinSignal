import { RotateCcw } from "lucide-react";
import { useState } from "react";
import { Alert } from "../../../components/ui/Alert.tsx";
import { Button } from "../../../components/ui/Button.tsx";
import { Card, CardContent } from "../../../components/ui/Card.tsx";
import { Input } from "../../../components/ui/Input.tsx";
import { Select } from "../../../components/ui/Select.tsx";
import {
  IMPORT_STATUSES,
  mapDateRangeToUtcIsoBoundaries,
} from "../schemas/dataset-filter-schema.ts";
import type { DatasetImportListParams, DatasetImportStatus } from "../types/datasets.types.ts";

export interface DatasetFiltersBarProps {
  filters: DatasetImportListParams;
  onNamespaceChange: (ns: string) => void;
  onStatusChange: (status?: DatasetImportStatus | null) => void;
  onDateRangeChange: (fromTime?: string | null, toTime?: string | null) => void;
  onResetFilters: () => void;
  onRefresh: () => void;
  isNamespaceNotFound?: boolean | undefined;
  isLoading?: boolean | undefined;
}

export function DatasetFiltersBar({
  filters,
  onNamespaceChange,
  onStatusChange,
  onDateRangeChange,
  onResetFilters,
  onRefresh,
  isNamespaceNotFound = false,
  isLoading = false,
}: DatasetFiltersBarProps) {
  const [namespaceInput, setNamespaceInput] = useState(filters.source_namespace);
  const [startDate, setStartDate] = useState(() => {
    return filters.from_time ? filters.from_time.slice(0, 10) : "";
  });
  const [endDate, setEndDate] = useState(() => {
    if (!filters.to_time) return "";
    // Reconstruct inclusive UI date by subtracting 1 day if exact 00:00:00Z boundary
    const toDate = new Date(filters.to_time);
    toDate.setUTCDate(toDate.getUTCDate() - 1);
    return toDate.toISOString().slice(0, 10);
  });
  const [dateRangeError, setDateRangeError] = useState<string | null>(null);

  const handleNamespaceBlur = () => {
    const trimmed = namespaceInput.trim();
    if (trimmed && trimmed !== filters.source_namespace) {
      onNamespaceChange(trimmed);
    }
  };

  const handleNamespaceKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      handleNamespaceBlur();
    }
  };

  const handleDateChange = (newStart: string, newEnd: string) => {
    setStartDate(newStart);
    setEndDate(newEnd);
    setDateRangeError(null);

    if (!newStart && !newEnd) {
      onDateRangeChange(undefined, undefined);
      return;
    }

    const mapping = mapDateRangeToUtcIsoBoundaries(newStart || undefined, newEnd || undefined);
    if (mapping.error) {
      setDateRangeError(mapping.error);
    } else {
      onDateRangeChange(mapping.from_time, mapping.to_time);
    }
  };

  const handleReset = () => {
    setNamespaceInput("SYNTHETIC");
    setStartDate("");
    setEndDate("");
    setDateRangeError(null);
    onResetFilters();
  };

  return (
    <div className="space-y-3">
      {isNamespaceNotFound ? (
        <Alert
          variant="warning"
          role="alert"
          aria-label="Namespace not found error"
          action={
            <Button
              size="sm"
              variant="secondary"
              onClick={() => {
                setNamespaceInput("SYNTHETIC");
                onNamespaceChange("SYNTHETIC");
              }}
            >
              Reset to SYNTHETIC
            </Button>
          }
        >
          Target namespace &ldquo;{filters.source_namespace}&rdquo; does not exist. No import history can be shown for this namespace.
        </Alert>
      ) : null}

      <Card padding="md">
        <CardContent className="p-0">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-4 lg:flex lg:flex-wrap lg:items-end">
              <div className="w-full sm:w-44">
                <Input
                  label="Namespace"
                  value={namespaceInput}
                  onChange={(e) => setNamespaceInput(e.target.value)}
                  onBlur={handleNamespaceBlur}
                  onKeyDown={handleNamespaceKeyDown}
                  placeholder="e.g. SYNTHETIC"
                  aria-label="Filter by source namespace"
                />
              </div>

              <div className="w-full sm:w-40">
                <Select
                  label="Status"
                  value={filters.status ?? "ALL"}
                  onValueChange={(val) => {
                    onStatusChange(val === "ALL" ? undefined : (val as DatasetImportStatus));
                  }}
                  options={[
                    { value: "ALL", label: "All Statuses" },
                    ...IMPORT_STATUSES.map((st) => ({
                      value: st,
                      label: st.charAt(0) + st.slice(1).toLowerCase(),
                    })),
                  ]}
                  aria-label="Filter by import status"
                />
              </div>

              <div className="w-full sm:w-40">
                <Input
                  type="date"
                  label="From Date (UTC)"
                  value={startDate}
                  onChange={(e) => handleDateChange(e.target.value, endDate)}
                  aria-label="Start date filter in UTC"
                />
              </div>

              <div className="w-full sm:w-40">
                <Input
                  type="date"
                  label="To Date (UTC)"
                  value={endDate}
                  onChange={(e) => handleDateChange(startDate, e.target.value)}
                  aria-label="End date filter in UTC"
                />
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="tertiary"
                size="sm"
                onClick={handleReset}
                aria-label="Reset all filters to defaults"
              >
                Reset
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={onRefresh}
                isLoading={isLoading}
                aria-label="Refresh import history list"
              >
                <RotateCcw className="h-4 w-4" />
                Refresh
              </Button>
            </div>
          </div>

          {dateRangeError ? (
            <p className="mt-2 text-[12px] leading-4 text-accent-danger" role="alert">
              {dateRangeError}
            </p>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
