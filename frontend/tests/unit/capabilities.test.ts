import { describe, expect, it } from "vitest";
import { isUserRole, type AuthUser } from "../../src/features/auth/types/auth.types.ts";
import {
  canAccessWorkspace,
  canAdminAssignInvestigation,
  canAnalyzeActiveRisk,
  canAnalyzeValidatedRisk,
  canCreateInvestigation,
  canLinkInvestigationTransaction,
  canManageDatasets,
  canModifyInvestigation,
  canResolveInvestigation,
  canSelfAssignInvestigation,
  canSelfUnassignInvestigation,
  canTransitionInvestigation,
  canUpdateInvestigationPriority,
  canViewAnalytics,
  canViewDatasetImports,
  canViewInvestigations,
  canViewTransactions,
  getDefaultAuthenticatedRoute,
} from "../../src/lib/permissions/capabilities.ts";
import { buildAuthUser } from "../fixtures/auth.ts";

describe("F2 centralized role capabilities (fail-closed)", () => {
  it("validates recognized backend roles and rejects unknown strings at runtime", () => {
    expect(isUserRole("ADMIN")).toBe(true);
    expect(isUserRole("ANALYST")).toBe(true);
    expect(isUserRole("INVESTIGATOR")).toBe(true);
    expect(isUserRole("admin")).toBe(false);
    expect(isUserRole("SUPERUSER")).toBe(false);
    expect(isUserRole("")).toBe(false);
    expect(isUserRole(null)).toBe(false);
    expect(isUserRole(123)).toBe(false);
  });

  it("distinguishes read-only dataset import viewing from dataset management per role", () => {
    const admin = buildAuthUser("ADMIN");
    const analyst = buildAuthUser("ANALYST");
    const investigator = buildAuthUser("INVESTIGATOR");

    for (const user of [admin, analyst, investigator]) {
      expect(canAccessWorkspace(user)).toBe(true);
      expect(canViewTransactions(user)).toBe(true);
      expect(canViewAnalytics(user)).toBe(true);
      expect(canViewInvestigations(user)).toBe(true);
      expect(canViewDatasetImports(user)).toBe(true);
      expect(getDefaultAuthenticatedRoute(user)).toBe("/");
    }

    expect(canManageDatasets(admin)).toBe(true);
    expect(canManageDatasets(analyst)).toBe(true);
    expect(canManageDatasets(investigator)).toBe(false);

    for (const user of [admin, analyst, investigator]) {
      expect(canAnalyzeActiveRisk(user)).toBe(true);
    }
    expect(canAnalyzeValidatedRisk(admin)).toBe(true);
    expect(canAnalyzeValidatedRisk(analyst)).toBe(false);
    expect(canAnalyzeValidatedRisk(investigator)).toBe(false);
  });

  it("fails closed when user is null, inactive, or carries an unapproved role string", () => {
    const inactiveAdmin = buildAuthUser("ADMIN", { is_active: false });
    const unknownRoleUser = {
      ...buildAuthUser("ANALYST"),
      role: "UNKNOWN_ROLE",
    } as unknown as AuthUser;

    for (const candidate of [null, undefined, inactiveAdmin, unknownRoleUser]) {
      expect(canAccessWorkspace(candidate)).toBe(false);
      expect(canViewTransactions(candidate)).toBe(false);
      expect(canViewAnalytics(candidate)).toBe(false);
      expect(canViewInvestigations(candidate)).toBe(false);
      expect(canViewDatasetImports(candidate)).toBe(false);
      expect(canManageDatasets(candidate)).toBe(false);
      expect(canAnalyzeActiveRisk(candidate)).toBe(false);
      expect(canAnalyzeValidatedRisk(candidate)).toBe(false);
      expect(getDefaultAuthenticatedRoute(candidate)).toBe("/login");
    }
  });

  describe("F5 investigation role & lifecycle capabilities", () => {
    const admin = buildAuthUser("ADMIN", { id: "admin-id" });
    const investigator = buildAuthUser("INVESTIGATOR", { id: "investigator-id" });
    const peerInvestigator = buildAuthUser("INVESTIGATOR", { id: "peer-investigator-id" });
    const analyst = buildAuthUser("ANALYST", { id: "analyst-id" });
    const inactiveInvestigator = buildAuthUser("INVESTIGATOR", {
      id: "inactive-inv-id",
      is_active: false,
    });

    const openUnassigned = { status: "OPEN", assigned_to: null };
    const openAssignedToSelf = { status: "OPEN", assigned_to: investigator.id };
    const openAssignedToPeer = { status: "OPEN", assigned_to: peerInvestigator.id };
    const underReviewSelf = { status: "UNDER_REVIEW", assigned_to: investigator.id };
    const underReviewPeer = { status: "UNDER_REVIEW", assigned_to: peerInvestigator.id };
    const resolvedCase = { status: "RESOLVED", assigned_to: investigator.id };

    it("allows case creation for all active roles and fails closed for inactive or missing user", () => {
      expect(canCreateInvestigation(admin)).toBe(true);
      expect(canCreateInvestigation(investigator)).toBe(true);
      expect(canCreateInvestigation(analyst)).toBe(true);

      expect(canCreateInvestigation(inactiveInvestigator)).toBe(false);
      expect(canCreateInvestigation(null)).toBe(false);
      expect(canCreateInvestigation(undefined)).toBe(false);
    });

    it("verifies INVESTIGATOR self-assignment and self-unassignment boundaries", () => {
      // Can self-assign only unassigned non-resolved cases
      expect(canSelfAssignInvestigation(investigator, openUnassigned)).toBe(true);
      expect(canSelfAssignInvestigation(investigator, openAssignedToSelf)).toBe(false);
      expect(canSelfAssignInvestigation(investigator, openAssignedToPeer)).toBe(false);
      expect(canSelfAssignInvestigation(investigator, resolvedCase)).toBe(false);

      // Can self-unassign only cases assigned to themselves
      expect(canSelfUnassignInvestigation(investigator, openUnassigned)).toBe(false);
      expect(canSelfUnassignInvestigation(investigator, openAssignedToSelf)).toBe(true);
      expect(canSelfUnassignInvestigation(investigator, openAssignedToPeer)).toBe(false);
      expect(canSelfUnassignInvestigation(investigator, resolvedCase)).toBe(false);

      // Cannot admin-assign
      expect(canAdminAssignInvestigation(investigator, openUnassigned)).toBe(false);
    });

    it("verifies INVESTIGATOR mutation and lifecycle rules require assignment", () => {
      // Priority update
      expect(canUpdateInvestigationPriority(investigator, openAssignedToSelf)).toBe(true);
      expect(canUpdateInvestigationPriority(investigator, openAssignedToPeer)).toBe(false);
      expect(canUpdateInvestigationPriority(investigator, openUnassigned)).toBe(false);
      expect(canUpdateInvestigationPriority(investigator, resolvedCase)).toBe(false);

      // Lifecycle OPEN -> UNDER_REVIEW
      expect(canTransitionInvestigation(investigator, openAssignedToSelf)).toBe(true);
      expect(canTransitionInvestigation(investigator, openAssignedToPeer)).toBe(false);
      expect(canTransitionInvestigation(investigator, underReviewSelf)).toBe(false); // Already under review
      expect(canTransitionInvestigation(investigator, resolvedCase)).toBe(false);

      // Related transaction linking
      expect(canLinkInvestigationTransaction(investigator, openAssignedToSelf)).toBe(true);
      expect(canLinkInvestigationTransaction(investigator, underReviewSelf)).toBe(true);
      expect(canLinkInvestigationTransaction(investigator, openAssignedToPeer)).toBe(false);
      expect(canLinkInvestigationTransaction(investigator, resolvedCase)).toBe(false);

      // Case resolution requires UNDER_REVIEW state and assignment
      expect(canResolveInvestigation(investigator, openAssignedToSelf)).toBe(false); // OPEN, not UNDER_REVIEW
      expect(canResolveInvestigation(investigator, underReviewSelf)).toBe(true);
      expect(canResolveInvestigation(investigator, underReviewPeer)).toBe(false); // Peer's case
      expect(canResolveInvestigation(investigator, resolvedCase)).toBe(false); // Already resolved
    });

    it("verifies ADMIN has global assignment and lifecycle authority on active cases", () => {
      expect(canAdminAssignInvestigation(admin, openUnassigned)).toBe(true);
      expect(canAdminAssignInvestigation(admin, openAssignedToPeer)).toBe(true);
      expect(canAdminAssignInvestigation(admin, resolvedCase)).toBe(false); // Resolved cases immutable

      expect(canUpdateInvestigationPriority(admin, openAssignedToPeer)).toBe(true);
      expect(canTransitionInvestigation(admin, openAssignedToPeer)).toBe(true);
      expect(canLinkInvestigationTransaction(admin, openAssignedToPeer)).toBe(true);
      expect(canResolveInvestigation(admin, underReviewPeer)).toBe(true);
      expect(canResolveInvestigation(admin, openAssignedToPeer)).toBe(false); // Must be UNDER_REVIEW
      expect(canResolveInvestigation(admin, resolvedCase)).toBe(false);
    });

    it("verifies ANALYST is strictly read-only on existing cases", () => {
      expect(canViewInvestigations(analyst)).toBe(true);
      expect(canCreateInvestigation(analyst)).toBe(true);

      expect(canModifyInvestigation(analyst, openUnassigned)).toBe(false);
      expect(canSelfAssignInvestigation(analyst, openUnassigned)).toBe(false);
      expect(canSelfUnassignInvestigation(analyst, openAssignedToSelf)).toBe(false);
      expect(canAdminAssignInvestigation(analyst, openUnassigned)).toBe(false);
      expect(canUpdateInvestigationPriority(analyst, openUnassigned)).toBe(false);
      expect(canTransitionInvestigation(analyst, openUnassigned)).toBe(false);
      expect(canLinkInvestigationTransaction(analyst, openUnassigned)).toBe(false);
      expect(canResolveInvestigation(analyst, underReviewSelf)).toBe(false);
    });

    it("enforces terminal immutability across all roles for RESOLVED investigations", () => {
      for (const user of [admin, investigator, analyst]) {
        expect(canModifyInvestigation(user, resolvedCase)).toBe(false);
        expect(canSelfAssignInvestigation(user, resolvedCase)).toBe(false);
        expect(canSelfUnassignInvestigation(user, resolvedCase)).toBe(false);
        expect(canAdminAssignInvestigation(user, resolvedCase)).toBe(false);
        expect(canUpdateInvestigationPriority(user, resolvedCase)).toBe(false);
        expect(canTransitionInvestigation(user, resolvedCase)).toBe(false);
        expect(canLinkInvestigationTransaction(user, resolvedCase)).toBe(false);
        expect(canResolveInvestigation(user, resolvedCase)).toBe(false);
      }
    });

    it("fails closed for null, undefined, or inactive users across all helpers", () => {
      for (const candidate of [null, undefined, inactiveInvestigator]) {
        expect(canCreateInvestigation(candidate)).toBe(false);
        expect(canModifyInvestigation(candidate, openUnassigned)).toBe(false);
        expect(canSelfAssignInvestigation(candidate, openUnassigned)).toBe(false);
        expect(canSelfUnassignInvestigation(candidate, openAssignedToSelf)).toBe(false);
        expect(canAdminAssignInvestigation(candidate, openUnassigned)).toBe(false);
        expect(canUpdateInvestigationPriority(candidate, openAssignedToSelf)).toBe(false);
        expect(canTransitionInvestigation(candidate, openAssignedToSelf)).toBe(false);
        expect(canLinkInvestigationTransaction(candidate, openAssignedToSelf)).toBe(false);
        expect(canResolveInvestigation(candidate, underReviewSelf)).toBe(false);
      }
    });
  });
});
