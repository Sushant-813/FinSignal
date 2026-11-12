import { apiRequest } from "../../../lib/api/client.ts";
import type {
  TransactionDetailResponse,
  TransactionListFilters,
  TransactionListResponse,
} from "../types/transactions.types.ts";

function appendIfPresent(search: URLSearchParams, key: string, value: string | null | undefined) {
  if (value !== null && value !== undefined && value.trim() !== "") {
    search.set(key, value.trim());
  }
}

export async function getTransactions(
  filters: TransactionListFilters,
  signal?: AbortSignal
): Promise<TransactionListResponse> {
  const search = new URLSearchParams();
  search.set("page", String(filters.page));
  search.set("page_size", String(filters.page_size));
  search.set("source_namespace", filters.source_namespace);
  search.set("sort_by", filters.sort_by);
  search.set("sort_order", filters.sort_order);

  appendIfPresent(search, "account_id", filters.account_id);
  appendIfPresent(search, "merchant_id", filters.merchant_id);
  appendIfPresent(search, "device_id", filters.device_id);
  appendIfPresent(search, "location_id", filters.location_id);
  appendIfPresent(search, "transaction_type", filters.transaction_type);
  appendIfPresent(search, "direction", filters.direction);
  appendIfPresent(search, "category", filters.category);
  appendIfPresent(search, "currency", filters.currency);
  appendIfPresent(search, "from_time", filters.from_time);
  appendIfPresent(search, "to_time", filters.to_time);
  appendIfPresent(search, "min_amount", filters.min_amount);
  appendIfPresent(search, "max_amount", filters.max_amount);
  appendIfPresent(search, "risk_level", filters.risk_level);

  return apiRequest<TransactionListResponse>(`/transactions?${search.toString()}`, {
    method: "GET",
    signal,
  });
}

export async function getTransactionDetail(
  transactionId: string,
  options: {
    source_namespace?: string | null | undefined;
    signal?: AbortSignal | undefined;
  } = {}
): Promise<TransactionDetailResponse> {
  const search = new URLSearchParams();
  appendIfPresent(search, "source_namespace", options.source_namespace);
  const qs = search.toString();
  const path = qs ? `/transactions/${transactionId}?${qs}` : `/transactions/${transactionId}`;

  return apiRequest<TransactionDetailResponse>(path, {
    method: "GET",
    signal: options.signal,
  });
}
