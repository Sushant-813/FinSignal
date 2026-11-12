import { apiRequest } from "../../../lib/api/client.ts";
import { isApiClientError } from "../../../lib/api/errors.ts";
import { buildDefaultActiveAnalyzePayload } from "../schemas/risk-analyze-schema.ts";
import type { RiskAnalysisResponse, RiskQueryResult } from "../types/risk.types.ts";

export interface RiskRequestOptions {
  readonly signal?: AbortSignal | undefined;
}

/**
 * Fetches the latest persisted risk evaluation for a transaction (`GET /api/v1/transactions/{id}/risk`).
 * Backend returns 404 `RISK_ANALYSIS_NOT_FOUND` when no evaluation exists yet; map that cleanly
 * to `{ kind: "not_analyzed" }` while rethrowing real errors (`TRANSACTION_NOT_FOUND`, 403, 500, etc.).
 */
export async function getTransactionRisk(
  transactionId: string,
  options?: RiskRequestOptions
): Promise<RiskQueryResult> {
  try {
    const analysis = await apiRequest<RiskAnalysisResponse>(
      `/transactions/${encodeURIComponent(transactionId)}/risk`,
      options?.signal ? { signal: options.signal } : {}
    );
    return { kind: "analyzed", analysis };
  } catch (error) {
    if (
      isApiClientError(error) &&
      error.status === 404 &&
      error.code === "RISK_ANALYSIS_NOT_FOUND"
    ) {
      return { kind: "not_analyzed" };
    }
    throw error;
  }
}

/**
 * Triggers on-demand risk scoring using the workspace's default ACTIVE model
 * (`POST /api/v1/transactions/{id}/risk/analyze`).
 */
export async function analyzeTransactionRisk(
  transactionId: string,
  options?: RiskRequestOptions
): Promise<RiskAnalysisResponse> {
  const body = buildDefaultActiveAnalyzePayload();
  return apiRequest<RiskAnalysisResponse>(
    `/transactions/${encodeURIComponent(transactionId)}/risk/analyze`,
    {
      method: "POST",
      body,
      ...(options?.signal ? { signal: options.signal } : {}),
    }
  );
}
