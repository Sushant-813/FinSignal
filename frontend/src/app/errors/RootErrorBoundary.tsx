import { Component, type ReactNode } from "react";
import { Alert } from "../../components/ui/Alert.tsx";
import { Button } from "../../components/ui/Button.tsx";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "../../components/ui/Card.tsx";

export interface ErrorFallbackViewProps {
  onReload?: (() => void) | undefined;
  onReturnHome?: (() => void) | undefined;
}

export function ErrorFallbackView({ onReload, onReturnHome }: ErrorFallbackViewProps) {
  const handleReload = () => {
    if (onReload) {
      onReload();
      return;
    }
    window.location.reload();
  };

  const handleReturnHome = () => {
    if (onReturnHome) {
      onReturnHome();
      return;
    }
    window.location.assign("/");
  };

  const showReturnHome = typeof window !== "undefined" && window.location.pathname !== "/";

  return (
    <main className="flex min-h-screen items-center justify-center bg-canvas p-6">
      <Card as="section" aria-label="Application error" className="w-full max-w-lg" padding="lg">
        <CardHeader>
          <CardTitle as="h1" size="section">
            Something went wrong
          </CardTitle>
          <CardDescription>
            An unexpected rendering error prevented this view from loading.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Alert variant="danger" role="alert">
            Reload the application to recover. If the problem persists, return to the home screen or
            contact support.
          </Alert>
        </CardContent>
        <CardFooter>
          {showReturnHome ? (
            <Button variant="secondary" onClick={handleReturnHome}>
              Return to home
            </Button>
          ) : null}
          <Button variant="primary" onClick={handleReload}>
            Reload application
          </Button>
        </CardFooter>
      </Card>
    </main>
  );
}

export interface RootErrorBoundaryProps {
  children: ReactNode;
  onReload?: (() => void) | undefined;
  onReturnHome?: (() => void) | undefined;
}

interface RootErrorBoundaryState {
  hasError: boolean;
}

export class RootErrorBoundary extends Component<RootErrorBoundaryProps, RootErrorBoundaryState> {
  override state: RootErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): RootErrorBoundaryState {
    return { hasError: true };
  }

  override componentDidCatch(): void {
    // Deliberately suppress logging raw error stacks or payloads to avoid leaking sensitive state.
  }

  override render(): ReactNode {
    if (this.state.hasError) {
      return (
        <ErrorFallbackView onReload={this.props.onReload} onReturnHome={this.props.onReturnHome} />
      );
    }

    return this.props.children;
  }
}
