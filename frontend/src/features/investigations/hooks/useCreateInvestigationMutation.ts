import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import { investigationKeys } from "../../../lib/api/query-keys.ts";
import { createInvestigation } from "../api/investigations-api.ts";
import type {
  InvestigationCreateInput,
  InvestigationDetailResponse,
} from "../types/investigations.types.ts";

export interface UseCreateInvestigationOptions {
  readonly navigateOnSuccess?: boolean | undefined;
  readonly onSuccess?: ((data: InvestigationDetailResponse) => void) | undefined;
}

export function useCreateInvestigationMutation(options: UseCreateInvestigationOptions = {}) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { navigateOnSuccess = true, onSuccess } = options;

  return useMutation<InvestigationDetailResponse, unknown, InvestigationCreateInput>({
    mutationFn: (payload) => createInvestigation(payload),
    retry: false,
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: investigationKeys.lists() });
      if (onSuccess) {
        onSuccess(data);
      }
      if (navigateOnSuccess) {
        navigate(`/investigations/${data.id}`);
      }
    },
  });
}
