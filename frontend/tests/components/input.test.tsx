import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createRef } from "react";
import { describe, expect, it } from "vitest";
import { Input } from "../../src/components/ui/Input.tsx";

describe("Input", () => {
  it("associates persistent label, hint, and error via aria-describedby and aria-invalid", async () => {
    const user = userEvent.setup();
    render(
      <Input
        label="Transaction ID"
        hint="Enter UUID identifier."
        error="Transaction ID is required."
        required
      />
    );

    const input = screen.getByLabelText(/Transaction ID/);
    await user.click(screen.getByText("Transaction ID", { selector: "label" }));
    expect(input).toHaveFocus();
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveAccessibleDescription("Enter UUID identifier. Transaction ID is required.");
  });

  it("supports hidden accessible labels, disabled, readOnly, and ref forwarding", async () => {
    const user = userEvent.setup();
    const ref = createRef<HTMLInputElement>();

    const { rerender } = render(
      <Input ref={ref} label="Search" hideLabel placeholder="Search..." />
    );

    const input = screen.getByLabelText("Search");
    expect(ref.current).toBe(input);

    rerender(<Input label="Namespace" defaultValue="SYNTHETIC" readOnly />);
    const readOnlyInput = screen.getByLabelText("Namespace");
    expect(readOnlyInput).toHaveAttribute("readonly");
    await user.type(readOnlyInput, "X");
    expect(readOnlyInput).toHaveValue("SYNTHETIC");

    rerender(<Input label="Amount" defaultValue="100.00" disabled />);
    const disabledInput = screen.getByLabelText("Amount");
    expect(disabledInput).toBeDisabled();
    expect(disabledInput.className).toContain("text-text-disabled");
    expect(disabledInput.className).not.toContain("text-text-primary");
    expect(disabledInput.className).not.toContain("bg-surface ");
  });

  it("emits mutually exclusive surface, text, and border utility classes per state", () => {
    const { rerender } = render(<Input label="Reference" />);
    const normalInput = screen.getByLabelText("Reference");
    expect(normalInput.className).toContain("text-text-primary");
    expect(normalInput.className).toContain("bg-surface");
    expect(normalInput.className).toContain("border-border-strong");
    expect(normalInput.className).not.toContain("text-text-disabled");
    expect(normalInput.className).not.toContain("border-danger");

    rerender(<Input label="Reference" readOnly />);
    const readOnlyInput = screen.getByLabelText("Reference");
    expect(readOnlyInput.className).toContain("text-text-secondary");
    expect(readOnlyInput.className).toContain("bg-surface-subtle");
    expect(readOnlyInput.className).toContain("border-border");
    expect(readOnlyInput.className).not.toContain("text-text-primary");
    expect(readOnlyInput.className).not.toContain("border-border-strong");

    rerender(<Input label="Reference" error="Invalid value" />);
    const errorInput = screen.getByLabelText("Reference");
    expect(errorInput.className).toContain("border-danger");
    expect(errorInput.className).not.toContain("border-border-strong");
    expect(errorInput.className).not.toContain("border-border ");
  });
});
