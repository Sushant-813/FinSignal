import type { ReactNode } from "react";
import { Navigate, Outlet, useLocation, useSearchParams } from "react-router";
import { useAuth } from "../../features/auth/hooks/useAuth.ts";
import { sanitizeRedirectPath } from "../../lib/auth/redirect.ts";
import {
  canAccessWorkspace,
  getDefaultAuthenticatedRoute,
} from "../../lib/permissions/capabilities.ts";
import { SessionLoadingView } from "./SessionLoadingView.tsx";

export interface PublicOnlyRouteProps {
  children?: ReactNode;
}

export function PublicOnlyRoute({ children }: PublicOnlyRouteProps) {
  const { status, user } = useAuth();
  const location = useLocation();
  const [searchParams] = useSearchParams();

  if (status === "initializing") {
    return <SessionLoadingView />;
  }

  if (status === "authenticated" && canAccessWorkspace(user)) {
    const queryRedirect = searchParams.get("redirect");
    const stateFrom =
      typeof location.state === "object" &&
      location.state !== null &&
      "from" in location.state &&
      typeof (location.state as { from?: unknown }).from === "string"
        ? (location.state as { from: string }).from
        : null;

    const candidate = queryRedirect ?? stateFrom ?? getDefaultAuthenticatedRoute(user);
    return <Navigate to={sanitizeRedirectPath(candidate)} replace />;
  }

  return children ? <>{children}</> : <Outlet />;
}
