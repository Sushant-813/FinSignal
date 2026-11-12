import { useMutation, useQueryClient } from "@tanstack/react-query";
import { analyticsKeys, datasetImportKeys, transactionKeys } from "../../../lib/api/query-keys.ts";
import { recoverDatasetImport } from "../api/datasets-api.ts";
import type {
  DatasetImportDetailResponse,
  DatasetImportResponse,
  RecoverDatasetPayload,
} from "../types/datasets.types.ts";

export function useRecoverDatasetMutation() {
  const queryClient = useQueryClient();

  return useMutation<DatasetImportResponse, unknown, RecoverDatasetPayload>({
    mutationFn: (payload) => recoverDatasetImport(payload),
    retry: false,
    onSuccess: (summaryData, variables) => {
      const importId = variables.importId;

      // 1. Invalidate detail query to trigger authoritative refetch
      void queryClient.invalidateQueries({
        queryKey: datasetImportKeys.detail(importId),
      });

      // 2. Optimistically update existing detail cache ONLY if it already exists, strictly preserving errors
      queryClient.setQueryData<DatasetImportDetailResponse | undefined>(
        datasetImportKeys.detail(importId),
        (old) => {
          if (!old) {
            return undefined; // Never populate detail cache with summary-only data!
          }
          const updated: DatasetImportDetailResponse = {
            ...old,
            ...summaryData,
            ...(old.errors !== undefined ? { errors: old.errors } : {}),
          };
          return updated;
        }
      );

      // 3. Invalidate import history table
      void queryClient.invalidateQueries({
        queryKey: datasetImportKeys.lists(),
      });

      // 4. Invalidate transactions and analytics since recovery ingests uncommitted rows into PostgreSQL
      void queryClient.invalidateQueries({ queryKey: transactionKeys.lists() });
      void queryClient.invalidateQueries({ queryKey: analyticsKeys.all });
    },
  });
}
