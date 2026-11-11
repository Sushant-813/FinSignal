import type { components } from "../../../api/generated/schema.ts";
import { apiRequest } from "../../../lib/api/client.ts";

export type LoginRequest = components["schemas"]["LoginRequest"];
export type TokenResponse = components["schemas"]["TokenResponse"];
export type UserResponse = components["schemas"]["UserResponse"];
export type LogoutResponse = components["schemas"]["LogoutResponse"];

export function login(credentials: LoginRequest, signal?: AbortSignal): Promise<TokenResponse> {
  return apiRequest<TokenResponse>("/auth/login", {
    method: "POST",
    body: credentials,
    authMode: "none",
    skipUnauthorizedHandler: true,
    signal,
  });
}

export function getCurrentUser(signal?: AbortSignal): Promise<UserResponse> {
  return apiRequest<UserResponse>("/auth/me", {
    method: "GET",
    signal,
  });
}

export function logout(signal?: AbortSignal): Promise<LogoutResponse> {
  return apiRequest<LogoutResponse>("/auth/logout", {
    method: "POST",
    skipUnauthorizedHandler: true,
    signal,
  });
}
