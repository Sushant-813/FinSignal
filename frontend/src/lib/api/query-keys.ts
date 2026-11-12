import type {
  AnalyticsCategoryParams,
  AnalyticsMerchantParams,
  AnalyticsOverviewParams,
  AnalyticsTrendParams,
} from "../../features/analytics/types/analytics.types.ts";
import type { TransactionListFilters } from "../../features/transactions/types/transactions.types.ts";

function normalizeNullableString(value: string | null | undefined): string | null {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed === "" ? null : trimmed;
}

export const analyticsKeys = {
  all: ["analytics"] as const,
  overview: (params: AnalyticsOverviewParams) =>
    [
      ...analyticsKeys.all,
      "overview",
      {
        source_namespace: params.source_namespace,
        currency: params.currency,
        from_time: normalizeNullableString(params.from_time),
        to_time: normalizeNullableString(params.to_time),
        timezone: params.timezone ?? "UTC",
      },
    ] as const,
  trends: (params: AnalyticsTrendParams) =>
    [
      ...analyticsKeys.all,
      "trends",
      {
        source_namespace: params.source_namespace,
        currency: params.currency,
        from_time: params.from_time,
        to_time: params.to_time,
        interval: params.interval,
        timezone: params.timezone,
      },
    ] as const,
  categories: (params: AnalyticsCategoryParams) =>
    [
      ...analyticsKeys.all,
      "categories",
      {
        source_namespace: params.source_namespace,
        currency: params.currency,
        direction: params.direction,
        from_time: normalizeNullableString(params.from_time),
        to_time: normalizeNullableString(params.to_time),
        timezone: params.timezone ?? "UTC",
      },
    ] as const,
  merchants: (params: AnalyticsMerchantParams) =>
    [
      ...analyticsKeys.all,
      "merchants",
      {
        source_namespace: params.source_namespace,
        currency: params.currency,
        from_time: normalizeNullableString(params.from_time),
        to_time: normalizeNullableString(params.to_time),
        sort_by: params.sort_by,
        limit: params.limit,
        offset: params.offset,
        timezone: params.timezone ?? "UTC",
      },
    ] as const,
};

export const transactionKeys = {
  all: ["transactions"] as const,
  lists: () => [...transactionKeys.all, "list"] as const,
  list: (filters: TransactionListFilters) =>
    [
      ...transactionKeys.lists(),
      {
        page: filters.page,
        page_size: filters.page_size,
        source_namespace: filters.source_namespace,
        account_id: normalizeNullableString(filters.account_id),
        merchant_id: normalizeNullableString(filters.merchant_id),
        device_id: normalizeNullableString(filters.device_id),
        location_id: normalizeNullableString(filters.location_id),
        transaction_type: normalizeNullableString(filters.transaction_type),
        direction: filters.direction ?? null,
        category: normalizeNullableString(filters.category),
        currency: normalizeNullableString(filters.currency),
        from_time: normalizeNullableString(filters.from_time),
        to_time: normalizeNullableString(filters.to_time),
        min_amount: normalizeNullableString(filters.min_amount),
        max_amount: normalizeNullableString(filters.max_amount),
        risk_level: filters.risk_level ?? null,
        sort_by: filters.sort_by,
        sort_order: filters.sort_order,
      },
    ] as const,
  details: () => [...transactionKeys.all, "detail"] as const,
  detail: (transactionId: string, sourceNamespace?: string | null) =>
    [
      ...transactionKeys.details(),
      transactionId,
      { source_namespace: normalizeNullableString(sourceNamespace) },
    ] as const,
};

export const riskKeys = {
  all: ["risk"] as const,
  byTransaction: (transactionId: string) =>
    [...riskKeys.all, "transaction", transactionId] as const,
};
