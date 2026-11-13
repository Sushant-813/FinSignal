import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { InvestigationPriorityBadge } from "../../src/features/investigations/components/InvestigationPriorityBadge.tsx";
import { InvestigationResolutionBadge } from "../../src/features/investigations/components/InvestigationResolutionBadge.tsx";
import { InvestigationStatusBadge } from "../../src/features/investigations/components/InvestigationStatusBadge.tsx";
import type {
  InvestigationPriority,
  InvestigationResolution,
  InvestigationStatus,
} from "../../src/features/investigations/types/investigations.types.ts";

describe("Investigation badges (F5.2)", () => {
  it("renders all investigation statuses with semantic text and testids", () => {
    const statuses: InvestigationStatus[] = ["OPEN", "UNDER_REVIEW", "RESOLVED"];
    for (const status of statuses) {
      const { unmount } = render(<InvestigationStatusBadge status={status} />);
      const badge = screen.getByTestId(`investigation-status-badge-${status.toLowerCase()}`);
      expect(badge).toBeInTheDocument();
      unmount();
    }
  });

  it("renders all investigation priorities correctly", () => {
    const priorities: InvestigationPriority[] = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];
    for (const priority of priorities) {
      const { unmount } = render(<InvestigationPriorityBadge priority={priority} />);
      const badge = screen.getByTestId(`investigation-priority-badge-${priority.toLowerCase()}`);
      expect(badge).toBeInTheDocument();
      unmount();
    }
  });

  it("renders all resolution outcomes correctly", () => {
    const resolutions: InvestigationResolution[] = [
      "LEGITIMATE",
      "SUSPICIOUS",
      "CONFIRMED_FRAUD",
      "INCONCLUSIVE",
    ];
    for (const resolution of resolutions) {
      const { unmount } = render(<InvestigationResolutionBadge resolution={resolution} />);
      const badge = screen.getByTestId(
        `investigation-resolution-badge-${resolution.toLowerCase()}`
      );
      expect(badge).toBeInTheDocument();
      unmount();
    }
  });
});

