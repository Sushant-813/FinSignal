import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router";
import {
  DEFAULT_PAGE,
  DEFAULT_PAGE_SIZE,
  parseInvestigationFilterParams,
} from "../schemas/investigation-filter-schema.ts";
import type {
  InvestigationListParams,
  InvestigationPriority,
  InvestigationStatus,
} from "../types/investigations.types.ts";

export type AssigneeFilterMode = "ALL" | "MINE" | "UNASSIGNED" | "OTHER";

export function useInvestigationFilterParams(currentUserId?: string | null | undefined) {
  const [searchParams, setSearchParams] = useSearchParams();

  const filters = useMemo<InvestigationListParams>(() => {
    return parseInvestigationFilterParams(searchParams);
  }, [searchParams]);

  const assigneeMode = useMemo<AssigneeFilterMode>(() => {
    if (filters.unassigned === true) {
      return "UNASSIGNED";
    }
    if (filters.assigned_to) {
      if (currentUserId && filters.assigned_to === currentUserId) {
        return "MINE";
      }
      return "OTHER";
    }
    return "ALL";
  }, [filters.unassigned, filters.assigned_to, currentUserId]);

  const updateFilters = useCallback(
    (
      updater: (prev: InvestigationListParams) => Partial<InvestigationListParams>,
      replace = false
    ) => {
      setSearchParams(
        (current) => {
          const currentFilters = parseInvestigationFilterParams(current);
          const next = { ...currentFilters, ...updater(currentFilters) };

          const nextParams = new URLSearchParams();

          if (next.page > DEFAULT_PAGE) {
            nextParams.set("page", String(next.page));
          }
          if (next.page_size !== DEFAULT_PAGE_SIZE) {
            nextParams.set("page_size", String(next.page_size));
          }
          if (next.status) {
            nextParams.set("status", next.status);
          }
          if (next.priority) {
            nextParams.set("priority", next.priority);
          }
          if (next.unassigned === true) {
            nextParams.set("unassigned", "true");
          } else if (next.assigned_to && next.assigned_to.trim() !== "") {
            nextParams.set("assigned_to", next.assigned_to.trim());
          }

          return nextParams;
        },
        { replace }
      );
    },
    [setSearchParams]
  );

  const setPage = useCallback(
    (page: number) => {
      updateFilters(() => ({ page: Math.max(1, page) }), false);
    },
    [updateFilters]
  );

  const setPageSize = useCallback(
    (pageSize: number) => {
      updateFilters(
        () => ({
          page: 1,
          page_size: Math.max(1, Math.min(pageSize, 100)),
        }),
        false
      );
    },
    [updateFilters]
  );

  const setStatus = useCallback(
    (status?: InvestigationStatus | null) => {
      updateFilters(
        () => ({
          page: 1,
          status: status || undefined,
        }),
        false
      );
    },
    [updateFilters]
  );

  const setPriority = useCallback(
    (priority?: InvestigationPriority | null) => {
      updateFilters(
        () => ({
          page: 1,
          priority: priority || undefined,
        }),
        false
      );
    },
    [updateFilters]
  );

  const setAssigneeMode = useCallback(
    (mode: AssigneeFilterMode, customUserId?: string) => {
      updateFilters(() => {
        if (mode === "UNASSIGNED") {
          return {
            page: 1,
            unassigned: true,
            assigned_to: undefined,
          };
        }
        if (mode === "MINE") {
          return {
            page: 1,
            unassigned: undefined,
            assigned_to: currentUserId || undefined,
          };
        }
        if (mode === "OTHER") {
          return {
            page: 1,
            unassigned: undefined,
            assigned_to: customUserId?.trim() || undefined,
          };
        }
        // ALL
        return {
          page: 1,
          unassigned: undefined,
          assigned_to: undefined,
        };
      }, false);
    },
    [currentUserId, updateFilters]
  );

  const resetFilters = useCallback(() => {
    setSearchParams(new URLSearchParams(), { replace: false });
  }, [setSearchParams]);

  return {
    filters,
    assigneeMode,
    setPage,
    setPageSize,
    setStatus,
    setPriority,
    setAssigneeMode,
    resetFilters,
  };
}
