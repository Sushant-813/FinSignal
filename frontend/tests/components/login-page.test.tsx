import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";
import { AppProviders } from "../../src/app/providers/AppProviders.tsx";
import { appRoutes } from "../../src/app/router/routes.tsx";
import { apiRequest } from "../../src/lib/api/client.ts";
import { getAccessToken, setAccessToken } from "../../src/lib/auth/token-store.ts";
import { apiErrorFixtures } from "../fixtures/api-errors.ts";
import { buildAuthUser, createAuthHandlers } from "../fixtures/auth.ts";
import { buildOverviewFixture, buildTransactionListFixture } from "../fixtures/f3-data.ts";
import { server } from "../mocks/server.ts";

function renderAppAt(initialEntry: string) {
  const router = createMemoryRouter(appRoutes, { initialEntries: [initialEntry] });
  return render(
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>
  );
}

describe("LoginPage (F2.5)", () => {
  it("validates email and password (1..128) cleanly with accessible errors and no registration link", async () => {
    const user = userEvent.setup();
    renderAppAt("/login");

    expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: /register|create account|sign up/i })
    ).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Sign in" }));

    const emailInput = screen.getByLabelText(/Email/i);
    const passwordInput = screen.getByLabelText(/^Password/i);

    await waitFor(() => {
      expect(emailInput).toHaveAttribute("aria-invalid", "true");
      expect(passwordInput).toHaveAttribute("aria-invalid", "true");
    });
    expect(screen.getByText("Email is required.")).toBeInTheDocument();
    expect(screen.getByText("Password is required.")).toBeInTheDocument();

    await user.type(emailInput, "not-an-email");
    await user.type(passwordInput, "x".repeat(129));
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => {
      expect(screen.getByText("Enter a valid email address.")).toBeInTheDocument();
      expect(screen.getByText("Password must not exceed 128 characters.")).toBeInTheDocument();
    });
  });

  it("allows short valid passwords matching LoginRequest (min 1) and redirects to sanitized target", async () => {
    const user = userEvent.setup();
    const analyst = buildAuthUser("ANALYST");
    server.use(
      ...createAuthHandlers(analyst, { accessToken: "login-jwt" }),
      http.get("/api/v1/transactions", () => HttpResponse.json(buildTransactionListFixture([])))
    );

    renderAppAt("/login?redirect=%2Ftransactions%3Fpage%3D2");

    await user.type(screen.getByLabelText(/Email/i), "ANALYST@finsignal.test");
    await user.type(screen.getByLabelText(/^Password/i), "short1");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Transactions" })).toBeInTheDocument();
    });
    expect(getAccessToken()).toBe("login-jwt");
  });

  it("neutralizes unsafe external ?redirect= targets back to Dashboard Overview", async () => {
    const user = userEvent.setup();
    server.use(
      ...createAuthHandlers(buildAuthUser("ADMIN")),
      http.get("/api/v1/analytics/overview", () => HttpResponse.json(buildOverviewFixture()))
    );

    renderAppAt("/login?redirect=https%3A%2F%2Fevil.example%2Fsteal");

    await user.type(screen.getByLabelText(/Email/i), "admin@finsignal.test");
    await user.type(screen.getByLabelText(/^Password/i), "pass");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Dashboard Overview" })).toBeInTheDocument();
    });
  });

  it("disables submit during in-flight login to prevent duplicate submission", async () => {
    const user = userEvent.setup();
    let releaseLogin!: () => void;
    const loginGate = new Promise<void>((resolve) => {
      releaseLogin = resolve;
    });

    server.use(
      http.post("/api/v1/auth/login", async () => {
        await loginGate;
        return HttpResponse.json({
          access_token: "in-flight-jwt",
          token_type: "bearer",
          expires_in: 1800,
        });
      }),
      http.get("/api/v1/auth/me", () => HttpResponse.json(buildAuthUser("ANALYST"))),
      http.get("/api/v1/analytics/overview", () => HttpResponse.json(buildOverviewFixture()))
    );

    renderAppAt("/login");

    await user.type(screen.getByLabelText(/Email/i), "analyst@finsignal.test");
    await user.type(screen.getByLabelText(/^Password/i), "valid-password");

    const submitBtn = screen.getByRole("button", { name: "Sign in" });
    await user.click(submitBtn);

    await waitFor(() => {
      expect(submitBtn).toBeDisabled();
      expect(submitBtn).toHaveAttribute("aria-busy", "true");
    });

    releaseLogin();
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Dashboard Overview" })).toBeInTheDocument();
    });
  });

  it("handles 401, 429, 422, 500, network failure, and expired session banner safely", async () => {
    const user = userEvent.setup();
    renderAppAt("/login");

    // 401 generic failure (no account enumeration)
    server.use(http.post("/api/v1/auth/login", () => apiErrorFixtures.unauthorized()));
    await user.type(screen.getByLabelText(/Email/i), "analyst@finsignal.test");
    await user.type(screen.getByLabelText(/^Password/i), "wrong-password");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        /Invalid email or password, or your account is inactive/i
      );
    });
    expect(screen.getByText(/Request ID: req-401/i)).toBeInTheDocument();

    // 429 rate limit
    server.use(http.post("/api/v1/auth/login", () => apiErrorFixtures.rateLimited(42)));
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/wait 42 seconds/i);
    });

    // 422 backend field error
    server.use(
      http.post("/api/v1/auth/login", () =>
        apiErrorFixtures.validationError({ email: ["Backend email rejection."] })
      )
    );
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() => {
      expect(screen.getByText("Backend email rejection.")).toBeInTheDocument();
    });

    // 500 server error (never leaks internal message)
    server.use(http.post("/api/v1/auth/login", () => apiErrorFixtures.internalError()));
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/server error occurred/i);
    });
    expect(screen.getByText(/Request ID: req-500/i)).toBeInTheDocument();

    // Network failure
    server.use(http.post("/api/v1/auth/login", () => HttpResponse.error()));
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/Unable to reach the server/i);
    });
  });

  it("displays an expired session banner when a protected session receives 401", async () => {
    setAccessToken("expired-jwt");
    server.use(
      http.get("/api/v1/auth/me", () => HttpResponse.json(buildAuthUser("ANALYST"))),
      http.get("/api/v1/analytics/overview", () => HttpResponse.json(buildOverviewFixture())),
      http.get("/api/v1/sample-ping", () => apiErrorFixtures.unauthorized())
    );

    renderAppAt("/");

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Dashboard Overview" })).toBeInTheDocument();
    });

    await act(async () => {
      await expect(apiRequest("/sample-ping")).rejects.toMatchObject({ status: 401 });
    });

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
      expect(screen.getByRole("status")).toHaveTextContent(/Your session has expired/i);
    });
  });
});
