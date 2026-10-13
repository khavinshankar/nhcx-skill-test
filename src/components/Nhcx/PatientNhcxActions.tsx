import { useQueryClient } from "@tanstack/react-query";
import { Link } from "raviger";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import CareIcon from "@/CAREUI/icons/CareIcon";
import { Button } from "@/components/ui/button";

import AbhaDialog from "@/components/Nhcx/AbhaDialog";
import { Chip } from "@/pages/Facility/claims/components/ClaimWidgets";
import { nhcxCall, refusalText } from "@/pages/Facility/claims/useClaimAction";
import {
  formatAbha,
  patientAbha,
  patientMobile,
} from "@/pages/Facility/claims/utils";
import { PatientRead } from "@/types/emr/patient/patient";
import nhcxApi from "@/types/nhcx/nhcxApi";

// S15 additions: the ABHA chip, "Link ABHA" / "Verify ABHA" (A19 link), and the
// claim entry points "Search insurance policy" (S1) and "Claims" (S5).
export default function PatientNhcxActions({
  patient,
  facilityId,
}: {
  patient: PatientRead;
  facilityId?: string;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const abha = patientAbha(patient);
  const mobile = patientMobile(patient.phone_number);

  const link = async (txnId: string) => {
    try {
      const res = await nhcxCall(nhcxApi.abha, {
        pathParams: { action: "link" },
        body: { txn_id: txnId, patient: patient.id },
      });
      if (res.ok === false) {
        toast.error(res.error || t("something_went_wrong"));
        return;
      }
      toast.success(res.message || t("nhcx_abha_linked"));
      queryClient.invalidateQueries({ queryKey: ["patient", patient.id] });
    } catch (error) {
      toast.error(refusalText(error, t("something_went_wrong")));
    }
  };

  const searchQuery = new URLSearchParams({
    id_type: abha ? "AbhaNumber" : "MobileNo",
    id_value: abha || mobile,
    patient: patient.id,
  }).toString();
  const claimsQuery = new URLSearchParams({
    patient: patient.id,
    patient_name: patient.name,
  }).toString();

  return (
    <div className="space-y-2">
      {abha && (
        <Chip tone="success">
          {t("nhcx_abha_chip", { number: formatAbha(abha) })}
        </Chip>
      )}
      <Button
        variant="outline"
        className="w-full"
        onClick={() => setOpen(true)}
      >
        <CareIcon icon="l-shield-check" className="mr-2 size-4" />
        {abha ? t("nhcx_verify_abha") : t("nhcx_link_abha")}
      </Button>
      {facilityId && (
        <>
          <Button asChild variant="outline" className="w-full">
            <Link href={`/facility/${facilityId}/claims/search?${searchQuery}`}>
              <CareIcon icon="l-search" className="mr-2 size-4" />
              {t("nhcx_search_insurance_policy")}
            </Link>
          </Button>
          <Button asChild variant="outline" className="w-full">
            <Link href={`/facility/${facilityId}/claims?${claimsQuery}`}>
              <CareIcon icon="l-file-shield-alt" className="mr-2 size-4" />
              {t("nhcx_claims")}
            </Link>
          </Button>
        </>
      )}
      <AbhaDialog
        open={open}
        onOpenChange={setOpen}
        initialAbha={abha}
        confirmLabel={abha ? t("nhcx_verify_abha") : t("nhcx_link_abha")}
        onProfile={(_profile, txnId) => link(txnId)}
      />
    </div>
  );
}
