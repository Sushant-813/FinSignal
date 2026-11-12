import { z } from "zod";
import type { RiskAnalyzeRequest } from "../types/risk.types.ts";

/**
 * Approved F3 scope: on-demand risk analysis uses the default ACTIVE model only.
 * Any model selector or `force_recalculate` flag is excluded.
 */
export const riskAnalyzeRequestSchema = z
  .object({
    model_version_id: z.string().uuid("Model version ID must be a valid UUID.").optional(),
  })
  .strict();

export function buildDefaultActiveAnalyzePayload(): RiskAnalyzeRequest {
  return {};
}
