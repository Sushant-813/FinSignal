import type {
  AnalyticsCategoryParams,
  AnalyticsMerchantParams,
  AnalyticsOverviewParams,
  AnalyticsTrendParams,
} from "../../features/analytics/types/analytics.types.ts";
import type { DatasetImportListParams } from "../../features/datasets/types/datasets.types.ts";
import type { InvestigationListParams } from "../../features/investigations/types/investigations.types.ts";
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

export const datasetImportKeys = {
  all: ["datasets", "imports"] as const,
  lists: () => [...datasetImportKeys.all, "list"] as const,
  list: (params: DatasetImportListParams) =>
    [
      ...datasetImportKeys.lists(),
      {
        page: params.page,
        page_size: params.page_size,
        source_namespace: params.source_namespace,
        status: params.status ?? null,
        source_type: normalizeNullableString(params.source_type),
        from_time: normalizeNullableString(params.from_time),
        to_time: normalizeNullableString(params.to_time),
      },
    ] as const,
  details: () => [...datasetImportKeys.all, "detail"] as const,
  detail: (importId: string) => [...datasetImportKeys.details(), importId] as const,
};

export const investigationKeys = {
  all: ["investigations"] as const,
  lists: () => [...investigationKeys.all, "list"] as const,
  list: (params: InvestigationListParams) =>
    [
      ...investigationKeys.lists(),
      {
        page: params.page,
        page_size: params.page_size,
        status: params.status ?? null,
        priority: params.priority ?? null,
        assigned_to: normalizeNullableString(params.assigned_to),
        unassigned: params.unassigned ?? null,
      },
    ] as const,
  details: () => [...investigationKeys.all, "detail"] as const,
  detail: (id: string) => [...investigationKeys.details(), id] as const,
};
