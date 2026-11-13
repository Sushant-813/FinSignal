import { useMutation, useQueryClient } from "@tanstack/react-query";
import { isApiClientError } from "../../../lib/api/errors.ts";
import { investigationKeys } from "../../../lib/api/query-keys.ts";
import { addRelatedTransaction } from "../api/investigations-api.ts";
import type {
  InvestigationRelatedTransactionAddRequest,
  InvestigationTransactionItem,
} from "../types/investigations.types.ts";

export interface UseLinkTransactionOptions {
  readonly onSuccess?: ((data: InvestigationTransactionItem) => void) | undefined;
  readonly onError?: ((error: unknown) => void) | undefined;
}

export function useLinkTransactionMutation(
  investigationId: string,
  options: UseLinkTransactionOptions = {}
) {
  const queryClient = useQueryClient();
  const { onSuccess, onError } = options;

  return useMutation<
    InvestigationTransactionItem,
    unknown,
    InvestigationRelatedTransactionAddRequest
  >({
    mutationFn: (payload) => addRelatedTransaction(investigationId, payload),
    retry: false,
    onSuccess: (data) => {
      void queryClient.invalidateQueries({
        queryKey: investigationKeys.detail(investigationId),
      });
      if (onSuccess) {
        onSuccess(data);
      }
    },
    onError: (error) => {
      if (isApiClientError(error) && error.status === 409) {
        void queryClient.invalidateQueries({
          queryKey: investigationKeys.detail(investigationId),
        });
      }
      if (onError) {
        onError(error);
      }
    },
  });
}

