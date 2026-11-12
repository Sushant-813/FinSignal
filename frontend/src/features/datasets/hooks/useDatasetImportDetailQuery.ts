import { useQuery } from "@tanstack/react-query";
import { datasetImportKeys } from "../../../lib/api/query-keys.ts";
import { getDatasetImportDetail } from "../api/datasets-api.ts";
import { isPollingCutoffReached, shouldPollImport } from "./polling-tracker.ts";

export function useDatasetImportDetailQuery(importId: string) {
  const query = useQuery({
    queryKey: datasetImportKeys.detail(importId),
    queryFn: ({ signal }) => getDatasetImportDetail(importId, signal),
    enabled: Boolean(importId && importId.trim() !== ""),
    staleTime: 10_000,
    refetchInterval: (q) => {
      const data = q.state.data;
      if (!data) return false;
      return shouldPollImport(data.id, data.status) ? 5_000 : false;
    },
    refetchIntervalInBackground: false,
  });

  const isCutoffReached = Boolean(
    query.data && isPollingCutoffReached(query.data.id, query.data.status)
  );

  return {
    ...query,
    isCutoffReached,
  };
}

