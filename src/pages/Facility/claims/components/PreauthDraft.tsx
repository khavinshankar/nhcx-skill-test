import { useQuery } from "@tanstack/react-query";
import {
  Hospital,
  Link2,
  List,
  Plus,
  Save,
  Trash2,
  Unlink,
  UserPlus,
} from "lucide-react";
import { Link } from "raviger";
import { useEffect, useState } from "react";
import { Trans, useTranslation } from "react-i18next";

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/Common/Table";
import ValueSetSelect from "@/components/Questionnaire/ValueSetSelect";

import { getBasePrice } from "@/types/base/monetaryComponent/monetaryComponent";
import chargeItemDefinitionApi from "@/types/billing/chargeItemDefinition/chargeItemDefinitionApi";
import facilityApi from "@/types/facility/facilityApi";
import {
  Admission,
  CareTeamMember,
  CareTeamRole,
  ClaimItem,
  ClaimState,
  Diagnosis,
  DraftUpdate,
} from "@/types/nhcx/nhcx";
import nhcxApi from "@/types/nhcx/nhcxApi";
import query from "@/Utils/request/query";
import { formatName } from "@/Utils/utils";

import {
  ConfirmButton,
  DetailList,
  Muted,
} from "@/pages/Facility/claims/components/ClaimWidgets";
import { QuotedLinesTable } from "@/pages/Facility/claims/tabs/LineItemsTab";
import { ClaimTabKey } from "@/pages/Facility/claims/tabs/types";
import {
  nhcxCall,
  useClaimAction,
} from "@/pages/Facility/claims/useClaimAction";
import {
  formatAbha,
  formatDateTime,
  formatMoney,
} from "@/pages/Facility/claims/utils";

const BLANK = "__blank";

interface Props {
  facilityId: string;
  claimId: string;
  state: ClaimState;
  goTo?: (tab: ClaimTabKey) => void;
}

export const CARE_TEAM_ROLES: { value: CareTeamRole; label: string }[] = [
  { value: "admitting", label: "nhcx_role_admitting" },
  { value: "treating", label: "nhcx_role_treating" },
  { value: "surgeon", label: "nhcx_role_surgeon" },
  { value: "anaesthetist", label: "nhcx_role_anaesthetist" },
  { value: "nurse", label: "nhcx_role_nurse" },
];

function admissionPatient(a: Admission): { id?: string; name: string } {
  if (a.patient && typeof a.patient === "object") return a.patient;
  return {
    id: typeof a.patient === "string" ? a.patient : undefined,
    name: a.patient_name || "-",
  };
}

const admissionStart = (a: Admission) => a.period_start || a.period?.start;
const wardBed = (a: Admission) =>
  a.location && a.bed ? `${a.location} / ${a.bed}` : a.location || a.bed || "-";

function PatientLink({
  facilityId,
  admission,
}: {
  facilityId: string;
  admission: Admission;
}) {
  const p = admissionPatient(admission);
  if (!p.id) return <>{p.name}</>;
  return (
    <Link
      href={`/facility/${facilityId}/patient/${p.id}`}
      className="text-primary-700 underline"
    >
      {p.name}
    </Link>
  );
}

function AdmissionLink({
  facilityId,
  admission,
}: {
  facilityId: string;
  admission: Admission;
}) {
  const p = admissionPatient(admission);
  const label =
    admission.encounter_no || admission.external_identifier || admission.id;
  if (!p.id) return <>{label}</>;
  return (
    <Link
      href={`/facility/${facilityId}/patient/${p.id}/encounter/${admission.id}/updates`}
      className="text-primary-700 underline"
    >
      {label}
    </Link>
  );
}

// S4 / S9: the case is not eligible yet.
export function NotEligibleCard() {
  const { t } = useTranslation();
  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("nhcx_preauthorisation")}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm">
          <Trans
            i18nKey="nhcx_preauth_needs_eligible"
            components={{ b: <strong /> }}
          />
        </p>
      </CardContent>
    </Card>
  );
}

// S4 Link the admitted patient.
export function LinkAdmissionCard({ facilityId, claimId, state }: Props) {
  const { t } = useTranslation();
  const { claim, admissions } = state;
  const link = useClaimAction(
    claimId,
    (encounter: string) =>
      nhcxCall(nhcxApi.linkAdmission, {
        pathParams: { facilityId, claimId },
        body: { encounter },
      }),
    t("nhcx_admission_linked"),
  );
  if (!claim.abha_number) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{t("nhcx_link_admitted_patient")}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm">{t("nhcx_link_no_abha")}</p>
        </CardContent>
      </Card>
    );
  }
  const sorted = [...admissions].sort((a, b) =>
    (admissionStart(b) || "").localeCompare(admissionStart(a) || ""),
  );
  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("nhcx_link_admitted_patient")}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm">
          <Trans
            i18nKey="nhcx_link_intro"
            values={{
              name: claim.beneficiary_name || claim.member_id || "-",
              abha: formatAbha(claim.abha_number),
            }}
            components={{ b: <strong /> }}
          />
        </p>
        {!sorted.length ? (
          <div className="space-y-3">
            <Muted>{t("nhcx_no_matching_admission")}</Muted>
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" size="sm" asChild>
                <Link
                  href={`/facility/${facilityId}/patient/create?abha_number=${encodeURIComponent(claim.abha_number)}`}
                >
                  <UserPlus className="size-4" />
                  {t("nhcx_register_patient")}
                </Link>
              </Button>
              <Button variant="outline" size="sm" asChild>
                <Link href={`/facility/${facilityId}/patients`}>
                  <Hospital className="size-4" />
                  {t("nhcx_new_admission")}
                </Link>
              </Button>
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("patient")}</TableHead>
                  <TableHead>{t("nhcx_mrn")}</TableHead>
                  <TableHead>{t("nhcx_admission")}</TableHead>
                  <TableHead>{t("nhcx_ward_bed")}</TableHead>
                  <TableHead>{t("nhcx_admitted")}</TableHead>
                  <TableHead>{t("nhcx_doctor")}</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {sorted.map((a) => (
                  <TableRow key={a.id}>
                    <TableCell>
                      <PatientLink facilityId={facilityId} admission={a} />
                    </TableCell>
                    <TableCell>{a.mrn || "-"}</TableCell>
                    <TableCell>
                      <AdmissionLink facilityId={facilityId} admission={a} />
                    </TableCell>
                    <TableCell>{wardBed(a)}</TableCell>
                    <TableCell>{formatDateTime(admissionStart(a))}</TableCell>
                    <TableCell>{a.doctor || a.consultant || "-"}</TableCell>
                    <TableCell className="text-right">
                      <Button
                        size="sm"
                        variant="primary"
                        disabled={link.isPending}
                        onClick={() => link.mutate(a.id)}
                      >
                        <Link2 className="size-4" />
                        {t("nhcx_link")}
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function linkedAdmission(state: ClaimState): Admission | null {
  const encounter = state.claim.encounter;
  if (!encounter) return null;
  return (
    state.admissions.find((a) => a.id === encounter) ?? {
      id: encounter,
      patient: state.claim.patient,
      patient_name: state.claim.patient_name || state.claim.beneficiary_name,
    }
  );
}

// S4 Linked admission.
export function LinkedAdmissionCard({ facilityId, claimId, state }: Props) {
  const { t } = useTranslation();
  const admission = linkedAdmission(state);
  const unlink = useClaimAction(
    claimId,
    () =>
      nhcxCall(nhcxApi.linkAdmission, {
        pathParams: { facilityId, claimId },
        body: { encounter: null },
      }),
    t("nhcx_admission_unlinked"),
  );
  if (!admission) return null;
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-2">
        <CardTitle>{t("nhcx_linked_admission")}</CardTitle>
        <ConfirmButton
          variant="outline"
          confirm={t("nhcx_unlink_confirm")}
          disabled={unlink.isPending}
          onConfirm={() => unlink.mutate(undefined)}
        >
          <Unlink className="size-4" />
          {t("nhcx_unlink")}
        </ConfirmButton>
      </CardHeader>
      <CardContent>
        <DetailList
          items={[
            {
              label: t("patient"),
              value: (
                <PatientLink facilityId={facilityId} admission={admission} />
              ),
            },
            { label: t("nhcx_mrn"), value: admission.mrn },
            {
              label: t("nhcx_admission"),
              value: (
                <AdmissionLink facilityId={facilityId} admission={admission} />
              ),
            },
            { label: t("nhcx_ward_bed"), value: wardBed(admission) },
            {
              label: t("nhcx_admitted"),
              value: formatDateTime(admissionStart(admission)),
            },
            {
              label: t("nhcx_consultant"),
              value: admission.consultant || admission.doctor,
            },
          ]}
        />
      </CardContent>
    </Card>
  );
}

function RowBox({
  children,
  onRemove,
}: {
  children: React.ReactNode;
  onRemove: () => void;
}) {
  return (
    <div className="flex flex-wrap items-end gap-3 rounded-md border p-3">
      {children}
      <Button
        type="button"
        size="icon"
        variant="ghost"
        className="ml-auto text-red-600"
        onClick={onRemove}
      >
        <Trash2 className="size-4" />
      </Button>
    </div>
  );
}

const dateOnly = (v?: string | null) => (v ? v.slice(0, 10) : "");

// S4 Pre-authorisation draft.
export function DraftCard({ facilityId, claimId, state, goTo }: Props) {
  const { t } = useTranslation();
  const { claim } = state;
  const admission = linkedAdmission(state);
  const planReady = state.plan?.status === "ready";
  const consultant = admission?.consultant || admission?.doctor || null;

  const [admissionDate, setAdmissionDate] = useState("");
  const [dischargeDate, setDischargeDate] = useState("");
  const [diagnoses, setDiagnoses] = useState<Diagnosis[]>([]);
  const [team, setTeam] = useState<CareTeamMember[]>([]);
  const [caseType, setCaseType] = useState<"package" | "nonpackage">("package");
  const [packageCode, setPackageCode] = useState("");
  const [items, setItems] = useState<ClaimItem[]>([]);

  const seed = JSON.stringify([
    claim.admission_date,
    claim.expected_discharge_date,
    claim.case_type,
    claim.package_code,
    state.diagnoses,
    state.care_team,
    state.items,
    admission?.id,
  ]);
  useEffect(() => {
    setAdmissionDate(
      dateOnly(claim.admission_date) ||
        dateOnly(admission ? admissionStart(admission) : null),
    );
    setDischargeDate(dateOnly(claim.expected_discharge_date));
    setDiagnoses(state.diagnoses?.length ? state.diagnoses : []);
    setTeam(state.care_team?.length ? state.care_team : []);
    setCaseType(claim.case_type === "nonpackage" ? "nonpackage" : "package");
    setPackageCode(claim.package_code || "");
    setItems(state.items?.length ? state.items : []);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seed]);

  const { data: users } = useQuery({
    queryKey: ["nhcx-facility-users", facilityId],
    queryFn: query(facilityApi.getUsers, {
      pathParams: { facilityId },
      queryParams: { limit: 200 },
    }),
  });
  const doctors = [...(users?.results ?? [])].sort((a, b) =>
    formatName(a).localeCompare(formatName(b)),
  );

  const { data: chargeItems } = useQuery({
    queryKey: ["nhcx-charge-items", facilityId],
    queryFn: query(chargeItemDefinitionApi.listChargeItemDefinition, {
      pathParams: { facilityId },
      queryParams: { limit: 200, status: "active" },
    }),
    enabled: caseType === "nonpackage",
  });
  const chargeOptions = (chargeItems?.results ?? []).map((c) => ({
    code: c.slug || c.id,
    display: c.title,
    price: getBasePrice(c.price_components).toString(),
  }));

  const save = useClaimAction(
    claimId,
    (body: DraftUpdate) =>
      nhcxCall(nhcxApi.updateDraft, {
        pathParams: { facilityId, claimId },
        body,
      }),
    t("nhcx_draft_saved"),
  );

  const submit = (e: React.SyntheticEvent) => {
    e.preventDefault();
    const body: DraftUpdate = {
      admission_date: admissionDate || null,
      expected_discharge_date: dischargeDate || null,
      case_type: caseType,
      diagnoses: diagnoses.filter((d) => d.snomed_code || d.icd10_code),
      care_team: consultant
        ? undefined
        : team.filter((m) => m.practitioner && m.role),
    };
    if (caseType === "package") {
      body.package_code = planReady ? undefined : packageCode || null;
    } else {
      body.items = items
        .filter((i) => i.code)
        .map((i) => ({
          code: i.code,
          display: i.display,
          quantity: Number(i.quantity),
          unit_price:
            chargeOptions.find((c) => c.code === i.code)?.price ?? i.unit_price,
        }));
    }
    save.mutate(body);
  };

  return (
    <Card>
      <form onSubmit={submit}>
        <CardHeader>
          <CardTitle>{t("nhcx_preauth_draft")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {claim.preauth_saved_at && (
            <DetailList
              items={[
                {
                  label: t("nhcx_last_saved"),
                  value: formatDateTime(claim.preauth_saved_at),
                },
                {
                  label: t("nhcx_case"),
                  value:
                    claim.case_type === "nonpackage"
                      ? t("nhcx_case_nonpackage")
                      : claim.case_type === "package"
                        ? t("nhcx_case_package")
                        : "-",
                },
                {
                  label: t("nhcx_estimated_amount"),
                  value: claim.preauth_total
                    ? `₹${Number(claim.preauth_total).toLocaleString("en-IN", {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })}`
                    : "-",
                },
              ]}
            />
          )}
          <Accordion
            type="multiple"
            defaultValue={["stay", "diagnoses", "doctor", "case"]}
          >
            <AccordionItem value="stay">
              <AccordionTrigger>{t("nhcx_stay")}</AccordionTrigger>
              <AccordionContent>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  <div className="flex flex-col gap-1">
                    <Label htmlFor="nhcx-admission-date">
                      {t("nhcx_admission_date")}
                      <span className="text-red-500"> *</span>
                    </Label>
                    <Input
                      id="nhcx-admission-date"
                      type="date"
                      required
                      value={admissionDate}
                      onChange={(e) => setAdmissionDate(e.target.value)}
                    />
                  </div>
                  <div className="flex flex-col gap-1">
                    <Label htmlFor="nhcx-discharge-date">
                      {t("nhcx_provisional_discharge_date")}
                    </Label>
                    <Input
                      id="nhcx-discharge-date"
                      type="date"
                      min={admissionDate || undefined}
                      value={dischargeDate}
                      onChange={(e) => setDischargeDate(e.target.value)}
                    />
                  </div>
                </div>
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="diagnoses">
              <AccordionTrigger>{t("nhcx_diagnoses_icd10")}</AccordionTrigger>
              <AccordionContent className="space-y-3">
                <Muted>{t("nhcx_admission_no_diagnosis")}</Muted>
                {diagnoses.map((d, index) => (
                  <RowBox
                    key={index}
                    onRemove={() =>
                      setDiagnoses((cur) => cur.filter((_, i) => i !== index))
                    }
                  >
                    <div className="flex w-96 flex-col gap-1">
                      <Label>{t("nhcx_diagnosis_icd10")}</Label>
                      <ValueSetSelect
                        system="system-condition-code"
                        placeholder={t("nhcx_select_diagnosis")}
                        value={
                          d.snomed_code
                            ? {
                                system: "http://snomed.info/sct",
                                code: d.snomed_code,
                                display: d.snomed_display || d.snomed_code,
                              }
                            : null
                        }
                        onSelect={(code) =>
                          setDiagnoses((cur) =>
                            cur.map((x, i) =>
                              i === index
                                ? {
                                    ...x,
                                    snomed_code: code.code,
                                    snomed_display: code.display,
                                  }
                                : x,
                            ),
                          )
                        }
                      />
                    </div>
                    <div className="flex w-40 flex-col gap-1">
                      <Label>{t("nhcx_icd10_code")}</Label>
                      <Input
                        value={d.icd10_code || ""}
                        onChange={(e) =>
                          setDiagnoses((cur) =>
                            cur.map((x, i) =>
                              i === index
                                ? { ...x, icd10_code: e.target.value }
                                : x,
                            ),
                          )
                        }
                      />
                    </div>
                  </RowBox>
                ))}
                <Button
                  type="button"
                  size="sm"
                  variant="secondary"
                  onClick={() =>
                    setDiagnoses((cur) => [
                      ...cur,
                      {
                        snomed_code: null,
                        snomed_display: null,
                        icd10_code: null,
                        icd10_display: null,
                      },
                    ])
                  }
                >
                  <Plus className="size-4" />
                  {t("nhcx_add_diagnosis")}
                </Button>
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="doctor">
              <AccordionTrigger>{t("nhcx_treating_doctor")}</AccordionTrigger>
              <AccordionContent className="space-y-3">
                {consultant ? (
                  <>
                    <p className="text-sm">
                      {t("nhcx_consultant_treating", { name: consultant })}
                    </p>
                    <Muted>{t("nhcx_consultant_hint")}</Muted>
                  </>
                ) : (
                  <>
                    <Muted>{t("nhcx_no_consultant_hint")}</Muted>
                    {team.map((m, index) => (
                      <RowBox
                        key={index}
                        onRemove={() =>
                          setTeam((cur) => cur.filter((_, i) => i !== index))
                        }
                      >
                        <div className="flex flex-col gap-1">
                          <Label>{t("nhcx_doctor")}</Label>
                          <Select
                            value={m.practitioner || BLANK}
                            onValueChange={(v) =>
                              setTeam((cur) =>
                                cur.map((x, i) =>
                                  i === index
                                    ? {
                                        ...x,
                                        practitioner: v === BLANK ? "" : v,
                                      }
                                    : x,
                                ),
                              )
                            }
                          >
                            <SelectTrigger className="w-72">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value={BLANK}>
                                {t("nhcx_select_doctor")}
                              </SelectItem>
                              {m.practitioner &&
                                !doctors.some(
                                  (u) => u.id === m.practitioner,
                                ) && (
                                  <SelectItem value={m.practitioner}>
                                    {m.practitioner_name || m.practitioner}
                                  </SelectItem>
                                )}
                              {doctors.map((u) => (
                                <SelectItem key={u.id} value={u.id}>
                                  {formatName(u)} - {u.user_type}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="flex flex-col gap-1">
                          <Label>{t("nhcx_role")}</Label>
                          <Select
                            value={m.role}
                            onValueChange={(v) =>
                              setTeam((cur) =>
                                cur.map((x, i) =>
                                  i === index
                                    ? { ...x, role: v as CareTeamRole }
                                    : x,
                                ),
                              )
                            }
                          >
                            <SelectTrigger className="w-48">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {CARE_TEAM_ROLES.map((r) => (
                                <SelectItem key={r.value} value={r.value}>
                                  {t(r.label)}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                      </RowBox>
                    ))}
                    <Button
                      type="button"
                      size="sm"
                      variant="secondary"
                      onClick={() =>
                        setTeam((cur) => [
                          ...cur,
                          { practitioner: "", role: "treating" },
                        ])
                      }
                    >
                      <Plus className="size-4" />
                      {t("nhcx_add_doctor")}
                    </Button>
                  </>
                )}
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="case">
              <AccordionTrigger>{t("nhcx_case_and_estimate")}</AccordionTrigger>
              <AccordionContent className="space-y-4">
                <RadioGroup
                  value={caseType}
                  onValueChange={(v) =>
                    setCaseType(v as "package" | "nonpackage")
                  }
                  className="flex flex-wrap gap-6"
                >
                  <div className="flex items-center gap-2">
                    <RadioGroupItem value="package" id="nhcx-case-package" />
                    <Label htmlFor="nhcx-case-package">
                      {t("nhcx_case_package")}
                    </Label>
                  </div>
                  <div className="flex items-center gap-2">
                    <RadioGroupItem
                      value="nonpackage"
                      id="nhcx-case-nonpackage"
                    />
                    <Label htmlFor="nhcx-case-nonpackage">
                      {t("nhcx_case_nonpackage")}
                    </Label>
                  </div>
                </RadioGroup>

                <div className={caseType === "package" ? "" : "hidden"}>
                  {planReady ? (
                    <div className="space-y-3">
                      <QuotedLinesTable
                        lines={state.lines}
                        empty={t("nhcx_nothing_quoted_package")}
                      />
                      {goTo && (
                        <div className="flex justify-end">
                          <Button
                            type="button"
                            size="sm"
                            variant="primary"
                            onClick={() => goTo("lines")}
                          >
                            <List className="size-4" />
                            {t("nhcx_choose_line_items")}
                          </Button>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="flex flex-col gap-1">
                      <Label htmlFor="nhcx-package-code">
                        {t("nhcx_package")}
                      </Label>
                      <Input
                        id="nhcx-package-code"
                        className="w-72"
                        placeholder={t("nhcx_select_package")}
                        value={packageCode}
                        onChange={(e) => setPackageCode(e.target.value)}
                      />
                      <Muted className="text-xs">
                        {t("nhcx_local_package_help")}
                      </Muted>
                    </div>
                  )}
                </div>

                <div
                  className={caseType === "nonpackage" ? "space-y-3" : "hidden"}
                >
                  <Label>{t("nhcx_items")}</Label>
                  <Muted className="text-xs">{t("nhcx_items_help")}</Muted>
                  {items.map((item, index) => (
                    <RowBox
                      key={index}
                      onRemove={() =>
                        setItems((cur) => cur.filter((_, i) => i !== index))
                      }
                    >
                      <div className="flex flex-col gap-1">
                        <Label>{t("nhcx_item_fixed_price")}</Label>
                        <Select
                          value={item.code || BLANK}
                          onValueChange={(v) => {
                            const option = chargeOptions.find(
                              (c) => c.code === v,
                            );
                            setItems((cur) =>
                              cur.map((x, i) =>
                                i === index
                                  ? {
                                      ...x,
                                      code: v === BLANK ? "" : v,
                                      display: option?.display ?? "",
                                      unit_price: option?.price ?? null,
                                    }
                                  : x,
                              ),
                            );
                          }}
                        >
                          <SelectTrigger className="w-80">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value={BLANK}>
                              {t("nhcx_select_item")}
                            </SelectItem>
                            {item.code &&
                              !chargeOptions.some(
                                (c) => c.code === item.code,
                              ) && (
                                <SelectItem value={item.code}>
                                  {item.display} -{" "}
                                  {formatMoney(item.unit_price)}
                                </SelectItem>
                              )}
                            {chargeOptions.map((c) => (
                              <SelectItem key={c.code} value={c.code}>
                                {c.display} - {formatMoney(c.price)}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="flex flex-col gap-1">
                        <Label>{t("nhcx_quantity")}</Label>
                        <Input
                          type="number"
                          min={0.5}
                          step="any"
                          className="w-32"
                          value={String(item.quantity ?? "")}
                          onChange={(e) =>
                            setItems((cur) =>
                              cur.map((x, i) =>
                                i === index
                                  ? {
                                      ...x,
                                      quantity: e.target
                                        .value as unknown as number,
                                    }
                                  : x,
                              ),
                            )
                          }
                        />
                      </div>
                    </RowBox>
                  ))}
                  <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    onClick={() =>
                      setItems((cur) => [
                        ...cur,
                        {
                          code: "",
                          display: "",
                          unit_price: null,
                          quantity: 1,
                        },
                      ])
                    }
                  >
                    <Plus className="size-4" />
                    {t("nhcx_add_item")}
                  </Button>
                </div>
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        </CardContent>
        <CardFooter className="justify-end">
          <Button type="submit" variant="primary" disabled={save.isPending}>
            <Save className="size-4" />
            {t("nhcx_save_preauth_draft")}
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
}
