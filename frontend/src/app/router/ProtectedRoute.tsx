import type { ReactNode } from "react";
import { Navigate, Outlet, useLocation } from "react-router";
import { useAuth } from "../../features/auth/hooks/useAuth.ts";
import { buildLoginRedirectPath, sanitizeRedirectPath } from "../../lib/auth/redirect.ts";
import { canAccessWorkspace } from "../../lib/permissions/capabilities.ts";
import { SessionLoadingView } from "./SessionLoadingView.tsx";

export interface ProtectedRouteProps {
  children?: ReactNode;
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { status, user, preserveRedirectOnUnauthenticated } = useAuth();
  const location = useLocation();

  if (status === "initializing") {
    return <SessionLoadingView />;
  }

  if (status !== "authenticated" || !canAccessWorkspace(user)) {
    if (!preserveRedirectOnUnauthenticated) {
      return <Navigate to="/login" replace />;
    }
    const requestedPath = `${location.pathname}${location.search}${location.hash}`;
    const safeTarget = sanitizeRedirectPath(requestedPath);
    return (
      <Navigate to={buildLoginRedirectPath(safeTarget)} replace state={{ from: safeTarget }} />
    );
  }

  return children ? <>{children}</> : <Outlet />;
}
