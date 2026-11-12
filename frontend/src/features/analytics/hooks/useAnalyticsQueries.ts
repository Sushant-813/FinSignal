import { useQuery } from "@tanstack/react-query";
import { analyticsKeys } from "../../../lib/api/query-keys.ts";
import {
  getAnalyticsCategories,
  getAnalyticsMerchants,
  getAnalyticsOverview,
  getAnalyticsTrends,
} from "../api/analytics-api.ts";
import type {
  AnalyticsCategoryParams,
  AnalyticsMerchantParams,
  AnalyticsOverviewParams,
  AnalyticsTrendParams,
} from "../types/analytics.types.ts";

export function useOverviewAnalyticsQuery(params: AnalyticsOverviewParams, enabled = true) {
  return useQuery({
    queryKey: analyticsKeys.overview(params),
    queryFn: ({ signal }) => getAnalyticsOverview(params, signal),
    enabled,
  });
}

export function useTrendAnalyticsQuery(params: AnalyticsTrendParams, enabled = true) {
  return useQuery({
    queryKey: analyticsKeys.trends(params),
    queryFn: ({ signal }) => getAnalyticsTrends(params, signal),
    enabled,
  });
}

export function useCategoryAnalyticsQuery(params: AnalyticsCategoryParams, enabled = true) {
  return useQuery({
    queryKey: analyticsKeys.categories(params),
    queryFn: ({ signal }) => getAnalyticsCategories(params, signal),
    enabled,
  });
}

export function useMerchantAnalyticsQuery(params: AnalyticsMerchantParams, enabled = true) {
  return useQuery({
    queryKey: analyticsKeys.merchants(params),
    queryFn: ({ signal }) => getAnalyticsMerchants(params, signal),
    enabled,
  });
}
