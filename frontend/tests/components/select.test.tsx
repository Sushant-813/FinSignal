import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Select } from "../../src/components/ui/Select.tsx";

const priorityOptions = [
  { value: "LOW", label: "Low" },
  { value: "MEDIUM", label: "Medium" },
  { value: "HIGH", label: "High" },
  { value: "CRITICAL", label: "Critical", disabled: true },
];

describe("Select", () => {
  it("opens, supports keyboard selection, and calls onValueChange", async () => {
    const user = userEvent.setup();
    const onValueChange = vi.fn();

    render(
      <Select
        label="Priority"
        placeholder="Choose priority"
        options={priorityOptions}
        onValueChange={onValueChange}
      />
    );

    const trigger = screen.getByRole("combobox", { name: "Priority" });
    await user.click(trigger);

    const optionHigh = screen.getByRole("option", { name: "High" });
    expect(optionHigh).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Critical" })).toHaveAttribute(
      "aria-disabled",
      "true"
    );

    await user.click(optionHigh);
    expect(onValueChange).toHaveBeenCalledWith("HIGH");
    expect(trigger).toHaveTextContent("High");
  });

  it("dismisses on Escape, restores focus, and exposes error semantics", async () => {
    const user = userEvent.setup();

    render(
      <Select
        label="Status"
        options={priorityOptions}
        error="Status selection is required."
        hint="Pick initial triage priority."
      />
    );

    const trigger = screen.getByRole("combobox", { name: "Status" });
    expect(trigger).toHaveAttribute("aria-invalid", "true");
    expect(trigger).toHaveAccessibleDescription(
      "Pick initial triage priority. Status selection is required."
    );

    trigger.focus();
    await user.keyboard("{Enter}");
    expect(screen.getByRole("listbox")).toBeInTheDocument();

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });

  it("rejects empty string option values", () => {
    expect(() =>
      render(<Select label="Invalid" options={[{ value: "", label: "All" }]} />)
    ).toThrow(/non-empty strings/);
  });

  it("supports disabled state", () => {
    render(<Select label="Disabled select" options={priorityOptions} disabled />);
    expect(screen.getByRole("combobox", { name: "Disabled select" })).toBeDisabled();
  });
});
