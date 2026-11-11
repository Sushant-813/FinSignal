import { createContext } from "react";
import type { LoginRequest } from "../api/auth-api.ts";
import type { AuthStatus, AuthUser, SessionNotice } from "../types/auth.types.ts";

export interface AuthContextValue {
  readonly status: AuthStatus;
  readonly user: AuthUser | null;
  readonly sessionNotice: SessionNotice | null;
  readonly preserveRedirectOnUnauthenticated: boolean;
  readonly signIn: (credentials: LoginRequest) => Promise<AuthUser>;
  readonly signOut: () => void;
  readonly clearSessionNotice: () => void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);
