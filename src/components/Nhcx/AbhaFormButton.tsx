import { useQueryParams } from "raviger";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import CareIcon from "@/CAREUI/icons/CareIcon";
import { Button } from "@/components/ui/button";

import AbhaDialog, {
  abhaGender,
  abhaPhone,
} from "@/components/Nhcx/AbhaDialog";
import {
  ABHA_ADDRESS_SYSTEM,
  formatAbha,
  isAbhaSystem,
} from "@/pages/Facility/claims/utils";
import { FacilityRead } from "@/types/facility/facility";
import { AbhaProfile } from "@/types/nhcx/nhcx";

interface IdentifierValue {
  config: string;
  value?: string;
}

// The slice of the registration form this button touches; `UseFormReturn` of
// the registration schema satisfies it.
export interface AbhaFillableForm {
  getValues(name: string): unknown;
  setValue(name: string, value: unknown, options?: object): void;
}

const IDENTIFIER_LISTS = ["required_identifiers", "optional_identifiers"];

function abhaConfigIds(facility?: FacilityRead) {
  const configs = facility?.patient_instance_identifier_configs || [];
  return {
    number: configs.find((c) => isAbhaSystem(c.config.system))?.id,
    address: configs.find(
      (c) =>
        (c.config.system || "").replace(/\/+$/, "") === ABHA_ADDRESS_SYSTEM,
    )?.id,
  };
}

function setIdentifier(form: AbhaFillableForm, config: string, value: string) {
  for (const list of IDENTIFIER_LISTS) {
    const items = (form.getValues(list) as IdentifierValue[]) || [];
    const at = items.findIndex((i) => i.config === config);
    if (at >= 0) {
      const next = [...items];
      next[at] = { config, value };
      form.setValue(list, next, { shouldDirty: true });
      return true;
    }
  }
  return false;
}

// Writes the A19 profile onto the form. `all` fills every field (S13 hand-off);
// otherwise only blank fields are filled and a typed value is kept (S14).
function fillForm(
  form: AbhaFillableForm,
  facility: FacilityRead | undefined,
  profile: AbhaProfile,
  all: boolean,
) {
  const put = (name: string, value: string) => {
    if (!value) return;
    if (!all && form.getValues(name)) return;
    form.setValue(name, value, { shouldDirty: true });
  };
  put("name", profile.name || "");
  put("gender", abhaGender(profile.gender));
  if (profile.dob && (all || !form.getValues("date_of_birth"))) {
    form.setValue("age_or_dob", "dob");
    form.setValue("date_of_birth", profile.dob, { shouldDirty: true });
  }
  const phone = abhaPhone(profile.mobile);
  if (phone && (all || !form.getValues("phone_number"))) {
    form.setValue("phone_number", phone, { shouldDirty: true });
  }
  const ids = abhaConfigIds(facility);
  let placed = true;
  if (ids.number && profile.abha_no) {
    placed = setIdentifier(form, ids.number, formatAbha(profile.abha_no));
  }
  if (ids.address && profile.abha_address) {
    placed = setIdentifier(form, ids.address, profile.abha_address) && placed;
  }
  return placed;
}

// S14 "Verify or create an ABHA", plus the fill from S13's hand-off query.
export default function AbhaFormButton({
  form,
  facility,
  isCreate,
}: {
  form: AbhaFillableForm;
  facility?: FacilityRead;
  isCreate: boolean;
}) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [qParams] = useQueryParams();
  const fromAbha = isCreate && qParams.from_abha === "1";
  const prefillNumber = fromAbha ? (qParams.abha_number as string) || "" : "";
  const applied = useRef(false);

  useEffect(() => {
    if (!fromAbha || !facility || applied.current) return;
    const profile: AbhaProfile = {
      abha_no: prefillNumber,
      abha_address: qParams.abha_address || null,
      name: qParams.abha_name || null,
      gender: qParams.abha_gender || null,
      dob: qParams.abha_dob || null,
      mobile: qParams.abha_mobile || null,
    };
    // The registration page seeds its identifier rows after the facility
    // loads; retry until the ABHA rows exist.
    let tries = 0;
    const timer = setInterval(() => {
      tries += 1;
      if (fillForm(form, facility, profile, true) || tries > 25) {
        applied.current = true;
        clearInterval(timer);
      }
    }, 200);
    return () => clearInterval(timer);
  }, [fromAbha, facility]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="flex flex-col gap-2 rounded-md border border-dashed border-gray-300 bg-white p-4 md:flex-row md:items-center md:justify-between">
      <p className="text-sm text-gray-600">
        {fromAbha
          ? t("nhcx_abha_filled_from", { number: formatAbha(prefillNumber) })
          : t("nhcx_abha_dialog_description")}
      </p>
      <Button
        type="button"
        variant="secondary"
        onClick={() => setOpen(true)}
        className="shrink-0"
      >
        <CareIcon icon="l-shield-check" className="mr-2 size-4" />
        {t("nhcx_verify_or_create_abha")}
      </Button>
      <AbhaDialog
        open={open}
        onOpenChange={setOpen}
        onProfile={(profile) => {
          fillForm(form, facility, profile, false);
        }}
      />
    </div>
  );
}
