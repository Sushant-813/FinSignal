import type { components } from "../../../api/generated/schema.ts";

export type OverviewAnalyticsResponse = components["schemas"]["OverviewAnalyticsResponse"];
export type TrendAnalyticsResponse = components["schemas"]["TrendAnalyticsResponse"];
export type TrendBucketItem = components["schemas"]["TrendBucketItem"];
export type TrendInterval = components["schemas"]["TrendInterval"];
export type CategoryAnalyticsResponse = components["schemas"]["CategoryAnalyticsResponse"];
export type CategoryDistributionItem = components["schemas"]["CategoryDistributionItem"];
export type MerchantAnalyticsResponse = components["schemas"]["MerchantAnalyticsResponse"];
export type MerchantDistributionItem = components["schemas"]["MerchantDistributionItem"];

export type CategoryDirection = "DEBIT" | "CREDIT";
export type MerchantSortBy = "amount" | "count";

export interface AnalyticsOverviewParams {
  readonly source_namespace: string;
  readonly currency: string;
  readonly from_time?: string | null | undefined;
  readonly to_time?: string | null | undefined;
  readonly timezone?: string | undefined;
}

export interface AnalyticsTrendParams {
  readonly source_namespace: string;
  readonly currency: string;
  readonly from_time: string;
  readonly to_time: string;
  readonly interval: TrendInterval;
  readonly timezone: string;
}

export interface AnalyticsCategoryParams {
  readonly source_namespace: string;
  readonly currency: string;
  readonly direction: CategoryDirection;
  readonly from_time?: string | null | undefined;
  readonly to_time?: string | null | undefined;
  readonly timezone?: string | undefined;
}

export interface AnalyticsMerchantParams {
  readonly source_namespace: string;
  readonly currency: string;
  readonly from_time?: string | null | undefined;
  readonly to_time?: string | null | undefined;
  readonly sort_by: MerchantSortBy;
  readonly limit: number;
  readonly offset: number;
  readonly timezone?: string | undefined;
}

export interface ReportingScope {
  readonly source_namespace: string;
  readonly currency: string;
  readonly fromDate: string;
  readonly toDate: string;
  readonly timezone: string;
  readonly from_time: string;
  readonly to_time: string;
}
