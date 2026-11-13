import { useQuery } from "@tanstack/react-query";
import { investigationKeys } from "../../../lib/api/query-keys.ts";
import { getInvestigation } from "../api/investigations-api.ts";
import { UUID_REGEX } from "../schemas/investigation-filter-schema.ts";

export function useInvestigationDetailQuery(investigationId: string | undefined, enabled = true) {
  const isValid = Boolean(investigationId && UUID_REGEX.test(investigationId));

  return useQuery({
    queryKey: investigationKeys.detail(investigationId ?? ""),
    queryFn: ({ signal }) => getInvestigation(investigationId!, signal),
    enabled: enabled && isValid,
    staleTime: 10_000,
  });
}
