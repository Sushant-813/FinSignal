import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Button } from "../../src/components/ui/Button.tsx";
import { EmptyState } from "../../src/components/ui/EmptyState.tsx";

describe("EmptyState", () => {
  it("distinguishes empty collection from filtered no-results state and triggers action", async () => {
    const user = userEvent.setup();
    const onClear = vi.fn();

    const { rerender, container } = render(
      <EmptyState
        variant="empty"
        title="No investigations yet"
        description="Create an investigation from a transaction detail view."
      />
    );

    expect(container.firstElementChild).toHaveAttribute("data-empty-variant", "empty");
    expect(screen.getByRole("heading", { name: "No investigations yet" })).toBeInTheDocument();

    rerender(
      <EmptyState
        variant="no-results"
        title="No matching transactions"
        description="Try adjusting your date range or currency filter."
        action={
          <Button variant="secondary" onClick={onClear}>
            Clear filters
          </Button>
        }
      />
    );

    expect(container.firstElementChild).toHaveAttribute("data-empty-variant", "no-results");
    await user.click(screen.getByRole("button", { name: "Clear filters" }));
    expect(onClear).toHaveBeenCalledTimes(1);
  });
});
