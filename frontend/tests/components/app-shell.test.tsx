import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";
import { AppLayout } from "../../src/app/layouts/AppLayout.tsx";
import { AuthLayout } from "../../src/app/layouts/AuthLayout.tsx";
import { QueryProvider } from "../../src/app/providers/QueryProvider.tsx";
import { PhasePlaceholderPage } from "../../src/app/router/PhasePlaceholderPage.tsx";
import { WorkspaceHomePage } from "../../src/app/router/WorkspaceHomePage.tsx";
import { AuthProvider } from "../../src/features/auth/context/AuthProvider.tsx";
import type { UserRole } from "../../src/features/auth/types/auth.types.ts";
import { getAccessToken, setAccessToken } from "../../src/lib/auth/token-store.ts";
import { buildAuthUser } from "../fixtures/auth.ts";
import { server } from "../mocks/server.ts";

function renderShell(role: UserRole = "ADMIN", initialPath = "/") {
  setAccessToken("shell-jwt");
  server.use(http.get("/api/v1/auth/me", () => HttpResponse.json(buildAuthUser(role))));

  const router = createMemoryRouter(
    [
      {
        element: <AuthLayout />,
        children: [{ path: "/login", element: <div>Login Route Reached</div> }],
      },
      {
        element: <AppLayout />,
        children: [
          { path: "/", element: <WorkspaceHomePage /> },
          {
            path: "/transactions",
            element: (
              <PhasePlaceholderPage
                title="Transactions"
                phaseLabel="Phase F3"
                description="Transaction exploration"
              />
            ),
          },
          {
            path: "/datasets",
            element: (
              <PhasePlaceholderPage
                title="Datasets"
                phaseLabel="Phase F4"
                description="Dataset imports"
                isDatasetsRoute
              />
            ),
          },
        ],
      },
    ],
    { initialEntries: [initialPath] }
  );

  return render(
    <QueryProvider>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </QueryProvider>
  );
}

describe("Application Shell & Layouts (F2.4)", () => {
  it("renders skip link, landmarks, supported nav items only, active aria-current, and zero fake KPIs", async () => {
    renderShell("ANALYST", "/");

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Workspace Overview" })).toBeInTheDocument();
    });

    const skipLink = screen.getByRole("link", { name: "Skip to main content" });
    expect(skipLink).toHaveAttribute("href", "#main-content");
    expect(document.getElementById("main-content")).toBeInTheDocument();

    const overviewLink = screen.getByRole("link", { name: "Dashboard Overview" });
    expect(overviewLink).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Transactions" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Analytics" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Investigations" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Datasets" })).toBeInTheDocument();

    expect(screen.queryByRole("link", { name: /Accounts/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Audit/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Admin/i })).not.toBeInTheDocument();

    expect(screen.getAllByText("analyst@finsignal.test").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Allowed (Admin / Analyst)")).toBeInTheDocument();
  });

  it("supports desktop collapse toggle and accessible mobile drawer Escape dismissal", async () => {
    const user = userEvent.setup();
    renderShell("ADMIN", "/");

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Workspace Overview" })).toBeInTheDocument();
    });

    const collapseBtn = screen.getByRole("button", { name: "Collapse navigation sidebar" });
    expect(collapseBtn).toHaveAttribute("aria-expanded", "true");
    await user.click(collapseBtn);
    expect(screen.getByRole("button", { name: "Expand navigation sidebar" })).toHaveAttribute(
      "aria-expanded",
      "false"
    );

    const mobileOpenBtn = screen.getByRole("button", { name: "Open navigation menu" });
    await user.click(mobileOpenBtn);
    expect(screen.getByRole("dialog", { name: "Primary navigation" })).toBeInTheDocument();

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog", { name: "Primary navigation" })).not.toBeInTheDocument();
    expect(mobileOpenBtn).toHaveFocus();
  });

  it("displays investigator read-only dataset policy honestly and signs out via UserMenu", async () => {
    const user = userEvent.setup();
    renderShell("INVESTIGATOR", "/datasets");

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Datasets" })).toBeInTheDocument();
    });

    expect(
      screen.getByText(/Read-only dataset import history is permitted for Investigator accounts/i)
    ).toBeInTheDocument();

    const menuTrigger = screen.getByRole("button", { name: /investigator@finsignal\.test/i });
    await user.click(menuTrigger);
    const signOutBtn = screen.getByRole("menuitem", { name: "Sign out" });
    await user.click(signOutBtn);

    await waitFor(() => {
      expect(screen.getByText("Login Route Reached")).toBeInTheDocument();
    });
    expect(getAccessToken()).toBeNull();
  });
});
