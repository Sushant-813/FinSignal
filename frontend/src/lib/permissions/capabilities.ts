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

export interface InvestigationCapabilityContext {
  readonly status: string;
  readonly assigned_to?: string | null | undefined;
}

/** Manual investigation case creation capability (`POST /api/v1/investigations`). */
export function canCreateInvestigation(user: AuthUser | null | undefined): boolean {
  return hasActiveRole(user, ["ADMIN", "ANALYST", "INVESTIGATOR"]);
}

/** General investigation mutation guard (returns false if case is RESOLVED or user is read-only). */
export function canModifyInvestigation(
  user: AuthUser | null | undefined,
  investigation: InvestigationCapabilityContext
): boolean {
  if (!user || user.is_active !== true || !isUserRole(user.role)) {
    return false;
  }
  if (investigation.status === "RESOLVED") {
    return false;
  }
  if (user.role === "ADMIN") {
    return true;
  }
  if (user.role === "INVESTIGATOR") {
    return investigation.assigned_to == null || investigation.assigned_to === user.id;
  }
  return false;
}

/** Self-assignment capability (Investigators claim unassigned cases; Admins claim cases not assigned to self). */
export function canSelfAssignInvestigation(
  user: AuthUser | null | undefined,
  investigation: InvestigationCapabilityContext
): boolean {
  if (!user || user.is_active !== true || !isUserRole(user.role)) {
    return false;
  }
  if (investigation.status === "RESOLVED") {
    return false;
  }
  if (user.role === "INVESTIGATOR") {
    return investigation.assigned_to == null;
  }
  if (user.role === "ADMIN") {
    return investigation.assigned_to !== user.id;
  }
  return false;
}

/** Self-unassignment capability (Users release cases currently assigned to themselves). */
export function canSelfUnassignInvestigation(
  user: AuthUser | null | undefined,
  investigation: InvestigationCapabilityContext
): boolean {
  if (!user || user.is_active !== true || !isUserRole(user.role)) {
    return false;
  }
  if (investigation.status === "RESOLVED") {
    return false;
  }
  if (user.role === "ADMIN" || user.role === "INVESTIGATOR") {
    return investigation.assigned_to === user.id;
  }
  return false;
}

/** Admin assignment & reassignment capability (Admin sets assigned_to to any user UUID or null). */
export function canAdminAssignInvestigation(
  user: AuthUser | null | undefined,
  investigation?: InvestigationCapabilityContext | undefined
): boolean {
  if (!hasActiveRole(user, ["ADMIN"])) {
    return false;
  }
  if (investigation?.status === "RESOLVED") {
    return false;
  }
  return true;
}

/** Priority update capability (`PATCH /api/v1/investigations/{id}`). */
export function canUpdateInvestigationPriority(
  user: AuthUser | null | undefined,
  investigation: InvestigationCapabilityContext
): boolean {
  if (!user || user.is_active !== true || !isUserRole(user.role)) {
    return false;
  }
  if (investigation.status === "RESOLVED") {
    return false;
  }
  if (user.role === "ADMIN") {
    return true;
  }
  if (user.role === "INVESTIGATOR") {
    return investigation.assigned_to === user.id;
  }
  return false;
}

/** Lifecycle transition capability: OPEN -> UNDER_REVIEW (`PATCH /api/v1/investigations/{id}`). */
export function canTransitionInvestigation(
  user: AuthUser | null | undefined,
  investigation: InvestigationCapabilityContext
): boolean {
  if (!user || user.is_active !== true || !isUserRole(user.role)) {
    return false;
  }
  if (investigation.status !== "OPEN") {
    return false;
  }
  if (user.role === "ADMIN") {
    return true;
  }
  if (user.role === "INVESTIGATOR") {
    return investigation.assigned_to === user.id;
  }
  return false;
}

/** Related transaction linking capability (`POST /api/v1/investigations/{id}/transactions`). */
export function canLinkInvestigationTransaction(
  user: AuthUser | null | undefined,
  investigation: InvestigationCapabilityContext
): boolean {
  if (!user || user.is_active !== true || !isUserRole(user.role)) {
    return false;
  }
  if (investigation.status === "RESOLVED") {
    return false;
  }
  if (user.role === "ADMIN") {
    return true;
  }
  if (user.role === "INVESTIGATOR") {
    return investigation.assigned_to === user.id;
  }
  return false;
}

/** Human investigation resolution capability (`POST /api/v1/investigations/{id}/resolve`). Case must be in UNDER_REVIEW. */
export function canResolveInvestigation(
  user: AuthUser | null | undefined,
  investigation: InvestigationCapabilityContext
): boolean {
  if (!user || user.is_active !== true || !isUserRole(user.role)) {
    return false;
  }
  if (investigation.status !== "UNDER_REVIEW") {
    return false;
  }
  if (user.role === "ADMIN") {
    return true;
  }
  if (user.role === "INVESTIGATOR") {
    return investigation.assigned_to === user.id;
  }
  return false;
}

export function getDefaultAuthenticatedRoute(user: AuthUser | null | undefined): string {
  return canAccessWorkspace(user) ? "/" : "/login";
}
