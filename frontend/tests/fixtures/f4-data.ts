import type {
  DatasetImportDetailResponse,
  DatasetImportListResponse,
  DatasetImportResponse,
} from "../../src/features/datasets/types/datasets.types.ts";

export const SAMPLE_IMPORT_ID = "imp-9b7e3f2a-1122-3344-5566-778899aabbcc";
export const SAMPLE_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";

export function buildDatasetImportSummaryFixture(
  overrides: Partial<DatasetImportResponse> = {}
): DatasetImportResponse {
  return {
    id: SAMPLE_IMPORT_ID,
    source_namespace: "SYNTHETIC",
    source_type: "SYNTHETIC",
    status: "COMPLETED",
    filename: "transactions_2026_11.csv",
    file_hash: SAMPLE_SHA256,
    total_rows: 1000,
    valid_rows: 995,
    invalid_rows: 5,
    started_at: "2026-11-12T10:00:00Z",
    completed_at: "2026-11-12T10:00:15Z",
    is_duplicate: false,
    ...overrides,
  };
}

export function buildDatasetImportDetailFixture(
  overrides: Partial<DatasetImportDetailResponse> = {}
): DatasetImportDetailResponse {
  return {
    id: SAMPLE_IMPORT_ID,
    source_namespace: "SYNTHETIC",
    source_type: "SYNTHETIC",
    status: "COMPLETED",
    filename: "transactions_2026_11.csv",
    file_hash: SAMPLE_SHA256,
    total_rows: 1000,
    valid_rows: 995,
    invalid_rows: 5,
    started_at: "2026-11-12T10:00:00Z",
    completed_at: "2026-11-12T10:00:15Z",
    is_duplicate: false,
    errors: [
      {
        row_number: 42,
        field_name: "amount",
        error_code: "INVALID_FORMAT",
        message: "Invalid numeric currency format",
      },
      {
        row_number: 105,
        field_name: "timestamp",
        error_code: "OUT_OF_RANGE",
        message: "Timestamp outside supported date range",
      },
    ],
    ...overrides,
  };
}

export function buildDatasetImportListFixture(
  items: DatasetImportResponse[] = [buildDatasetImportSummaryFixture()],
  overrides: Partial<DatasetImportListResponse> = {}
): DatasetImportListResponse {
  return {
    items,
    page: 1,
    page_size: 20,
    total: items.length,
    total_pages: Math.max(1, Math.ceil(items.length / 20)),
    ...overrides,
  };
}
