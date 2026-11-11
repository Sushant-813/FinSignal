import { createBrowserRouter, type RouteObject } from "react-router";
import { LoginPage } from "../../features/auth/pages/LoginPage.tsx";
import { NotFoundPage } from "../errors/NotFoundPage.tsx";
import { ErrorFallbackView } from "../errors/RootErrorBoundary.tsx";
import { AppLayout } from "../layouts/AppLayout.tsx";
import { AuthLayout } from "../layouts/AuthLayout.tsx";
import { PhasePlaceholderPage } from "./PhasePlaceholderPage.tsx";
import { ProtectedRoute } from "./ProtectedRoute.tsx";
import { PublicOnlyRoute } from "./PublicOnlyRoute.tsx";
import { WorkspaceHomePage } from "./WorkspaceHomePage.tsx";

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
            element: <WorkspaceHomePage />,
          },
          {
            path: "/transactions",
            element: (
              <PhasePlaceholderPage
                title="Transactions"
                phaseLabel="Phase F3"
                description="Filterable transaction ledger, detail drawer, and risk scoring integration are scheduled for Phase F3."
              />
            ),
          },
          {
            path: "/analytics",
            element: (
              <PhasePlaceholderPage
                title="Analytics"
                phaseLabel="Phase F3"
                description="Backend-authoritative spend trends, category distributions, and merchant rankings are scheduled for Phase F3."
              />
            ),
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
            element: (
              <PhasePlaceholderPage
                title="Datasets"
                phaseLabel="Phase F4"
                description="Dataset import history and CSV ingestion recovery workflows are scheduled for Phase F4."
                isDatasetsRoute
              />
            ),
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
