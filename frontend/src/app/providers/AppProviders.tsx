import type { ReactNode } from "react";
import { RootErrorBoundary } from "../errors/RootErrorBoundary.tsx";
import { AuthProvider } from "../../features/auth/context/AuthProvider.tsx";
import { QueryProvider } from "./QueryProvider.tsx";

export interface AppProvidersProps {
  children: ReactNode;
}

export function AppProviders({ children }: AppProvidersProps) {
  return (
    <RootErrorBoundary>
      <QueryProvider>
        <AuthProvider>{children}</AuthProvider>
      </QueryProvider>
    </RootErrorBoundary>
  );
}
