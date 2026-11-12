import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";
import { QueryProvider } from "../../src/app/providers/QueryProvider.tsx";
import { AuthProvider } from "../../src/features/auth/context/AuthProvider.tsx";
import type { UserRole } from "../../src/features/auth/types/auth.types.ts";
import { DashboardPage } from "../../src/features/dashboard/pages/DashboardPage.tsx";
import { setAccessToken } from "../../src/lib/auth/token-store.ts";
import { apiErrorFixtures } from "../fixtures/api-errors.ts";
import { buildAuthUser } from "../fixtures/auth.ts";
import { buildOverviewFixture } from "../fixtures/f3-data.ts";
import { server } from "../mocks/server.ts";

function renderDashboard(role: UserRole = "ANALYST", initialPath = "/") {
  setAccessToken("dash-jwt");
  server.use(http.get("/api/v1/auth/me", () => HttpResponse.json(buildAuthUser(role))));

  const router = createMemoryRouter(
    [
      { path: "/", element: <DashboardPage /> },
      { path: "/transactions", element: <div>Transactions Target</div> },
      { path: "/analytics", element: <div>Analytics Target</div> },
      { path: "/datasets", element: <div>Datasets Target</div> },
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

describe("DashboardPage (F3.2)", () => {
  it("renders authoritative macro KPIs with exact decimal formatting and role-honest links", async () => {
    server.use(
      http.get("/api/v1/analytics/overview", () =>
        HttpResponse.json(
          buildOverviewFixture({
            total_volume_amount: "9007199254740993.50",
            net_cash_flow: "-320987.88",
          })
        )
      )
    );

    renderDashboard("ANALYST");

    await waitFor(() => {
      expect(screen.getByText("142")).toBeInTheDocument();
      expect(screen.getByText("9,007,199,254,740,993.50")).toBeInTheDocument();
      expect(screen.getByText("-320,987.88")).toBeInTheDocument();
    });
    expect(screen.getByText(/CSV upload and recovery/i)).toBeInTheDocument();
  });

  it("re-queries with updated namespace & currency via ReportingScopeBar and shows empty window cleanly", async () => {
    const user = userEvent.setup();
    const seenUrls: string[] = [];

    server.use(
      http.get("/api/v1/analytics/overview", ({ request }) => {
        seenUrls.push(request.url);
        const url = new URL(request.url);
        if (url.searchParams.get("source_namespace") === "PROD_LEDGER") {
          return HttpResponse.json(
            buildOverviewFixture({
              source_namespace: "PROD_LEDGER",
              currency: "USD",
              total_transaction_count: 0,
              debit_transaction_count: 0,
              credit_transaction_count: 0,
              total_volume_amount: "0.00",
              total_debit_amount: "0.00",
              total_credit_amount: "0.00",
              net_cash_flow: "0.00",
              average_transaction_amount: null,
              median_transaction_amount: null,
              debit_average_amount: null,
              debit_median_amount: null,
            })
          );
        }
        return HttpResponse.json(buildOverviewFixture());
      })
    );

    const { router } = renderDashboard("INVESTIGATOR");

    await waitFor(() => {
      expect(screen.getByText("142")).toBeInTheDocument();
    });
    expect(
      screen.getByText(/Read-only import history visibility for Investigator/i)
    ).toBeInTheDocument();

    const nsInput = screen.getByLabelText("Namespace");
    const currencyInput = screen.getByLabelText("Currency (ISO)");
    await user.clear(nsInput);
    await user.type(nsInput, "prod_ledger");
    await user.clear(currencyInput);
    await user.type(currencyInput, "usd");
    await user.click(screen.getByRole("button", { name: "Apply scope" }));

    await waitFor(() => {
      expect(screen.getByText(/No transactions in selected reporting scope/i)).toBeInTheDocument();
    });

    expect(router.state.location.search).toContain("source_namespace=PROD_LEDGER");
    expect(router.state.location.search).toContain("currency=USD");
    expect(seenUrls.some((u) => u.includes("source_namespace=PROD_LEDGER"))).toBe(true);
  });

  it("handles 404 NAMESPACE_NOT_FOUND reset and 500 Retry cleanly", async () => {
    const user = userEvent.setup();
    let failMode: "namespace" | "server" | "ok" = "namespace";

    server.use(
      http.get("/api/v1/analytics/overview", () => {
        if (failMode === "namespace") {
          return HttpResponse.json(
            {
              error: {
                code: "NAMESPACE_NOT_FOUND",
                message: "Unknown namespace UNKNOWN_NS.",
                details: {},
                request_id: "req-ns-404",
              },
            },
            { status: 404 }
          );
        }
        if (failMode === "server") {
          return apiErrorFixtures.internalError();
        }
        return HttpResponse.json(buildOverviewFixture());
      })
    );

    renderDashboard("ADMIN", "/?source_namespace=UNKNOWN_NS");

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/Unknown namespace/i);
    });

    failMode = "server";
    await user.click(screen.getByRole("button", { name: "Reset to SYNTHETIC" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/Unable to load dashboard overview/i);
    });
    expect(screen.getByText(/Request ID: req-500/i)).toBeInTheDocument();

    failMode = "ok";
    await user.click(screen.getByRole("button", { name: "Retry" }));

    await waitFor(() => {
      expect(screen.getByText("142")).toBeInTheDocument();
    });
  });
});
