import type {
  InvestigationDetailResponse,
  InvestigationListResponse,
  InvestigationSummaryItem,
  InvestigationTransactionItem,
  InvestigationTransactionsListResponse,
} from "../../src/features/investigations/types/investigations.types.ts";

export const SAMPLE_INVESTIGATION_ID = "11111111-2222-3333-4444-555555555555";
export const SAMPLE_PRIMARY_TX_ID = "22222222-3333-4444-5555-666666666666";
export const SAMPLE_RELATED_TX_ID = "33333333-4444-5555-6666-777777777777";
export const SAMPLE_ACCOUNT_ID = "44444444-5555-6666-7777-888888888888";
export const SAMPLE_INVESTIGATOR_ID = "55555555-6666-7777-8888-999999999999";
export const SAMPLE_INVESTIGATOR_EMAIL = "investigator@finsignal.internal";

export function buildInvestigationSummaryItem(
  overrides: Partial<InvestigationSummaryItem> = {}
): InvestigationSummaryItem {
  return {
    id: SAMPLE_INVESTIGATION_ID,
    status: "OPEN",
    priority: "MEDIUM",
    assigned_to: null,
    primary_transaction_id: SAMPLE_PRIMARY_TX_ID,
    account_id: SAMPLE_ACCOUNT_ID,
    resolution: null,
    created_at: "2026-11-13T10:00:00.000Z",
    updated_at: "2026-11-13T10:00:00.000Z",
    ...overrides,
  };
}

export function buildInvestigationListResponse(
  overrides: Partial<InvestigationListResponse> = {}
): InvestigationListResponse {
  const defaultItems = [buildInvestigationSummaryItem()];
  return {
    items: defaultItems,
    page: 1,
    page_size: 25,
    total: defaultItems.length,
    total_pages: 1,
    ...overrides,
  };
}

export function buildInvestigationTransactionItem(
  overrides: Partial<InvestigationTransactionItem> = {}
): InvestigationTransactionItem {
  return {
    transaction_id: SAMPLE_RELATED_TX_ID,
    relationship_type: "RELATED",
    account_id: SAMPLE_ACCOUNT_ID,
    amount: "250.00",
    currency: "INR",
    direction: "CREDIT",
    occurred_at: "2026-11-13T09:30:00.000Z",
    created_at: "2026-11-13T10:05:00.000Z",
    ...overrides,
  };
}

export function buildInvestigationDetailResponse(
  overrides: Partial<InvestigationDetailResponse> = {}
): InvestigationDetailResponse {
  return {
    id: SAMPLE_INVESTIGATION_ID,
    status: "OPEN",
    priority: "MEDIUM",
    assigned_to: null,
    assigned_user_email: null,
    primary_transaction: {
      id: SAMPLE_PRIMARY_TX_ID,
      external_transaction_id: "EXT-TX-9901",
      account_id: SAMPLE_ACCOUNT_ID,
      amount: "1500.00",
      currency: "INR",
      direction: "DEBIT",
      occurred_at: "2026-11-13T09:00:00.000Z",
      source_namespace: "SYNTHETIC",
      category: "WIRE_TRANSFER",
      payment_method: "IMPS",
    },
    latest_risk_analysis: {
      id: "66666666-7777-8888-9999-000000000000",
      score: 0.88,
      risk_level: "HIGH",
      model_version: "v1.0.0",
      created_at: "2026-11-13T09:01:00.000Z",
    },
    related_transactions: [],
    resolution: null,
    resolution_notes: null,
    created_at: "2026-11-13T10:00:00.000Z",
    updated_at: "2026-11-13T10:00:00.000Z",
    ...overrides,
  };
}

export function buildInvestigationTransactionsListResponse(
  overrides: Partial<InvestigationTransactionsListResponse> = {}
): InvestigationTransactionsListResponse {
  return {
    investigation_id: SAMPLE_INVESTIGATION_ID,
    items: [
      {
        transaction_id: SAMPLE_PRIMARY_TX_ID,
        relationship_type: "PRIMARY",
        account_id: SAMPLE_ACCOUNT_ID,
        amount: "1500.00",
        currency: "INR",
        direction: "DEBIT",
        occurred_at: "2026-11-13T09:00:00.000Z",
        created_at: "2026-11-13T10:00:00.000Z",
      },
      buildInvestigationTransactionItem(),
    ],
    ...overrides,
  };
}
