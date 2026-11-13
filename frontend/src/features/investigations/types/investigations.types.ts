import type { components, operations } from "../../../api/generated/schema.ts";

export type InvestigationStatus = components["schemas"]["InvestigationStatus"];
export type InvestigationPriority = components["schemas"]["InvestigationPriority"];
export type InvestigationResolution = components["schemas"]["InvestigationResolution"];
export type InvestigationRelationshipType = components["schemas"]["InvestigationRelationshipType"];

export type InvestigationSummaryItem = components["schemas"]["InvestigationSummaryItem"];
export type InvestigationListResponse = components["schemas"]["InvestigationListResponse"];
export type InvestigationDetailResponse = components["schemas"]["InvestigationDetailResponse"];
export type InvestigationPrimaryTransactionDTO =
  components["schemas"]["InvestigationPrimaryTransactionDTO"];
export type InvestigationLatestRiskDTO = components["schemas"]["InvestigationLatestRiskDTO"];
export type InvestigationTransactionItem = components["schemas"]["InvestigationTransactionItem"];
export type InvestigationTransactionsListResponse =
  components["schemas"]["InvestigationTransactionsListResponse"];

export type InvestigationCreateRequest = components["schemas"]["InvestigationCreateRequest"];
export interface InvestigationCreateInput {
  readonly transaction_id: string;
  readonly priority?: InvestigationPriority | undefined;
}
export type InvestigationPatchRequest = components["schemas"]["InvestigationPatchRequest"];
export type InvestigationResolveRequest = components["schemas"]["InvestigationResolveRequest"];
export type InvestigationRelatedTransactionAddRequest =
  components["schemas"]["InvestigationRelatedTransactionAddRequest"];

export interface InvestigationListParams {
  readonly page: number;
  readonly page_size: number;
  readonly status?: InvestigationStatus | null | undefined;
  readonly priority?: InvestigationPriority | null | undefined;
  readonly assigned_to?: string | null | undefined;
  readonly unassigned?: boolean | null | undefined;
}

export type ListInvestigationsOperation =
  operations["list_investigations_api_v1_investigations_get"];
export type CreateInvestigationOperation =
  operations["create_investigation_api_v1_investigations_post"];
export type GetInvestigationOperation =
  operations["get_investigation_api_v1_investigations__id__get"];
export type PatchInvestigationOperation =
  operations["patch_investigation_api_v1_investigations__id__patch"];
export type ResolveInvestigationOperation =
  operations["resolve_investigation_api_v1_investigations__id__resolve_post"];
export type ListInvestigationTransactionsOperation =
  operations["list_investigation_transactions_api_v1_investigations__id__transactions_get"];
export type AddRelatedTransactionOperation =
  operations["add_related_transaction_api_v1_investigations__id__transactions_post"];

