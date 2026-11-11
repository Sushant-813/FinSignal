import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Plus } from "lucide-react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Button, type ButtonProps } from "../../src/components/ui/Button.tsx";

describe("Button", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });
  it("renders variants and sizes with native button defaults", () => {
    const { rerender } = render(<Button variant="primary">Create investigation</Button>);
    const btn = screen.getByRole("button", { name: "Create investigation" });
    expect(btn).toHaveAttribute("type", "button");
    expect(btn.className).toContain("bg-brand-700");

    rerender(
      <Button variant="secondary" size="sm">
        Secondary
      </Button>
    );
    expect(screen.getByRole("button", { name: "Secondary" }).className).toContain("bg-surface");

    rerender(
      <Button variant="tertiary" size="lg">
        Tertiary
      </Button>
    );
    expect(screen.getByRole("button", { name: "Tertiary" }).className).toContain("bg-transparent");

    rerender(<Button variant="danger">Delete</Button>);
    expect(screen.getByRole("button", { name: "Delete" }).className).toContain("bg-danger");
  });

  it("supports icon-only buttons with accessible names", () => {
    render(
      <Button size="icon" aria-label="Add item">
        <Plus className="h-4 w-4" aria-hidden="true" />
      </Button>
    );
    expect(screen.getByRole("button", { name: "Add item" })).toBeInTheDocument();
  });

  it("sets disabled and aria-busy when loading and blocks click interactions", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();

    render(
      <Button isLoading onClick={onClick}>
        Run analysis
      </Button>
    );

    const btn = screen.getByRole("button", { name: "Run analysis" });
    expect(btn).toBeDisabled();
    expect(btn).toHaveAttribute("aria-busy", "true");
    await user.click(btn);
    expect(onClick).not.toHaveBeenCalled();
  });

  it("blocks clicks when disabled", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();

    render(
      <Button disabled onClick={onClick}>
        Submit
      </Button>
    );

    const btn = screen.getByRole("button", { name: "Submit" });
    expect(btn).toBeDisabled();
    await user.click(btn);
    expect(onClick).not.toHaveBeenCalled();
  });

  it("renders child anchor cleanly with asChild without invalid disabled attribute", () => {
    render(
      <Button asChild variant="secondary">
        <a href="/transactions">View transactions</a>
      </Button>
    );

    const link = screen.getByRole("link", { name: "View transactions" });
    expect(link).toHaveAttribute("href", "/transactions");
    expect(link).not.toHaveAttribute("disabled");
    expect(link.className).toContain("bg-surface");
  });

  it("throws in development when asChild is coerced with disabled or isLoading", () => {
    const invalidProps = {
      asChild: true,
      disabled: true,
      children: <a href="/">Home</a>,
    } as unknown as ButtonProps;

    expect(() => render(<Button {...invalidProps} />)).toThrow(
      /'disabled' and 'isLoading' cannot be used with 'asChild'/
    );
  });

  it("forwards valid slot props and strips disabled/isLoading when DEV guard is inactive", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn((event: { preventDefault: () => void }) => {
      event.preventDefault();
    });
    vi.stubEnv("DEV", false);

    const coercedProps = {
      asChild: true,
      disabled: true,
      isLoading: true,
      "data-testid": "slotted-link",
      onClick,
      children: <a href="/cases">Cases</a>,
    } as unknown as ButtonProps;

    render(<Button {...coercedProps} />);

    const link = screen.getByTestId("slotted-link");
    expect(link).toHaveAttribute("href", "/cases");
    expect(link).not.toHaveAttribute("disabled");
    expect(link).not.toHaveAttribute("isLoading");
    expect(link).not.toHaveAttribute("aria-busy");

    await user.click(link);
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});
