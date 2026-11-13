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
import { Input } from "../../../components/ui/Input.tsx";
import { getUserFriendlyErrorMessage, isApiClientError } from "../../../lib/api/errors.ts";
import { usePatchInvestigationMutation } from "../hooks/usePatchInvestigationMutation.ts";
import { UUID_REGEX } from "../schemas/investigation-filter-schema.ts";
import type { InvestigationDetailResponse } from "../types/investigations.types.ts";

export interface InvestigationAssignDialogProps {
  readonly isOpen: boolean;
  readonly onClose: () => void;
  readonly investigation: InvestigationDetailResponse;
}

export function InvestigationAssignDialog({
  isOpen,
  onClose,
  investigation,
}: InvestigationAssignDialogProps) {
  const [assigneeId, setAssigneeId] = useState(investigation.assigned_to ?? "");
  const [formatError, setFormatError] = useState<string | undefined>();

  const patchMutation = usePatchInvestigationMutation(investigation.id, {
    onSuccess: () => {
      onClose();
    },
  });

  const handleAssign = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setFormatError(undefined);

    const trimmed = assigneeId.trim();
    if (!trimmed) {
      setFormatError("Please enter a valid user UUID or choose Unassign.");
      return;
    }
    if (!UUID_REGEX.test(trimmed)) {
      setFormatError("User ID must be a valid UUID.");
      return;
    }

    patchMutation.mutate({
      assigned_to: trimmed,
    });
  };

  const handleUnassign = () => {
    setFormatError(undefined);
    patchMutation.mutate({
      assigned_to: null,
    });
  };

  const err = patchMutation.error;
  const isClientErr = isApiClientError(err);
  let errorMessage = getUserFriendlyErrorMessage(err);
  if (isClientErr) {
    if (err.code === "CASE_ALREADY_ASSIGNED" || err.status === 409) {
      errorMessage = "Assignment conflict: this investigation was modified or claimed concurrently.";
    } else if (err.code === "USER_NOT_FOUND") {
      errorMessage = "Assignee user not found. Verify the user UUID.";
    } else if (err.code === "USER_INACTIVE") {
      errorMessage = "The specified user account is inactive.";
    } else if (err.code === "INVALID_ASSIGNEE_ROLE") {
      errorMessage = "The specified user does not possess an eligible role for case assignment.";
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && !patchMutation.isPending && onClose()}>
      <DialogContent size="md" aria-describedby="assign-dialog-description">
        <DialogHeader>
          <DialogTitle>Assign Investigation</DialogTitle>
          <DialogDescription id="assign-dialog-description">
            Assign this investigation to an investigator or administrator, or remove current assignment.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleAssign} className="space-y-4">
          {patchMutation.isError && (
            <Alert
              variant="danger"
              role="alert"
              title="Assignment failed"
              requestId={isClientErr ? err.requestId : undefined}
            >
              {errorMessage}
            </Alert>
          )}

          <div className="space-y-1">
            <Input
              label="Assignee User UUID"
              placeholder="00000000-0000-4000-8000-000000000000"
              value={assigneeId}
              onChange={(e) => setAssigneeId(e.target.value)}
              disabled={patchMutation.isPending}
              error={formatError}
              required
            />
            <p className="text-[12px] text-text-muted">
              Enter the UUID of the target user with INVESTIGATOR or ADMIN role.
            </p>
          </div>

          <DialogFooter className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-between pt-2">
            <div>
              {investigation.assigned_to && (
                <Button
                  type="button"
                  variant="danger"
                  size="sm"
                  onClick={handleUnassign}
                  disabled={patchMutation.isPending}
                  data-testid="unassign-case-button"
                >
                  {patchMutation.isPending ? "Updating…" : "Unassign Case"}
                </Button>
              )}
            </div>

            <div className="flex gap-2">
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
                disabled={patchMutation.isPending}
                data-testid="confirm-assign-button"
              >
                {patchMutation.isPending ? "Assigning…" : "Assign Case"}
              </Button>
            </div>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
