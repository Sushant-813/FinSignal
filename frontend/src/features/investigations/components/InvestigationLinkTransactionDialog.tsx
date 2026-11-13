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
import { useLinkTransactionMutation } from "../hooks/useLinkTransactionMutation.ts";
import { UUID_REGEX } from "../schemas/investigation-filter-schema.ts";

export interface InvestigationLinkTransactionDialogProps {
  readonly isOpen: boolean;
  readonly onClose: () => void;
  readonly investigationId: string;
}

export function InvestigationLinkTransactionDialog({
  isOpen,
  onClose,
  investigationId,
}: InvestigationLinkTransactionDialogProps) {
  const [transactionId, setTransactionId] = useState("");
  const [formatError, setFormatError] = useState<string | undefined>();

  const linkMutation = useLinkTransactionMutation(investigationId, {
    onSuccess: () => {
      onClose();
    },
  });

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setFormatError(undefined);

    const trimmed = transactionId.trim();
    if (!trimmed) {
      setFormatError("Transaction ID is required.");
      return;
    }
    if (!UUID_REGEX.test(trimmed)) {
      setFormatError("Transaction ID must be a valid UUID.");
      return;
    }

    linkMutation.mutate({
      transaction_id: trimmed,
    });
  };

  const err = linkMutation.error;
  const isClientErr = isApiClientError(err);
  let errorMessage = getUserFriendlyErrorMessage(err);
  if (isClientErr) {
    if (err.code === "NAMESPACE_MISMATCH") {
      errorMessage = "Namespace mismatch: the target transaction belongs to a different partition.";
    } else if (err.code === "TRANSACTION_NOT_RELATED") {
      errorMessage =
        "The target transaction is not related to this investigation's primary transaction.";
    } else if (err.code === "TRANSACTION_ALREADY_LINKED") {
      errorMessage = "This transaction is already linked to the current investigation.";
    } else if (err.code === "INVESTIGATION_ALREADY_RESOLVED") {
      errorMessage = "Cannot link transactions to a resolved investigation.";
    } else if (err.code === "TRANSACTION_NOT_FOUND" || err.status === 404) {
      errorMessage = "Transaction record not found. Verify the UUID.";
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && !linkMutation.isPending && onClose()}>
      <DialogContent size="md" aria-describedby="link-dialog-description">
        <DialogHeader>
          <DialogTitle>Link Related Transaction</DialogTitle>
          <DialogDescription id="link-dialog-description">
            Attach an existing financial transaction as related context for this case.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {linkMutation.isError && (
            <Alert
              variant="danger"
              role="alert"
              title="Linking failed"
              requestId={isClientErr ? err.requestId : undefined}
            >
              {errorMessage}
            </Alert>
          )}

          <div className="space-y-1">
            <Input
              label="Related Transaction UUID"
              placeholder="00000000-0000-4000-8000-000000000000"
              value={transactionId}
              onChange={(e) => setTransactionId(e.target.value)}
              disabled={linkMutation.isPending}
              error={formatError}
              required
            />
            <p className="text-[12px] text-text-muted">
              The backend strictly validates namespace partition and relational relevance.
            </p>
          </div>

          <DialogFooter className="pt-2">
            <Button
              type="button"
              variant="secondary"
              onClick={onClose}
              disabled={linkMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              disabled={linkMutation.isPending}
              data-testid="confirm-link-transaction-button"
            >
              {linkMutation.isPending ? "Linking…" : "Link Transaction"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
