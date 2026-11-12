import type { components } from "../../../api/generated/schema.ts";

export type TransactionSummaryItem = components["schemas"]["TransactionSummaryItem"];
export type TransactionListResponse = components["schemas"]["TransactionListResponse"];
export type TransactionDetailResponse = components["schemas"]["TransactionDetailResponse"];
export type TransactionAccountDTO = components["schemas"]["TransactionAccountDTO"];
export type TransactionMerchantDTO = components["schemas"]["TransactionMerchantDTO"];
export type TransactionDeviceDTO = components["schemas"]["TransactionDeviceDTO"];
export type TransactionLocationDTO = components["schemas"]["TransactionLocationDTO"];
export type TransactionLatestRiskDTO = components["schemas"]["TransactionLatestRiskDTO"];

export type TransactionDirection = "DEBIT" | "CREDIT";
export type TransactionRiskLevel = components["schemas"]["RiskLevel"];
export type TransactionSortField = "occurred_at" | "amount" | "created_at";
export type TransactionSortOrder = "asc" | "desc";

export interface TransactionListFilters {
  readonly page: number;
  readonly page_size: number;
  readonly source_namespace: string;
  readonly account_id?: string | null | undefined;
  readonly merchant_id?: string | null | undefined;
  readonly device_id?: string | null | undefined;
  readonly location_id?: string | null | undefined;
  readonly transaction_type?: string | null | undefined;
  readonly direction?: TransactionDirection | null | undefined;
  readonly category?: string | null | undefined;
  readonly currency?: string | null | undefined;
  readonly from_time?: string | null | undefined;
  readonly to_time?: string | null | undefined;
  readonly min_amount?: string | null | undefined;
  readonly max_amount?: string | null | undefined;
  readonly risk_level?: TransactionRiskLevel | null | undefined;
  readonly sort_by: TransactionSortField;
  readonly sort_order: TransactionSortOrder;
}
