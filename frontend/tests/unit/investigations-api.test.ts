import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import {
  addRelatedTransaction,
  createInvestigation,
  getInvestigation,
  getInvestigationTransactions,
  listInvestigations,
  patchInvestigation,
  resolveInvestigation,
} from "../../src/features/investigations/api/investigations-api.ts";
import { setAccessToken } from "../../src/lib/auth/token-store.ts";
import {
  buildInvestigationDetailResponse,
  buildInvestigationListResponse,
  buildInvestigationTransactionItem,
  buildInvestigationTransactionsListResponse,
  SAMPLE_INVESTIGATION_ID,
  SAMPLE_INVESTIGATOR_ID,
  SAMPLE_PRIMARY_TX_ID,
  SAMPLE_RELATED_TX_ID,
} from "../fixtures/f5-data.ts";
import { server } from "../mocks/server.ts";

describe("Investigations API client functions (F5.1)", () => {
  it("listInvestigations serializes filters into URL search params and omits empty/null params", async () => {
    setAccessToken("test-jwt");
    let capturedUrl = "";

    server.use(
      http.get("*/api/v1/investigations", ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json(buildInvestigationListResponse());
      })
    );

    const res = await listInvestigations({
      page: 2,
      page_size: 50,
      status: "OPEN",
      priority: "HIGH",
      assigned_to: SAMPLE_INVESTIGATOR_ID,
    });

    expect(res.items).toHaveLength(1);
    expect(capturedUrl).toContain("page=2");
    expect(capturedUrl).toContain("page_size=50");
    expect(capturedUrl).toContain("status=OPEN");
    expect(capturedUrl).toContain("priority=HIGH");
    expect(capturedUrl).toContain(`assigned_to=${SAMPLE_INVESTIGATOR_ID}`);
    expect(capturedUrl).not.toContain("unassigned");
  });

  it("listInvestigations avoids sending conflicting assigned_to when unassigned is true", async () => {
    setAccessToken("test-jwt");
    let capturedUrl = "";

    server.use(
      http.get("*/api/v1/investigations", ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json(buildInvestigationListResponse());
      })
    );

    await listInvestigations({
      page: 1,
      page_size: 25,
      unassigned: true,
      assigned_to: SAMPLE_INVESTIGATOR_ID,
    });

    expect(capturedUrl).toContain("unassigned=true");
    expect(capturedUrl).not.toContain("assigned_to");
  });

  it("createInvestigation sends POST with strictly transaction_id and priority only", async () => {
    setAccessToken("test-jwt");
    let capturedBody: unknown = null;

    server.use(
      http.post("*/api/v1/investigations", async ({ request }) => {
        capturedBody = await request.json();
        return HttpResponse.json(buildInvestigationDetailResponse(), { status: 201 });
      })
    );

    const created = await createInvestigation({
      transaction_id: SAMPLE_PRIMARY_TX_ID,
      priority: "CRITICAL",
    });

    expect(created.id).toBe(SAMPLE_INVESTIGATION_ID);
    expect(capturedBody).toEqual({
      transaction_id: SAMPLE_PRIMARY_TX_ID,
      priority: "CRITICAL",
    });
    // Explicitly verify no forbidden notes or title fields are transmitted
    expect(capturedBody).not.toHaveProperty("notes");
    expect(capturedBody).not.toHaveProperty("title");
  });

  it("getInvestigation retrieves workspace detail by investigation id", async () => {
    setAccessToken("test-jwt");
    let capturedUrl = "";

    server.use(
      http.get(`*/api/v1/investigations/${SAMPLE_INVESTIGATION_ID}`, ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json(buildInvestigationDetailResponse());
      })
    );

    const detail = await getInvestigation(SAMPLE_INVESTIGATION_ID);
    expect(detail.id).toBe(SAMPLE_INVESTIGATION_ID);
    expect(capturedUrl).toContain(SAMPLE_INVESTIGATION_ID);
  });

  it("getInvestigation throws normalized ApiClientError on 404 NOT_FOUND", async () => {
    setAccessToken("test-jwt");

    server.use(
      http.get("*/api/v1/investigations/unknown-id", () => {
        return HttpResponse.json(
          {
            error: {
              code: "INVESTIGATION_NOT_FOUND",
              message: "Investigation 'unknown-id' was not found.",
            },
          },
          { status: 404 }
        );
      })
    );

    await expect(getInvestigation("unknown-id")).rejects.toMatchObject({
      status: 404,
      code: "INVESTIGATION_NOT_FOUND",
    });
  });

  it("patchInvestigation sends PATCH request to update assignment, priority, or status", async () => {
    setAccessToken("test-jwt");
    let capturedBody: unknown = null;

    server.use(
      http.patch(`*/api/v1/investigations/${SAMPLE_INVESTIGATION_ID}`, async ({ request }) => {
        capturedBody = await request.json();
        return HttpResponse.json(
          buildInvestigationDetailResponse({
            assigned_to: SAMPLE_INVESTIGATOR_ID,
            status: "UNDER_REVIEW",
          })
        );
      })
    );

    const updated = await patchInvestigation(SAMPLE_INVESTIGATION_ID, {
      assigned_to: SAMPLE_INVESTIGATOR_ID,
      status: "UNDER_REVIEW",
    });

    expect(updated.assigned_to).toBe(SAMPLE_INVESTIGATOR_ID);
    expect(updated.status).toBe("UNDER_REVIEW");
    expect(capturedBody).toEqual({
      assigned_to: SAMPLE_INVESTIGATOR_ID,
      status: "UNDER_REVIEW",
    });
  });

  it("patchInvestigation handles 409 CASE_ALREADY_ASSIGNED concurrency conflict", async () => {
    setAccessToken("test-jwt");

    server.use(
      http.patch(`*/api/v1/investigations/${SAMPLE_INVESTIGATION_ID}`, () => {
        return HttpResponse.json(
          {
            error: {
              code: "CASE_ALREADY_ASSIGNED",
              message: "Investigation was concurrently assigned to another user.",
            },
          },
          { status: 409 }
        );
      })
    );

    await expect(
      patchInvestigation(SAMPLE_INVESTIGATION_ID, { assigned_to: SAMPLE_INVESTIGATOR_ID })
    ).rejects.toMatchObject({
      status: 409,
      code: "CASE_ALREADY_ASSIGNED",
    });
  });

  it("resolveInvestigation sends POST with explicit resolution and mandatory notes", async () => {
    setAccessToken("test-jwt");
    let capturedBody: unknown = null;

    server.use(
      http.post(
        `*/api/v1/investigations/${SAMPLE_INVESTIGATION_ID}/resolve`,
        async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json(
            buildInvestigationDetailResponse({
              status: "RESOLVED",
              resolution: "CONFIRMED_FRAUD",
              resolution_notes: "Account takeover verified via IP clustering.",
            })
          );
        }
      )
    );

    const resolved = await resolveInvestigation(SAMPLE_INVESTIGATION_ID, {
      resolution: "CONFIRMED_FRAUD",
      resolution_notes: "Account takeover verified via IP clustering.",
    });

    expect(resolved.status).toBe("RESOLVED");
    expect(resolved.resolution).toBe("CONFIRMED_FRAUD");
    expect(capturedBody).toEqual({
      resolution: "CONFIRMED_FRAUD",
      resolution_notes: "Account takeover verified via IP clustering.",
    });
  });

  it("getInvestigationTransactions retrieves all associated transactions", async () => {
    setAccessToken("test-jwt");

    server.use(
      http.get(`*/api/v1/investigations/${SAMPLE_INVESTIGATION_ID}/transactions`, () => {
        return HttpResponse.json(buildInvestigationTransactionsListResponse());
      })
    );

    const txList = await getInvestigationTransactions(SAMPLE_INVESTIGATION_ID);
    expect(txList.investigation_id).toBe(SAMPLE_INVESTIGATION_ID);
    expect(txList.items).toHaveLength(2);
    expect(txList.items[0]?.relationship_type).toBe("PRIMARY");
    expect(txList.items[1]?.relationship_type).toBe("RELATED");
  });

  it("addRelatedTransaction links a related transaction satisfying the 1-hop predicate", async () => {
    setAccessToken("test-jwt");
    let capturedBody: unknown = null;

    server.use(
      http.post(
        `*/api/v1/investigations/${SAMPLE_INVESTIGATION_ID}/transactions`,
        async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json(buildInvestigationTransactionItem(), { status: 201 });
        }
      )
    );

    const linkedItem = await addRelatedTransaction(SAMPLE_INVESTIGATION_ID, {
      transaction_id: SAMPLE_RELATED_TX_ID,
    });

    expect(linkedItem.transaction_id).toBe(SAMPLE_RELATED_TX_ID);
    expect(linkedItem.relationship_type).toBe("RELATED");
    expect(capturedBody).toEqual({
      transaction_id: SAMPLE_RELATED_TX_ID,
    });
  });

  it("addRelatedTransaction propagates 422 TRANSACTION_NOT_RELATED error", async () => {
    setAccessToken("test-jwt");

    server.use(
      http.post(`*/api/v1/investigations/${SAMPLE_INVESTIGATION_ID}/transactions`, () => {
        return HttpResponse.json(
          {
            error: {
              code: "TRANSACTION_NOT_RELATED",
              message:
                "Transaction does not satisfy direct 1-hop relationship condition with primary transaction.",
            },
          },
          { status: 422 }
        );
      })
    );

    await expect(
      addRelatedTransaction(SAMPLE_INVESTIGATION_ID, {
        transaction_id: "00000000-0000-0000-0000-000000000000",
      })
    ).rejects.toMatchObject({
      status: 422,
      code: "TRANSACTION_NOT_RELATED",
    });
  });
});
