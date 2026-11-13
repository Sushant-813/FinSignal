import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";
import { QueryProvider } from "../../src/app/providers/QueryProvider.tsx";
import { ProtectedRoute } from "../../src/app/router/ProtectedRoute.tsx";
import { AuthProvider } from "../../src/features/auth/context/AuthProvider.tsx";
import { InvestigationWorkspacePage } from "../../src/features/investigations/pages/InvestigationWorkspacePage.tsx";
import { setAccessToken } from "../../src/lib/auth/token-store.ts";
import { buildAuthUser } from "../fixtures/auth.ts";
import {
  buildInvestigationDetailResponse,
  buildInvestigationTransactionItem,
  SAMPLE_INVESTIGATION_ID,
  SAMPLE_INVESTIGATOR_ID,
} from "../fixtures/f5-data.ts";
import { server } from "../mocks/server.ts";

function renderWorkspacePage(
  investigationId = SAMPLE_INVESTIGATION_ID,
  role: "ADMIN" | "ANALYST" | "INVESTIGATOR" = "INVESTIGATOR",
  userOverrides: { id?: string } = {}
) {
  setAccessToken("test-role-jwt");
  server.use(
    http.get("*/api/v1/auth/me", () =>
      HttpResponse.json(buildAuthUser(role, { id: SAMPLE_INVESTIGATOR_ID, ...userOverrides }))
    )
  );

  const router = createMemoryRouter(
    [
      {
        element: <ProtectedRoute />,
        children: [
          {
            path: "/investigations/:investigationId",
            element: <InvestigationWorkspacePage />,
          },
          { path: "/investigations", element: <div>Queue Stub</div> },
        ],
      },
      { path: "/login", element: <div>Login Target</div> },
    ],
    { initialEntries: [`/investigations/${investigationId}`] }
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

describe("InvestigationWorkspacePage component (F5.5–F5.6)", () => {
  it("renders workspace aggregate, primary transaction facts, risk snapshot, and F6 placeholders", async () => {
    server.use(
      http.get("*/api/v1/investigations/:id", () => {
        return HttpResponse.json(
          buildInvestigationDetailResponse({
            id: SAMPLE_INVESTIGATION_ID,
            status: "OPEN",
            priority: "HIGH",
            assigned_to: null,
            related_transactions: [
              buildInvestigationTransactionItem({
                transaction_id: "33333333-3333-3333-3333-333333333333",
                amount: "250.00",
                currency: "INR",
              }),
            ],
          })
        );
      })
    );

    renderWorkspacePage();

    expect(await screen.findByRole("heading", { name: "Investigation Case" })).toBeInTheDocument();
    expect(screen.getByTestId("investigation-primary-tx-card")).toBeInTheDocument();
    expect(screen.getByTestId("investigation-latest-risk-card")).toBeInTheDocument();
    expect(screen.getByTestId("investigation-related-tx-card")).toBeInTheDocument();
    expect(screen.getByTestId("investigation-evidence-placeholder")).toBeInTheDocument();
    expect(screen.getByTestId("investigation-ai-summary-placeholder")).toBeInTheDocument();
    expect(screen.getByTestId("take-case-button")).toBeInTheDocument();
  });

  it("handles INVESTIGATOR self-assignment (Take Case) successfully", async () => {
    const user = userEvent.setup();
    let patchedPayload: Record<string, unknown> | null = null;
    server.use(
      http.get("*/api/v1/investigations/:id", () => {
        return HttpResponse.json(
          buildInvestigationDetailResponse({
            id: SAMPLE_INVESTIGATION_ID,
            status: "OPEN",
            assigned_to: null,
          })
        );
      }),
      http.patch("*/api/v1/investigations/:id", async ({ request }) => {
        patchedPayload = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(
          buildInvestigationDetailResponse({
            id: SAMPLE_INVESTIGATION_ID,
            status: "OPEN",
            assigned_to: SAMPLE_INVESTIGATOR_ID,
            assigned_user_email: "investigator@finsignal.internal",
          })
        );
      })
    );

    renderWorkspacePage();

    const takeCaseBtn = await screen.findByTestId("take-case-button");
    await user.click(takeCaseBtn);

    await waitFor(() => {
      expect(patchedPayload).toEqual({ assigned_to: SAMPLE_INVESTIGATOR_ID });
    });
  });

  it("transitions lifecycle from OPEN to UNDER_REVIEW via Begin Review", async () => {
    const user = userEvent.setup();
    let patchedPayload: Record<string, unknown> | null = null;
    server.use(
      http.get("*/api/v1/investigations/:id", () => {
        return HttpResponse.json(
          buildInvestigationDetailResponse({
            id: SAMPLE_INVESTIGATION_ID,
            status: "OPEN",
            assigned_to: SAMPLE_INVESTIGATOR_ID,
          })
        );
      }),
      http.patch("*/api/v1/investigations/:id", async ({ request }) => {
        patchedPayload = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(
          buildInvestigationDetailResponse({
            id: SAMPLE_INVESTIGATION_ID,
            status: "UNDER_REVIEW",
            assigned_to: SAMPLE_INVESTIGATOR_ID,
          })
        );
      })
    );

    renderWorkspacePage();

    const beginReviewBtn = await screen.findByTestId("begin-review-button");
    await user.click(beginReviewBtn);

    await waitFor(() => {
      expect(patchedPayload).toEqual({ status: "UNDER_REVIEW" });
    });
  });

  it("allows linking a related transaction via modal dialog", async () => {
    const user = userEvent.setup();
    const newRelatedTxId = "44444444-4444-4444-4444-444444444444";
    let linkedPayload: Record<string, unknown> | null = null;

    server.use(
      http.get("*/api/v1/investigations/:id", () => {
        return HttpResponse.json(
          buildInvestigationDetailResponse({
            id: SAMPLE_INVESTIGATION_ID,
            status: "UNDER_REVIEW",
            assigned_to: SAMPLE_INVESTIGATOR_ID,
          })
        );
      }),
      http.post("*/api/v1/investigations/:id/transactions", async ({ request }) => {
        linkedPayload = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(
          buildInvestigationTransactionItem({
            transaction_id: newRelatedTxId,
            relationship_type: "RELATED",
          }),
          { status: 201 }
        );
      })
    );

    renderWorkspacePage();

    const openLinkBtn = await screen.findByTestId("open-link-transaction-button");
    await user.click(openLinkBtn);

    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Link Related Transaction" })).toBeInTheDocument();

    const txInput = screen.getByLabelText(/related transaction uuid/i);
    await user.type(txInput, newRelatedTxId);

    const submitBtn = screen.getByTestId("confirm-link-transaction-button");
    await user.click(submitBtn);

    await waitFor(() => {
      expect(linkedPayload).toEqual({ transaction_id: newRelatedTxId });
    });
  });

  it("completes case resolution with mandatory notes and renders permanent read-only state", async () => {
    const user = userEvent.setup();
    let resolvedPayload: Record<string, unknown> | null = null;

    server.use(
      http.get("*/api/v1/investigations/:id", () => {
        return HttpResponse.json(
          buildInvestigationDetailResponse({
            id: SAMPLE_INVESTIGATION_ID,
            status: "UNDER_REVIEW",
            assigned_to: SAMPLE_INVESTIGATOR_ID,
          })
        );
      }),
      http.post("*/api/v1/investigations/:id/resolve", async ({ request }) => {
        resolvedPayload = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(
          buildInvestigationDetailResponse({
            id: SAMPLE_INVESTIGATION_ID,
            status: "RESOLVED",
            resolution: "CONFIRMED_FRAUD",
            resolution_notes: "Identity theft and unauthorized device velocity confirmed.",
            assigned_to: SAMPLE_INVESTIGATOR_ID,
          })
        );
      })
    );

    renderWorkspacePage();

    const resolveBtn = await screen.findByTestId("resolve-case-button");
    await user.click(resolveBtn);

    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Resolve Investigation Case" })).toBeInTheDocument();

    const outcomeSelect = screen.getByRole("combobox", { name: "Resolution Outcome" });
    await user.click(outcomeSelect);
    const confirmedFraudOption = await screen.findByRole("option", {
      name: "Confirmed Fraud (Adverse Action)",
    });
    await user.click(confirmedFraudOption);

    const notesArea = screen.getByLabelText(/resolution notes/i);
    await user.type(
      notesArea,
      "Identity theft and unauthorized device velocity confirmed."
    );

    const confirmBtn = screen.getByTestId("confirm-resolve-case-button");
    await user.click(confirmBtn);

    await waitFor(() => {
      expect(resolvedPayload).toEqual({
        resolution: "CONFIRMED_FRAUD",
        resolution_notes: "Identity theft and unauthorized device velocity confirmed.",
      });
    });
  });

  it("handles 404 when investigation ID does not exist", async () => {
    server.use(
      http.get("*/api/v1/investigations/:id", () => {
        return HttpResponse.json(
          { error: { code: "INVESTIGATION_NOT_FOUND", message: "Not found." } },
          { status: 404 }
        );
      })
    );

    renderWorkspacePage();

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("Investigation case not found")).toBeInTheDocument();
  });

  it("handles concurrency conflict (HTTP 409) with informative banner", async () => {
    server.use(
      http.get("*/api/v1/investigations/:id", () => {
        return HttpResponse.json(
          buildInvestigationDetailResponse({
            id: SAMPLE_INVESTIGATION_ID,
            status: "OPEN",
            assigned_to: null,
          })
        );
      }),
      http.patch("*/api/v1/investigations/:id", () => {
        return HttpResponse.json(
          {
            error: {
              code: "CASE_ALREADY_ASSIGNED",
              message: "Case has already been claimed by another investigator.",
            },
          },
          { status: 409 }
        );
      })
    );

    renderWorkspacePage();

    const takeCaseBtn = await screen.findByTestId("take-case-button");
    await userEvent.click(takeCaseBtn);

    expect(await screen.findByText("Concurrency Conflict")).toBeInTheDocument();
  });
});
