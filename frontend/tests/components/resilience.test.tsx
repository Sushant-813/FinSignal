import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it, vi } from "vitest";
import { RootErrorBoundary } from "../../src/app/errors/RootErrorBoundary.tsx";
import { AppProviders } from "../../src/app/providers/AppProviders.tsx";
import { appRoutes } from "../../src/app/router/routes.tsx";

function Bomb(): ReactNode {
  throw new Error("Sensitive internal stack detail: SECRET_XYZ");
}

describe("Application resilience and F2 routing", () => {
  it("renders NotFoundPage on unknown routes and enforces auth redirect when returning to /", async () => {
    const user = userEvent.setup();
    const router = createMemoryRouter(appRoutes, {
      initialEntries: ["/nonexistent"],
    });

    render(
      <AppProviders>
        <RouterProvider router={router} />
      </AppProviders>
    );

    expect(screen.getByRole("heading", { name: "Page not found" })).toBeInTheDocument();
    const homeLink = screen.getByRole("link", { name: "Return to home" });
    expect(homeLink).toHaveAttribute("href", "/");

    await user.click(homeLink);
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    });
  });

  it("catches rendering errors in RootErrorBoundary without exposing stack traces and triggers reload", async () => {
    const user = userEvent.setup();
    const onReload = vi.fn();
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    render(
      <RootErrorBoundary onReload={onReload}>
        <Bomb />
      </RootErrorBoundary>
    );

    expect(screen.getByRole("heading", { name: "Something went wrong" })).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent(/Reload the application to recover/i);
    expect(screen.queryByText(/SECRET_XYZ/)).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Reload application" }));
    expect(onReload).toHaveBeenCalledTimes(1);

    consoleErrorSpy.mockRestore();
  });

  it("catches route-level rendering errors via route errorElement safely", () => {
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    const faultyRoutes = [
      {
        path: "/",
        element: <Bomb />,
        errorElement: appRoutes[0]?.errorElement,
      },
    ];
    const router = createMemoryRouter(faultyRoutes, { initialEntries: ["/"] });

    render(<RouterProvider router={router} />);

    expect(screen.getByRole("heading", { name: "Something went wrong" })).toBeInTheDocument();
    expect(screen.queryByText(/SECRET_XYZ/)).not.toBeInTheDocument();

    consoleErrorSpy.mockRestore();
  });
});
