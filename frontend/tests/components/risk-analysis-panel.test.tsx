import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { QueryProvider } from "../../src/app/providers/QueryProvider.tsx";
import { AuthProvider } from "../../src/features/auth/context/AuthProvider.tsx";
import type { UserRole } from "../../src/features/auth/types/auth.types.ts";
import { RiskAnalysisPanel } from "../../src/features/risk/components/RiskAnalysisPanel.tsx";
import type { TransactionLatestRiskDTO } from "../../src/features/transactions/types/transactions.types.ts";
import { setAccessToken } from "../../src/lib/auth/token-store.ts";
import { apiErrorFixtures } from "../fixtures/api-errors.ts";
import { buildAuthUser } from "../fixtures/auth.ts";
import { buildRiskAnalysisFixture, SAMPLE_TX_UUID } from "../fixtures/f3-data.ts";
import { server } from "../mocks/server.ts";

function renderRiskPanel(
  role: UserRole = "ANALYST",
  latestRiskSnapshot?: TransactionLatestRiskDTO | null
) {
  setAccessToken("risk-panel-jwt");
  server.use(http.get("/api/v1/auth/me", () => HttpResponse.json(buildAuthUser(role))));

  return render(
    <QueryProvider>
      <AuthProvider>
        <RiskAnalysisPanel transactionId={SAMPLE_TX_UUID} latestRiskSnapshot={latestRiskSnapshot} />
      </AuthProvider>
    </QueryProvider>
  );
}

describe("RiskAnalysisPanel (F3.6–F3.7)", () => {
  it("renders prioritization non-verdict notice, score decomposition, and explainable factors", async () => {
    server.use(
      http.get(`/api/v1/transactions/${SAMPLE_TX_UUID}/risk`, () =>
        HttpResponse.json(buildRiskAnalysisFixture())
      )
    );

    renderRiskPanel("INVESTIGATOR");

    await waitFor(() => {
      expect(screen.getByText("Prioritization Risk Score (0–100)")).toBeInTheDocument();
      expect(screen.getByText("78")).toBeInTheDocument();
    });

    expect(screen.getByText(/not an automated fraud verdict/i)).toBeInTheDocument();
    expect(screen.getByText("HIGH RISK")).toBeInTheDocument();
    expect(screen.getByText("Unseen device fingerprint")).toBeInTheDocument();
    expect(screen.getByText("NEW_DEVICE")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Re-run risk analysis" })).toBeInTheDocument();
  });

  it("handles missing risk (404 RISK_ANALYSIS_NOT_FOUND) neutrally and triggers default-ACTIVE analysis", async () => {
    const user = userEvent.setup();
    let hasAnalyzed = false;

    server.use(
      http.get(`/api/v1/transactions/${SAMPLE_TX_UUID}/risk`, () => {
        if (!hasAnalyzed) {
          return HttpResponse.json(
            {
              error: {
                code: "RISK_ANALYSIS_NOT_FOUND",
                message: "Not analyzed yet.",
                details: {},
                request_id: "req-missing-risk",
              },
            },
            { status: 404 }
          );
        }
        return HttpResponse.json(buildRiskAnalysisFixture());
      }),
      http.post(`/api/v1/transactions/${SAMPLE_TX_UUID}/risk/analyze`, async () => {
        hasAnalyzed = true;
        return HttpResponse.json(buildRiskAnalysisFixture());
      })
    );

    renderRiskPanel("ADMIN");

    await waitFor(() => {
      expect(screen.getByText("No risk analysis recorded yet.")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "Run risk analysis" }));

    await waitFor(() => {
      expect(screen.getByText("HIGH RISK")).toBeInTheDocument();
      expect(screen.getByText("Unseen device fingerprint")).toBeInTheDocument();
    });
  });

  it("surfaces snapshot mismatch and preserves prior valid analysis if a re-run fails", async () => {
    const user = userEvent.setup();

    server.use(
      http.get(`/api/v1/transactions/${SAMPLE_TX_UUID}/risk`, () =>
        HttpResponse.json(buildRiskAnalysisFixture({ id: "aaaaaaaa-1111-4111-8111-111111111111" }))
      ),
      http.post(`/api/v1/transactions/${SAMPLE_TX_UUID}/risk/analyze`, () =>
        apiErrorFixtures.internalError()
      )
    );

    renderRiskPanel("ANALYST", {
      analysis_id: "bbbbbbbb-2222-4222-8222-222222222222",
      score: 60,
      risk_level: "MEDIUM",
      model_version: "iforest-v1",
      evaluated_at: "2026-11-09T10:00:00Z",
    });

    await waitFor(() => {
      expect(screen.getByText("Synchronized latest evaluation")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "Re-run risk analysis" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/Risk analysis failed/i);
    });
    // Existing valid result remains visible
    expect(screen.getByText("HIGH RISK")).toBeInTheDocument();
    expect(screen.getByText("Unseen device fingerprint")).toBeInTheDocument();
  });
});
