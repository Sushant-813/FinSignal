import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";
import { QueryProvider } from "../../src/app/providers/QueryProvider.tsx";
import { ProtectedRoute } from "../../src/app/router/ProtectedRoute.tsx";
import { AuthProvider } from "../../src/features/auth/context/AuthProvider.tsx";
import { DatasetsPage } from "../../src/features/datasets/pages/DatasetsPage.tsx";
import { setAccessToken } from "../../src/lib/auth/token-store.ts";
import { buildAuthUser } from "../fixtures/auth.ts";
import {
  buildDatasetImportListFixture,
  buildDatasetImportSummaryFixture,
  SAMPLE_IMPORT_ID,
} from "../fixtures/f4-data.ts";
import { server } from "../mocks/server.ts";

function renderDatasetsPage(
  initialPath = "/datasets",
  role: "ADMIN" | "ANALYST" | "INVESTIGATOR" = "ANALYST"
) {
  setAccessToken("test-role-jwt");
  server.use(http.get("/api/v1/auth/me", () => HttpResponse.json(buildAuthUser(role))));

  const router = createMemoryRouter(
    [
      {
        element: <ProtectedRoute />,
        children: [
          { path: "/datasets", element: <DatasetsPage /> },
          { path: "/datasets/imports/:importId", element: <div>Import Detail Stub</div> },
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

describe("DatasetsPage component (F4.2)", () => {
  it("renders ledger rows, pagination, and upload card for ANALYST role", async () => {
    server.use(
      http.get("/api/v1/datasets/imports", () => {
        return HttpResponse.json(
          buildDatasetImportListFixture([
            buildDatasetImportSummaryFixture({
              id: SAMPLE_IMPORT_ID,
              filename: "sample_batch.csv",
              status: "COMPLETED",
              total_rows: 500,
              valid_rows: 490,
              invalid_rows: 10,
            }),
          ])
        );
      })
    );

    renderDatasetsPage("/datasets", "ANALYST");

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Datasets", level: 1 })).toBeInTheDocument();
      expect(
        screen.getByRole("heading", { name: /import transaction dataset/i })
      ).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByText("sample_batch.csv")).toBeInTheDocument();
    });
    expect(screen.getByText("Completed")).toBeInTheDocument();
    expect(screen.getByText("500")).toBeInTheDocument();
    expect(screen.getByText("490")).toBeInTheDocument();
  });

  it("renders read-only notice and hides upload card for INVESTIGATOR role", async () => {
    server.use(
      http.get("/api/v1/datasets/imports", () => {
        return HttpResponse.json(buildDatasetImportListFixture([]));
      })
    );

    renderDatasetsPage("/datasets", "INVESTIGATOR");

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Datasets", level: 1 })).toBeInTheDocument();
    });

    expect(
      screen.getByLabelText(/investigator read-only dataset permissions/i)
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: /import transaction dataset/i })
    ).not.toBeInTheDocument();
  });

  it("handles 404 namespace not found with reset action", async () => {
    const user = userEvent.setup();

    server.use(
      http.get("/api/v1/datasets/imports", ({ request }) => {
        const url = new URL(request.url);
        if (url.searchParams.get("source_namespace") === "UNKNOWN_NS") {
          return HttpResponse.json(
            {
              error: {
                code: "NAMESPACE_NOT_FOUND",
                message: "Requested namespace does not exist.",
              },
            },
            { status: 404 }
          );
        }
        return HttpResponse.json(buildDatasetImportListFixture([]));
      })
    );

    renderDatasetsPage("/datasets?source_namespace=UNKNOWN_NS", "ANALYST");

    await waitFor(() => {
      expect(screen.getByRole("alert", { name: /namespace not found error/i })).toBeInTheDocument();
    });

    const resetBtn = screen.getByRole("button", { name: /reset to synthetic/i });
    expect(resetBtn).toBeInTheDocument();
    await user.click(resetBtn);

    await waitFor(() => {
      expect(
        screen.queryByRole("alert", { name: /namespace not found error/i })
      ).not.toBeInTheDocument();
    });
  });

  it("allows filtering by status and updates the query parameters", async () => {
    const user = userEvent.setup();
    let capturedUrl = "";

    server.use(
      http.get("/api/v1/datasets/imports", ({ request }) => {
        capturedUrl = request.url;
        return HttpResponse.json(buildDatasetImportListFixture([]));
      })
    );

    renderDatasetsPage("/datasets", "ANALYST");

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Datasets", level: 1 })).toBeInTheDocument();
    });

    // Radix UI Select trigger labeled by its visible "Status" label
    const statusSelect = screen.getByRole("combobox", { name: "Status" });
    await user.click(statusSelect);

    const failedOption = await screen.findByRole("option", { name: /^failed$/i });
    await user.click(failedOption);

    await waitFor(() => {
      expect(capturedUrl).toContain("status=FAILED");
    });
  });
});
