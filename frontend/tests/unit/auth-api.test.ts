import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { getCurrentUser, login, logout } from "../../src/features/auth/api/auth-api.ts";
import { ApiClientError } from "../../src/lib/api/client.ts";
import { registerUnauthorizedHandler } from "../../src/lib/auth/session-events.ts";
import { setAccessToken } from "../../src/lib/auth/token-store.ts";
import { server } from "../mocks/server.ts";

describe("auth-api (OpenAPI-aligned endpoints)", () => {
  it("calls POST /api/v1/auth/login with JSON body, omits Bearer token, and skips 401 session hook", async () => {
    let seenAuthHeader: string | null = null;
    let seenBody: unknown = null;

    setAccessToken("stale-token-should-not-be-sent");
    const unauthorizedSpy = vi.fn();
    const unsubscribe = registerUnauthorizedHandler(unauthorizedSpy);

    try {
      server.use(
        http.post("/api/v1/auth/login", async ({ request }) => {
          seenAuthHeader = request.headers.get("Authorization");
          seenBody = await request.json();
          return HttpResponse.json({
            access_token: "jwt-login-token",
            token_type: "bearer",
            expires_in: 1800,
          });
        })
      );

      const response = await login({
        email: "analyst@finsignal.test",
        password: "valid-password",
      });

      expect(seenAuthHeader).toBeNull();
      expect(seenBody).toEqual({
        email: "analyst@finsignal.test",
        password: "valid-password",
      });
      expect(response).toEqual({
        access_token: "jwt-login-token",
        token_type: "bearer",
        expires_in: 1800,
      });

      server.use(
        http.post("/api/v1/auth/login", () =>
          HttpResponse.json(
            {
              error: {
                code: "UNAUTHORIZED",
                message: "Invalid credentials.",
                details: {},
                request_id: "req-login-401",
              },
            },
            { status: 401 }
          )
        )
      );

      await expect(
        login({ email: "analyst@finsignal.test", password: "wrong" })
      ).rejects.toMatchObject({
        status: 401,
        code: "UNAUTHORIZED",
        requestId: "req-login-401",
      } satisfies Partial<ApiClientError>);

      expect(unauthorizedSpy).not.toHaveBeenCalled();
    } finally {
      unsubscribe();
    }
  });

  it("calls GET /api/v1/auth/me with Bearer token and returns all 5 UserResponse fields", async () => {
    let seenAuthHeader: string | null = null;
    setAccessToken("jwt-me-token");

    server.use(
      http.get("/api/v1/auth/me", ({ request }) => {
        seenAuthHeader = request.headers.get("Authorization");
        return HttpResponse.json({
          id: "00000000-0000-4000-8000-000000000101",
          email: "investigator@finsignal.test",
          role: "INVESTIGATOR",
          is_active: true,
          created_at: "2026-11-10T10:00:00Z",
        });
      })
    );

    const user = await getCurrentUser();
    expect(seenAuthHeader).toBe("Bearer jwt-me-token");
    expect(user).toEqual({
      id: "00000000-0000-4000-8000-000000000101",
      email: "investigator@finsignal.test",
      role: "INVESTIGATOR",
      is_active: true,
      created_at: "2026-11-10T10:00:00Z",
    });
  });

  it("calls POST /api/v1/auth/logout with Bearer token, returns 200 LogoutResponse, and skips 401 handler", async () => {
    let seenAuthHeader: string | null = null;
    const unauthorizedSpy = vi.fn();
    const unsubscribe = registerUnauthorizedHandler(unauthorizedSpy);
    setAccessToken("jwt-logout-token");

    try {
      server.use(
        http.post("/api/v1/auth/logout", ({ request }) => {
          seenAuthHeader = request.headers.get("Authorization");
          return HttpResponse.json({ message: "Successfully logged out." }, { status: 200 });
        })
      );

      const result = await logout();
      expect(seenAuthHeader).toBe("Bearer jwt-logout-token");
      expect(result).toEqual({ message: "Successfully logged out." });

      server.use(
        http.post("/api/v1/auth/logout", () =>
          HttpResponse.json(
            {
              error: {
                code: "UNAUTHORIZED",
                message: "Token expired.",
                details: {},
              },
            },
            { status: 401 }
          )
        )
      );

      await expect(logout()).rejects.toMatchObject({ status: 401, code: "UNAUTHORIZED" });
      expect(unauthorizedSpy).not.toHaveBeenCalled();
    } finally {
      unsubscribe();
    }
  });
});
