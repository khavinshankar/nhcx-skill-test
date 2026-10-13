import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";

import { userChildProps } from "@/components/Common/UserColumns";
import useAuthUser from "@/hooks/useAuthUser";
import {
  Chip,
  DetailList,
} from "@/pages/Facility/claims/components/ClaimWidgets";
import { nhcxCall, refusalText } from "@/pages/Facility/claims/useClaimAction";
import { PractitionerProfile } from "@/types/nhcx/nhcx";
import nhcxApi from "@/types/nhcx/nhcxApi";

// S16 department and identifier type options.
const DEPARTMENTS = [
  "General Medicine",
  "Cardiology",
  "Pediatrics",
  "Orthopedics",
  "Obstetrics & Gynaecology",
  "Dermatology",
  "Emergency",
  "Gastroenterology",
  "Nephrology",
  "General Surgery",
];

const IDENTIFIER_TYPES = [
  { code: "HPID", label: "nhcx_identifier_type_hpid" },
  { code: "MD", label: "nhcx_identifier_type_md" },
  { code: "OIN", label: "nhcx_identifier_type_oin" },
];

const NOT_STATED = "__not_stated__";

type Draft = Pick<
  PractitionerProfile,
  | "hpr_id"
  | "qualification_code"
  | "qualification_display"
  | "specialty_code"
  | "specialty_display"
  | "department"
  | "active"
> & { identifier_type_code: string };

function toDraft(p?: PractitionerProfile): Draft {
  return {
    hpr_id: p?.hpr_id || "",
    identifier_type_code: p?.identifier_type_code || "HPID",
    qualification_code: p?.qualification_code || "",
    qualification_display: p?.qualification_display || "",
    specialty_code: p?.specialty_code || "",
    specialty_display: p?.specialty_display || "",
    department: p?.department || "",
    active: p?.active ?? true,
  };
}

// S16 on the user page: the NHCX practitioner profile (HPR id, qualification,
// specialty, department, active) read and saved through
// /api/v1/nhcx/practitioner/{user_id}/. Only the user or a superuser edits.
export default function PractitionerProfileCard({ userData }: userChildProps) {
  const { t } = useTranslation();
  const authUser = useAuthUser();
  const queryClient = useQueryClient();
  const queryKey = ["nhcx-practitioner", userData.id];
  const canEdit =
    authUser.username === userData.username || authUser.is_superuser;
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<Draft>(toDraft());

  const { data, isLoading } = useQuery({
    queryKey,
    queryFn: () =>
      nhcxCall(nhcxApi.getPractitioner, {
        pathParams: { userId: userData.id },
      }),
  });
  const profile = data?.profile;

  useEffect(() => {
    if (!editing) setDraft(toDraft(profile));
  }, [profile, editing]);

  const save = useMutation({
    mutationFn: (body: Draft) =>
      nhcxCall(nhcxApi.updatePractitioner, {
        pathParams: { userId: userData.id },
        body,
      }),
    onSuccess: (res) => {
      toast.success(res.message || t("nhcx_practitioner_saved"));
      setEditing(false);
      queryClient.invalidateQueries({ queryKey });
    },
    onError: (error) =>
      toast.error(refusalText(error, t("something_went_wrong"))),
  });

  if (isLoading) {
    return <p className="text-sm text-gray-500">{t("loading")}</p>;
  }

  const identifierLabel = profile?.hpr_id
    ? `${profile.identifier_type_code || "HPID"} ${profile.hpr_id}`
    : "-";

  if (!editing) {
    return (
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <Chip tone={profile?.active === false ? "neutral" : "success"}>
            {profile?.active === false
              ? t("nhcx_practitioner_retired")
              : t("nhcx_practitioner_active")}
          </Chip>
        </div>
        <DetailList
          columns={2}
          items={[
            {
              label: t("nhcx_practitioner_identifier"),
              value: identifierLabel,
            },
            {
              label: t("nhcx_practitioner_qualification"),
              value:
                profile?.qualification_display ||
                profile?.qualification_code ||
                "-",
            },
            {
              label: t("nhcx_practitioner_specialty"),
              value: profile?.specialty_display
                ? `${profile.specialty_display}${profile.specialty_code ? ` (${profile.specialty_code})` : ""}`
                : profile?.specialty_code || "-",
            },
            {
              label: t("nhcx_practitioner_department"),
              value: profile?.department || "-",
            },
          ]}
        />
        {canEdit && (
          <Button variant="outline" size="sm" onClick={() => setEditing(true)}>
            {t("edit")}
          </Button>
        )}
      </div>
    );
  }

  const set = <K extends keyof Draft>(key: K, value: Draft[K]) =>
    setDraft((d) => ({ ...d, [key]: value }));

  return (
    <form
      className="grid grid-cols-1 gap-4 md:grid-cols-2"
      onSubmit={(e) => {
        e.preventDefault();
        save.mutate(draft);
      }}
    >
      <div className="space-y-1">
        <Label>{t("nhcx_practitioner_identifier_type")}</Label>
        <Select
          value={draft.identifier_type_code}
          onValueChange={(v) => set("identifier_type_code", v)}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {IDENTIFIER_TYPES.map((o) => (
              <SelectItem key={o.code} value={o.code}>
                {t(o.label)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <p className="text-xs text-gray-500">
          {t("nhcx_practitioner_identifier_type_help")}
        </p>
      </div>
      <div className="space-y-1">
        <Label htmlFor="nhcx-hpr">
          {t("nhcx_practitioner_identifier_number")}
        </Label>
        <Input
          id="nhcx-hpr"
          value={draft.hpr_id || ""}
          onChange={(e) => set("hpr_id", e.target.value)}
        />
      </div>
      <div className="space-y-1">
        <Label htmlFor="nhcx-qual">
          {t("nhcx_practitioner_qualification")}
        </Label>
        <Input
          id="nhcx-qual"
          value={draft.qualification_display || ""}
          placeholder={t("nhcx_practitioner_qualification_example")}
          onChange={(e) => set("qualification_display", e.target.value)}
        />
      </div>
      <div className="space-y-1">
        <Label htmlFor="nhcx-qual-code">
          {t("nhcx_practitioner_qualification_code")}
        </Label>
        <Input
          id="nhcx-qual-code"
          value={draft.qualification_code || ""}
          onChange={(e) => set("qualification_code", e.target.value)}
        />
      </div>
      <div className="space-y-1">
        <Label htmlFor="nhcx-spec-code">
          {t("nhcx_practitioner_specialty_code")}
        </Label>
        <Input
          id="nhcx-spec-code"
          value={draft.specialty_code || ""}
          onChange={(e) => set("specialty_code", e.target.value)}
        />
      </div>
      <div className="space-y-1">
        <Label htmlFor="nhcx-spec">
          {t("nhcx_practitioner_specialty_display")}
        </Label>
        <Input
          id="nhcx-spec"
          value={draft.specialty_display || ""}
          onChange={(e) => set("specialty_display", e.target.value)}
        />
      </div>
      <div className="space-y-1">
        <Label>{t("nhcx_practitioner_department")}</Label>
        <Select
          value={draft.department || NOT_STATED}
          onValueChange={(v) => set("department", v === NOT_STATED ? "" : v)}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={NOT_STATED}>{t("nhcx_not_stated")}</SelectItem>
            {DEPARTMENTS.map((d) => (
              <SelectItem key={d} value={d}>
                {d}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="flex items-center gap-2 pt-6">
        <Switch
          id="nhcx-active"
          checked={draft.active}
          onCheckedChange={(v) => set("active", v)}
        />
        <Label htmlFor="nhcx-active">{t("nhcx_practitioner_active")}</Label>
      </div>
      <div className="flex gap-2 md:col-span-2">
        <Button type="submit" disabled={save.isPending}>
          {t("nhcx_save_practitioner")}
        </Button>
        <Button
          type="button"
          variant="outline"
          onClick={() => setEditing(false)}
        >
          {t("cancel")}
        </Button>
      </div>
    </form>
  );
}
