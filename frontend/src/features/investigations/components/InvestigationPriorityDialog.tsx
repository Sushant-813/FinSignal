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
import { usePatchInvestigationMutation } from "../hooks/usePatchInvestigationMutation.ts";
import type {
  InvestigationDetailResponse,
  InvestigationPriority,
} from "../types/investigations.types.ts";

export interface InvestigationPriorityDialogProps {
  readonly isOpen: boolean;
  readonly onClose: () => void;
  readonly investigation: InvestigationDetailResponse;
}

const PRIORITY_OPTIONS = [
  { value: "LOW", label: "Low" },
  { value: "MEDIUM", label: "Medium" },
  { value: "HIGH", label: "High" },
  { value: "CRITICAL", label: "Critical" },
] as const;

export function InvestigationPriorityDialog({
  isOpen,
  onClose,
  investigation,
}: InvestigationPriorityDialogProps) {
  const [priority, setPriority] = useState<InvestigationPriority>(investigation.priority);

  const patchMutation = usePatchInvestigationMutation(investigation.id, {
    onSuccess: () => {
      onClose();
    },
  });

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (priority === investigation.priority) {
      onClose();
      return;
    }
    patchMutation.mutate({
      priority,
    });
  };

  const err = patchMutation.error;
  const isClientErr = isApiClientError(err);

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && !patchMutation.isPending && onClose()}>
      <DialogContent size="sm" aria-describedby="priority-dialog-description">
        <DialogHeader>
          <DialogTitle>Update Case Priority</DialogTitle>
          <DialogDescription id="priority-dialog-description">
            Change triage priority for investigation #{investigation.id.slice(0, 8)}.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {patchMutation.isError && (
            <Alert
              variant="danger"
              role="alert"
              title="Failed to update priority"
              requestId={isClientErr ? err.requestId : undefined}
            >
              {getUserFriendlyErrorMessage(err)}
            </Alert>
          )}

          <div className="space-y-1">
            <Select
              label="Priority Level"
              value={priority}
              onValueChange={(val) => setPriority(val as InvestigationPriority)}
              options={PRIORITY_OPTIONS}
              disabled={patchMutation.isPending}
              aria-label="Investigation priority level"
            />
          </div>

          <DialogFooter className="pt-2">
            <Button
              type="button"
              variant="secondary"
              onClick={onClose}
              disabled={patchMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              disabled={patchMutation.isPending || priority === investigation.priority}
              data-testid="confirm-priority-button"
            >
              {patchMutation.isPending ? "Updating…" : "Update Priority"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
