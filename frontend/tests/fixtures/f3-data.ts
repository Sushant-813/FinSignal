import type {
  CategoryAnalyticsResponse,
  MerchantAnalyticsResponse,
  OverviewAnalyticsResponse,
  TrendAnalyticsResponse,
} from "../../src/features/analytics/types/analytics.types.ts";
import type { RiskAnalysisResponse } from "../../src/features/risk/types/risk.types.ts";
import type {
  TransactionDetailResponse,
  TransactionListResponse,
  TransactionSummaryItem,
} from "../../src/features/transactions/types/transactions.types.ts";

export function buildOverviewFixture(
  overrides: Partial<OverviewAnalyticsResponse> = {}
): OverviewAnalyticsResponse {
  return {
    source_namespace: "SYNTHETIC",
    currency: "INR",
    from_time: "2026-10-12T00:00:00Z",
    to_time: "2026-11-12T00:00:00Z",
    total_transaction_count: 142,
    debit_transaction_count: 108,
    credit_transaction_count: 34,
    total_volume_amount: "987654.32",
    total_debit_amount: "654321.10",
    total_credit_amount: "333333.22",
    net_cash_flow: "-320987.88",
    average_transaction_amount: "6955.31",
    median_transaction_amount: "2450.00",
    debit_average_amount: "6058.53",
    debit_median_amount: "2100.00",
    ...overrides,
  };
}

export function buildTrendsFixture(
  overrides: Partial<TrendAnalyticsResponse> = {}
): TrendAnalyticsResponse {
  return {
    source_namespace: "SYNTHETIC",
    currency: "INR",
    interval: "day",
    timezone: "UTC",
    from_time: "2026-11-09T00:00:00Z",
    to_time: "2026-11-12T00:00:00Z",
    total_buckets: 3,
    buckets: [
      {
        bucket_start: "2026-11-09T00:00:00Z",
        transaction_count: 12,
        debit_count: 9,
        credit_count: 3,
        total_debit_amount: "18400.50",
        total_credit_amount: "9200.00",
        net_cash_flow: "-9200.50",
      },
      {
        bucket_start: "2026-11-10T00:00:00Z",
        transaction_count: 0,
        debit_count: 0,
        credit_count: 0,
        total_debit_amount: "0.00",
        total_credit_amount: "0.00",
        net_cash_flow: "0.00",
      },
      {
        bucket_start: "2026-11-11T00:00:00Z",
        transaction_count: 18,
        debit_count: 14,
        credit_count: 4,
        total_debit_amount: "42100.75",
        total_credit_amount: "15000.00",
        net_cash_flow: "-27100.75",
      },
    ],
    ...overrides,
  };
}

export function buildCategoriesFixture(
  overrides: Partial<CategoryAnalyticsResponse> = {}
): CategoryAnalyticsResponse {
  return {
    source_namespace: "SYNTHETIC",
    currency: "INR",
    direction: "DEBIT",
    total_directional_amount: "100000.00",
    categories: [
      {
        category_name: "TRAVEL",
        transaction_count: 24,
        total_amount: "48500.00",
        percentage_of_total: "48.50",
        average_amount: "2020.83",
      },
      {
        category_name: "RETAIL",
        transaction_count: 36,
        total_amount: "31500.00",
        percentage_of_total: "31.50",
        average_amount: "875.00",
      },
      {
        category_name: "UNCATEGORIZED",
        transaction_count: 10,
        total_amount: "20000.00",
        percentage_of_total: "20.00",
        average_amount: "2000.00",
      },
    ],
    ...overrides,
  };
}

export function buildMerchantsFixture(
  overrides: Partial<MerchantAnalyticsResponse> = {}
): MerchantAnalyticsResponse {
  return {
    source_namespace: "SYNTHETIC",
    currency: "INR",
    total_debit_amount: "100000.00",
    total_merchant_debit_amount: "78000.00",
    non_merchant_debit_amount: "22000.00",
    returned_merchant_count: 2,
    merchants: [
      {
        merchant_id: "11111111-1111-4111-8111-111111111111",
        merchant_name: "Apex Airlines",
        merchant_category: "TRAVEL",
        transaction_count: 11,
        total_amount: "52000.00",
        average_amount: "4727.27",
        percentage_of_total_debit: "52.00",
        percentage_of_merchant_spend: "66.67",
      },
      {
        merchant_id: "22222222-2222-4222-8222-222222222222",
        merchant_name: "Metro Electronics",
        merchant_category: "RETAIL",
        transaction_count: 19,
        total_amount: "26000.00",
        average_amount: "1368.42",
        percentage_of_total_debit: "26.00",
        percentage_of_merchant_spend: "33.33",
      },
    ],
    ...overrides,
  };
}

export const SAMPLE_TX_UUID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
export const SAMPLE_TX_UUID_2 = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";

export function buildTransactionSummaryFixture(
  overrides: Partial<TransactionSummaryItem> = {}
): TransactionSummaryItem {
  return {
    id: SAMPLE_TX_UUID,
    source_namespace: "SYNTHETIC",
    external_transaction_id: "TXN-2026-0001",
    account_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
    counterparty_account_id: null,
    merchant_id: "11111111-1111-4111-8111-111111111111",
    device_id: "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
    location_id: "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
    occurred_at: "2026-11-10T14:25:00Z",
    amount: "12345.67",
    currency: "INR",
    transaction_type: "CARD_PURCHASE",
    direction: "DEBIT",
    category: "TRAVEL",
    payment_method: "CARD",
    channel: "POS",
    first_seen_import_id: "ffffffff-ffff-4fff-8fff-ffffffffffff",
    created_at: "2026-11-10T14:26:00Z",
    ...overrides,
  };
}

export function buildTransactionListFixture(
  items: TransactionSummaryItem[] = [buildTransactionSummaryFixture()],
  overrides: Partial<TransactionListResponse> = {}
): TransactionListResponse {
  return {
    items,
    page: 1,
    page_size: 50,
    total: items.length,
    total_pages: items.length > 0 ? 1 : 0,
    ...overrides,
  };
}

export function buildTransactionDetailFixture(
  overrides: Partial<TransactionDetailResponse> = {}
): TransactionDetailResponse {
  return {
    id: SAMPLE_TX_UUID,
    source_namespace: "SYNTHETIC",
    external_transaction_id: "TXN-2026-0001",
    first_seen_import_id: "ffffffff-ffff-4fff-8fff-ffffffffffff",
    account_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
    counterparty_account_id: null,
    merchant_id: "11111111-1111-4111-8111-111111111111",
    device_id: "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
    location_id: "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
    occurred_at: "2026-11-10T14:25:00Z",
    amount: "12345.67",
    currency: "INR",
    transaction_type: "CARD_PURCHASE",
    direction: "DEBIT",
    category: "TRAVEL",
    payment_method: "CARD",
    channel: "POS",
    created_at: "2026-11-10T14:26:00Z",
    account: {
      id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
      external_account_id: "ACC-1001",
      account_type: "CHECKING",
      status: "ACTIVE",
    },
    counterparty_account: null,
    merchant: {
      id: "11111111-1111-4111-8111-111111111111",
      external_merchant_id: "MER-101",
      merchant_name: "Apex Airlines",
      merchant_category: "TRAVEL",
    },
    device: {
      id: "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
      external_device_id: "DEV-88",
      device_type: "MOBILE_IOS",
    },
    location: {
      id: "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
      city: "Bengaluru",
      state: "KA",
      country: "IN",
    },
    latest_risk: {
      analysis_id: "99999999-9999-4999-8999-999999999999",
      score: 78,
      risk_level: "HIGH",
      model_version: "iforest-v2",
      evaluated_at: "2026-11-10T14:30:00Z",
    },
    ...overrides,
  };
}

export function buildRiskAnalysisFixture(
  overrides: Partial<RiskAnalysisResponse> = {}
): RiskAnalysisResponse {
  return {
    id: "99999999-9999-4999-8999-999999999999",
    transaction_id: SAMPLE_TX_UUID,
    model_version_id: "77777777-7777-4777-8777-777777777777",
    model_version: "iforest-v2",
    config_version: "rules-v1.4",
    feature_vector_hash: "sha256:abcdef0123456789",
    score: 78,
    risk_level: "HIGH",
    ml_anomaly_score: -0.214,
    ml_threshold: -0.1,
    normalized_ml_score: 72,
    rule_score: 65,
    normalization_params: {
      min_score: -0.45,
      max_score: 0.15,
      weight_ml: 0.6,
    },
    factors: [
      {
        code: "NEW_DEVICE",
        label: "Unseen device fingerprint",
        severity: "HIGH",
        description: "Device DEV-88 was not observed in the account baseline window.",
        value_numeric: "1.00",
        value_text: "DEV-88",
        evidence: {
          device_id: "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
          lookback_days: 30,
        },
      },
      {
        code: "LARGE_AMOUNT_DEVIATION",
        label: "Amount exceeds 90-day baseline",
        severity: "MEDIUM",
        description: "Transaction amount exceeds 3.4x median account spend.",
        value_numeric: "3.42",
        value_text: "12345.67 INR",
        evidence: {
          baseline_median: "3610.00",
        },
      },
    ],
    created_at: "2026-11-10T14:30:00Z",
    ...overrides,
  };
}
