import { useQuery } from "@tanstack/react-query";
import { riskKeys } from "../../../lib/api/query-keys.ts";
import { getTransactionRisk } from "../api/risk-api.ts";

export function useTransactionRiskQuery(transactionId: string, enabled = true) {
  return useQuery({
    queryKey: riskKeys.byTransaction(transactionId),
    queryFn: ({ signal }) => getTransactionRisk(transactionId, { signal }),
    enabled: enabled && transactionId.trim() !== "",
  });
}
