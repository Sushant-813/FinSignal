import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";
import { QueryProvider } from "../../src/app/providers/QueryProvider.tsx";
import { ProtectedRoute } from "../../src/app/router/ProtectedRoute.tsx";
import { AuthProvider } from "../../src/features/auth/context/AuthProvider.tsx";
import { TransactionDetailPage } from "../../src/features/transactions/pages/TransactionDetailPage.tsx";
import { setAccessToken } from "../../src/lib/auth/token-store.ts";
import { buildAuthUser } from "../fixtures/auth.ts";
import { buildTransactionDetailFixture } from "../fixtures/f3-data.ts";
import { SAMPLE_PRIMARY_TX_ID } from "../fixtures/f5-data.ts";
import { server } from "../mocks/server.ts";

function renderTransactionDetailPage(role: "ADMIN" | "ANALYST" | "INVESTIGATOR" = "ANALYST") {
  setAccessToken("test-jwt");
  server.use(
    http.get("*/api/v1/auth/me", () => HttpResponse.json(buildAuthUser(role))),
    http.get(`*/api/v1/transactions/${SAMPLE_PRIMARY_TX_ID}`, () => {
      return HttpResponse.json(buildTransactionDetailFixture({ id: SAMPLE_PRIMARY_TX_ID }));
    }),
    http.get(`*/api/v1/transactions/${SAMPLE_PRIMARY_TX_ID}/risk`, () => {
      return HttpResponse.json(null, { status: 404 });
    })
  );

  const router = createMemoryRouter(
    [
      {
        element: <ProtectedRoute />,
        children: [
          {
            path: "/transactions/:transactionId",
            element: <TransactionDetailPage />,
          },
          {
            path: "/investigations/:investigationId",
            element: <div>Workspace Target Stub</div>,
          },
        ],
      },
    ],
    { initialEntries: [`/transactions/${SAMPLE_PRIMARY_TX_ID}`] }
  );

  return {
    router,
    ...render(
      <QueryProvider>
        <AuthProvider>
          <RouterProvider router={router} />
        </AuthProvider>
      </QueryProvider>
    ),
  };
}

describe("Investigation creation entry points (F5.4)", () => {
  it("renders Investigate Transaction action on TransactionDetailPage and submits with prefilled ID", async () => {
    const user = userEvent.setup();
    let createdPayload: Record<string, unknown> | null = null;
    server.use(
      http.post("*/api/v1/investigations", async ({ request }) => {
        createdPayload = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(
          {
            id: "77777777-8888-9999-aaaa-bbbbbbbbbbbb",
            status: "OPEN",
            priority: "MEDIUM",
            assigned_to: null,
            primary_transaction: {
              id: SAMPLE_PRIMARY_TX_ID,
              external_transaction_id: "EXT-TXN-001",
              account_id: "00000000-0000-0000-0000-000000000000",
              amount: "5000.00",
              currency: "USD",
              direction: "DEBIT",
              occurred_at: "2026-11-13T10:00:00Z",
              source_namespace: "SYNTHETIC",
            },
            latest_risk_analysis: null,
            related_transactions: [],
            resolution: null,
            resolution_notes: null,
            created_at: "2026-11-13T10:00:00Z",
            updated_at: "2026-11-13T10:00:00Z",
          },
          { status: 201 }
        );
      })
    );

    const { router } = renderTransactionDetailPage("ANALYST");

    const investigateBtn = await screen.findByTestId("investigate-transaction-button");
    expect(investigateBtn).toBeInTheDocument();
    await user.click(investigateBtn);

    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Create Investigation Case" })).toBeInTheDocument();

    const txInput = screen.getByLabelText(/primary transaction id/i) as HTMLInputElement;
    expect(txInput.value).toBe(SAMPLE_PRIMARY_TX_ID);
    expect(txInput).toBeDisabled();

    const submitBtn = screen.getByTestId("create-investigation-submit");
    await user.click(submitBtn);

    await waitFor(() => {
      expect(createdPayload).toEqual({
        transaction_id: SAMPLE_PRIMARY_TX_ID,
        priority: "MEDIUM",
      });
      expect(router.state.location.pathname).toBe(
        "/investigations/77777777-8888-9999-aaaa-bbbbbbbbbbbb"
      );
    });
  });
});
