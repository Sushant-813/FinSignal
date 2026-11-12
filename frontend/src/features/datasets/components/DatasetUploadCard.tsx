import { Loader2, Upload } from "lucide-react";
import { useRef, useState } from "react";
import { Link } from "react-router";
import { Alert } from "../../../components/ui/Alert.tsx";
import { Button } from "../../../components/ui/Button.tsx";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "../../../components/ui/Card.tsx";
import { Input } from "../../../components/ui/Input.tsx";
import { isApiClientError } from "../../../lib/api/errors.ts";
import { useUploadDatasetMutation } from "../hooks/useUploadDatasetMutation.ts";
import {
  datasetUploadFormSchema,
  validateCsvFile,
} from "../schemas/dataset-upload-schema.ts";
import type { DatasetImportResponse } from "../types/datasets.types.ts";

export interface DatasetUploadCardProps {
  onUploadSuccess?: ((response: DatasetImportResponse) => void) | undefined;
  onRefreshHistory?: (() => void) | undefined;
}

function extractActiveImportId(details: unknown): string | undefined {
  if (typeof details === "object" && details !== null) {
    const rec = details as Record<string, unknown>;
    if (typeof rec.active_import_id === "string" && rec.active_import_id.trim() !== "") {
      return rec.active_import_id.trim();
    }
  }
  return undefined;
}

export function DatasetUploadCard({ onUploadSuccess, onRefreshHistory }: DatasetUploadCardProps) {
  const [file, setFile] = useState<File | null>(null);
  const [namespace, setNamespace] = useState("SYNTHETIC");
  const [sourceType, setSourceType] = useState("SYNTHETIC");
  const [fileError, setFileError] = useState<string | null>(null);
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const [uploadResult, setUploadResult] = useState<DatasetImportResponse | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const uploadMutation = useUploadDatasetMutation();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    setUploadResult(null);
    setFileError(null);

    if (!selected) {
      setFile(null);
      return;
    }

    const validation = validateCsvFile(selected);
    if (!validation.valid) {
      setFile(null);
      setFileError(validation.error || "Invalid file.");
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      return;
    }

    setFile(selected);
  };

  const handleClear = () => {
    setFile(null);
    setFileError(null);
    setFormErrors({});
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setUploadResult(null);
    setFileError(null);
    setFormErrors({});

    const fileValidation = validateCsvFile(file);
    if (!fileValidation.valid) {
      setFileError(fileValidation.error || "Please select a valid CSV file.");
      return;
    }

    const formValidation = datasetUploadFormSchema.safeParse({
      source_namespace: namespace,
      source_type: sourceType,
    });

    if (!formValidation.success) {
      const errMap: Record<string, string> = {};
      formValidation.error.issues.forEach((issue) => {
        const path = String(issue.path[0]);
        errMap[path] = issue.message;
      });
      setFormErrors(errMap);
      return;
    }

    if (!file) return;

    try {
      const result = await uploadMutation.mutateAsync({
        file,
        source_namespace: formValidation.data.source_namespace,
        source_type: formValidation.data.source_type,
      });

      setUploadResult(result);
      handleClear();
      onUploadSuccess?.(result);
    } catch {
      // Handled via uploadMutation.error state below
    }
  };

  const isUploading = uploadMutation.isPending;
  const error = uploadMutation.error;

  return (
    <Card padding="lg" className="border-border-default">
      <CardHeader>
        <div className="flex items-center gap-2">
          <Upload className="h-5 w-5 text-accent-primary" aria-hidden="true" />
          <CardTitle as="h2" size="panel">
            Import Transaction Dataset
          </CardTitle>
        </div>
        <CardDescription>
          Upload a UTF-8 or UTF-8 BOM CSV dataset (up to 50 MB). Transactions will be validated, deduplicated, and committed with row-level provenance.
        </CardDescription>
      </CardHeader>

      <form onSubmit={handleSubmit}>
        <CardContent className="space-y-4">
          {/* Outcome Alerts */}
          {uploadResult ? (
            uploadResult.is_duplicate ? (
              <Alert
                variant="info"
                role="status"
                aria-label="Duplicate upload notice"
                action={
                  <Button asChild size="sm" variant="secondary">
                    <Link to={`/datasets/imports/${uploadResult.id}`}>View Existing Import</Link>
                  </Button>
                }
              >
                Identical file has already been imported in namespace &ldquo;{uploadResult.source_namespace}&rdquo;. Existing import records and summary were retained without re-ingesting.
              </Alert>
            ) : (
              <Alert
                variant="success"
                role="status"
                aria-label="Upload ingestion success"
                action={
                  <Button asChild size="sm" variant="secondary">
                    <Link to={`/datasets/imports/${uploadResult.id}`}>View Import Details</Link>
                  </Button>
                }
              >
                Successfully ingested dataset &ldquo;{uploadResult.filename}&rdquo; into namespace &ldquo;{uploadResult.source_namespace}&rdquo;. Total rows: {uploadResult.total_rows.toLocaleString()} ({uploadResult.valid_rows.toLocaleString()} valid, {uploadResult.invalid_rows.toLocaleString()} invalid).
              </Alert>
            )
          ) : null}

          {error && isApiClientError(error) ? (
            error.status === 409 ? (
              <Alert
                variant="warning"
                role="alert"
                aria-label="Import in progress conflict"
                action={
                  extractActiveImportId(error.details) ? (
                    <Button asChild size="sm" variant="secondary">
                      <Link to={`/datasets/imports/${extractActiveImportId(error.details)}`}>
                        View In-Progress Import
                      </Link>
                    </Button>
                  ) : onRefreshHistory ? (
                    <Button size="sm" variant="secondary" onClick={onRefreshHistory}>
                      Refresh History
                    </Button>
                  ) : undefined
                }
              >
                An import for this identical file is currently active or processing in namespace &ldquo;{namespace}&rdquo;. Please wait for the active job to finish.
              </Alert>
            ) : error.status === 413 ? (
              <Alert variant="danger" role="alert" aria-label="Payload too large error">
                File exceeds maximum allowable size of 50 MB. Please partition the dataset and upload smaller batches.
              </Alert>
            ) : error.status === 422 ? (
              <Alert
                variant="danger"
                role="alert"
                aria-label="CSV validation error"
                action={
                  onRefreshHistory ? (
                    <Button size="sm" variant="secondary" onClick={onRefreshHistory}>
                      Refresh History
                    </Button>
                  ) : undefined
                }
              >
                {error.message || "CSV validation or domain verification failed. Check the file structure."}
              </Alert>
            ) : error.status === 0 || error.code === "NETWORK_ERROR" ? (
              <Alert
                variant="warning"
                role="alert"
                aria-label="Network timeout warning"
                action={
                  onRefreshHistory ? (
                    <Button size="sm" variant="secondary" onClick={onRefreshHistory}>
                      Check Import History
                    </Button>
                  ) : undefined
                }
              >
                The network connection was interrupted or timed out. The server may still be ingesting your dataset in the background. Please inspect the Import History table before attempting to re-upload.
              </Alert>
            ) : (
              <Alert variant="danger" role="alert" aria-label="Upload error">
                {error.message || "An unexpected error occurred during dataset upload."}
              </Alert>
            )
          ) : null}

          {/* File Picker & Preflight */}
          <div className="space-y-1.5">
            <label
              htmlFor="csv-file-input"
              className="text-[12px] font-medium tracking-tight text-text-primary"
            >
              CSV File (.csv)
            </label>
            <div className="flex items-center gap-3">
              <input
                ref={fileInputRef}
                id="csv-file-input"
                type="file"
                accept=".csv,text/csv"
                onChange={handleFileChange}
                disabled={isUploading}
                className="block w-full text-[13px] text-text-secondary file:mr-3 file:cursor-pointer file:rounded-md file:border-0 file:bg-surface-secondary file:px-3 file:py-1.5 file:text-[13px] file:font-medium file:text-text-primary hover:file:bg-border-default focus:outline-none disabled:opacity-50"
                aria-invalid={Boolean(fileError)}
                aria-describedby={fileError ? "csv-file-error" : "csv-file-helper"}
              />
              {file ? (
                <Button
                  type="button"
                  variant="tertiary"
                  size="sm"
                  onClick={handleClear}
                  disabled={isUploading}
                >
                  Clear
                </Button>
              ) : null}
            </div>

            <p id="csv-file-helper" className="text-[12px] text-text-muted">
              Supported format: CSV (UTF-8 or UTF-8 BOM). Maximum size: 50 MB.
            </p>
            {fileError ? (
              <p id="csv-file-error" className="text-[12px] text-accent-danger" role="alert">
                {fileError}
              </p>
            ) : null}
          </div>

          {/* Form Fields: Namespace and Source Type */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Input
              id="upload-source-namespace"
              label="Source Namespace"
              value={namespace}
              onChange={(e) => setNamespace(e.target.value.toUpperCase())}
              disabled={isUploading}
              error={formErrors.source_namespace}
              hint="Target partition (e.g. SYNTHETIC)"
              aria-label="Dataset target namespace partition"
            />

            <Input
              id="upload-source-type"
              label="Source Type"
              value={sourceType}
              onChange={(e) => setSourceType(e.target.value.toUpperCase())}
              disabled={isUploading}
              error={formErrors.source_type}
              hint="Origin identifier (e.g. SYNTHETIC)"
              aria-label="Dataset source type origin"
            />
          </div>

          {/* Indeterminate Streaming Indicator */}
          {isUploading ? (
            <div
              className="flex items-center gap-3 rounded-lg border border-border-default bg-surface-secondary p-3 text-[13px] text-text-secondary"
              role="status"
              aria-live="polite"
            >
              <Loader2 className="h-5 w-5 animate-spin text-accent-primary" aria-hidden="true" />
              <span>
                Streaming CSV and ingesting records... Processing large datasets (up to 50 MB) may take up to 30 seconds.
              </span>
            </div>
          ) : null}
        </CardContent>

        <CardFooter className="flex justify-end gap-2">
          <Button
            type="submit"
            variant="primary"
            isLoading={isUploading}
            disabled={!file || Boolean(fileError) || isUploading}
          >
            {isUploading ? "Ingesting..." : "Upload Dataset"}
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
}
