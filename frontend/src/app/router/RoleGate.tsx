import type { ReactNode } from "react";
import { Link, Outlet } from "react-router";
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
import { useAuth } from "../../features/auth/hooks/useAuth.ts";
import type { AuthUser } from "../../features/auth/types/auth.types.ts";

export interface RoleGateProps {
  isAllowed: (user: AuthUser | null) => boolean;
  title?: string | undefined;
  description?: string | undefined;
  children?: ReactNode;
}

export function RoleGate({
  isAllowed,
  title = "Access restricted by workspace policy",
  description = "Your current role does not have permission to view this workflow.",
  children,
}: RoleGateProps) {
  const { user } = useAuth();

  if (isAllowed(user)) {
    return children ? <>{children}</> : <Outlet />;
  }

  return (
    <section aria-label="Access restricted" className="mx-auto max-w-2xl py-6">
      <Card padding="lg">
        <CardHeader>
          <CardTitle as="h1" size="section">
            {title}
          </CardTitle>
          <CardDescription>{description}</CardDescription>
        </CardHeader>
        <CardContent>
          <Alert variant="warning" role="region" aria-label="Role policy notice">
            This navigation restriction applies to your current user role ({user?.role ?? "Unknown"}
            ). Contact a FinSignal administrator if your investigation duties require updated
            access.
          </Alert>
        </CardContent>
        <CardFooter>
          <Button asChild variant="primary">
            <Link to="/">Return to workspace overview</Link>
          </Button>
        </CardFooter>
      </Card>
    </section>
  );
}
