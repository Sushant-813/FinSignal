import { render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";
import { QueryProvider } from "../../src/app/providers/QueryProvider.tsx";
import { AuthProvider } from "../../src/features/auth/context/AuthProvider.tsx";
import { TransactionDetailPage } from "../../src/features/transactions/pages/TransactionDetailPage.tsx";
import { setAccessToken } from "../../src/lib/auth/token-store.ts";
import { buildAuthUser } from "../fixtures/auth.ts";
import {
  buildRiskAnalysisFixture,
  buildTransactionDetailFixture,
  SAMPLE_TX_UUID,
} from "../fixtures/f3-data.ts";
import { server } from "../mocks/server.ts";

function renderDetail(
  initialEntry: string | { pathname: string; search?: string; state?: unknown }
) {
  setAccessToken("tx-detail-jwt");
  server.use(http.get("/api/v1/auth/me", () => HttpResponse.json(buildAuthUser("ANALYST"))));

  const router = createMemoryRouter(
    [
      { path: "/transactions/:transactionId", element: <TransactionDetailPage /> },
      { path: "/transactions", element: <div>Transactions Return View</div> },
    ],
    { initialEntries: [initialEntry] }
  );

  return render(
    <QueryProvider>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </QueryProvider>
  );
}

describe("TransactionDetailPage (F3.5)", () => {
  it("validates UUID path parameters client-side before issuing API calls", async () => {
    let detailCalls = 0;
    server.use(
      http.get("/api/v1/transactions/*", () => {
        detailCalls += 1;
        return HttpResponse.json(buildTransactionDetailFixture());
      })
    );

    renderDetail("/transactions/not-a-valid-uuid");

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/not a valid UUID/i);
    });
    expect(detailCalls).toBe(0);
  });

  it("renders separate Immutable Facts, Relational Context, and Risk Intelligence and preserves Back filter state", async () => {
    server.use(
      http.get(`/api/v1/transactions/${SAMPLE_TX_UUID}`, () =>
        HttpResponse.json(buildTransactionDetailFixture())
      ),
      http.get(`/api/v1/transactions/${SAMPLE_TX_UUID}/risk`, () =>
        HttpResponse.json(buildRiskAnalysisFixture())
      )
    );

    renderDetail({
      pathname: `/transactions/${SAMPLE_TX_UUID}`,
      search: "?source_namespace=SYNTHETIC",
      state: { fromTransactionsSearch: "?source_namespace=SYNTHETIC&direction=DEBIT" },
    });

    await waitFor(() => {
      expect(screen.getByText("Immutable Transaction Facts")).toBeInTheDocument();
      expect(screen.getByText("Relational Entity Context")).toBeInTheDocument();
      expect(screen.getByText("Risk Intelligence")).toBeInTheDocument();
      expect(screen.getByText("HIGH RISK")).toBeInTheDocument();
    });

    expect(screen.getByText("TXN-2026-0001")).toBeInTheDocument();
    expect(screen.getByText("12,345.67")).toBeInTheDocument();
    expect(screen.getByText("Apex Airlines")).toBeInTheDocument();
    expect(screen.getByText("Bengaluru, KA, IN")).toBeInTheDocument();

    const backLink = screen.getByRole("link", { name: /Back to Transactions/i });
    expect(backLink).toHaveAttribute(
      "href",
      "/transactions?source_namespace=SYNTHETIC&direction=DEBIT"
    );
  });

  it("surfaces 404 TRANSACTION_NOT_FOUND cleanly without issuing risk endpoint calls", async () => {
    let riskCalls = 0;
    server.use(
      http.get(`/api/v1/transactions/${SAMPLE_TX_UUID}`, () =>
        HttpResponse.json(
          {
            error: {
              code: "TRANSACTION_NOT_FOUND",
              message: "Transaction was not found.",
              details: {},
              request_id: "req-detail-404",
            },
          },
          { status: 404 }
        )
      ),
      http.get(`/api/v1/transactions/${SAMPLE_TX_UUID}/risk`, () => {
        riskCalls += 1;
        return HttpResponse.json(buildRiskAnalysisFixture());
      })
    );

    renderDetail(`/transactions/${SAMPLE_TX_UUID}`);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/Transaction was not found/i);
    });
    expect(riskCalls).toBe(0);
  });
});
