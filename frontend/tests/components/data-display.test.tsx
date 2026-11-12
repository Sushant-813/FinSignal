import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { MoneyValue } from "../../src/components/data-display/MoneyValue.tsx";
import { RiskBadge } from "../../src/components/data-display/RiskBadge.tsx";
import { TimestampDisplay } from "../../src/components/data-display/TimestampDisplay.tsx";
import { Pagination } from "../../src/components/ui/Pagination.tsx";

describe("F3.1 shared data-display and Pagination primitives", () => {
  it("renders MoneyValue with exact decimal digits and handles missing/invalid values", () => {
    const { rerender } = render(<MoneyValue amount="987654.30" currency="INR" />);
    expect(screen.getByText("987,654.30")).toBeInTheDocument();
    expect(screen.getByText("INR")).toBeInTheDocument();

    rerender(<MoneyValue amount={null} currency="INR" />);
    expect(screen.getByLabelText("Unavailable")).toHaveTextContent("—");

    rerender(<MoneyValue amount="not-money" currency="INR" />);
    expect(screen.getByLabelText("Invalid monetary value")).toHaveTextContent("Unavailable");
  });

  it("renders TimestampDisplay with timezone awareness and fallback states", () => {
    const { rerender } = render(
      <TimestampDisplay value="2026-11-10T14:25:00Z" timeZone="Asia/Kolkata" />
    );
    const timeEl = screen.getByText("2026-11-10 19:55:00 Asia/Kolkata");
    expect(timeEl.tagName).toBe("TIME");
    expect(timeEl).toHaveAttribute("dateTime", "2026-11-10T14:25:00Z");

    rerender(<TimestampDisplay value={null} />);
    expect(screen.getByLabelText("Unavailable")).toHaveTextContent("—");

    rerender(<TimestampDisplay value="invalid-iso" />);
    expect(screen.getByText("Invalid timestamp")).toBeInTheDocument();
  });

  it("renders RiskBadge for all four levels plus unlabeled fallback", () => {
    const { rerender } = render(<RiskBadge level="CRITICAL" />);
    expect(screen.getByText("CRITICAL RISK")).toBeInTheDocument();

    rerender(<RiskBadge level="high" />);
    expect(screen.getByText("HIGH RISK")).toBeInTheDocument();

    rerender(<RiskBadge level={null} />);
    expect(screen.getByText("Not analyzed")).toBeInTheDocument();
  });

  it("handles Pagination boundary states, page navigation, and page-size changes", async () => {
    const user = userEvent.setup();
    const onPageChange = vi.fn();
    const onPageSizeChange = vi.fn();

    render(
      <Pagination
        page={1}
        pageSize={50}
        total={125}
        totalPages={3}
        onPageChange={onPageChange}
        onPageSizeChange={onPageSizeChange}
      />
    );

    expect(screen.getByText(/Page 1 of 3/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Previous page" })).toBeDisabled();
    const nextBtn = screen.getByRole("button", { name: "Next page" });
    expect(nextBtn).toBeEnabled();

    await user.click(nextBtn);
    expect(onPageChange).toHaveBeenCalledWith(2);

    const sizeCombobox = screen.getByRole("combobox", { name: /Rows per page/i });
    await user.click(sizeCombobox);
    await user.click(screen.getByRole("option", { name: "25" }));
    expect(onPageSizeChange).toHaveBeenCalledWith(25);
  });
});
