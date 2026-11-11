import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeAll } from "vitest";
import { clearAccessToken } from "../src/lib/auth/token-store.ts";
import { server } from "./mocks/server.ts";

if (typeof globalThis.ResizeObserver === "undefined") {
  globalThis.ResizeObserver = class ResizeObserver {
    observe(): void {}
    unobserve(): void {}
    disconnect(): void {}
  };
}

if (typeof Element !== "undefined") {
  if (typeof Element.prototype.hasPointerCapture === "undefined") {
    Element.prototype.hasPointerCapture = () => false;
  }
  if (typeof Element.prototype.releasePointerCapture === "undefined") {
    Element.prototype.releasePointerCapture = () => {};
  }
  if (typeof Element.prototype.scrollIntoView === "undefined") {
    Element.prototype.scrollIntoView = () => {};
  }
}

// Guard against Node 24 undici.Request vs jsdom AbortSignal realm mismatch in React Router v7
if (
  typeof globalThis.Request !== "undefined" &&
  typeof globalThis.AbortController !== "undefined"
) {
  try {
    new globalThis.Request("http://localhost", { signal: new globalThis.AbortController().signal });
  } catch {
    const NativeRequest = globalThis.Request;
    const nodeProcess = (
      globalThis as {
        process?: {
          getBuiltinModule?: (
            id: string
          ) => { runInThisContext?: (code: string) => unknown } | undefined;
        };
      }
    ).process;
    const NativeAbortController = nodeProcess
      ?.getBuiltinModule?.("node:vm")
      ?.runInThisContext?.("AbortController") as typeof AbortController | undefined;
    const NativeAbortSignal = Object.getPrototypeOf(new NativeRequest("http://localhost").signal)
      .constructor as typeof AbortSignal;
    globalThis.Request = class PatchedRequest extends NativeRequest {
      constructor(input: RequestInfo | URL, init?: RequestInit) {
        if (init?.signal) {
          try {
            new NativeRequest("http://localhost", { signal: init.signal });
          } catch {
            const rest: RequestInit = { ...init };
            const foreignSignal = init.signal;
            if (foreignSignal.aborted) {
              rest.signal = NativeAbortSignal.abort(foreignSignal.reason);
            } else if (NativeAbortController) {
              const nativeController = new NativeAbortController();
              const forwardAbort = () => {
                nativeController.abort(foreignSignal.reason);
              };
              foreignSignal.addEventListener("abort", forwardAbort, { once: true });
              nativeController.signal.addEventListener(
                "abort",
                () => {
                  foreignSignal.removeEventListener("abort", forwardAbort);
                },
                { once: true }
              );
              rest.signal = nativeController.signal;
            } else {
              delete rest.signal;
            }
            super(input, rest);
            return;
          }
        }
        super(input, init);
      }
    };
  }
}

beforeAll(() => {
  server.listen({ onUnhandledRequest: "error" });
});

afterEach(() => {
  cleanup();
  server.resetHandlers();
  clearAccessToken();
});

afterAll(() => {
  server.close();
});
