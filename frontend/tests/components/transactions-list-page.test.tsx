import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";
import { QueryProvider } from "../../src/app/providers/QueryProvider.tsx";
import { ProtectedRoute } from "../../src/app/router/ProtectedRoute.tsx";
import { AuthProvider } from "../../src/features/auth/context/AuthProvider.tsx";
import { TransactionsListPage } from "../../src/features/transactions/pages/TransactionsListPage.tsx";
import { setAccessToken } from "../../src/lib/auth/token-store.ts";
import { buildAuthUser } from "../fixtures/auth.ts";
import {
  buildTransactionListFixture,
  buildTransactionSummaryFixture,
  SAMPLE_TX_UUID,
  SAMPLE_TX_UUID_2,
} from "../fixtures/f3-data.ts";
import { server } from "../mocks/server.ts";

function renderTransactionsList(initialPath = "/transactions") {
  setAccessToken("tx-list-jwt");
  server.use(http.get("/api/v1/auth/me", () => HttpResponse.json(buildAuthUser("ANALYST"))));

  const router = createMemoryRouter(
    [
      {
        element: <ProtectedRoute />,
        children: [
          { path: "/transactions", element: <TransactionsListPage /> },
          { path: "/transactions/:transactionId", element: <div>Transaction Detail Target</div> },
        ],
      },
      { path: "/login", element: <div>Login Target</div> },
    ],
    { initialEntries: [initialPath] }
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

describe("TransactionsListPage (F3.4)", () => {
  it("renders server-paginated ledger rows, preserves decimal strings, and updates URL sort & page", async () => {
    const user = userEvent.setup();
    const seenUrls: string[] = [];

    server.use(
      http.get("/api/v1/transactions", ({ request }) => {
        seenUrls.push(request.url);
        const url = new URL(request.url);
        const page = Number(url.searchParams.get("page") ?? "1");
        if (page === 2) {
          return HttpResponse.json(
            buildTransactionListFixture(
              [
                buildTransactionSummaryFixture({
                  id: SAMPLE_TX_UUID_2,
                  external_transaction_id: "TXN-PAGE-2",
                  amount: "5432.10",
                }),
              ],
              { page: 2, page_size: 50, total: 51, total_pages: 2 }
            )
          );
        }

        return HttpResponse.json(
          buildTransactionListFixture(
            [
              buildTransactionSummaryFixture({
                id: SAMPLE_TX_UUID,
                external_transaction_id: "TXN-2026-0001",
                amount: "12345.67",
              }),
            ],
            { page: 1, page_size: 50, total: 51, total_pages: 2 }
          )
        );
      })
    );

    const { router } = renderTransactionsList();

    await waitFor(() => {
      expect(screen.getByText("TXN-2026-0001")).toBeInTheDocument();
      expect(screen.getByText("12,345.67")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /Amount/i }));
    await waitFor(() => {
      expect(router.state.location.search).toContain("sort_by=amount");
    });

    await user.click(screen.getByRole("button", { name: "Next page" }));
    await waitFor(() => {
      expect(screen.getByText("TXN-PAGE-2")).toBeInTheDocument();
      expect(screen.getByText("5,432.10")).toBeInTheDocument();
    });
    expect(router.state.location.search).toContain("page=2");
    expect(seenUrls.some((u) => u.includes("page=2"))).toBe(true);
  });

  it("blocks invalid client filter inputs via Zod without dispatching bad API calls", async () => {
    const user = userEvent.setup();
    let apiCalls = 0;

    server.use(
      http.get("/api/v1/transactions", () => {
        apiCalls += 1;
        return HttpResponse.json(buildTransactionListFixture([]));
      })
    );

    renderTransactionsList();
    await waitFor(() => {
      expect(screen.getByText("No transactions found")).toBeInTheDocument();
    });
    const callsBeforeInvalidSubmit = apiCalls;

    await user.click(screen.getByRole("button", { name: /Advanced filters/i }));
    const accountInput = screen.getByLabelText("Account UUID");
    await user.type(accountInput, "not-a-uuid");
    await user.click(screen.getByRole("button", { name: "Apply filters" }));

    await waitFor(() => {
      expect(screen.getByText("Must be a valid UUID.")).toBeInTheDocument();
    });
    expect(apiCalls).toBe(callsBeforeInvalidSubmit);
  });

  it("normalizes invalid URL params and surfaces backend NAMESPACE_NOT_FOUND cleanly", async () => {
    server.use(
      http.get("/api/v1/transactions", () =>
        HttpResponse.json(
          {
            error: {
              code: "NAMESPACE_NOT_FOUND",
              message: "Namespace MISSING_NS does not exist.",
              details: {},
              request_id: "req-tx-ns-404",
            },
          },
          { status: 404 }
        )
      )
    );

    renderTransactionsList("/transactions?source_namespace=MISSING_NS&page=abc");

    await waitFor(() => {
      expect(
        screen.getByText(/One or more invalid URL query parameters were ignored/i)
      ).toBeInTheDocument();
      expect(screen.getByRole("alert")).toHaveTextContent(/Namespace MISSING_NS does not exist/i);
    });
  });
});
