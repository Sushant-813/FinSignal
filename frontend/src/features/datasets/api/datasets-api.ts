import { apiRequest } from "../../../lib/api/client.ts";
import type {
  DatasetImportDetailResponse,
  DatasetImportListParams,
  DatasetImportListResponse,
  DatasetImportResponse,
  RecoverDatasetPayload,
  UploadDatasetPayload,
} from "../types/datasets.types.ts";

export async function uploadDataset(
  payload: UploadDatasetPayload,
  signal?: AbortSignal
): Promise<DatasetImportResponse> {
  const formData = new FormData();
  formData.append("file", payload.file, payload.file.name);
  formData.append("source_namespace", payload.source_namespace.trim());
  formData.append("source_type", payload.source_type.trim());

  return apiRequest<DatasetImportResponse>("/datasets/imports", {
    method: "POST",
    body: formData,
    signal,
  });
}

export async function listDatasetImports(
  params: DatasetImportListParams,
  signal?: AbortSignal
): Promise<DatasetImportListResponse> {
  const search = new URLSearchParams();
  search.set("page", String(params.page));
  search.set("page_size", String(params.page_size));
  search.set("source_namespace", params.source_namespace.trim());

  if (params.status) {
    search.set("status", params.status);
  }
  if (params.source_type && params.source_type.trim() !== "") {
    search.set("source_type", params.source_type.trim());
  }
  if (params.from_time && params.from_time.trim() !== "") {
    search.set("from_time", params.from_time.trim());
  }
  if (params.to_time && params.to_time.trim() !== "") {
    search.set("to_time", params.to_time.trim());
  }

  return apiRequest<DatasetImportListResponse>(`/datasets/imports?${search.toString()}`, {
    method: "GET",
    signal,
  });
}

export async function getDatasetImportDetail(
  importId: string,
  signal?: AbortSignal
): Promise<DatasetImportDetailResponse> {
  return apiRequest<DatasetImportDetailResponse>(
    `/datasets/imports/${encodeURIComponent(importId)}`,
    {
      method: "GET",
      signal,
    }
  );
}

export async function recoverDatasetImport(
  payload: RecoverDatasetPayload,
  signal?: AbortSignal
): Promise<DatasetImportResponse> {
  const formData = new FormData();
  formData.append("file", payload.file, payload.file.name);

  return apiRequest<DatasetImportResponse>(
    `/datasets/imports/${encodeURIComponent(payload.importId)}/recover`,
    {
      method: "POST",
      body: formData,
      signal,
    }
  );
}

