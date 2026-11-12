import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import {
  analyzeTransactionRisk,
  getTransactionRisk,
} from "../../src/features/risk/api/risk-api.ts";
import { ApiClientError } from "../../src/lib/api/client.ts";
import { setAccessToken } from "../../src/lib/auth/token-store.ts";
import { apiErrorFixtures } from "../fixtures/api-errors.ts";
import { buildRiskAnalysisFixture, SAMPLE_TX_UUID } from "../fixtures/f3-data.ts";
import { server } from "../mocks/server.ts";

describe("Risk API wrappers (F3.6–F3.7)", () => {
  it("maps 404 RISK_ANALYSIS_NOT_FOUND to not_analyzed while rethrowing real errors", async () => {
    setAccessToken("risk-jwt");

    server.use(
      http.get(`/api/v1/transactions/${SAMPLE_TX_UUID}/risk`, () =>
        HttpResponse.json(
          {
            error: {
              code: "RISK_ANALYSIS_NOT_FOUND",
              message: "No risk evaluation exists for transaction.",
              details: {},
              request_id: "req-risk-404",
            },
          },
          { status: 404 }
        )
      )
    );

    const missingResult = await getTransactionRisk(SAMPLE_TX_UUID);
    expect(missingResult).toEqual({ kind: "not_analyzed" });

    server.use(
      http.get(`/api/v1/transactions/${SAMPLE_TX_UUID}/risk`, () =>
        HttpResponse.json(
          {
            error: {
              code: "TRANSACTION_NOT_FOUND",
              message: "Transaction does not exist.",
              details: {},
              request_id: "req-tx-404",
            },
          },
          { status: 404 }
        )
      )
    );

    await expect(getTransactionRisk(SAMPLE_TX_UUID)).rejects.toMatchObject({
      name: "ApiClientError",
      status: 404,
      code: "TRANSACTION_NOT_FOUND",
    } satisfies Partial<ApiClientError>);
  });

  it("posts default ACTIVE payload without model_version_id or force_recalculate and surfaces failures", async () => {
    setAccessToken("risk-jwt");
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.post(`/api/v1/transactions/${SAMPLE_TX_UUID}/risk/analyze`, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(buildRiskAnalysisFixture());
      })
    );

    const analyzed = await analyzeTransactionRisk(SAMPLE_TX_UUID);
    expect(analyzed.score).toBe(78);
    expect(capturedBody).toEqual({});
    expect(capturedBody).not.toHaveProperty("model_version_id");
    expect(capturedBody).not.toHaveProperty("force_recalculate");

    server.use(
      http.post(`/api/v1/transactions/${SAMPLE_TX_UUID}/risk/analyze`, () =>
        apiErrorFixtures.forbidden()
      )
    );

    await expect(analyzeTransactionRisk(SAMPLE_TX_UUID)).rejects.toMatchObject({
      status: 403,
      code: "FORBIDDEN",
    });

    server.use(
      http.post(`/api/v1/transactions/${SAMPLE_TX_UUID}/risk/analyze`, () =>
        HttpResponse.json(
          {
            error: {
              code: "INELIGIBLE_MODEL_STATUS",
              message: "Model is EXPERIMENTAL.",
              details: {},
              request_id: "req-422-model",
            },
          },
          { status: 422 }
        )
      )
    );

    await expect(analyzeTransactionRisk(SAMPLE_TX_UUID)).rejects.toMatchObject({
      status: 422,
      code: "INELIGIBLE_MODEL_STATUS",
    });
  });
});
