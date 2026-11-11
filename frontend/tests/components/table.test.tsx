import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableContainer,
  TableHead,
  TableHeader,
  TableRow,
} from "../../src/components/ui/Table.tsx";

describe("Table", () => {
  it("renders semantic headers, tabular-numeric monetary strings without coercion, and sortable columns", async () => {
    const user = userEvent.setup();
    const onSort = vi.fn();

    render(
      <TableContainer>
        <Table>
          <TableCaption>Recent transactions</TableCaption>
          <TableHeader>
            <TableRow>
              <TableHead>Reference</TableHead>
              <TableHead align="right" sortDirection="desc" onSort={onSort}>
                Amount
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow interactive>
              <TableCell>TXN_00000100</TableCell>
              <TableCell numeric>1250.50 INR</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </TableContainer>
    );

    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByText("Recent transactions")).toBeInTheDocument();

    const refHeader = screen.getByRole("columnheader", { name: "Reference" });
    expect(refHeader).toHaveAttribute("scope", "col");

    const amountHeader = screen.getByRole("columnheader", { name: "Amount" });
    expect(amountHeader).toHaveAttribute("aria-sort", "descending");

    const amountCell = screen.getByRole("cell", { name: "1250.50 INR" });
    expect(amountCell.className).toContain("tabular-nums");
    expect(amountCell.className).toContain("text-right");

    const sortButton = screen.getByRole("button", { name: "Amount" });
    await user.click(sortButton);
    expect(onSort).toHaveBeenCalledTimes(1);
  });
});
