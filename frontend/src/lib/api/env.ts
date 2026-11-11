/**
 * Public frontend runtime configuration.
 * Only non-secret VITE_* variables are permitted (ADR-075, FRONTEND_SECURITY.md §8.3).
 */
export interface FrontendEnv {
  readonly apiBaseUrl: string;
  readonly appEnv: string;
}

function hasControlOrWhitespace(value: string): boolean {
  for (let i = 0; i < value.length; i += 1) {
    const code = value.charCodeAt(i);
    if (code <= 0x1f || code === 0x7f || /\s/.test(value[i] ?? "")) {
      return true;
    }
  }
  return false;
}

export function resolveApiBaseUrl(
  rawUrl: string | undefined,
  appEnv: string = (import.meta.env.VITE_APP_ENV ?? "development").trim() || "development"
): string {
  const trimmed = (rawUrl ?? "/api/v1").trim();
  if (!trimmed) {
    throw new Error("VITE_API_BASE_URL must not be empty when specified.");
  }

  if (hasControlOrWhitespace(trimmed)) {
    throw new Error("VITE_API_BASE_URL must not contain control characters or whitespace.");
  }

  if (trimmed.includes("?") || trimmed.includes("#")) {
    throw new Error("VITE_API_BASE_URL must not contain query strings or fragments.");
  }

  if (trimmed.startsWith("//")) {
    throw new Error("VITE_API_BASE_URL must not be protocol-relative.");
  }

  if (trimmed.startsWith("/")) {
    const normalized = trimmed.replace(/\/+$/, "");
    return normalized || "/";
  }

  let parsed: URL;
  try {
    parsed = new URL(trimmed);
  } catch {
    throw new Error(
      "VITE_API_BASE_URL must be a relative path starting with '/' or an HTTP(S) URL."
    );
  }

  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    throw new Error("VITE_API_BASE_URL must use http: or https: scheme.");
  }

  if (appEnv === "production" && parsed.protocol !== "https:") {
    throw new Error("VITE_API_BASE_URL must use https: in production.");
  }

  if (parsed.username || parsed.password) {
    throw new Error("VITE_API_BASE_URL must not include embedded credentials.");
  }

  const normalizedPath = parsed.pathname.replace(/\/+$/, "");
  return `${parsed.origin}${normalizedPath}`;
}

const resolvedAppEnv = (import.meta.env.VITE_APP_ENV ?? "development").trim() || "development";

export const frontendEnv: FrontendEnv = {
  apiBaseUrl: resolveApiBaseUrl(import.meta.env.VITE_API_BASE_URL, resolvedAppEnv),
  appEnv: resolvedAppEnv,
};
