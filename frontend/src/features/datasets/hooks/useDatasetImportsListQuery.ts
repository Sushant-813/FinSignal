import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { datasetImportKeys } from "../../../lib/api/query-keys.ts";
import { listDatasetImports } from "../api/datasets-api.ts";
import type { DatasetImportListParams } from "../types/datasets.types.ts";
import { isPollingCutoffReached, shouldPollImport } from "./polling-tracker.ts";

export function useDatasetImportsListQuery(params: DatasetImportListParams) {
  const query = useQuery({
    queryKey: datasetImportKeys.list(params),
    queryFn: ({ signal }) => listDatasetImports(params, signal),
    placeholderData: keepPreviousData,
    staleTime: 10_000,
    refetchInterval: (q) => {
      const data = q.state.data;
      if (!data?.items || data.items.length === 0) {
        return false;
      }
      const hasActive = data.items.some((item) => shouldPollImport(item.id, item.status));
      return hasActive ? 5_000 : false;
    },
    refetchIntervalInBackground: false,
  });

  const hasCutoffReached = Boolean(
    query.data?.items?.some((item) => isPollingCutoffReached(item.id, item.status))
  );

  return {
    ...query,
    hasCutoffReached,
  };
}

