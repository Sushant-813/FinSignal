import type { ReactNode } from "react";
import { RootErrorBoundary } from "../errors/RootErrorBoundary.tsx";
import { QueryProvider } from "./QueryProvider.tsx";

export interface AppProvidersProps {
  children: ReactNode;
}

export function AppProviders({ children }: AppProvidersProps) {
  return (
    <RootErrorBoundary>
      <QueryProvider>{children}</QueryProvider>
    </RootErrorBoundary>
  );
}
