import { http, HttpResponse } from "msw";
import type { UserResponse } from "../../src/features/auth/api/auth-api.ts";
import type { AuthUser, UserRole } from "../../src/features/auth/types/auth.types.ts";
import { apiErrorFixtures } from "./api-errors.ts";

export function buildAuthUser(
  role: UserRole = "ANALYST",
  overrides: Partial<AuthUser> = {}
): AuthUser {
  const roleDefaults: Record<UserRole, { id: string; email: string }> = {
    ADMIN: {
      id: "00000000-0000-4000-8000-000000000001",
      email: "admin@finsignal.test",
    },
    ANALYST: {
      id: "00000000-0000-4000-8000-000000000002",
      email: "analyst@finsignal.test",
    },
    INVESTIGATOR: {
      id: "00000000-0000-4000-8000-000000000003",
      email: "investigator@finsignal.test",
    },
  };

  return {
    id: roleDefaults[role].id,
    email: roleDefaults[role].email,
    role,
    is_active: true,
    created_at: "2026-11-10T10:00:00Z",
    ...overrides,
  };
}

export function createAuthHandlers(
  user: UserResponse = buildAuthUser("ANALYST"),
  options: { accessToken?: string; expiresIn?: number } = {}
) {
  const accessToken = options.accessToken ?? `synthetic-jwt-${user.role.toLowerCase()}`;
  const expiresIn = options.expiresIn ?? 1800;

  return [
    http.post("/api/v1/auth/login", () =>
      HttpResponse.json({
        access_token: accessToken,
        token_type: "bearer",
        expires_in: expiresIn,
      })
    ),
    http.get("/api/v1/auth/me", ({ request }) => {
      if (!request.headers.get("Authorization")?.startsWith("Bearer ")) {
        return apiErrorFixtures.unauthorized();
      }
      return HttpResponse.json(user);
    }),
    http.post("/api/v1/auth/logout", ({ request }) => {
      if (!request.headers.get("Authorization")?.startsWith("Bearer ")) {
        return apiErrorFixtures.unauthorized();
      }
      return HttpResponse.json({ message: "Successfully logged out." }, { status: 200 });
    }),
  ];
}
