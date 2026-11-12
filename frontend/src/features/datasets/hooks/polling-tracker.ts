const MAX_POLLING_DURATION_MS = 5 * 60 * 1000; // 5 minutes

// Import-scoped tracker surviving rerenders and navigation within SPA session
const importPollingTracker = new Map<string, number>();

export function shouldPollImport(id: string, status: string | undefined): boolean {
  if (status !== "PENDING" && status !== "PROCESSING") {
    importPollingTracker.delete(id);
    return false;
  }

  const now = Date.now();
  const firstObserved = importPollingTracker.get(id);

  if (firstObserved === undefined) {
    importPollingTracker.set(id, now);
    return true;
  }

  if (now - firstObserved >= MAX_POLLING_DURATION_MS) {
    return false;
  }

  return true;
}

export function isPollingCutoffReached(id: string, status: string | undefined): boolean {
  if (status !== "PENDING" && status !== "PROCESSING") {
    return false;
  }
  const firstObserved = importPollingTracker.get(id);
  if (firstObserved === undefined) {
    return false;
  }
  return Date.now() - firstObserved >= MAX_POLLING_DURATION_MS;
}

export function resetImportPolling(id: string): void {
  importPollingTracker.delete(id);
}

export function clearAllImportPolling(): void {
  importPollingTracker.clear();
}
