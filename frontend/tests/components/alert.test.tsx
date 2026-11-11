import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Alert } from "../../src/components/ui/Alert.tsx";
import { Button } from "../../src/components/ui/Button.tsx";

describe("Alert", () => {
  it("defaults to non-interruptive role='status' across info, success, warning, and danger", () => {
    const { rerender } = render(<Alert variant="info">Informational notice</Alert>);
    expect(screen.getByRole("status")).toHaveTextContent("Informational notice");

    rerender(<Alert variant="success">Saved successfully</Alert>);
    expect(screen.getByRole("status")).toHaveTextContent("Saved successfully");

    rerender(<Alert variant="warning">Summary is stale</Alert>);
    expect(screen.getByRole("status")).toHaveTextContent("Summary is stale");

    rerender(<Alert variant="danger">Failed to load panel</Alert>);
    expect(screen.getByRole("status")).toHaveTextContent("Failed to load panel");
  });

  it("supports explicit role='alert' for urgent errors and role='region' for static notices", () => {
    const { rerender } = render(
      <Alert variant="danger" role="alert" title="Submission failed">
        Unable to resolve case.
      </Alert>
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Unable to resolve case.");

    rerender(
      <Alert variant="warning" role="region" title="Read-only case">
        Resolved cases cannot be modified.
      </Alert>
    );
    expect(screen.getByRole("region", { name: "Read-only case" })).toHaveTextContent(
      "Resolved cases cannot be modified."
    );
  });

  it("renders title, requestId, action slot, and escapes text safely", async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();

    render(
      <Alert
        variant="danger"
        role="alert"
        title="Request error"
        requestId="req-9988"
        action={
          <Button size="sm" variant="secondary" onClick={onRetry}>
            Retry
          </Button>
        }
      >
        {"<script>alert(1)</script>"}
      </Alert>
    );

    expect(screen.getByText("Request error")).toBeInTheDocument();
    expect(screen.getByText("Request ID: req-9988")).toBeInTheDocument();
    expect(screen.getByText("<script>alert(1)</script>")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});
