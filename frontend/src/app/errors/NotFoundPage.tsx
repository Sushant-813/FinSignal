import { Link } from "react-router";
import { Button } from "../../components/ui/Button.tsx";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "../../components/ui/Card.tsx";

export function NotFoundPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-canvas p-6">
      <Card as="section" aria-label="Page not found" className="w-full max-w-lg" padding="lg">
        <CardHeader>
          <CardTitle as="h1" size="page">
            Page not found
          </CardTitle>
          <CardDescription>
            The requested route does not exist or is not available in this workspace.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-[13px] leading-[19px] text-text-secondary">
            Check the web address or return to the FinSignal home view.
          </p>
        </CardContent>
        <CardFooter>
          <Button asChild variant="primary">
            <Link to="/">Return to home</Link>
          </Button>
        </CardFooter>
      </Card>
    </main>
  );
}
