import type { components, operations } from "../../../api/generated/schema.ts";

export type DatasetImportResponse = components["schemas"]["DatasetImportResponse"];
export type DatasetImportDetailResponse = components["schemas"]["DatasetImportDetailResponse"];
export type DatasetImportListResponse = components["schemas"]["DatasetImportListResponse"];
export type DatasetImportErrorItem = components["schemas"]["DatasetImportErrorItem"];

export type DatasetImportStatus = "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";

export interface DatasetImportListParams {
  page: number;
  page_size: number;
  source_namespace: string;
  status?: DatasetImportStatus | null | undefined;
  source_type?: string | null | undefined;
  from_time?: string | null | undefined;
  to_time?: string | null | undefined;
}

export interface UploadDatasetPayload {
  file: File;
  source_namespace: string;
  source_type: string;
}

export interface RecoverDatasetPayload {
  importId: string;
  file: File;
}

export type UploadDatasetOperation =
  operations["upload_dataset_import_api_v1_datasets_imports_post"];
export type ListDatasetImportsOperation =
  operations["list_dataset_imports_api_v1_datasets_imports_get"];
export type GetDatasetImportDetailOperation =
  operations["get_dataset_import_details_api_v1_datasets_imports__import_id__get"];
export type RecoverDatasetImportOperation =
  operations["recover_dataset_import_api_v1_datasets_imports__import_id__recover_post"];

