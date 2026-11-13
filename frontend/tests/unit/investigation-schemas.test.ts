import { describe, expect, it } from "vitest";
import {
  investigationFilterSchema,
  parseInvestigationFilterParams,
  UUID_REGEX,
} from "../../src/features/investigations/schemas/investigation-filter-schema.ts";
import {
  investigationCreateSchema,
  investigationLinkSchema,
  investigationPatchSchema,
  investigationResolveSchema,
} from "../../src/features/investigations/schemas/investigation-mutations-schema.ts";
import {
  SAMPLE_INVESTIGATOR_ID,
  SAMPLE_PRIMARY_TX_ID,
  SAMPLE_RELATED_TX_ID,
} from "../fixtures/f5-data.ts";

describe("Investigation Zod schemas (F5.1)", () => {
  describe("UUID_REGEX", () => {
    it("validates well-formed UUIDs and rejects invalid formats", () => {
      expect(UUID_REGEX.test(SAMPLE_PRIMARY_TX_ID)).toBe(true);
      expect(UUID_REGEX.test("11111111-2222-3333-4444-555555555555")).toBe(true);
      expect(UUID_REGEX.test("not-a-uuid")).toBe(false);
      expect(UUID_REGEX.test("11111111-2222-3333-4444-55555555555")).toBe(false);
      expect(UUID_REGEX.test("")).toBe(false);
    });
  });

  describe("investigationFilterSchema & parseInvestigationFilterParams", () => {
    it("parses valid filter params with defaults", () => {
      const parsed = parseInvestigationFilterParams(new URLSearchParams());
      expect(parsed).toEqual({
        page: 1,
        page_size: 25,
        status: undefined,
        priority: undefined,
        assigned_to: undefined,
        unassigned: undefined,
      });
    });

    it("parses status, priority, and pagination from search params", () => {
      const search = new URLSearchParams({
        page: "3",
        page_size: "50",
        status: "UNDER_REVIEW",
        priority: "CRITICAL",
        assigned_to: SAMPLE_INVESTIGATOR_ID,
      });

      const parsed = parseInvestigationFilterParams(search);
      expect(parsed.page).toBe(3);
      expect(parsed.page_size).toBe(50);
      expect(parsed.status).toBe("UNDER_REVIEW");
      expect(parsed.priority).toBe("CRITICAL");
      expect(parsed.assigned_to).toBe(SAMPLE_INVESTIGATOR_ID);
      expect(parsed.unassigned).toBeUndefined();
    });

    it("enforces mutual exclusivity: omits assigned_to when unassigned is true", () => {
      const search = new URLSearchParams({
        unassigned: "true",
        assigned_to: SAMPLE_INVESTIGATOR_ID,
      });

      const parsed = parseInvestigationFilterParams(search);
      expect(parsed.unassigned).toBe(true);
      expect(parsed.assigned_to).toBeUndefined();
    });

    it("direct rawFilterSchema rejects conflicting assigned_to + unassigned=true", () => {
      const result = investigationFilterSchema.safeParse({
        unassigned: true,
        assigned_to: SAMPLE_INVESTIGATOR_ID,
      });

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues[0]?.message).toContain(
          "Cannot combine assigned_to filter with unassigned=true."
        );
      }
    });

    it("gracefully normalizes invalid pagination and bogus status strings", () => {
      const parsed = parseInvestigationFilterParams({
        page: "-5",
        page_size: "999",
        status: "INVALID_STATUS",
        priority: "SUPER_HIGH",
        assigned_to: "bogus-uuid",
      });

      expect(parsed.page).toBe(1);
      expect(parsed.page_size).toBe(25);
      expect(parsed.status).toBeUndefined();
      expect(parsed.priority).toBeUndefined();
      expect(parsed.assigned_to).toBeUndefined();
    });
  });

  describe("investigationCreateSchema", () => {
    it("accepts valid transaction_id and priority", () => {
      const result = investigationCreateSchema.safeParse({
        transaction_id: SAMPLE_PRIMARY_TX_ID,
        priority: "HIGH",
      });

      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.transaction_id).toBe(SAMPLE_PRIMARY_TX_ID);
        expect(result.data.priority).toBe("HIGH");
      }
    });

    it("applies default priority MEDIUM when omitted", () => {
      const result = investigationCreateSchema.safeParse({
        transaction_id: SAMPLE_PRIMARY_TX_ID,
      });

      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.priority).toBe("MEDIUM");
      }
    });

    it("strictly rejects unsupported fields (notes, title) matching backend extra='forbid'", () => {
      const result = investigationCreateSchema.safeParse({
        transaction_id: SAMPLE_PRIMARY_TX_ID,
        priority: "LOW",
        notes: "Some investigator notes",
        title: "Suspicious Case",
      });

      expect(result.success).toBe(false);
    });

    it("rejects non-UUID transaction_id", () => {
      const result = investigationCreateSchema.safeParse({
        transaction_id: "invalid-uuid",
      });

      expect(result.success).toBe(false);
    });
  });

  describe("investigationPatchSchema", () => {
    it("accepts valid partial patch attributes", () => {
      const result = investigationPatchSchema.safeParse({
        assigned_to: SAMPLE_INVESTIGATOR_ID,
        status: "UNDER_REVIEW",
        priority: "CRITICAL",
      });

      expect(result.success).toBe(true);
    });

    it("accepts explicit null for assigned_to (self-unassignment)", () => {
      const result = investigationPatchSchema.safeParse({
        assigned_to: null,
      });

      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.assigned_to).toBeNull();
      }
    });

    it("rejects invalid status transitions via PATCH (only UNDER_REVIEW is supported)", () => {
      const resultResolved = investigationPatchSchema.safeParse({
        status: "RESOLVED",
      });
      expect(resultResolved.success).toBe(false);

      const resultOpen = investigationPatchSchema.safeParse({
        status: "OPEN",
      });
      expect(resultOpen.success).toBe(false);
    });
  });

  describe("investigationResolveSchema", () => {
    it("accepts valid resolution and non-whitespace notes", () => {
      const result = investigationResolveSchema.safeParse({
        resolution: "CONFIRMED_FRAUD",
        resolution_notes: "Multiple structured transactions below reporting threshold.",
      });

      expect(result.success).toBe(true);
    });

    it("rejects empty or whitespace-only resolution notes", () => {
      const emptyResult = investigationResolveSchema.safeParse({
        resolution: "LEGITIMATE",
        resolution_notes: "",
      });
      expect(emptyResult.success).toBe(false);

      const whitespaceResult = investigationResolveSchema.safeParse({
        resolution: "LEGITIMATE",
        resolution_notes: "   \t\n   ",
      });
      expect(whitespaceResult.success).toBe(false);
    });

    it("rejects unrecognized resolution outcomes", () => {
      const result = investigationResolveSchema.safeParse({
        resolution: "UNCONFIRMED_FRAUD",
        resolution_notes: "Valid notes text.",
      });

      expect(result.success).toBe(false);
    });
  });

  describe("investigationLinkSchema", () => {
    it("accepts valid transaction_id UUID", () => {
      const result = investigationLinkSchema.safeParse({
        transaction_id: SAMPLE_RELATED_TX_ID,
      });

      expect(result.success).toBe(true);
    });

    it("rejects invalid transaction UUID", () => {
      const result = investigationLinkSchema.safeParse({
        transaction_id: "not-a-uuid",
      });

      expect(result.success).toBe(false);
    });
  });
});
