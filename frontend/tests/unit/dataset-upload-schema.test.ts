import { describe, expect, it } from "vitest";
import { datasetUploadSchema } from "../../src/features/datasets/schemas/dataset-upload-schema.ts";

describe("datasetUploadSchema (F4.4)", () => {
  it("accepts a valid CSV file within 50MB limit", () => {
    const file = new File(["account_id,amount\nacc1,100.00\n"], "test.csv", {
      type: "text/csv",
    });

    const result = datasetUploadSchema.safeParse({ file });
    expect(result.success).toBe(true);
  });

  it("rejects an empty file (0 bytes)", () => {
    const emptyFile = new File([], "empty.csv", { type: "text/csv" });
    const result = datasetUploadSchema.safeParse({ file: emptyFile });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues[0]?.message).toMatch(/empty/i);
    }
  });

  it("rejects a file exceeding 50 MB", () => {
    const hugeFile = {
      name: "huge.csv",
      size: 50 * 1024 * 1024 + 1,
      type: "text/csv",
    } as unknown as File;

    const result = datasetUploadSchema.safeParse({ file: hugeFile });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues[0]?.message).toMatch(/50 MB/i);
    }
  });

  it("rejects non-CSV file extensions case-insensitively", () => {
    const txtFile = new File(["some text"], "report.txt", { type: "text/plain" });
    const exeFile = new File(["binary"], "malware.exe", {
      type: "application/octet-stream",
    });

    expect(datasetUploadSchema.safeParse({ file: txtFile }).success).toBe(false);
    expect(datasetUploadSchema.safeParse({ file: exeFile }).success).toBe(false);

    const upperCsv = new File(["col1,col2\n1,2"], "REPORT.CSV", {
      type: "text/csv",
    });
    expect(datasetUploadSchema.safeParse({ file: upperCsv }).success).toBe(true);
  });
});
