import { createBrowserRouter, type RouteObject } from "react-router";
import { NotFoundPage } from "../errors/NotFoundPage.tsx";
import { ErrorFallbackView } from "../errors/RootErrorBoundary.tsx";
import { FoundationPage } from "./FoundationPage.tsx";

export const appRoutes: RouteObject[] = [
  {
    path: "/",
    element: <FoundationPage />,
    errorElement: <ErrorFallbackView />,
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
