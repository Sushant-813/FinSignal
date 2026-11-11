/**
 * Lightweight singleton event bridge decoupling `apiRequest` (`401` detection)
 * from React `AuthProvider` state without creating circular module dependencies.
 */
export type UnauthorizedHandler = (sessionEpoch: number) => void;

const unauthorizedHandlers = new Set<UnauthorizedHandler>();

export function registerUnauthorizedHandler(handler: UnauthorizedHandler): () => void {
  unauthorizedHandlers.add(handler);
  return () => {
    unauthorizedHandlers.delete(handler);
  };
}

export function notifyUnauthorized(sessionEpoch: number): void {
  for (const handler of unauthorizedHandlers) {
    handler(sessionEpoch);
  }
}
