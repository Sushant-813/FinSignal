import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";
import { QueryProvider } from "../../src/app/providers/QueryProvider.tsx";
import { ProtectedRoute } from "../../src/app/router/ProtectedRoute.tsx";
import { AuthProvider } from "../../src/features/auth/context/AuthProvider.tsx";
import { InvestigationsQueuePage } from "../../src/features/investigations/pages/InvestigationsQueuePage.tsx";
import { setAccessToken } from "../../src/lib/auth/token-store.ts";
import { buildAuthUser } from "../fixtures/auth.ts";
import {
  buildInvestigationListResponse,
  buildInvestigationSummaryItem,
  SAMPLE_INVESTIGATION_ID,
  SAMPLE_PRIMARY_TX_ID,
} from "../fixtures/f5-data.ts";
import { server } from "../mocks/server.ts";

function renderQueuePage(
  initialPath = "/investigations",
  role: "ADMIN" | "ANALYST" | "INVESTIGATOR" = "INVESTIGATOR",
  userOverrides: { id?: string } = {}
) {
  setAccessToken("test-role-jwt");
  server.use(
    http.get("*/api/v1/auth/me", () =>
      HttpResponse.json(buildAuthUser(role, userOverrides))
    )
  );

  const router = createMemoryRouter(
    [
      {
        element: <ProtectedRoute />,
        children: [
          { path: "/investigations", element: <InvestigationsQueuePage /> },
          {
            path: "/investigations/:investigationId",
            element: <div>Workspace Target Stub</div>,
          },
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

describe("InvestigationsQueuePage component (F5.2–F5.3)", () => {
  it("renders queue table, status badges, and actions for authenticated users", async () => {
    server.use(
      http.get("*/api/v1/investigations", () => {
        return HttpResponse.json(
          buildInvestigationListResponse({
            items: [
              buildInvestigationSummaryItem({
                id: SAMPLE_INVESTIGATION_ID,
                status: "OPEN",
                priority: "HIGH",
                primary_transaction_id: SAMPLE_PRIMARY_TX_ID,
                assigned_to: null,
              }),
            ],
            total: 1,
            total_pages: 1,
          })
        );
      })
    );

    renderQueuePage();

    expect(await screen.findByRole("heading", { name: "Investigations" })).toBeInTheDocument();
    expect(await screen.findByTestId("investigation-queue-table")).toBeInTheDocument();
    expect(await screen.findByTestId(`investigation-row-${SAMPLE_INVESTIGATION_ID}`)).toBeInTheDocument();
    expect(screen.getByTestId("investigation-status-badge-open")).toBeInTheDocument();
    expect(screen.getByTestId("investigation-priority-badge-high")).toBeInTheDocument();
    expect(screen.getByText("Unassigned")).toBeInTheDocument();
  });

  it("allows filtering by status and updates the query parameters", async () => {
    const user = userEvent.setup();
    let capturedUrl = "";
    server.use(
      http.get("*/api/v1/investigations", ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json(buildInvestigationListResponse());
      })
    );

    const { router } = renderQueuePage();
    await screen.findByTestId("investigation-queue-table");

    const statusTrigger = screen.getByRole("combobox", { name: "Status" });
    await user.click(statusTrigger);

    const underReviewOption = await screen.findByRole("option", { name: "Under Review" });
    await user.click(underReviewOption);

    await waitFor(() => {
      expect(router.state.location.search).toContain("status=UNDER_REVIEW");
      expect(capturedUrl).toContain("status=UNDER_REVIEW");
    });
  });

  it("filters by UNASSIGNED mode and clears assigned_to", async () => {
    const user = userEvent.setup();
    let capturedUrl = "";
    server.use(
      http.get("*/api/v1/investigations", ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json(buildInvestigationListResponse());
      })
    );

    const { router } = renderQueuePage();
    await screen.findByTestId("investigation-queue-table");

    const assigneeTrigger = screen.getByRole("combobox", { name: "Assignee" });
    await user.click(assigneeTrigger);

    const unassignedOption = await screen.findByRole("option", { name: "Unassigned" });
    await user.click(unassignedOption);

    await waitFor(() => {
      expect(router.state.location.search).toContain("unassigned=true");
      expect(router.state.location.search).not.toContain("assigned_to");
      expect(capturedUrl).toContain("unassigned=true");
    });
  });

  it("opens New Investigation dialog when permitted and submits successfully", async () => {
    const user = userEvent.setup();
    server.use(
      http.get("*/api/v1/investigations", () => HttpResponse.json(buildInvestigationListResponse())),
      http.post("*/api/v1/investigations", async () => {
        return HttpResponse.json({
          id: "99999999-8888-7777-6666-555555555555",
          status: "OPEN",
          priority: "HIGH",
          assigned_to: null,
          primary_transaction: {
            id: SAMPLE_PRIMARY_TX_ID,
            external_transaction_id: "EXT-001",
            account_id: "00000000-0000-0000-0000-000000000000",
            amount: "100.00",
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
        }, { status: 201 });
      })
    );

    const { router } = renderQueuePage();
    await screen.findByTestId("investigation-queue-table");

    const newBtn = screen.getByTestId("new-investigation-button");
    await user.click(newBtn);

    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Create Investigation Case" })).toBeInTheDocument();

    const txInput = screen.getByLabelText(/primary transaction id/i);
    await user.type(txInput, SAMPLE_PRIMARY_TX_ID);

    const submitBtn = screen.getByTestId("create-investigation-submit");
    await user.click(submitBtn);

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/investigations/99999999-8888-7777-6666-555555555555");
    });
  });

  it("handles empty queue cleanly and displays empty state", async () => {
    server.use(
      http.get("*/api/v1/investigations", () => {
        return HttpResponse.json(
          buildInvestigationListResponse({
            items: [],
            total: 0,
            total_pages: 0,
          })
        );
      })
    );

    renderQueuePage();

    expect(await screen.findByText("No investigations recorded")).toBeInTheDocument();
  });

  it("handles 500 API failure with retry action", async () => {
    let callCount = 0;
    server.use(
      http.get("*/api/v1/investigations", () => {
        callCount++;
        if (callCount === 1) {
          return HttpResponse.json(
            { error: { code: "INTERNAL_SERVER_ERROR", message: "Database offline." } },
            { status: 500 }
          );
        }
        return HttpResponse.json(buildInvestigationListResponse());
      })
    );

    renderQueuePage();

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("Failed to load investigations")).toBeInTheDocument();

    const retryBtn = screen.getByRole("button", { name: "Retry" });
    await userEvent.click(retryBtn);

    expect(await screen.findByTestId("investigation-queue-table")).toBeInTheDocument();
  });
});
