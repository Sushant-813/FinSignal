import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { transactionKeys } from "../../../lib/api/query-keys.ts";
import { getTransactions } from "../api/transactions-api.ts";
import type { TransactionListFilters } from "../types/transactions.types.ts";

export function useTransactionListQuery(filters: TransactionListFilters, enabled = true) {
  return useQuery({
    queryKey: transactionKeys.list(filters),
    queryFn: ({ signal }) => getTransactions(filters, signal),
    placeholderData: keepPreviousData,
    enabled,
  });
}
