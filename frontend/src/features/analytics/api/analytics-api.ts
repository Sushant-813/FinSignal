import { apiRequest } from "../../../lib/api/client.ts";
import type {
  AnalyticsCategoryParams,
  AnalyticsMerchantParams,
  AnalyticsOverviewParams,
  AnalyticsTrendParams,
  CategoryAnalyticsResponse,
  MerchantAnalyticsResponse,
  OverviewAnalyticsResponse,
  TrendAnalyticsResponse,
} from "../types/analytics.types.ts";

function appendOptionalParam(
  search: URLSearchParams,
  key: string,
  value: string | null | undefined
) {
  if (value !== null && value !== undefined && value.trim() !== "") {
    search.set(key, value.trim());
  }
}

export async function getAnalyticsOverview(
  params: AnalyticsOverviewParams,
  signal?: AbortSignal
): Promise<OverviewAnalyticsResponse> {
  const search = new URLSearchParams();
  search.set("source_namespace", params.source_namespace);
  search.set("currency", params.currency);
  appendOptionalParam(search, "from_time", params.from_time);
  appendOptionalParam(search, "to_time", params.to_time);
  if (params.timezone) {
    search.set("timezone", params.timezone);
  }

  return apiRequest<OverviewAnalyticsResponse>(`/analytics/overview?${search.toString()}`, {
    method: "GET",
    signal,
  });
}

export async function getAnalyticsTrends(
  params: AnalyticsTrendParams,
  signal?: AbortSignal
): Promise<TrendAnalyticsResponse> {
  const search = new URLSearchParams();
  search.set("source_namespace", params.source_namespace);
  search.set("currency", params.currency);
  search.set("from_time", params.from_time);
  search.set("to_time", params.to_time);
  search.set("interval", params.interval);
  search.set("timezone", params.timezone);

  return apiRequest<TrendAnalyticsResponse>(`/analytics/trends?${search.toString()}`, {
    method: "GET",
    signal,
  });
}

export async function getAnalyticsCategories(
  params: AnalyticsCategoryParams,
  signal?: AbortSignal
): Promise<CategoryAnalyticsResponse> {
  const search = new URLSearchParams();
  search.set("source_namespace", params.source_namespace);
  search.set("currency", params.currency);
  search.set("direction", params.direction);
  appendOptionalParam(search, "from_time", params.from_time);
  appendOptionalParam(search, "to_time", params.to_time);
  if (params.timezone) {
    search.set("timezone", params.timezone);
  }

  return apiRequest<CategoryAnalyticsResponse>(`/analytics/categories?${search.toString()}`, {
    method: "GET",
    signal,
  });
}

export async function getAnalyticsMerchants(
  params: AnalyticsMerchantParams,
  signal?: AbortSignal
): Promise<MerchantAnalyticsResponse> {
  const search = new URLSearchParams();
  search.set("source_namespace", params.source_namespace);
  search.set("currency", params.currency);
  appendOptionalParam(search, "from_time", params.from_time);
  appendOptionalParam(search, "to_time", params.to_time);
  search.set("sort_by", params.sort_by);
  search.set("limit", String(params.limit));
  search.set("offset", String(params.offset));
  if (params.timezone) {
    search.set("timezone", params.timezone);
  }

  return apiRequest<MerchantAnalyticsResponse>(`/analytics/merchants?${search.toString()}`, {
    method: "GET",
    signal,
  });
}
