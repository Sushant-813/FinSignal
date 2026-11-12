import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router";
import {
  parseDatasetFiltersFromParams,
} from "../schemas/dataset-filter-schema.ts";
import type { DatasetImportListParams, DatasetImportStatus } from "../types/datasets.types.ts";

export function useDatasetFilterParams() {
  const [searchParams, setSearchParams] = useSearchParams();

  const filters = useMemo<DatasetImportListParams>(() => {
    return parseDatasetFiltersFromParams(searchParams);
  }, [searchParams]);

  const updateFilters = useCallback(
    (updater: (prev: DatasetImportListParams) => Partial<DatasetImportListParams>) => {
      setSearchParams(
        (current) => {
          const currentFilters = parseDatasetFiltersFromParams(current);
          const next = { ...currentFilters, ...updater(currentFilters) };

          const nextParams = new URLSearchParams();

          if (next.page > 1) {
            nextParams.set("page", String(next.page));
          }
          if (next.page_size !== 20) {
            nextParams.set("page_size", String(next.page_size));
          }
          if (next.source_namespace && next.source_namespace !== "SYNTHETIC") {
            nextParams.set("source_namespace", next.source_namespace);
          }
          if (next.status) {
            nextParams.set("status", next.status);
          }
          if (next.source_type && next.source_type.trim() !== "") {
            nextParams.set("source_type", next.source_type.trim());
          }
          if (next.from_time && next.from_time.trim() !== "") {
            nextParams.set("from_time", next.from_time.trim());
          }
          if (next.to_time && next.to_time.trim() !== "") {
            nextParams.set("to_time", next.to_time.trim());
          }

          return nextParams;
        },
        { replace: true }
      );
    },
    [setSearchParams]
  );

  const setPage = useCallback(
    (page: number) => {
      updateFilters(() => ({ page: Math.max(1, page) }));
    },
    [updateFilters]
  );

  const setPageSize = useCallback(
    (pageSize: number) => {
      updateFilters(() => ({ page: 1, page_size: Math.max(1, Math.min(pageSize, 100)) }));
    },
    [updateFilters]
  );

  const setNamespace = useCallback(
    (ns: string) => {
      updateFilters(() => ({ page: 1, source_namespace: ns.trim() }));
    },
    [updateFilters]
  );

  const setStatus = useCallback(
    (status?: DatasetImportStatus | null) => {
      updateFilters(() => ({ page: 1, status: status || undefined }));
    },
    [updateFilters]
  );

  const setSourceType = useCallback(
    (sourceType?: string | null) => {
      updateFilters(() => ({ page: 1, source_type: sourceType?.trim() || undefined }));
    },
    [updateFilters]
  );

  const setDateRange = useCallback(
    (fromTime?: string | null, toTime?: string | null) => {
      updateFilters(() => ({
        page: 1,
        from_time: fromTime || undefined,
        to_time: toTime || undefined,
      }));
    },
    [updateFilters]
  );

  const resetFilters = useCallback(() => {
    setSearchParams(
      (current) => {
        const next = new URLSearchParams();
        // Preserve namespace if set, or revert to SYNTHETIC
        const currentNs = current.get("source_namespace");
        if (currentNs && currentNs !== "SYNTHETIC") {
          next.set("source_namespace", currentNs);
        }
        return next;
      },
      { replace: true }
    );
  }, [setSearchParams]);

  return {
    filters,
    setPage,
    setPageSize,
    setNamespace,
    setStatus,
    setSourceType,
    setDateRange,
    resetFilters,
  };
}
