import { render, screen } from "@testing-library/react";
import { ShieldAlert } from "lucide-react";
import { describe, expect, it } from "vitest";
import { Badge } from "../../src/components/ui/Badge.tsx";

describe("Badge", () => {
  it("renders visible semantic and risk severity labels without color-only encoding", () => {
    const { rerender } = render(<Badge variant="risk-critical">CRITICAL</Badge>);
    const critical = screen.getByText("CRITICAL");
    expect(critical.parentElement?.className).toContain("text-risk-critical");

    rerender(<Badge variant="risk-high">HIGH</Badge>);
    expect(screen.getByText("HIGH").parentElement?.className).toContain("text-risk-high");

    rerender(<Badge variant="risk-medium">MEDIUM</Badge>);
    expect(screen.getByText("MEDIUM").parentElement?.className).toContain("text-risk-medium");

    rerender(<Badge variant="risk-low">LOW</Badge>);
    expect(screen.getByText("LOW").parentElement?.className).toContain("text-risk-low");

    rerender(<Badge variant="brand">ACTIVE</Badge>);
    expect(screen.getByText("ACTIVE").parentElement?.className).toContain("text-brand-700");

    rerender(
      <Badge variant="warning" size="md" icon={<ShieldAlert className="h-3 w-3" />}>
        STALE
      </Badge>
    );
    const stale = screen.getByText("STALE");
    expect(stale.parentElement?.className).toContain("text-warning");
  });
});
