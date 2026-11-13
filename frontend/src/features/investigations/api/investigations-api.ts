import { apiRequest } from "../../../lib/api/client.ts";
import type {
  InvestigationCreateInput,
  InvestigationCreateRequest,
  InvestigationDetailResponse,
  InvestigationListParams,
  InvestigationListResponse,
  InvestigationPatchRequest,
  InvestigationPriority,
  InvestigationRelatedTransactionAddRequest,
  InvestigationResolveRequest,
  InvestigationTransactionItem,
  InvestigationTransactionsListResponse,
} from "../types/investigations.types.ts";

export interface InvestigationApiOptions {
  readonly signal?: AbortSignal | undefined;
}

function resolveSignal(options?: InvestigationApiOptions | AbortSignal): AbortSignal | undefined {
  if (!options) {
    return undefined;
  }
  if (options instanceof AbortSignal) {
    return options;
  }
  return options.signal;
}

export async function listInvestigations(
  params: InvestigationListParams,
  options?: InvestigationApiOptions | AbortSignal
): Promise<InvestigationListResponse> {
  const search = new URLSearchParams();
  search.set("page", String(params.page));
  search.set("page_size", String(params.page_size));

  if (params.status) {
    search.set("status", params.status);
  }
  if (params.priority) {
    search.set("priority", params.priority);
  }
  if (params.unassigned !== undefined && params.unassigned !== null) {
    search.set("unassigned", String(params.unassigned));
  }
  // Avoid sending conflicting assigned_to if unassigned is true (prevents HTTP 400 FILTER_CONFLICT)
  if (!params.unassigned && params.assigned_to && params.assigned_to.trim() !== "") {
    search.set("assigned_to", params.assigned_to.trim());
  }

  const query = search.toString();
  const path = query ? `/investigations?${query}` : "/investigations";

  return apiRequest<InvestigationListResponse>(path, {
    method: "GET",
    signal: resolveSignal(options),
  });
}

export async function createInvestigation(
  payload: InvestigationCreateInput | InvestigationCreateRequest,
  options?: InvestigationApiOptions | AbortSignal
): Promise<InvestigationDetailResponse> {
  const body: { transaction_id: string; priority?: InvestigationPriority } = {
    transaction_id: payload.transaction_id,
  };
  if (payload.priority) {
    body.priority = payload.priority;
  }

  return apiRequest<InvestigationDetailResponse>("/investigations", {
    method: "POST",
    body,
    signal: resolveSignal(options),
  });
}

export async function getInvestigation(
  id: string,
  options?: InvestigationApiOptions | AbortSignal
): Promise<InvestigationDetailResponse> {
  return apiRequest<InvestigationDetailResponse>(`/investigations/${encodeURIComponent(id)}`, {
    method: "GET",
    signal: resolveSignal(options),
  });
}

export async function patchInvestigation(
  id: string,
  payload: InvestigationPatchRequest,
  options?: InvestigationApiOptions | AbortSignal
): Promise<InvestigationDetailResponse> {
  return apiRequest<InvestigationDetailResponse>(`/investigations/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: payload,
    signal: resolveSignal(options),
  });
}

export async function resolveInvestigation(
  id: string,
  payload: InvestigationResolveRequest,
  options?: InvestigationApiOptions | AbortSignal
): Promise<InvestigationDetailResponse> {
  return apiRequest<InvestigationDetailResponse>(
    `/investigations/${encodeURIComponent(id)}/resolve`,
    {
      method: "POST",
      body: payload,
      signal: resolveSignal(options),
    }
  );
}

export async function getInvestigationTransactions(
  id: string,
  options?: InvestigationApiOptions | AbortSignal
): Promise<InvestigationTransactionsListResponse> {
  return apiRequest<InvestigationTransactionsListResponse>(
    `/investigations/${encodeURIComponent(id)}/transactions`,
    {
      method: "GET",
      signal: resolveSignal(options),
    }
  );
}

export async function addRelatedTransaction(
  id: string,
  payload: InvestigationRelatedTransactionAddRequest,
  options?: InvestigationApiOptions | AbortSignal
): Promise<InvestigationTransactionItem> {
  return apiRequest<InvestigationTransactionItem>(
    `/investigations/${encodeURIComponent(id)}/transactions`,
    {
      method: "POST",
      body: payload,
      signal: resolveSignal(options),
    }
  );
}
