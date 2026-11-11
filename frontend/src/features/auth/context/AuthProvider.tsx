import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { ApiClientError } from "../../../lib/api/errors.ts";
import { registerUnauthorizedHandler } from "../../../lib/auth/session-events.ts";
import {
  clearAccessToken,
  getAccessToken,
  getSessionEpoch,
  setAccessToken,
} from "../../../lib/auth/token-store.ts";
import { getCurrentUser, login, type LoginRequest } from "../api/auth-api.ts";
import {
  parseAuthUser,
  type AuthStatus,
  type AuthUser,
  type SessionNotice,
} from "../types/auth.types.ts";
import { AuthContext, type AuthContextValue } from "./AuthContext.ts";

export interface AuthProviderProps {
  children: ReactNode;
}

const MAX_TIMEOUT_MS = 2_147_483_647;

function createSupersededAuthError(): DOMException {
  return new DOMException("Authentication attempt was superseded.", "AbortError");
}

export function AuthProvider({ children }: AuthProviderProps) {
  const queryClient = useQueryClient();

  const [status, setStatus] = useState<AuthStatus>("initializing");
  const [user, setUser] = useState<AuthUser | null>(null);
  const [sessionNotice, setSessionNotice] = useState<SessionNotice | null>(null);
  const [preserveRedirectOnUnauthenticated, setPreserveRedirectOnUnauthenticated] = useState(true);

  const statusRef = useRef<AuthStatus>("initializing");
  const authAttemptRef = useRef(0);
  const authAbortRef = useRef<AbortController | null>(null);
  const expiryTimerRef = useRef<ReturnType<typeof globalThis.setTimeout> | null>(null);

  const clearExpiryTimer = useCallback(() => {
    if (expiryTimerRef.current !== null) {
      globalThis.clearTimeout(expiryTimerRef.current);
      expiryTimerRef.current = null;
    }
  }, []);

  const abortPendingAuth = useCallback(() => {
    if (authAbortRef.current !== null) {
      authAbortRef.current.abort();
      authAbortRef.current = null;
    }
  }, []);

  const terminateSession = useCallback(
    (notice: SessionNotice | null, preserveRedirect = true) => {
      authAttemptRef.current += 1;
      clearExpiryTimer();
      abortPendingAuth();
      clearAccessToken();

      statusRef.current = "unauthenticated";
      setUser(null);
      setStatus("unauthenticated");
      setSessionNotice(notice);
      setPreserveRedirectOnUnauthenticated(preserveRedirect);

      void queryClient.cancelQueries();
      queryClient.clear();
    },
    [abortPendingAuth, clearExpiryTimer, queryClient]
  );

  const scheduleExpiryTimer = useCallback(
    (expiresInSeconds: number, expectedEpoch: number) => {
      clearExpiryTimer();
      const timeoutMs = Math.min(Math.max(1, Math.floor(expiresInSeconds)) * 1000, MAX_TIMEOUT_MS);

      expiryTimerRef.current = globalThis.setTimeout(() => {
        if (getSessionEpoch() !== expectedEpoch || statusRef.current !== "authenticated") {
          return;
        }
        terminateSession({
          reason: "expired",
          message: "Your session has expired. Please sign in again.",
        });
      }, timeoutMs);
    },
    [clearExpiryTimer, terminateSession]
  );

  useEffect(() => {
    return registerUnauthorizedHandler((requestEpoch) => {
      if (statusRef.current !== "authenticated" || requestEpoch !== getSessionEpoch()) {
        return;
      }
      terminateSession({
        reason: "expired",
        message: "Your session has expired or is no longer valid. Please sign in again.",
      });
    });
  }, [terminateSession]);

  useEffect(() => {
    authAttemptRef.current += 1;
    const attemptId = authAttemptRef.current;

    const existingToken = getAccessToken();
    if (!existingToken) {
      statusRef.current = "unauthenticated";
      setUser(null);
      setStatus("unauthenticated");
      return;
    }

    const attemptEpoch = getSessionEpoch();
    const controller = new AbortController();
    authAbortRef.current = controller;
    statusRef.current = "initializing";
    setStatus("initializing");

    void (async () => {
      try {
        const me = await getCurrentUser(controller.signal);
        if (
          controller.signal.aborted ||
          attemptId !== authAttemptRef.current ||
          attemptEpoch !== getSessionEpoch()
        ) {
          return;
        }

        const validatedUser = parseAuthUser(me);
        if (!validatedUser) {
          terminateSession(null);
          return;
        }

        void queryClient.cancelQueries();
        queryClient.clear();
        statusRef.current = "authenticated";
        setUser(validatedUser);
        setStatus("authenticated");
        setSessionNotice(null);
      } catch {
        if (controller.signal.aborted) {
          return;
        }
        if (attemptId === authAttemptRef.current && attemptEpoch === getSessionEpoch()) {
          terminateSession(null);
        }
      }
    })();

    return () => {
      controller.abort();
      if (authAbortRef.current === controller) {
        authAbortRef.current = null;
      }
      clearExpiryTimer();
    };
  }, [clearExpiryTimer, queryClient, terminateSession]);

  const signIn = useCallback(
    async (credentials: LoginRequest): Promise<AuthUser> => {
      authAttemptRef.current += 1;
      const attemptId = authAttemptRef.current;
      clearExpiryTimer();
      abortPendingAuth();

      const controller = new AbortController();
      authAbortRef.current = controller;

      try {
        // Steps 1-3: authenticate credentials and verify attempt is still current before setting token.
        const tokenResp = await login(credentials, controller.signal);
        if (controller.signal.aborted || attemptId !== authAttemptRef.current) {
          throw createSupersededAuthError();
        }

        if (
          typeof tokenResp.access_token !== "string" ||
          tokenResp.access_token.trim() === "" ||
          typeof tokenResp.expires_in !== "number" ||
          !Number.isFinite(tokenResp.expires_in) ||
          tokenResp.expires_in < 1
        ) {
          throw new ApiClientError({
            status: 500,
            code: "INVALID_RESPONSE",
            message: "Received an invalid authentication token response from the server.",
          });
        }

        // Steps 4-6: set in-memory token, capture the new epoch, and validate via /auth/me.
        setAccessToken(tokenResp.access_token);
        const attemptEpoch = getSessionEpoch();

        let me;
        try {
          me = await getCurrentUser(controller.signal);
        } catch (meError: unknown) {
          if (controller.signal.aborted || attemptId !== authAttemptRef.current) {
            if (attemptEpoch === getSessionEpoch()) {
              clearAccessToken();
            }
            throw createSupersededAuthError();
          }
          if (attemptEpoch === getSessionEpoch()) {
            terminateSession(null);
          }
          throw meError;
        }

        // Step 7: confirm both attempt identity and token generation before committing state.
        if (
          controller.signal.aborted ||
          attemptId !== authAttemptRef.current ||
          attemptEpoch !== getSessionEpoch()
        ) {
          if (attemptEpoch === getSessionEpoch()) {
            clearAccessToken();
          }
          throw createSupersededAuthError();
        }

        const validatedUser = parseAuthUser(me);
        if (!validatedUser) {
          terminateSession(null);
          throw new ApiClientError({
            status: 403,
            code: "INVALID_ACCOUNT_STATE",
            message: "Your account is inactive or lacks an authorized workspace role.",
          });
        }

        // Step 8: evict any pre-login query state, schedule backend expires_in timer, commit user.
        void queryClient.cancelQueries();
        queryClient.clear();
        statusRef.current = "authenticated";
        setUser(validatedUser);
        setStatus("authenticated");
        setSessionNotice(null);
        setPreserveRedirectOnUnauthenticated(true);
        scheduleExpiryTimer(tokenResp.expires_in, attemptEpoch);

        return validatedUser;
      } finally {
        if (authAbortRef.current === controller) {
          authAbortRef.current = null;
        }
      }
    },
    [abortPendingAuth, clearExpiryTimer, queryClient, scheduleExpiryTimer, terminateSession]
  );

  // Local-only logout (Option B per F2 specification; does not claim server-side JWT revocation).
  const signOut = useCallback(() => {
    terminateSession(null, false);
  }, [terminateSession]);

  const clearSessionNotice = useCallback(() => {
    setSessionNotice(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      sessionNotice,
      preserveRedirectOnUnauthenticated,
      signIn,
      signOut,
      clearSessionNotice,
    }),
    [
      clearSessionNotice,
      preserveRedirectOnUnauthenticated,
      sessionNotice,
      signIn,
      signOut,
      status,
      user,
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
