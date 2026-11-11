import { render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { createMemoryRouter, RouterProvider, useLocation } from "react-router";
import { describe, expect, it } from "vitest";
import { QueryProvider } from "../../src/app/providers/QueryProvider.tsx";
import { ProtectedRoute } from "../../src/app/router/ProtectedRoute.tsx";
import { PublicOnlyRoute } from "../../src/app/router/PublicOnlyRoute.tsx";
import { RoleGate } from "../../src/app/router/RoleGate.tsx";
import { AuthProvider } from "../../src/features/auth/context/AuthProvider.tsx";
import { setAccessToken } from "../../src/lib/auth/token-store.ts";
import {
  canManageDatasets,
  canViewDatasetImports,
} from "../../src/lib/permissions/capabilities.ts";
import { buildAuthUser } from "../fixtures/auth.ts";
import { server } from "../mocks/server.ts";

function LocationEcho({ label }: { label: string }) {
  const location = useLocation();
  return (
    <div data-testid="route-view">
      <span>{label}</span>
      <span data-testid="current-url">{`${location.pathname}${location.search}`}</span>
    </div>
  );
}

function renderRoutedHarness(initialEntry: string) {
  const router = createMemoryRouter(
    [
      {
        element: <PublicOnlyRoute />,
        children: [{ path: "/login", element: <LocationEcho label="Login View" /> }],
      },
      {
        element: <ProtectedRoute />,
        children: [
          { path: "/", element: <LocationEcho label="Workspace Overview" /> },
          {
            path: "/investigations",
            element: <LocationEcho label="Investigations View" />,
          },
          {
            path: "/datasets",
            element: (
              <RoleGate isAllowed={canViewDatasetImports}>
                <LocationEcho label="Datasets History View" />
              </RoleGate>
            ),
          },
          {
            path: "/datasets/manage",
            element: (
              <RoleGate isAllowed={canManageDatasets}>
                <LocationEcho label="Datasets Management View" />
              </RoleGate>
            ),
          },
        ],
      },
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

describe("ProtectedRoute, PublicOnlyRoute, and RoleGate (F2.3)", () => {
  it("renders neutral loading indicator while initializing and never flashes protected content", async () => {
    let releaseMe!: () => void;
    const gate = new Promise<void>((resolve) => {
      releaseMe = resolve;
    });

    setAccessToken("initializing-jwt");
    server.use(
      http.get("/api/v1/auth/me", async () => {
        await gate;
        return HttpResponse.json(buildAuthUser("ANALYST"));
      })
    );

    renderRoutedHarness("/");

    expect(screen.getByRole("status")).toHaveTextContent("Checking session...");
    expect(screen.queryByText("Workspace Overview")).not.toBeInTheDocument();

    releaseMe();
    await waitFor(() => {
      expect(screen.getByText("Workspace Overview")).toBeInTheDocument();
    });
  });

  it("redirects unauthenticated protected access to /login with encoded safe redirect", async () => {
    renderRoutedHarness("/investigations?status=OPEN");

    await waitFor(() => {
      expect(screen.getByText("Login View")).toBeInTheDocument();
    });
    expect(screen.getByTestId("current-url")).toHaveTextContent(
      "/login?redirect=%2Finvestigations%3Fstatus%3DOPEN"
    );
  });

  it("redirects already-authenticated users from /login to sanitized target and neutralizes external redirects", async () => {
    setAccessToken("authenticated-jwt");
    server.use(http.get("/api/v1/auth/me", () => HttpResponse.json(buildAuthUser("ANALYST"))));

    renderRoutedHarness("/login?redirect=https://evil.example/steal");

    await waitFor(() => {
      expect(screen.getByText("Workspace Overview")).toBeInTheDocument();
    });
    expect(screen.getByTestId("current-url")).toHaveTextContent("/");
  });

  it("allows INVESTIGATOR read-only /datasets import history while restricting dataset management UI policy", async () => {
    setAccessToken("investigator-jwt");
    server.use(http.get("/api/v1/auth/me", () => HttpResponse.json(buildAuthUser("INVESTIGATOR"))));

    renderRoutedHarness("/datasets");

    await waitFor(() => {
      expect(screen.getByText("Datasets History View")).toBeInTheDocument();
    });

    setAccessToken("investigator-jwt");
    renderRoutedHarness("/datasets/manage");

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: /Access restricted by workspace policy/i })
      ).toBeInTheDocument();
    });
    expect(screen.queryByText("Datasets Management View")).not.toBeInTheDocument();
  });
});
