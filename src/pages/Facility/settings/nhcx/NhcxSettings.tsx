import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

import Page from "@/components/Common/Page";

import { Chip } from "@/pages/Facility/claims/components/ClaimWidgets";
import { nhcxCall, refusalText } from "@/pages/Facility/claims/useClaimAction";
import { FacilityProfile, FacilityProfileResponse } from "@/types/nhcx/nhcx";
import nhcxApi from "@/types/nhcx/nhcxApi";

type Draft = Record<keyof FacilityProfile, string>;

function toDraft(p?: FacilityProfile): Draft {
  return {
    hfr_id: p?.hfr_id || "",
    participant_code: p?.participant_code || "",
    email: p?.email || "",
    gstin: p?.gstin || "",
  };
}

// The facility's NHCX identity (D1): HFR ID, participant code, email and
// GSTIN, read and saved through /api/v1/facility/{id}/nhcx/profile/. A blank
// HFR ID uses the HIP ID configured through the care_abdm plug.
export default function NhcxSettings({ facilityId }: { facilityId: string }) {
  const { t } = useTranslation();
  const { data, isLoading } = useQuery({
    queryKey: ["nhcx-facility-profile", facilityId],
    queryFn: () =>
      nhcxCall(nhcxApi.getFacilityProfile, { pathParams: { facilityId } }),
  });

  return (
    <Page title={t("nhcx_settings")} hideTitleOnPage>
      <div className="container mx-auto max-w-3xl space-y-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-700">
            {t("nhcx_settings")}
          </h1>
          <p className="text-sm text-gray-500">
            {t("nhcx_settings_description")}
          </p>
        </div>
        {isLoading || !data ? (
          <p className="text-sm text-gray-500">{t("loading")}</p>
        ) : (
          <NhcxProfileForm
            key={JSON.stringify(data.profile)}
            facilityId={facilityId}
            data={data}
          />
        )}
      </div>
    </Page>
  );
}

function NhcxProfileForm({
  facilityId,
  data,
}: {
  facilityId: string;
  data: FacilityProfileResponse;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState<Draft>(() => toDraft(data.profile));

  const save = useMutation({
    mutationFn: (body: Draft) =>
      nhcxCall(nhcxApi.updateFacilityProfile, {
        pathParams: { facilityId },
        body,
      }),
    onSuccess: (res) => {
      toast.success(res.message || t("nhcx_settings_saved"));
      queryClient.setQueryData(["nhcx-facility-profile", facilityId], res);
    },
    onError: (error) =>
      toast.error(refusalText(error, t("something_went_wrong"))),
  });

  const canEdit = data.can_edit;
  const abdmId = data.abdm_hf_id || "";
  const set = (key: keyof Draft, value: string) =>
    setDraft((d) => ({ ...d, [key]: value }));

  return (
    <Card>
      <CardContent className="p-6">
        <div className="mb-4 flex flex-wrap items-center gap-2 text-sm">
          <span className="text-gray-600">{t("nhcx_effective_hfr_id")}:</span>
          <span className="font-medium">{data.effective_hfr_id || "-"}</span>
          {data.hfr_id_source === "abdm" && (
            <Chip tone="info">{t("nhcx_hfr_from_abdm")}</Chip>
          )}
          {!data.effective_hfr_id && (
            <Chip tone="warning">{t("nhcx_hfr_missing")}</Chip>
          )}
        </div>
        <form
          className="grid grid-cols-1 gap-4 md:grid-cols-2"
          onSubmit={(e) => {
            e.preventDefault();
            save.mutate(draft);
          }}
        >
          <div className="space-y-1 md:col-span-2">
            <Label htmlFor="nhcx-hfr">{t("nhcx_hfr_id")}</Label>
            <div className="flex gap-2">
              <Input
                id="nhcx-hfr"
                value={draft.hfr_id}
                placeholder={abdmId}
                disabled={!canEdit}
                onChange={(e) => set("hfr_id", e.target.value)}
              />
              {abdmId && canEdit && draft.hfr_id !== abdmId && (
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => set("hfr_id", abdmId)}
                >
                  {t("nhcx_use_abdm_hip_id")}
                </Button>
              )}
            </div>
            <p className="text-xs text-gray-500">
              {abdmId
                ? t("nhcx_hfr_id_help_abdm", { id: abdmId })
                : t("nhcx_hfr_id_help")}
            </p>
          </div>
          <div className="space-y-1">
            <Label htmlFor="nhcx-participant">
              {t("nhcx_participant_code")}
            </Label>
            <Input
              id="nhcx-participant"
              value={draft.participant_code}
              disabled={!canEdit}
              onChange={(e) => set("participant_code", e.target.value)}
            />
            <p className="text-xs text-gray-500">
              {t("nhcx_participant_code_help")}
            </p>
          </div>
          <div className="space-y-1">
            <Label htmlFor="nhcx-email">{t("email")}</Label>
            <Input
              id="nhcx-email"
              type="email"
              value={draft.email}
              disabled={!canEdit}
              onChange={(e) => set("email", e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="nhcx-gstin">{t("nhcx_gstin")}</Label>
            <Input
              id="nhcx-gstin"
              value={draft.gstin}
              disabled={!canEdit}
              onChange={(e) => set("gstin", e.target.value)}
            />
          </div>
          {canEdit ? (
            <div className="flex gap-2 md:col-span-2">
              <Button type="submit" disabled={save.isPending}>
                {t("save")}
              </Button>
              <Button
                type="button"
                variant="outline"
                disabled={save.isPending}
                onClick={() => setDraft(toDraft(data.profile))}
              >
                {t("reset")}
              </Button>
            </div>
          ) : (
            <p className="text-sm text-gray-500 md:col-span-2">
              {t("nhcx_settings_read_only")}
            </p>
          )}
        </form>
      </CardContent>
    </Card>
  );
}
