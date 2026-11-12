import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";
import { QueryProvider } from "../../src/app/providers/QueryProvider.tsx";
import { DatasetUploadCard } from "../../src/features/datasets/components/DatasetUploadCard.tsx";
import { setAccessToken } from "../../src/lib/auth/token-store.ts";
import { buildDatasetImportSummaryFixture } from "../fixtures/f4-data.ts";
import { server } from "../mocks/server.ts";

function renderUploadCard(onSuccess = vi.fn()) {
  setAccessToken("test-analyst-jwt");
  return {
    onSuccess,
    ...render(
      <QueryProvider>
        <MemoryRouter>
          <DatasetUploadCard onUploadSuccess={onSuccess} />
        </MemoryRouter>
      </QueryProvider>
    ),
  };
}

describe("DatasetUploadCard component (F4.4)", () => {
  it("renders upload form and handles successful 201 ingestion", async () => {
    const user = userEvent.setup();
    const onSuccess = vi.fn();

    server.use(
      http.post("http://localhost:3000/api/v1/datasets/imports", () => {
        return HttpResponse.json(
          buildDatasetImportSummaryFixture({
            status: "COMPLETED",
            is_duplicate: false,
          }),
          { status: 201 }
        );
      })
    );

    renderUploadCard(onSuccess);

    expect(screen.getByRole("heading", { name: /import transaction dataset/i })).toBeInTheDocument();
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    expect(fileInput).toBeInTheDocument();

    const validCsv = new File(["col1,col2\n1,2"], "test_dataset.csv", { type: "text/csv" });
    await user.upload(fileInput, validCsv);

    const submitBtn = screen.getByRole("button", { name: /upload dataset/i });
    expect(submitBtn).not.toBeDisabled();
    await user.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByRole("status", { name: /upload ingestion success/i })).toBeInTheDocument();
      expect(screen.getByText(/successfully ingested dataset/i)).toBeInTheDocument();
    });
    expect(onSuccess).toHaveBeenCalled();
  });

  it("handles 200 duplicate file detection response", async () => {
    const user = userEvent.setup();

    server.use(
      http.post("http://localhost:3000/api/v1/datasets/imports", () => {
        return HttpResponse.json(
          buildDatasetImportSummaryFixture({
            status: "COMPLETED",
            is_duplicate: true,
          }),
          { status: 200 }
        );
      })
    );

    renderUploadCard();

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const validCsv = new File(["col1,col2\n1,2"], "duplicate.csv", { type: "text/csv" });
    await user.upload(fileInput, validCsv);

    await user.click(screen.getByRole("button", { name: /upload dataset/i }));

    await waitFor(() => {
      expect(screen.getByRole("status", { name: /duplicate upload notice/i })).toBeInTheDocument();
      expect(screen.getByText(/identical file has already been imported/i)).toBeInTheDocument();
    });
  });

  it("handles 409 conflict when another import is in progress", async () => {
    const user = userEvent.setup();

    server.use(
      http.post("http://localhost:3000/api/v1/datasets/imports", () => {
        return HttpResponse.json(
          {
            error: {
              code: "IMPORT_IN_PROGRESS",
              message: "An import is currently in progress for this namespace.",
              details: { active_import_id: "imp-active-456" },
            },
          },
          { status: 409 }
        );
      })
    );

    renderUploadCard();

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const validCsv = new File(["col1,col2\n1,2"], "concurrent.csv", { type: "text/csv" });
    await user.upload(fileInput, validCsv);

    await user.click(screen.getByRole("button", { name: /upload dataset/i }));

    await waitFor(() => {
      expect(screen.getByText(/an import for this identical file is currently active/i)).toBeInTheDocument();
      expect(screen.getByText(/view in-progress import/i)).toBeInTheDocument();
    });
  });

  it("handles 413 file too large error", async () => {
    const user = userEvent.setup();

    server.use(
      http.post("http://localhost:3000/api/v1/datasets/imports", () => {
        return HttpResponse.json(
          {
            error: {
              code: "PAYLOAD_TOO_LARGE",
              message: "File exceeds maximum allowable size of 50 MB.",
            },
          },
          { status: 413 }
        );
      })
    );

    renderUploadCard();

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const validCsv = new File(["col1,col2\n1,2"], "too_large.csv", { type: "text/csv" });
    await user.upload(fileInput, validCsv);

    await user.click(screen.getByRole("button", { name: /upload dataset/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert", { name: /payload too large error/i })).toBeInTheDocument();
    });
  });

  it("rejects invalid client-side preflight (non-csv or empty) before API submission", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    renderUploadCard();

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const emptyFile = new File([], "empty.csv", { type: "text/csv" });
    await user.upload(fileInput, emptyFile);

    expect(screen.getByText(/uploaded csv file is empty/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /upload dataset/i })).toBeDisabled();

    expect(fetchSpy).not.toHaveBeenCalled();
    fetchSpy.mockRestore();
  });
});
