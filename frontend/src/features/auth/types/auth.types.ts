import type { UserResponse } from "../api/auth-api.ts";

export const USER_ROLES = ["ADMIN", "ANALYST", "INVESTIGATOR"] as const;

export type UserRole = (typeof USER_ROLES)[number];

export function isUserRole(value: unknown): value is UserRole {
  return typeof value === "string" && (USER_ROLES as readonly string[]).includes(value);
}

export type AuthUser = Omit<UserResponse, "role"> & {
  readonly role: UserRole;
};

export type AuthStatus = "initializing" | "authenticated" | "unauthenticated";

export interface SessionNotice {
  readonly reason: "expired";
  readonly message: string;
}

export function parseAuthUser(candidate: UserResponse): AuthUser | null {
  if (!candidate || typeof candidate.id !== "string" || typeof candidate.email !== "string") {
    return null;
  }
  if (candidate.is_active !== true || !isUserRole(candidate.role)) {
    return null;
  }
  return {
    id: candidate.id,
    email: candidate.email,
    role: candidate.role,
    is_active: true,
    created_at: candidate.created_at,
  };
}
