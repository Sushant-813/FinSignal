import { Link } from "react-router";
import { Alert } from "../../components/ui/Alert.tsx";
import { Badge } from "../../components/ui/Badge.tsx";
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
import { canManageDatasets } from "../../lib/permissions/capabilities.ts";

export interface PhasePlaceholderPageProps {
  title: string;
  phaseLabel: string;
  description: string;
  isDatasetsRoute?: boolean | undefined;
}

export function PhasePlaceholderPage({
  title,
  phaseLabel,
  description,
  isDatasetsRoute = false,
}: PhasePlaceholderPageProps) {
  const { user } = useAuth();
  const managesDatasets = canManageDatasets(user);

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-[20px] leading-7 font-semibold tracking-tight text-text-primary">
          {title}
        </h1>
        <Badge variant="info">{phaseLabel}</Badge>
      </div>

      <Card padding="lg">
        <CardHeader>
          <CardTitle as="h2" size="section">
            Not yet implemented in Phase F2
          </CardTitle>
          <CardDescription>{description}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <Alert variant="info" role="region" aria-label={`${title} phase status`}>
            This module is intentionally unpopulated in Phase F2 so zero fabricated rows, metrics,
            or interactive stubs are displayed before API integration in {phaseLabel}.
          </Alert>

          {isDatasetsRoute ? (
            <Alert
              variant={managesDatasets ? "info" : "warning"}
              role="region"
              aria-label="Dataset role permissions"
            >
              {managesDatasets
                ? "Your role has full dataset permissions: read-only import history plus CSV upload and recovery workflows (Phase F4)."
                : "Read-only dataset import history is permitted for Investigator accounts. Dataset upload and import recovery actions require Administrator or Analyst roles and are disabled for your role."}
            </Alert>
          ) : null}
        </CardContent>
        <CardFooter>
          <Button asChild variant="secondary" size="sm">
            <Link to="/">Return to Workspace Overview</Link>
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}
