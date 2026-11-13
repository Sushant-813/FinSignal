import { useMutation, useQueryClient } from "@tanstack/react-query";
import { isApiClientError } from "../../../lib/api/errors.ts";
import { investigationKeys } from "../../../lib/api/query-keys.ts";
import { resolveInvestigation } from "../api/investigations-api.ts";
import type {
  InvestigationDetailResponse,
  InvestigationResolveRequest,
} from "../types/investigations.types.ts";

export interface UseResolveInvestigationOptions {
  readonly onSuccess?: ((data: InvestigationDetailResponse) => void) | undefined;
  readonly onError?: ((error: unknown) => void) | undefined;
}

export function useResolveInvestigationMutation(
  investigationId: string,
  options: UseResolveInvestigationOptions = {}
) {
  const queryClient = useQueryClient();
  const { onSuccess, onError } = options;

  return useMutation<InvestigationDetailResponse, unknown, InvestigationResolveRequest>({
    mutationFn: (payload) => resolveInvestigation(investigationId, payload),
    retry: false,
    onSuccess: (data) => {
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
