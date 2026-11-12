import { render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";
import { QueryProvider } from "../../src/app/providers/QueryProvider.tsx";
import { ProtectedRoute } from "../../src/app/router/ProtectedRoute.tsx";
import { AuthProvider } from "../../src/features/auth/context/AuthProvider.tsx";
import { DatasetImportDetailPage } from "../../src/features/datasets/pages/DatasetImportDetailPage.tsx";
import { setAccessToken } from "../../src/lib/auth/token-store.ts";
import { buildAuthUser } from "../fixtures/auth.ts";
import {
  buildDatasetImportDetailFixture,
  SAMPLE_IMPORT_ID,
  SAMPLE_SHA256,
} from "../fixtures/f4-data.ts";
import { server } from "../mocks/server.ts";

function renderDetailPage(
  initialPath = `/datasets/imports/${SAMPLE_IMPORT_ID}`,
  role: "ADMIN" | "ANALYST" | "INVESTIGATOR" = "ANALYST"
) {
  setAccessToken("test-role-jwt");
  server.use(
    http.get("http://localhost:3000/api/v1/auth/me", () => HttpResponse.json(buildAuthUser(role)))
  );

  const router = createMemoryRouter(
    [
      {
        element: <ProtectedRoute />,
        children: [
          { path: "/datasets", element: <div>Datasets Ledger Stub</div> },
          { path: "/datasets/imports/:importId", element: <DatasetImportDetailPage /> },
        ],
      },
      { path: "/login", element: <div>Login Target</div> },
    ],
    { initialEntries: [initialPath] }
  );

  return {
    router,
    ...render(
      <QueryProvider>
        <AuthProvider>
          <RouterProvider router={router} />
        </AuthProvider>
      </QueryProvider>
    ),
  };
}

describe("DatasetImportDetailPage component (F4.3)", () => {
  it("renders fact cards, duration, and error table for completed import", async () => {
    server.use(
      http.get(`http://localhost:3000/api/v1/datasets/imports/${SAMPLE_IMPORT_ID}`, () => {
        return HttpResponse.json(
          buildDatasetImportDetailFixture({
            status: "COMPLETED",
            filename: "transactions_2026_11.csv",
            file_hash: SAMPLE_SHA256,
            total_rows: 1000,
            valid_rows: 995,
            invalid_rows: 5,
            started_at: "2026-11-12T10:00:00Z",
            completed_at: "2026-11-12T10:00:15Z",
            errors: [
              {
                row_number: 42,
                field_name: "amount",
                error_code: "INVALID_FORMAT",
                message: "Invalid numeric currency format",
              },
            ],
          })
        );
      })
    );

    renderDetailPage();

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /import details/i })).toBeInTheDocument();
      expect(screen.getByText("transactions_2026_11.csv")).toBeInTheDocument();
    });

    expect(screen.getByText("Completed")).toBeInTheDocument();
    expect(screen.getByText("1,000")).toBeInTheDocument();
    expect(screen.getByText("995")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByText("15s")).toBeInTheDocument(); // Duration
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("amount")).toBeInTheDocument();
    expect(screen.getByText("INVALID_FORMAT")).toBeInTheDocument();
    expect(screen.getByText("Invalid numeric currency format")).toBeInTheDocument();

    // Recover button must NOT be present when status is COMPLETED
    expect(screen.queryByRole("button", { name: /recover import/i })).not.toBeInTheDocument();
  });

  it("exposes 'Recover Import' button when import status is FAILED and role is ANALYST", async () => {
    server.use(
      http.get(`http://localhost:3000/api/v1/datasets/imports/${SAMPLE_IMPORT_ID}`, () => {
        return HttpResponse.json(
          buildDatasetImportDetailFixture({
            status: "FAILED",
            errors: [
              {
                row_number: 1,
                field_name: "file",
                error_code: "IO_ERROR",
                message: "Interrupted database stream during ingestion.",
              },
            ],
          })
        );
      })
    );

    renderDetailPage(`/datasets/imports/${SAMPLE_IMPORT_ID}`, "ANALYST");

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /recover import/i })).toBeInTheDocument();
    });
  });

  it("hides 'Recover Import' button for INVESTIGATOR role even when import status is FAILED", async () => {
    server.use(
      http.get(`http://localhost:3000/api/v1/datasets/imports/${SAMPLE_IMPORT_ID}`, () => {
        return HttpResponse.json(
          buildDatasetImportDetailFixture({
            status: "FAILED",
          })
        );
      })
    );

    renderDetailPage(`/datasets/imports/${SAMPLE_IMPORT_ID}`, "INVESTIGATOR");

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /import details/i })).toBeInTheDocument();
    });

    expect(screen.queryByRole("button", { name: /recover import/i })).not.toBeInTheDocument();
  });

  it("renders 404 alert when import does not exist", async () => {
    server.use(
      http.get("http://localhost:3000/api/v1/datasets/imports/non-existent-id", () => {
        return HttpResponse.json(
          {
            error: {
              code: "RESOURCE_NOT_FOUND",
              message: "Dataset import not found.",
            },
          },
          { status: 404 }
        );
      })
    );

    renderDetailPage("/datasets/imports/non-existent-id", "ANALYST");

    await waitFor(() => {
      expect(screen.getByRole("alert", { name: /dataset import not found/i })).toBeInTheDocument();
    });
  });
});
