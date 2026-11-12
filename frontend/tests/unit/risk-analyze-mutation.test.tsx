import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { useAnalyzeTransactionRiskMutation } from "../../src/features/risk/hooks/useAnalyzeTransactionRiskMutation.ts";
import { useTransactionRiskQuery } from "../../src/features/risk/hooks/useTransactionRiskQuery.ts";
import { riskKeys, transactionKeys } from "../../src/lib/api/query-keys.ts";
import { setAccessToken } from "../../src/lib/auth/token-store.ts";
import { buildRiskAnalysisFixture, SAMPLE_TX_UUID } from "../fixtures/f3-data.ts";
import { server } from "../mocks/server.ts";

function MutationHarness() {
  const riskQuery = useTransactionRiskQuery(SAMPLE_TX_UUID);
  const analyzeMutation = useAnalyzeTransactionRiskMutation();

  return (
    <div>
      <div data-testid="risk-state">
        {riskQuery.data?.kind === "analyzed"
          ? `analyzed:${riskQuery.data.analysis.score}`
          : (riskQuery.data?.kind ?? "loading")}
      </div>
      <button
        type="button"
        disabled={analyzeMutation.isPending}
        onClick={() => analyzeMutation.mutate({ transactionId: SAMPLE_TX_UUID })}
      >
        Analyze Now
      </button>
    </div>
  );
}

describe("useAnalyzeTransactionRiskMutation (F3.7)", () => {
  it("updates risk query cache immediately and invalidates risk and transaction queries on success", async () => {
    const user = userEvent.setup();
    setAccessToken("mutation-jwt");
    let hasAnalysis = false;

    server.use(
      http.get(`/api/v1/transactions/${SAMPLE_TX_UUID}/risk`, () => {
        if (!hasAnalysis) {
          return HttpResponse.json(
            {
              error: {
                code: "RISK_ANALYSIS_NOT_FOUND",
                message: "None yet.",
                details: {},
                request_id: "req-init-404",
              },
            },
            { status: 404 }
          );
        }
        return HttpResponse.json(buildRiskAnalysisFixture({ score: 84, risk_level: "CRITICAL" }));
      }),
      http.post(`/api/v1/transactions/${SAMPLE_TX_UUID}/risk/analyze`, () => {
        hasAnalysis = true;
        return HttpResponse.json(buildRiskAnalysisFixture({ score: 84, risk_level: "CRITICAL" }));
      })
    );

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    render(
      <QueryClientProvider client={queryClient}>
        <MutationHarness />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("risk-state")).toHaveTextContent("not_analyzed");
    });

    await user.click(screen.getByRole("button", { name: "Analyze Now" }));

    await waitFor(() => {
      expect(screen.getByTestId("risk-state")).toHaveTextContent("analyzed:84");
    });

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: riskKeys.byTransaction(SAMPLE_TX_UUID),
    });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: transactionKeys.details() });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: transactionKeys.lists() });
  });
});
