import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { investigationKeys } from "../../../lib/api/query-keys.ts";
import { listInvestigations } from "../api/investigations-api.ts";
import type { InvestigationListParams } from "../types/investigations.types.ts";

export function useInvestigationListQuery(params: InvestigationListParams) {
  return useQuery({
    queryKey: investigationKeys.list(params),
    queryFn: ({ signal }) => listInvestigations(params, signal),
    placeholderData: keepPreviousData,
    staleTime: 10_000,
  });
}

