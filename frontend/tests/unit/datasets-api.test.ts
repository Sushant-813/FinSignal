import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import {
  getDatasetImportDetail,
  listDatasetImports,
  recoverDatasetImport,
  uploadDataset,
} from "../../src/features/datasets/api/datasets-api.ts";
import { setAccessToken } from "../../src/lib/auth/token-store.ts";
import {
  buildDatasetImportDetailFixture,
  buildDatasetImportListFixture,
  buildDatasetImportSummaryFixture,
  SAMPLE_IMPORT_ID,
} from "../fixtures/f4-data.ts";
import { server } from "../mocks/server.ts";

describe("Datasets API client functions (F4.1)", () => {
  it("encodes list filters into query params and omits empty/null params", async () => {
    setAccessToken("test-jwt");
    let capturedUrl = "";

    server.use(
      http.get("http://localhost:3000/api/v1/datasets/imports", ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json(buildDatasetImportListFixture());
      })
    );

    const res = await listDatasetImports({
      page: 2,
      page_size: 50,
      source_namespace: "SYNTHETIC",
      status: "FAILED",
      from_time: "2026-11-01T00:00:00.000Z",
      to_time: "2026-11-02T00:00:00.000Z",
    });

    expect(res.items).toHaveLength(1);
    expect(capturedUrl).toContain("page=2");
    expect(capturedUrl).toContain("page_size=50");
    expect(capturedUrl).toContain("source_namespace=SYNTHETIC");
    expect(capturedUrl).toContain("status=FAILED");
    expect(capturedUrl).toContain("from_time=2026-11-01T00%3A00%3A00.000Z");
    expect(capturedUrl).toContain("to_time=2026-11-02T00%3A00%3A00.000Z");
  });

  it("fetches dataset import detail by URL-encoded import_id", async () => {
    setAccessToken("test-jwt");
    let capturedUrl = "";

    server.use(
      http.get(`http://localhost:3000/api/v1/datasets/imports/${SAMPLE_IMPORT_ID}`, ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json(buildDatasetImportDetailFixture());
      })
    );

    const detail = await getDatasetImportDetail(SAMPLE_IMPORT_ID);
    expect(detail.id).toBe(SAMPLE_IMPORT_ID);
    expect(capturedUrl).toContain(SAMPLE_IMPORT_ID);
  });

  it("submits multipart/form-data for uploadDataset without manual Content-Type header override", async () => {
    setAccessToken("test-jwt");
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    server.use(
      http.post("http://localhost:3000/api/v1/datasets/imports", () => {
        return HttpResponse.json(buildDatasetImportSummaryFixture(), { status: 201 });
      })
    );

    const testFile = new File(["account,amount\nacc1,500"], "batch.csv", {
      type: "text/csv",
    });

    const summary = await uploadDataset({
      file: testFile,
      source_namespace: "SYNTHETIC",
      source_type: "SYNTHETIC",
    });

    expect(summary.id).toBe(SAMPLE_IMPORT_ID);
    expect(fetchSpy).toHaveBeenCalled();
    const lastCallInit = fetchSpy.mock.calls[fetchSpy.mock.calls.length - 1]?.[1];
    expect(lastCallInit?.body).toBeInstanceOf(FormData);
    const sentFormData = lastCallInit?.body as FormData;
    expect(sentFormData.get("file")).not.toBeNull();
    const uploadedFile = sentFormData.get("file") as File;
    expect(uploadedFile.name).toBe("batch.csv");
    expect(sentFormData.get("source_namespace")).toBe("SYNTHETIC");
    expect(sentFormData.get("source_type")).toBe("SYNTHETIC");
    expect(new Headers(lastCallInit?.headers).has("Content-Type")).toBe(false);

    fetchSpy.mockRestore();
  });

  it("submits multipart/form-data for recoverDatasetImport with recovery file", async () => {
    setAccessToken("test-jwt");
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    server.use(
      http.post(
        `http://localhost:3000/api/v1/datasets/imports/${SAMPLE_IMPORT_ID}/recover`,
        () => {
          return HttpResponse.json(buildDatasetImportSummaryFixture({ status: "PROCESSING" }));
        }
      )
    );

    const recoveryFile = new File(["account,amount\nacc1,500"], "batch_recovered.csv", {
      type: "text/csv",
    });

    const res = await recoverDatasetImport({
      importId: SAMPLE_IMPORT_ID,
      file: recoveryFile,
    });

    expect(res.status).toBe("PROCESSING");
    expect(fetchSpy).toHaveBeenCalled();
    const lastCallInit = fetchSpy.mock.calls[fetchSpy.mock.calls.length - 1]?.[1];
    expect(lastCallInit?.body).toBeInstanceOf(FormData);
    const sentFormData = lastCallInit?.body as FormData;
    expect(sentFormData.get("file")).not.toBeNull();
    const uploadedRecoveryFile = sentFormData.get("file") as File;
    expect(uploadedRecoveryFile.name).toBe("batch_recovered.csv");
    expect(new Headers(lastCallInit?.headers).has("Content-Type")).toBe(false);

    fetchSpy.mockRestore();
  });
});
