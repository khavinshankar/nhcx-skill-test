import { navigate } from "raviger";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import CareIcon from "@/CAREUI/icons/CareIcon";
import { Button } from "@/components/ui/button";

import AbhaDialog from "@/components/Nhcx/AbhaDialog";
import { nhcxCall } from "@/pages/Facility/claims/useClaimAction";
import { isAbhaSystem } from "@/pages/Facility/claims/utils";
import useCurrentFacility from "@/pages/Facility/utils/useCurrentFacility";
import {
  getPartialId,
  PartialPatientModel,
  PatientRead,
} from "@/types/emr/patient/patient";
import patientApi from "@/types/emr/patient/patientApi";
import { AbhaProfile } from "@/types/nhcx/nhcx";

// S13 "Register with ABHA": verify or create first, then open the patient
// already on the register under that ABHA, else the registration form (S14)
// filled from the profile.
export default function RegisterWithAbhaButton({
  facilityId,
}: {
  facilityId: string;
}) {
  const { t } = useTranslation();
  const { facility } = useCurrentFacility();
  const [open, setOpen] = useState(false);

  const abhaConfig = facility?.patient_instance_identifier_configs?.find((c) =>
    isAbhaSystem(c.config.system),
  );

  const onProfile = async (profile: AbhaProfile) => {
    if (abhaConfig && profile.abha_no) {
      try {
        const found = await nhcxCall(patientApi.search, {
          body: { config: abhaConfig.id, value: profile.abha_no, page_size: 1 },
        });
        const patient = found.results[0] as
          PartialPatientModel | PatientRead | undefined;
        if (patient) {
          toast.info(t("nhcx_abha_patient_on_file"));
          navigate(`/facility/${facilityId}/patients/home`, {
            query: {
              config: abhaConfig.id,
              value: profile.abha_no,
              phone_number: patient.phone_number,
              year_of_birth:
                (patient as PatientRead).year_of_birth?.toString() ||
                (profile.dob || "").slice(0, 4),
              partial_id: getPartialId(patient),
            },
          });
          return;
        }
      } catch {
        // No match could be read; fall through to registration.
      }
    }
    navigate(`/facility/${facilityId}/patient/create`, {
      query: {
        from_abha: "1",
        abha_number: profile.abha_no || "",
        abha_address: profile.abha_address || "",
        abha_name: profile.name || "",
        abha_gender: profile.gender || "",
        abha_dob: profile.dob || "",
        abha_mobile: profile.mobile || "",
      },
    });
  };

  return (
    <>
      <Button
        variant="outline"
        className="w-full md:w-auto"
        onClick={() => setOpen(true)}
      >
        <CareIcon icon="l-user-plus" className="mr-2 size-4" />
        {t("nhcx_register_with_abha")}
      </Button>
      <AbhaDialog open={open} onOpenChange={setOpen} onProfile={onProfile} />
    </>
  );
}
