import { describe, expect, it } from "vitest";
import { isUserRole, type AuthUser } from "../../src/features/auth/types/auth.types.ts";
import {
  canAccessWorkspace,
  canAnalyzeActiveRisk,
  canAnalyzeValidatedRisk,
  canManageDatasets,
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
});
