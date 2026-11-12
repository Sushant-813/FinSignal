import { isUserRole, type AuthUser, type UserRole } from "../../features/auth/types/auth.types.ts";

/**
 * Centralized F2 capability helpers matching verified backend authentication/navigation policy.
 * Always fail closed when user is missing, inactive, or carries an unknown role string.
 *
 * Frontend UI visibility and route guards are UX policy only; backend `require_roles`
 * enforcement remains authoritative on every API request.
 */
function hasActiveRole(
  user: AuthUser | null | undefined,
  allowedRoles: readonly UserRole[]
): boolean {
  if (!user || user.is_active !== true || !isUserRole(user.role)) {
    return false;
  }
  return allowedRoles.includes(user.role);
}

export function canAccessWorkspace(user: AuthUser | null | undefined): boolean {
  return hasActiveRole(user, ["ADMIN", "ANALYST", "INVESTIGATOR"]);
}

export function canViewTransactions(user: AuthUser | null | undefined): boolean {
  return hasActiveRole(user, ["ADMIN", "ANALYST", "INVESTIGATOR"]);
}

export function canViewAnalytics(user: AuthUser | null | undefined): boolean {
  return hasActiveRole(user, ["ADMIN", "ANALYST", "INVESTIGATOR"]);
}

export function canViewInvestigations(user: AuthUser | null | undefined): boolean {
  return hasActiveRole(user, ["ADMIN", "ANALYST", "INVESTIGATOR"]);
}

/** Read-only dataset import history visibility (`GET /api/v1/datasets/imports`). */
export function canViewDatasetImports(user: AuthUser | null | undefined): boolean {
  return hasActiveRole(user, ["ADMIN", "ANALYST", "INVESTIGATOR"]);
}

/** Dataset upload and import recovery capability (`POST /api/v1/datasets/imports`, `/recover`). */
export function canManageDatasets(user: AuthUser | null | undefined): boolean {
  return hasActiveRole(user, ["ADMIN", "ANALYST"]);
}

/** On-demand transaction risk scoring using the default ACTIVE model (`POST /api/v1/transactions/{id}/risk/analyze`). */
export function canAnalyzeActiveRisk(user: AuthUser | null | undefined): boolean {
  return hasActiveRole(user, ["ADMIN", "ANALYST", "INVESTIGATOR"]);
}

/** Explicit VALIDATED model risk analysis capability (Admin only). */
export function canAnalyzeValidatedRisk(user: AuthUser | null | undefined): boolean {
  return hasActiveRole(user, ["ADMIN"]);
}

export function getDefaultAuthenticatedRoute(user: AuthUser | null | undefined): string {
  return canAccessWorkspace(user) ? "/" : "/login";
}
