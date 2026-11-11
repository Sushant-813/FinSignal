import { describe, expect, it } from "vitest";
import { cn } from "../../src/lib/utils/cn.ts";

describe("cn", () => {
  it("joins truthy class strings and ignores falsy or blank values", () => {
    expect(cn("base", false, null, undefined, "   ", "active")).toBe("base active");
  });

  it("preserves both classes without conflict resolution (simple joiner contract)", () => {
    expect(cn("px-4 text-sm", "px-8")).toBe("px-4 text-sm px-8");
  });
});
