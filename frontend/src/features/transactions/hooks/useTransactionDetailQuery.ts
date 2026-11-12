import { useQuery } from "@tanstack/react-query";
import { transactionKeys } from "../../../lib/api/query-keys.ts";
import { getTransactionDetail } from "../api/transactions-api.ts";

export function useTransactionDetailQuery(
  transactionId: string,
  sourceNamespace?: string | null,
  enabled = true
) {
  return useQuery({
    queryKey: transactionKeys.detail(transactionId, sourceNamespace),
    queryFn: ({ signal }) =>
      getTransactionDetail(transactionId, {
        source_namespace: sourceNamespace,
        signal,
      }),
    enabled: enabled && transactionId.trim() !== "",
  });
}
