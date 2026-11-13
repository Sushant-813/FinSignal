import { AlertTriangle } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Alert } from "../../../components/ui/Alert.tsx";
import { Button } from "../../../components/ui/Button.tsx";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../../../components/ui/Dialog.tsx";
import { Select } from "../../../components/ui/Select.tsx";
import { getUserFriendlyErrorMessage, isApiClientError } from "../../../lib/api/errors.ts";
import { useResolveInvestigationMutation } from "../hooks/useResolveInvestigationMutation.ts";
import { investigationResolveSchema } from "../schemas/investigation-mutations-schema.ts";
import type {
  InvestigationDetailResponse,
  InvestigationResolution,
} from "../types/investigations.types.ts";

export interface InvestigationResolveDialogProps {
  readonly isOpen: boolean;
  readonly onClose: () => void;
  readonly investigation: InvestigationDetailResponse;
}

const RESOLUTION_OPTIONS = [
  { value: "LEGITIMATE", label: "Legitimate (No Fraud Detected)" },
  { value: "SUSPICIOUS", label: "Suspicious (High Risk / Flagged)" },
  { value: "CONFIRMED_FRAUD", label: "Confirmed Fraud (Adverse Action)" },
  { value: "INCONCLUSIVE", label: "Inconclusive (Insufficient Evidence)" },
] as const;

export function InvestigationResolveDialog({
  isOpen,
  onClose,
  investigation,
}: InvestigationResolveDialogProps) {
  const [resolution, setResolution] = useState<InvestigationResolution>("LEGITIMATE");
  const [notes, setNotes] = useState("");
  const [fieldErrors, setFieldErrors] = useState<{
    resolution?: string | undefined;
    resolution_notes?: string | undefined;
  }>({});

  const resolveMutation = useResolveInvestigationMutation(investigation.id, {
    onSuccess: () => {
      onClose();
    },
  });

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setFieldErrors({});

    const parseResult = investigationResolveSchema.safeParse({
      resolution,
      resolution_notes: notes,
    });

    if (!parseResult.success) {
      const formatted = parseResult.error.format();
      setFieldErrors({
        resolution: formatted.resolution?._errors?.[0],
        resolution_notes: formatted.resolution_notes?._errors?.[0],
      });
      return;
    }

    resolveMutation.mutate({
      resolution: parseResult.data.resolution as InvestigationResolution,
      resolution_notes: parseResult.data.resolution_notes,
    });
  };

  const err = resolveMutation.error;
  const isClientErr = isApiClientError(err);
  let errorMessage = getUserFriendlyErrorMessage(err);
  if (isClientErr) {
    if (err.code === "INVALID_LIFECYCLE_TRANSITION" || err.status === 409) {
      errorMessage =
        "Resolution rejected: case must be in UNDER_REVIEW status and not already resolved.";
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && !resolveMutation.isPending && onClose()}>
      <DialogContent size="md" aria-describedby="resolve-dialog-description">
        <DialogHeader>
          <DialogTitle>Resolve Investigation Case</DialogTitle>
          <DialogDescription id="resolve-dialog-description">
            Complete formal resolution of case #{investigation.id.slice(0, 8)}.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <Alert variant="warning" role="alert">
            <div className="flex items-start gap-2">
              <AlertTriangle className="h-4 w-4 text-warning shrink-0 mt-0.5" aria-hidden="true" />
              <div>
                <p className="font-medium text-text-primary">Resolution is permanent and irreversible.</p>
                <p className="mt-0.5 text-xs text-text-secondary">
                  Once resolved, this case becomes strictly read-only. No further status changes,
                  assignee modifications, or transaction links can be made.
                </p>
              </div>
            </div>
          </Alert>

          {resolveMutation.isError && (
            <Alert
              variant="danger"
              role="alert"
              title="Resolution failed"
              requestId={isClientErr ? err.requestId : undefined}
            >
              {errorMessage}
            </Alert>
          )}

          <div className="space-y-1">
            <Select
              label="Resolution Outcome"
              value={resolution}
              onValueChange={(val) => setResolution(val as InvestigationResolution)}
              options={RESOLUTION_OPTIONS}
              disabled={resolveMutation.isPending}
              error={fieldErrors.resolution}
              aria-label="Resolution outcome"
            />
          </div>

          <div className="space-y-1">
            <label
              htmlFor="resolution-notes-input"
              className="block text-xs font-medium text-text-secondary"
            >
              Resolution Notes (Mandatory)
            </label>
            <textarea
              id="resolution-notes-input"
              rows={4}
              className={`w-full rounded-input border bg-surface p-2.5 text-sm text-text-primary placeholder:text-text-muted focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 disabled:opacity-50 ${
                fieldErrors.resolution_notes ? "border-danger focus:border-danger focus:ring-danger" : "border-border"
              }`}
              placeholder="Document the analytical findings, evidence basis, and justification for this case verdict…"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              disabled={resolveMutation.isPending}
              required
            />
            {fieldErrors.resolution_notes && (
              <p className="text-xs text-danger">{fieldErrors.resolution_notes}</p>
            )}
          </div>

          <DialogFooter className="pt-2">
            <Button
              type="button"
              variant="secondary"
              onClick={onClose}
              disabled={resolveMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              disabled={resolveMutation.isPending}
              data-testid="confirm-resolve-case-button"
            >
              {resolveMutation.isPending ? "Resolving Case…" : "Confirm Resolution"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
