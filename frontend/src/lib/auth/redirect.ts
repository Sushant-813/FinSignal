const SYNTHETIC_ORIGIN = "https://finsignal.local";
const SCHEME_PREFIX = /^[a-zA-Z][a-zA-Z\d+\-.]*:/;
const SENSITIVE_QUERY_KEYS = new Set(["token", "access_token", "password", "secret"]);

function hasControlCharacter(value: string): boolean {
  for (let i = 0; i < value.length; i += 1) {
    const code = value.charCodeAt(i);
    if (code <= 0x1f || code === 0x7f) {
      return true;
    }
  }
  return false;
}

/**
 * Validates post-login destination targets and allows only safe internal app routes.
 * External URLs, protocol-relative URLs, backslashes, non-path schemes, control characters,
 * `/login` redirect loops, and sensitive query parameters are normalized back to `/`.
 */
export function sanitizeRedirectPath(raw: string | null | undefined): string {
  if (!raw) {
    return "/";
  }

  const trimmed = raw.trim();
  if (!trimmed || hasControlCharacter(trimmed) || trimmed.includes("\\")) {
    return "/";
  }

  if (!trimmed.startsWith("/") || trimmed.startsWith("//") || SCHEME_PREFIX.test(trimmed)) {
    return "/";
  }

  try {
    const parsed = new URL(trimmed, SYNTHETIC_ORIGIN);
    if (
      parsed.origin !== SYNTHETIC_ORIGIN ||
      !parsed.pathname.startsWith("/") ||
      parsed.pathname.startsWith("//")
    ) {
      return "/";
    }

    if (parsed.pathname === "/login" || parsed.pathname.startsWith("/login/")) {
      return "/";
    }

    for (const key of parsed.searchParams.keys()) {
      if (SENSITIVE_QUERY_KEYS.has(key.toLowerCase())) {
        return "/";
      }
    }

    return `${parsed.pathname}${parsed.search}${parsed.hash}`;
  } catch {
    return "/";
  }
}

export function buildLoginRedirectPath(rawTarget: string | null | undefined): string {
  const safeTarget = sanitizeRedirectPath(rawTarget);
  return safeTarget === "/" ? "/login" : `/login?redirect=${encodeURIComponent(safeTarget)}`;
}
