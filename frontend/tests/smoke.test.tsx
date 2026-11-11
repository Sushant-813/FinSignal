import { render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import App from "../src/App.tsx";
import type { components } from "../src/api/generated/schema.ts";
import { ApiClientError, apiRequest } from "../src/lib/api/client.ts";
import { resolveApiBaseUrl } from "../src/lib/api/env.ts";
import { clearAccessToken, getAccessToken, setAccessToken } from "../src/lib/auth/token-store.ts";
import { apiErrorFixtures } from "./fixtures/api-errors.ts";
import { buildAuthUser } from "./fixtures/auth.ts";
import { server } from "./mocks/server.ts";

type TransactionListResponse = components["schemas"]["TransactionListResponse"];

describe("Phase F2 authenticated workspace smoke baseline", () => {
  it("redirects unauthenticated visits at / to the FinSignal Sign in view", async () => {
    window.history.replaceState({}, "", "/");
    render(<App />);
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    });
  });

  it("renders Workspace Overview when an authenticated session is active", async () => {
    window.history.replaceState({}, "", "/");
    setAccessToken("smoke-valid-jwt");
    server.use(http.get("/api/v1/auth/me", () => HttpResponse.json(buildAuthUser("ANALYST"))));

    render(<App />);
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Workspace Overview" })).toBeInTheDocument();
    });
    expect(screen.getAllByText("analyst@finsignal.test").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("/api/v1")).toBeInTheDocument();
  });

  it("normalizes VITE_API_BASE_URL safely", () => {
    expect(resolveApiBaseUrl(undefined)).toBe("/api/v1");
    expect(resolveApiBaseUrl("http://localhost:8000/api/v1/")).toBe("http://localhost:8000/api/v1");
    expect(() => resolveApiBaseUrl("   ")).toThrow(/must not be empty/);
  });

  it("holds access tokens strictly in memory without browser persistence", () => {
    expect(getAccessToken()).toBeNull();
    setAccessToken("mem-token-123");
    expect(getAccessToken()).toBe("mem-token-123");
    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(0);
    clearAccessToken();
    expect(getAccessToken()).toBeNull();
  });

  it("injects Bearer token and parses generated OpenAPI response + error envelopes via MSW", async () => {
    server.use(
      http.get("http://localhost/api/v1/transactions", ({ request }) => {
        const auth = request.headers.get("Authorization");
        if (auth !== "Bearer test-jwt-token") {
          return apiErrorFixtures.unauthorized();
        }

        const payload: TransactionListResponse = {
          items: [],
          page: 1,
          page_size: 50,
          total: 0,
          total_pages: 0,
        };
        return HttpResponse.json(payload);
      })
    );

    await expect(
      apiRequest<TransactionListResponse>("/transactions", {
        baseUrl: "http://localhost/api/v1",
      })
    ).rejects.toMatchObject({
      name: "ApiClientError",
      status: 401,
      code: "UNAUTHORIZED",
      requestId: "req-401",
    } satisfies Partial<ApiClientError>);

    setAccessToken("test-jwt-token");
    const data = await apiRequest<TransactionListResponse>("/transactions", {
      baseUrl: "http://localhost/api/v1",
    });
    expect(data.total).toBe(0);
    expect(data.page_size).toBe(50);
  });
});
