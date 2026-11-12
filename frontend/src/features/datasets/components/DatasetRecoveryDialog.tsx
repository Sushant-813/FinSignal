import { FileCheck } from "lucide-react";
import { useRef, useState } from "react";
import { Alert } from "../../../components/ui/Alert.tsx";
import { Button } from "../../../components/ui/Button.tsx";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../../../components/ui/Dialog.tsx";
import { isApiClientError } from "../../../lib/api/errors.ts";
import { useRecoverDatasetMutation } from "../hooks/useRecoverDatasetMutation.ts";
import { validateCsvFile } from "../schemas/dataset-upload-schema.ts";
import type {
  DatasetImportDetailResponse,
  DatasetImportResponse,
} from "../types/datasets.types.ts";

export interface DatasetRecoveryDialogProps {
  importData: DatasetImportResponse | DatasetImportDetailResponse;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onRecoverySuccess?: ((result: DatasetImportResponse) => void) | undefined;
}

export function DatasetRecoveryDialog({
  importData,
  open,
  onOpenChange,
  onRecoverySuccess,
}: DatasetRecoveryDialogProps) {
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const recoverMutation = useRecoverDatasetMutation();

  const handleClose = () => {
    setFile(null);
    setFileError(null);
    recoverMutation.reset();
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
    onOpenChange(false);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    setFileError(null);
    recoverMutation.reset();

    if (!selected) {
      setFile(null);
      return;
    }

    const validation = validateCsvFile(selected);
    if (!validation.valid) {
      setFile(null);
      setFileError(validation.error || "Invalid CSV file.");
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      return;
    }

    setFile(selected);
  };

  const handleRecover = async (e: React.FormEvent) => {
    e.preventDefault();
    setFileError(null);

    const validation = validateCsvFile(file);
    if (!validation.valid || !file) {
      setFileError(validation.error || "Please select the original CSV file to resume recovery.");
      return;
    }

    try {
      const result = await recoverMutation.mutateAsync({
        importId: importData.id,
        file,
      });

      handleClose();
      onRecoverySuccess?.(result);
    } catch {
      // Handled in dialog error display
    }
  };

  const isRecovering = recoverMutation.isPending;
  const error = recoverMutation.error;

  return (
    <Dialog open={open} onOpenChange={(isOpen) => (!isRecovering ? onOpenChange(isOpen) : null)}>
      <DialogContent className="max-w-lg">
        <form onSubmit={handleRecover}>
          <DialogHeader>
            <DialogTitle>Recover Failed Dataset Import</DialogTitle>
            <DialogDescription>
              Resume ingestion of uncommitted records without skipping rows or duplicating primary
              transactions.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="rounded-lg border border-border-default bg-surface-secondary p-3 text-[12px] text-text-secondary space-y-1">
              <div className="font-semibold text-text-primary">
                SHA-256 Hash Verification Requirement:
              </div>
              <p>
                The backend requires the <strong>original CSV file</strong> (
                {importData.filename || "identical file"}). It will compute the SHA-256 stream hash
                and verify that it matches the recorded import hash:
              </p>
              <div className="font-mono text-[11px] text-text-primary break-all bg-surface-primary p-2 rounded border border-border-subtle">
                {importData.file_hash || "No recorded file hash"}
              </div>
            </div>

            {error && isApiClientError(error) ? (
              error.status === 409 ? (
                <Alert variant="warning" role="alert" aria-label="Advisory lock timeout">
                  {error.message ||
                    "Another upload or recovery operation is currently active. Please try again shortly."}
                </Alert>
              ) : error.status === 422 ? (
                <Alert variant="danger" role="alert" aria-label="Recovery hash mismatch">
                  {error.message ||
                    "Uploaded file content does not match the original import SHA-256 hash. Please re-select the exact original CSV file."}
                </Alert>
              ) : error.status === 413 ? (
                <Alert variant="danger" role="alert" aria-label="Payload too large">
                  File exceeds the maximum allowable size of 50 MB.
                </Alert>
              ) : (
                <Alert variant="danger" role="alert" aria-label="Recovery error">
                  {error.message || "An unexpected error occurred while executing import recovery."}
                </Alert>
              )
            ) : null}

            <div className="space-y-1.5">
              <label
                htmlFor="recovery-file-input"
                className="text-[12px] font-medium text-text-primary"
              >
                Select Original CSV File (.csv)
              </label>
              <input
                ref={fileInputRef}
                id="recovery-file-input"
                type="file"
                accept=".csv,text/csv"
                onChange={handleFileChange}
                disabled={isRecovering}
                className="block w-full text-[13px] text-text-secondary file:mr-3 file:cursor-pointer file:rounded-md file:border-0 file:bg-surface-secondary file:px-3 file:py-1.5 file:text-[13px] file:font-medium file:text-text-primary hover:file:bg-border-default focus:outline-none disabled:opacity-50"
                aria-invalid={Boolean(fileError)}
                aria-describedby={fileError ? "recovery-file-error" : undefined}
              />
              {fileError ? (
                <p id="recovery-file-error" className="text-[12px] text-accent-danger" role="alert">
                  {fileError}
                </p>
              ) : null}
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="tertiary" onClick={handleClose} disabled={isRecovering}>
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              isLoading={isRecovering}
              disabled={!file || Boolean(fileError) || isRecovering}
            >
              <FileCheck className="h-4 w-4" />
              {isRecovering ? "Verifying & Resuming..." : "Resume Ingestion"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
