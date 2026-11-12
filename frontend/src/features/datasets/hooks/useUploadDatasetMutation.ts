import { useMutation, useQueryClient } from "@tanstack/react-query";
import { isApiClientError } from "../../../lib/api/errors.ts";
import { analyticsKeys, datasetImportKeys, transactionKeys } from "../../../lib/api/query-keys.ts";
import { uploadDataset } from "../api/datasets-api.ts";
import type { DatasetImportResponse, UploadDatasetPayload } from "../types/datasets.types.ts";

function extractPersistedImportId(details: unknown): string | undefined {
  if (typeof details === "object" && details !== null) {
    const rec = details as Record<string, unknown>;
    if (typeof rec.import_id === "string" && rec.import_id.trim() !== "") {
      return rec.import_id.trim();
    }
    if (typeof rec.persisted_import_id === "string" && rec.persisted_import_id.trim() !== "") {
      return rec.persisted_import_id.trim();
    }
  }
  return undefined;
}

export function useUploadDatasetMutation() {
  const queryClient = useQueryClient();

  return useMutation<DatasetImportResponse, unknown, UploadDatasetPayload>({
    mutationFn: (payload) => uploadDataset(payload),
    retry: false,
    onSuccess: (data) => {
      // Always invalidate import history so the new or duplicate execution is listed
      void queryClient.invalidateQueries({ queryKey: datasetImportKeys.lists() });

      // Transactions and analytics are invalidated ONLY if new transactions were actually ingested
      if (!data.is_duplicate) {
        void queryClient.invalidateQueries({ queryKey: transactionKeys.lists() });
        void queryClient.invalidateQueries({ queryKey: analyticsKeys.all });
      }
    },
    onError: (error) => {
      // Invalidate import history ONLY if a persisted import record ID is confirmed in error details
      if (isApiClientError(error) && error.status === 422) {
        const persistedId = extractPersistedImportId(error.details);
        if (persistedId) {
          void queryClient.invalidateQueries({ queryKey: datasetImportKeys.lists() });
        }
      }
    },
  });
}
