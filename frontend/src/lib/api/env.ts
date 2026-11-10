/**
 * Public frontend runtime configuration.
 * Only non-secret VITE_* variables are permitted (ADR-075, FRONTEND_SECURITY.md §8.3).
 */
export interface FrontendEnv {
  readonly apiBaseUrl: string;
  readonly appEnv: string;
}

export function resolveApiBaseUrl(rawUrl: string | undefined): string {
  const trimmed = (rawUrl ?? "/api/v1").trim();
  if (!trimmed) {
    throw new Error("VITE_API_BASE_URL must not be empty when specified.");
  }
  return trimmed.endsWith("/") ? trimmed.slice(0, -1) : trimmed;
}

export const frontendEnv: FrontendEnv = {
  apiBaseUrl: resolveApiBaseUrl(import.meta.env.VITE_API_BASE_URL),
  appEnv: (import.meta.env.VITE_APP_ENV ?? "development").trim() || "development",
};
