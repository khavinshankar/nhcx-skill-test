import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { NhcxOk } from "@/types/nhcx/nhcx";
import { callApi } from "@/Utils/request/query";
import { ApiCallOptions, ApiRoute, HTTPError } from "@/Utils/request/types";

export const claimStateKey = (claimId: string) => ["nhcx-claim-state", claimId];

// Calls an NHCX route without the global error toast; refusals are read by
// `refusalText` and shown by the caller.
export function nhcxCall<Route extends ApiRoute<unknown, unknown>>(
  route: Route,
  options: ApiCallOptions<Route>,
) {
  return callApi(route, { ...options, silent: true });
}

export function refusalText(error: unknown, fallback: string): string {
  if (error instanceof HTTPError) {
    const cause = error.cause as Record<string, unknown> | undefined;
    if (cause && typeof cause.error === "string") return cause.error;
    if (cause && typeof cause.detail === "string") return cause.detail;
    if (cause && typeof cause.message === "string") return cause.message;
  }
  if (error instanceof Error && error.message) return error.message;
  return fallback;
}

// A mutation on one claim: shows the server's flash (else `success`) or the
// refusal as a toast, then refetches the claim's A17 state.
export function useClaimAction<TVars>(
  claimId: string,
  fn: (vars: TVars) => Promise<unknown>,
  success?: string,
  onDone?: () => void,
) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: (res) => {
      const body = (res ?? {}) as Partial<NhcxOk>;
      if (body.ok === false) {
        toast.error(body.error || t("something_went_wrong"));
      } else {
        const text = body.message || success;
        if (text) toast.success(text);
        onDone?.();
      }
      queryClient.invalidateQueries({ queryKey: claimStateKey(claimId) });
    },
    onError: (error) => {
      toast.error(refusalText(error, t("something_went_wrong")));
      queryClient.invalidateQueries({ queryKey: claimStateKey(claimId) });
    },
  });
}
