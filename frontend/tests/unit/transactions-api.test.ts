import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import {
  getTransactionDetail,
  getTransactions,
} from "../../src/features/transactions/api/transactions-api.ts";
import { setAccessToken } from "../../src/lib/auth/token-store.ts";
import {
  buildTransactionDetailFixture,
  buildTransactionListFixture,
  SAMPLE_TX_UUID,
} from "../fixtures/f3-data.ts";
import { server } from "../mocks/server.ts";

describe("Transactions API wrappers (F3.4–F3.5)", () => {
  it("encodes list filters while omitting null/blank optional parameters", async () => {
    setAccessToken("tx-jwt");
    let capturedListUrl = "";
    let capturedDetailUrl = "";

    server.use(
      http.get("/api/v1/transactions", ({ request }) => {
        capturedListUrl = request.url;
        return HttpResponse.json(buildTransactionListFixture());
      }),
      http.get(`/api/v1/transactions/${SAMPLE_TX_UUID}`, ({ request }) => {
        capturedDetailUrl = request.url;
        return HttpResponse.json(buildTransactionDetailFixture());
      })
    );

    const listRes = await getTransactions({
      page: 2,
      page_size: 25,
      source_namespace: "SYNTHETIC",
      sort_by: "amount",
      sort_order: "asc",
      direction: "DEBIT",
      risk_level: "HIGH",
      min_amount: "100.00",
      max_amount: "5000.00",
      category: "  ",
      account_id: null,
    });
    expect(listRes.items).toHaveLength(1);
    expect(capturedListUrl).toContain("page=2");
    expect(capturedListUrl).toContain("page_size=25");
    expect(capturedListUrl).toContain("sort_by=amount");
    expect(capturedListUrl).toContain("sort_order=asc");
    expect(capturedListUrl).toContain("risk_level=HIGH");
    expect(capturedListUrl).toContain("min_amount=100.00");
    expect(capturedListUrl).not.toContain("category=");
    expect(capturedListUrl).not.toContain("account_id=");

    const detailRes = await getTransactionDetail(SAMPLE_TX_UUID, {
      source_namespace: "SYNTHETIC",
    });
    expect(detailRes.id).toBe(SAMPLE_TX_UUID);
    expect(capturedDetailUrl).toContain("source_namespace=SYNTHETIC");
  });
});
