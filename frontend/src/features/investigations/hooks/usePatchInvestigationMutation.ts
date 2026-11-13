import { useMutation, useQueryClient } from "@tanstack/react-query";
import { isApiClientError } from "../../../lib/api/errors.ts";
import { investigationKeys } from "../../../lib/api/query-keys.ts";
import { patchInvestigation } from "../api/investigations-api.ts";
import type {
  InvestigationDetailResponse,
  InvestigationPatchRequest,
} from "../types/investigations.types.ts";

export interface UsePatchInvestigationOptions {
  readonly onSuccess?: ((data: InvestigationDetailResponse) => void) | undefined;
  readonly onError?: ((error: unknown) => void) | undefined;
}

export function usePatchInvestigationMutation(
  investigationId: string,
  options: UsePatchInvestigationOptions = {}
) {
  const queryClient = useQueryClient();
  const { onSuccess, onError } = options;

  return useMutation<InvestigationDetailResponse, unknown, InvestigationPatchRequest>({
    mutationFn: (payload) => patchInvestigation(investigationId, payload),
    retry: false,
    onSuccess: (data) => {
      // Invalidate detail and all list views
      void queryClient.invalidateQueries({
        queryKey: investigationKeys.detail(investigationId),
      });
      void queryClient.invalidateQueries({
        queryKey: investigationKeys.lists(),
      });
      if (onSuccess) {
        onSuccess(data);
      }
    },
    onError: (error) => {
      // On 409 conflict, reload authoritative server state immediately
      if (isApiClientError(error) && error.status === 409) {
        void queryClient.invalidateQueries({
          queryKey: investigationKeys.detail(investigationId),
        });
        void queryClient.invalidateQueries({
          queryKey: investigationKeys.lists(),
        });
      }
      if (onError) {
        onError(error);
      }
    },
  });
}
