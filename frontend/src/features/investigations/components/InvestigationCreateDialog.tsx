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
import { Select } from "../../../components/ui/Select.tsx";
import { getUserFriendlyErrorMessage, isApiClientError } from "../../../lib/api/errors.ts";
import { useCreateInvestigationMutation } from "../hooks/useCreateInvestigationMutation.ts";
import { investigationCreateSchema } from "../schemas/investigation-mutations-schema.ts";
import type { InvestigationPriority } from "../types/investigations.types.ts";

export interface InvestigationCreateDialogProps {
  readonly isOpen: boolean;
  readonly onClose: () => void;
  readonly defaultTransactionId?: string | undefined;
  readonly isTransactionIdFixed?: boolean | undefined;
}

const PRIORITY_OPTIONS = [
  { value: "LOW", label: "Low" },
  { value: "MEDIUM", label: "Medium (Default)" },
  { value: "HIGH", label: "High" },
  { value: "CRITICAL", label: "Critical" },
] as const;

export function InvestigationCreateDialog({
  isOpen,
  onClose,
  defaultTransactionId = "",
  isTransactionIdFixed = false,
}: InvestigationCreateDialogProps) {
  const [transactionId, setTransactionId] = useState(defaultTransactionId);
  const [priority, setPriority] = useState<InvestigationPriority>("MEDIUM");
  const [fieldErrors, setFieldErrors] = useState<{ transaction_id?: string | undefined }>({});

  const createMutation = useCreateInvestigationMutation({
    onSuccess: () => {
      onClose();
    },
  });

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setFieldErrors({});

    const parseResult = investigationCreateSchema.safeParse({
      transaction_id: transactionId,
      priority,
    });

    if (!parseResult.success) {
      const formatted = parseResult.error.format();
      setFieldErrors({
        transaction_id: formatted.transaction_id?._errors?.[0],
      });
      return;
    }

    createMutation.mutate({
      transaction_id: parseResult.data.transaction_id,
      priority: parseResult.data.priority as InvestigationPriority,
    });
  };

  const handleOpenChange = (open: boolean) => {
    if (!open) {
      if (!createMutation.isPending) {
        setFieldErrors({});
        createMutation.reset();
        onClose();
      }
    }
  };

  const err = createMutation.error;
  const isClientErr = isApiClientError(err);

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogContent size="md" aria-describedby="create-investigation-description">
        <DialogHeader>
          <DialogTitle>Create Investigation Case</DialogTitle>
          <DialogDescription id="create-investigation-description">
            Open a formal investigation case anchored to a target primary transaction.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {createMutation.isError && (
            <Alert
              variant="danger"
              role="alert"
              title="Failed to create investigation"
              requestId={isClientErr ? err.requestId : undefined}
            >
              {getUserFriendlyErrorMessage(err)}
            </Alert>
          )}

          <div className="space-y-1">
            <Input
              label="Primary Transaction ID (UUID)"
              value={transactionId}
              onChange={(e) => setTransactionId(e.target.value)}
              disabled={isTransactionIdFixed || createMutation.isPending}
              placeholder="00000000-0000-4000-8000-000000000000"
              required
              error={fieldErrors.transaction_id}
            />
            {isTransactionIdFixed && (
              <p className="text-[12px] text-text-muted">
                Pre-selected from current transaction detail context.
              </p>
            )}
          </div>

          <div className="space-y-1">
            <Select
              label="Triage Priority"
              value={priority}
              onValueChange={(val) => setPriority(val as InvestigationPriority)}
              options={PRIORITY_OPTIONS}
              disabled={createMutation.isPending}
              aria-label="Investigation priority"
            />
            <p className="text-[12px] text-text-muted">
              Defaults to Medium. Can be updated later by authorized investigators or admins.
            </p>
          </div>

          <DialogFooter className="pt-2">
            <Button
              type="button"
              variant="secondary"
              onClick={onClose}
              disabled={createMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              disabled={createMutation.isPending}
              data-testid="create-investigation-submit"
            >
              {createMutation.isPending ? "Creating Case…" : "Create Investigation"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
