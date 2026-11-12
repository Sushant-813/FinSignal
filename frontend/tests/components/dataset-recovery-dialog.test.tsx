import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { QueryProvider } from "../../src/app/providers/QueryProvider.tsx";
import { DatasetRecoveryDialog } from "../../src/features/datasets/components/DatasetRecoveryDialog.tsx";
import { setAccessToken } from "../../src/lib/auth/token-store.ts";
import {
  buildDatasetImportDetailFixture,
  buildDatasetImportSummaryFixture,
  SAMPLE_IMPORT_ID,
} from "../fixtures/f4-data.ts";
import { server } from "../mocks/server.ts";

function renderRecoveryDialog(
  open = true,
  onOpenChange = vi.fn(),
  onRecoverySuccess = vi.fn()
) {
  setAccessToken("test-analyst-jwt");
  const importData = buildDatasetImportDetailFixture({
    status: "FAILED",
  });

  return {
    onOpenChange,
    onRecoverySuccess,
    importData,
    ...render(
      <QueryProvider>
        <DatasetRecoveryDialog
          importData={importData}
          open={open}
          onOpenChange={onOpenChange}
          onRecoverySuccess={onRecoverySuccess}
        />
      </QueryProvider>
    ),
  };
}

describe("DatasetRecoveryDialog component (F4.5)", () => {
  it("renders modal, accepts matching file, and submits recovery request", async () => {
    const user = userEvent.setup();
    const onSuccess = vi.fn();

    server.use(
      http.post(
        `http://localhost:3000/api/v1/datasets/imports/${SAMPLE_IMPORT_ID}/recover`,
        () => {
          return HttpResponse.json(
            buildDatasetImportSummaryFixture({
              status: "PROCESSING",
            })
          );
        }
      )
    );

    renderRecoveryDialog(true, vi.fn(), onSuccess);

    expect(screen.getByRole("heading", { name: /recover failed dataset import/i })).toBeInTheDocument();

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const originalFile = new File(["col1,col2\n1,2"], "original_transactions.csv", {
      type: "text/csv",
    });

    await user.upload(fileInput, originalFile);

    const submitBtn = screen.getByRole("button", { name: /resume ingestion/i });
    expect(submitBtn).not.toBeDisabled();
    await user.click(submitBtn);

    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalled();
    });
  });

  it("handles 422 hash mismatch error cleanly in modal alert", async () => {
    const user = userEvent.setup();

    server.use(
      http.post(
        `http://localhost:3000/api/v1/datasets/imports/${SAMPLE_IMPORT_ID}/recover`,
        () => {
          return HttpResponse.json(
            {
              error: {
                code: "FILE_HASH_MISMATCH",
                message: "Uploaded file SHA-256 does not match original import record.",
              },
            },
            { status: 422 }
          );
        }
      )
    );

    renderRecoveryDialog();

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const wrongFile = new File(["different content"], "wrong.csv", { type: "text/csv" });
    await user.upload(fileInput, wrongFile);

    await user.click(screen.getByRole("button", { name: /resume ingestion/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert", { name: /recovery hash mismatch/i })).toBeInTheDocument();
      expect(screen.getByText(/does not match/i)).toBeInTheDocument();
    });
  });

  it("handles 409 advisory lock timeout error", async () => {
    const user = userEvent.setup();

    server.use(
      http.post(
        `http://localhost:3000/api/v1/datasets/imports/${SAMPLE_IMPORT_ID}/recover`,
        () => {
          return HttpResponse.json(
            {
              error: {
                code: "IMPORT_IN_PROGRESS",
                message: "Another upload or recovery operation is currently active.",
              },
            },
            { status: 409 }
          );
        }
      )
    );

    renderRecoveryDialog();

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(["col1,col2\n1,2"], "file.csv", { type: "text/csv" });
    await user.upload(fileInput, file);

    await user.click(screen.getByRole("button", { name: /resume ingestion/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert", { name: /advisory lock timeout/i })).toBeInTheDocument();
    });
  });
});

