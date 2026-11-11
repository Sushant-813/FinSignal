import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "../../src/components/ui/Card.tsx";

describe("Card", () => {
  it("renders composable semantic Card sections with padding and elevation options", () => {
    render(
      <Card as="section" aria-label="Case summary" padding="lg" elevated>
        <CardHeader>
          <CardTitle as="h3">Investigation Overview</CardTitle>
          <CardDescription>Primary transaction facts and metadata.</CardDescription>
        </CardHeader>
        <CardContent>Status: OPEN</CardContent>
        <CardFooter>Footer actions</CardFooter>
      </Card>
    );

    const section = screen.getByRole("region", { name: "Case summary" });
    expect(section.className).toContain("shadow-card");
    expect(section.className).toContain("p-6");
    expect(
      screen.getByRole("heading", { level: 3, name: "Investigation Overview" })
    ).toBeInTheDocument();
    expect(screen.getByText("Primary transaction facts and metadata.")).toBeInTheDocument();
    expect(screen.getByText("Status: OPEN")).toBeInTheDocument();
    expect(screen.getByText("Footer actions")).toBeInTheDocument();
  });
});
