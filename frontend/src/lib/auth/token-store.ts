/**
 * In-memory JWT access-token store per ADR-075 (Option 1).
 * Tokens must never be persisted in localStorage, sessionStorage, cookies, or IndexedDB.
 *
 * `sessionEpoch` identifies the current in-memory token generation and increments
 * monotonically on every token write or clear so stale `/auth/me` completions and
 * lagging `401` callbacks from earlier tokens cannot corrupt a newer session.
 */
let accessToken: string | null = null;
let sessionEpoch = 0;

export function getAccessToken(): string | null {
  return accessToken;
}

export function getSessionEpoch(): number {
  return sessionEpoch;
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
  sessionEpoch += 1;
}

export function clearAccessToken(): void {
  accessToken = null;
  sessionEpoch += 1;
}
