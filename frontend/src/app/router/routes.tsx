import { createBrowserRouter, type RouteObject } from "react-router";
import { AnalyticsPage } from "../../features/analytics/pages/AnalyticsPage.tsx";
import { LoginPage } from "../../features/auth/pages/LoginPage.tsx";
import { DashboardPage } from "../../features/dashboard/pages/DashboardPage.tsx";
import { DatasetImportDetailPage } from "../../features/datasets/pages/DatasetImportDetailPage.tsx";
import { DatasetsPage } from "../../features/datasets/pages/DatasetsPage.tsx";
import { TransactionDetailPage } from "../../features/transactions/pages/TransactionDetailPage.tsx";
import { TransactionsListPage } from "../../features/transactions/pages/TransactionsListPage.tsx";
import { NotFoundPage } from "../errors/NotFoundPage.tsx";
import { ErrorFallbackView } from "../errors/RootErrorBoundary.tsx";
import { AppLayout } from "../layouts/AppLayout.tsx";
import { AuthLayout } from "../layouts/AuthLayout.tsx";
import { PhasePlaceholderPage } from "./PhasePlaceholderPage.tsx";
import { ProtectedRoute } from "./ProtectedRoute.tsx";
import { PublicOnlyRoute } from "./PublicOnlyRoute.tsx";

export const appRoutes: RouteObject[] = [
  {
    element: <PublicOnlyRoute />,
    errorElement: <ErrorFallbackView />,
    children: [
      {
        element: <AuthLayout />,
        children: [
          {
            path: "/login",
            element: <LoginPage />,
          },
        ],
      },
    ],
  },
  {
    element: <ProtectedRoute />,
    errorElement: <ErrorFallbackView />,
    children: [
      {
        element: <AppLayout />,
        children: [
          {
            path: "/",
            element: <DashboardPage />,
          },
          {
            path: "/transactions",
            element: <TransactionsListPage />,
          },
          {
            path: "/transactions/:transactionId",
            element: <TransactionDetailPage />,
          },
          {
            path: "/analytics",
            element: <AnalyticsPage />,
          },
          {
            path: "/investigations",
            element: (
              <PhasePlaceholderPage
                title="Investigations"
                phaseLabel="Phase F5"
                description="Case queue, assignment management, evidence attachment, and AI advisory summary views are scheduled for Phases F5–F6."
              />
            ),
          },
          {
            path: "/datasets",
            element: <DatasetsPage />,
          },
          {
            path: "/datasets/imports/:importId",
            element: <DatasetImportDetailPage />,
          },
        ],
      },
    ],
  },
  {
    path: "*",
    element: <NotFoundPage />,
    errorElement: <ErrorFallbackView />,
  },
];

export function createAppRouter() {
  return createBrowserRouter(appRoutes);
}
