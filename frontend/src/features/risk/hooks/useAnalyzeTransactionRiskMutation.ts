import { useMutation, useQueryClient } from "@tanstack/react-query";
import { riskKeys, transactionKeys } from "../../../lib/api/query-keys.ts";
import { analyzeTransactionRisk } from "../api/risk-api.ts";
import type { RiskAnalysisResponse, RiskQueryResult } from "../types/risk.types.ts";

export interface AnalyzeTransactionRiskVariables {
  readonly transactionId: string;
}

export function useAnalyzeTransactionRiskMutation() {
  const queryClient = useQueryClient();

  return useMutation<RiskAnalysisResponse, unknown, AnalyzeTransactionRiskVariables>({
    mutationFn: ({ transactionId }) => analyzeTransactionRisk(transactionId),
    retry: false,
    onSuccess: (analysis, { transactionId }) => {
      const nextResult: RiskQueryResult = { kind: "analyzed", analysis };
      queryClient.setQueryData(riskKeys.byTransaction(transactionId), nextResult);
      void queryClient.invalidateQueries({ queryKey: riskKeys.byTransaction(transactionId) });
      void queryClient.invalidateQueries({ queryKey: transactionKeys.details() });
      void queryClient.invalidateQueries({ queryKey: transactionKeys.lists() });
    },
  });
}
