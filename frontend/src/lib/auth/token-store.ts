/**
 * In-memory JWT access-token store per ADR-075 (Option 1).
 * Tokens must never be persisted in localStorage, sessionStorage, cookies, or IndexedDB.
 */
let accessToken: string | null = null;

export function getAccessToken(): string | null {
  return accessToken;
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function clearAccessToken(): void {
  accessToken = null;
}
