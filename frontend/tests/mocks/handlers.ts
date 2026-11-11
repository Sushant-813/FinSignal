import type { RequestHandler } from "msw";

/**
 * Shared baseline MSW handlers.
 * Keep default handlers empty so unexpected network requests fail tests
 * via `onUnhandledRequest: "error"`. Register endpoint-specific handlers
 * locally inside the tests that require them using `server.use(...)`.
 */
export const handlers: RequestHandler[] = [];
