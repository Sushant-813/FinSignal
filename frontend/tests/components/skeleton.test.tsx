import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Skeleton, TableSkeleton } from "../../src/components/ui/Skeleton.tsx";

describe("Skeleton", () => {
  it("renders decorative placeholders hidden from assistive technology", () => {
    const { container } = render(
      <div>
        <Skeleton variant="text" />
        <Skeleton variant="block" />
        <Skeleton variant="circle" />
      </div>
    );

    const skeletons = container.querySelectorAll("[aria-hidden='true']");
    expect(skeletons).toHaveLength(3);
  });

  it("renders TableSkeleton with configured rows, columns, and non-conflicting heights", () => {
    const { container } = render(<TableSkeleton rows={4} columns={3} />);
    const root = container.firstElementChild;
    expect(root).toHaveAttribute("aria-hidden", "true");
    // 1 header row + 4 body rows = 5 grids * 3 cells = 15 inner skeleton blocks
    const blocks = root?.querySelectorAll(".animate-pulse");
    expect(blocks).toHaveLength(15);

    const headerCells = root?.firstElementChild?.querySelectorAll(".animate-pulse");
    expect(headerCells).toHaveLength(3);
    headerCells?.forEach((cell) => {
      expect(cell.className).toContain("h-3.5");
      expect(cell.className).not.toContain("h-4");
    });

    const firstBodyCells = root?.children[1]?.querySelectorAll(".animate-pulse");
    expect(firstBodyCells).toHaveLength(3);
    firstBodyCells?.forEach((cell) => {
      expect(cell.className).toContain("h-4");
      expect(cell.className).not.toContain("h-3.5");
    });
  });
});
