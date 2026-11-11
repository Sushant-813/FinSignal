import { zodResolver } from "@hookform/resolvers/zod";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useForm } from "react-hook-form";
import { describe, expect, it, vi } from "vitest";
import { z } from "zod";
import { Button } from "../../src/components/ui/Button.tsx";
import { Input } from "../../src/components/ui/Input.tsx";

const triageFormSchema = z.object({
  reference: z
    .string()
    .trim()
    .min(3, "Reference must be at least 3 characters.")
    .max(32, "Reference must not exceed 32 characters."),
  severity: z.enum(["LOW", "MEDIUM", "HIGH", "CRITICAL"]),
  tags: z.array(z.string().trim().min(1).max(24)).max(5, "At most 5 tags allowed."),
});

type TriageFormValues = z.infer<typeof triageFormSchema>;

function TriageFormHarness({ onValidSubmit }: { onValidSubmit: (data: TriageFormValues) => void }) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<TriageFormValues>({
    resolver: zodResolver(triageFormSchema),
    defaultValues: {
      reference: "",
      severity: "HIGH",
      tags: ["velocity"],
    },
  });

  return (
    <form onSubmit={handleSubmit(onValidSubmit)} noValidate>
      <Input label="Case reference" error={errors.reference?.message} {...register("reference")} />
      <Button type="submit" variant="primary">
        Save triage
      </Button>
    </form>
  );
}

describe("Zod 4 validation & React Hook Form resolver compatibility", () => {
  it("validates constrained objects, enums, and bounded collections with Zod 4", () => {
    const valid = triageFormSchema.safeParse({
      reference: "INV-00123",
      severity: "CRITICAL",
      tags: ["aml", "structuring"],
    });
    expect(valid.success).toBe(true);

    const oversizedTags = triageFormSchema.safeParse({
      reference: "INV-00123",
      severity: "HIGH",
      tags: ["t1", "t2", "t3", "t4", "t5", "t6"],
    });
    expect(oversizedTags.success).toBe(false);
    if (!oversizedTags.success) {
      expect(oversizedTags.error.issues[0]?.message).toBe("At most 5 tags allowed.");
    }
  });

  it("integrates zodResolver cleanly with React Hook Form and accessible Input errors", async () => {
    const user = userEvent.setup();
    const onValidSubmit = vi.fn();

    render(<TriageFormHarness onValidSubmit={onValidSubmit} />);

    await user.click(screen.getByRole("button", { name: "Save triage" }));

    const input = screen.getByLabelText("Case reference");
    await waitFor(() => {
      expect(input).toHaveAttribute("aria-invalid", "true");
    });
    expect(screen.getByText("Reference must be at least 3 characters.")).toBeInTheDocument();
    expect(onValidSubmit).not.toHaveBeenCalled();

    await user.type(input, "CASE_2026_01");
    await user.click(screen.getByRole("button", { name: "Save triage" }));

    await waitFor(() => {
      expect(onValidSubmit).toHaveBeenCalledWith(
        {
          reference: "CASE_2026_01",
          severity: "HIGH",
          tags: ["velocity"],
        },
        expect.anything()
      );
    });
  });
});

