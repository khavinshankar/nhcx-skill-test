import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowLeft, Loader2 } from "lucide-react";
import { Link, navigate, useQueryParams } from "raviger";
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import Page from "@/components/Common/Page";
import PatientIdentifierFilter from "@/components/Patient/PatientIdentifierFilter";

import patientApi from "@/types/emr/patient/patientApi";
import { Claim, ClaimState, SearchIdType } from "@/types/nhcx/nhcx";
import nhcxApi from "@/types/nhcx/nhcxApi";
import query from "@/Utils/request/query";
import { formatPatientAge } from "@/Utils/utils";

import {
  Chip,
  CorrelationId,
  ErrorText,
  Muted,
} from "./components/ClaimWidgets";
import { nhcxCall, refusalText } from "./useClaimAction";
import {
  ID_TYPES,
  formatAbha,
  formatDate,
  formatDateTime,
  formatMoney,
  patientAbha,
  patientMobile,
} from "./utils";

const DISCOVERY_ID_TYPES: SearchIdType[] = [
  "AbhaNumber",
  "MobileNo",
  "MemberId",
];

function discoveryChip(claim: Claim) {
  if (claim.status === "checking")
    return { tone: "info" as const, label: "nhcx_waiting" };
  if (claim.status === "error")
    return { tone: "danger" as const, label: "nhcx_failed" };
  if (claim.status === "draft")
    return { tone: "warning" as const, label: "nhcx_status_draft" };
  return { tone: "success" as const, label: "nhcx_answered" };
}

// S17 Beneficiary Discovery: a coverage eligibility check with purpose
// `discovery`, sent to one payer with every handle the desk knows.
export default function BeneficiaryDiscovery({
  facilityId,
}: {
  facilityId: string;
}) {
  const { t } = useTranslation();
  const [qParams, setQParams] = useQueryParams<{
    patient?: string;
    patient_name?: string;
    case?: string;
    id_type?: string;
    id_value?: string;
  }>();
  const caseId = qParams.case;

  const caseState = useQuery({
    queryKey: ["nhcx-claim-state", caseId],
    queryFn: query(nhcxApi.claimState, {
      pathParams: { facilityId, claimId: caseId! },
    }),
    enabled: !!caseId,
  });

  const patientId = qParams.patient || caseState.data?.claim.patient || "";
  const patientQuery = useQuery({
    queryKey: ["patient", patientId],
    queryFn: query(patientApi.get, {
      pathParams: { id: patientId },
      queryParams: { facility: facilityId },
    }),
    enabled: !!patientId,
  });
  const patient = patientQuery.data;
  const abha = patientAbha(patient);
  const mobile = patientMobile(patient?.phone_number);

  // Payers seen on this facility's cases make the typeahead list.
  const knownClaims = useQuery({
    queryKey: ["nhcx-claims", facilityId, "payers"],
    queryFn: query(nhcxApi.listClaims, {
      pathParams: { facilityId },
      queryParams: { limit: 100 },
    }),
  });
  const payers = useMemo(() => {
    const map = new Map<string, string>();
    knownClaims.data?.results.forEach((c) => {
      if (c.payer_id) map.set(c.payer_id, c.payer_name || c.payer_id);
    });
    return [...map.entries()];
  }, [knownClaims.data]);

  const [payer, setPayer] = useState("");
  const [idType, setIdType] = useState<SearchIdType>("AbhaNumber");
  const [idValue, setIdValue] = useState("");
  const [aadhaar, setAadhaar] = useState("");
  const [mobileExtra, setMobileExtra] = useState("");
  const [memberExtra, setMemberExtra] = useState("");
  const [formError, setFormError] = useState<string>();
  const [watching, setWatching] = useState<string | undefined>(caseId);
  const [polling, setPolling] = useState(false);

  useEffect(() => {
    if (!payer && payers.length === 1) setPayer(payers[0][0]);
  }, [payers, payer]);

  useEffect(() => {
    const c = caseState.data?.claim;
    if (c?.payer_id && !payer) setPayer(c.payer_id);
    if (c?.member_id && !memberExtra) setMemberExtra(c.member_id);
  }, [caseState.data]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (qParams.id_type && ID_TYPES.some((o) => o.value === qParams.id_type)) {
      setIdType(qParams.id_type as SearchIdType);
      setIdValue(qParams.id_value || "");
      return;
    }
    if (!patient) return;
    const kind: SearchIdType = abha ? "AbhaNumber" : "MobileNo";
    setIdType(kind);
    setIdValue(kind === "AbhaNumber" ? (abha ?? "") : mobile);
    setMobileExtra(mobile);
  }, [patient?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const changeIdType = (kind: SearchIdType) => {
    setIdType(kind);
    if (kind === "AbhaNumber") setIdValue(abha ?? "");
    else if (kind === "MobileNo") setIdValue(mobile);
    else setIdValue(memberExtra);
  };

  const watched = useQuery<ClaimState>({
    queryKey: ["nhcx-claim-state", watching],
    queryFn: query(nhcxApi.claimState, {
      pathParams: { facilityId, claimId: watching! },
    }),
    enabled: !!watching,
    refetchInterval: (q) =>
      polling && q.state.data?.claim.status === "checking" ? 5000 : false,
  });

  const sent = useQuery({
    queryKey: ["nhcx-claims", facilityId, "discoveries", patientId],
    queryFn: query(nhcxApi.listClaims, {
      pathParams: { facilityId },
      queryParams: { patient: patientId, limit: 50 },
    }),
    enabled: !!patientId,
    refetchInterval: polling ? 5000 : false,
  });
  const discoveries = (sent.data?.results ?? [])
    .filter((c) => c.purpose === "discovery")
    .sort((a, b) => (b.created_date || "").localeCompare(a.created_date || ""));

  const discover = useMutation({
    mutationFn: async () => {
      const extras = {
        aadhaar_number: aadhaar.replace(/[\s-]/g, "") || undefined,
        mobile_number:
          idType === "MobileNo" ? undefined : mobileExtra.trim() || undefined,
        member_id:
          idType === "MemberId" ? undefined : memberExtra.trim() || undefined,
      };
      if (caseId) {
        const res = await nhcxCall(nhcxApi.checkEligibility, {
          pathParams: { facilityId, claimId: caseId },
          body: {
            purpose: "discovery",
            payer_id: payer.trim(),
            identifier_type: idType,
            identifier_value: idValue.trim(),
            ...extras,
          },
        });
        return { ...res, claim_id: res.claim_id || caseId };
      }
      return nhcxCall(nhcxApi.openClaim, {
        pathParams: { facilityId },
        body: {
          purpose: "discovery",
          payer_id: payer.trim(),
          id_type: idType,
          id_value: idValue.trim(),
          patient: patientId,
          ...extras,
        },
      });
    },
    onSuccess: (res) => {
      if (res.ok === false) {
        toast.error(res.error || t("something_went_wrong"));
        return;
      }
      if (res.message) toast.success(res.message);
      setWatching(res.claim_id);
      setPolling(true);
      sent.refetch();
    },
    onError: (error) =>
      toast.error(refusalText(error, t("something_went_wrong"))),
  });

  const submit = () => {
    const idLabel = t(ID_TYPES.find((o) => o.value === idType)!.label);
    const aadhaarDigits = aadhaar.replace(/[\s-]/g, "");
    const mobileDigits = mobileExtra.replace(/[\s-]/g, "");
    let error: string | undefined;
    if (!patientId) error = t("nhcx_select_patient_first");
    else if (!payer.trim()) error = t("nhcx_choose_payer");
    else if (!idValue.trim())
      error = t("nhcx_enter_identifier_to_ask", { identifier: idLabel });
    else if (aadhaarDigits && !/^\d{12}$/.test(aadhaarDigits))
      error = t("nhcx_aadhaar_12_digits_short");
    else if (
      idType !== "MobileNo" &&
      mobileDigits &&
      !/^\d{10}$/.test(mobileDigits)
    )
      error = t("nhcx_mobile_10_digits_short");
    setFormError(error);
    if (!error) discover.mutate();
  };

  const claim = watched.data?.claim;
  const waiting = polling && claim?.status === "checking";
  const answered =
    claim && (claim.status === "eligible" || claim.status === "not-eligible");

  useEffect(() => {
    if (claim && claim.status !== "checking") setPolling(false);
  }, [claim?.status]); // eslint-disable-line react-hooks/exhaustive-deps

  const backHref = caseId
    ? `/facility/${facilityId}/claims/${caseId}/eligibility`
    : `/facility/${facilityId}/claims`;

  return (
    <Page
      title={t("nhcx_discovery")}
      options={
        <Button variant="outline" asChild>
          <Link href={backHref}>
            <ArrowLeft className="size-4" />
            {t("back")}
          </Link>
        </Button>
      }
    >
      <div className="mt-4 flex flex-col gap-4">
        <Card>
          <CardHeader>
            <CardTitle>{t("patient")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {!patientId ? (
              <PatientIdentifierFilter
                onSelect={(id, name) =>
                  setQParams({ ...qParams, patient: id, patient_name: name })
                }
                placeholder={t("nhcx_select_patient")}
              />
            ) : (
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
                <span className="font-semibold">
                  {patient?.name || qParams.patient_name || "-"}
                </span>
                {patient && (
                  <>
                    <span>
                      {formatPatientAge(patient, true)} ·{" "}
                      {t(`GENDER__${patient.gender}`)}
                    </span>
                    <span>{patient.phone_number || "-"}</span>
                    <span>
                      {t("nhcx_abha")} {abha ? formatAbha(abha) : "-"}
                    </span>
                  </>
                )}
                {!caseId && (
                  <Button
                    variant="link"
                    size="sm"
                    onClick={() =>
                      setQParams({
                        ...qParams,
                        patient: undefined,
                        patient_name: undefined,
                      })
                    }
                  >
                    {t("nhcx_change_patient")}
                  </Button>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("nhcx_discovery_request")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-3">
              <div className="flex flex-col gap-1">
                <Label htmlFor="nhcx-payer">{t("nhcx_payer")} *</Label>
                <Input
                  id="nhcx-payer"
                  list="nhcx-payers"
                  value={payer}
                  placeholder={t("nhcx_payer_placeholder")}
                  onChange={(e) => setPayer(e.target.value)}
                />
                <datalist id="nhcx-payers">
                  {payers.map(([code, name]) => (
                    <option key={code} value={code}>
                      {name}
                    </option>
                  ))}
                </datalist>
              </div>
              <div className="flex flex-col gap-1">
                <Label>{t("nhcx_search_by")} *</Label>
                <Select
                  value={idType}
                  onValueChange={(v) => changeIdType(v as SearchIdType)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {DISCOVERY_ID_TYPES.map((v) => (
                      <SelectItem key={v} value={v}>
                        {t(ID_TYPES.find((o) => o.value === v)!.label)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex flex-col gap-1">
                <Label htmlFor="nhcx-disc-value">
                  {t("nhcx_identifier_value")} *
                </Label>
                <Input
                  id="nhcx-disc-value"
                  value={idValue}
                  onChange={(e) => setIdValue(e.target.value)}
                />
              </div>
            </div>
            <div className="space-y-2">
              <h4 className="text-sm font-semibold">
                {t("nhcx_additional_information")}
              </h4>
              <Muted>{t("nhcx_additional_information_note")}</Muted>
              <div className="grid gap-4 md:grid-cols-3">
                <div className="flex flex-col gap-1">
                  <Label htmlFor="nhcx-aadhaar">
                    {t("nhcx_aadhaar_number")}
                  </Label>
                  <Input
                    id="nhcx-aadhaar"
                    inputMode="numeric"
                    value={aadhaar}
                    onChange={(e) => setAadhaar(e.target.value)}
                  />
                </div>
                {idType !== "MobileNo" && (
                  <div className="flex flex-col gap-1">
                    <Label htmlFor="nhcx-mobile">
                      {t("nhcx_mobile_number")}
                    </Label>
                    <Input
                      id="nhcx-mobile"
                      inputMode="numeric"
                      value={mobileExtra}
                      onChange={(e) => setMobileExtra(e.target.value)}
                    />
                  </div>
                )}
                {idType !== "MemberId" && (
                  <div className="flex flex-col gap-1">
                    <Label htmlFor="nhcx-member">{t("nhcx_member_id")}</Label>
                    <Input
                      id="nhcx-member"
                      value={memberExtra}
                      onChange={(e) => setMemberExtra(e.target.value)}
                    />
                  </div>
                )}
              </div>
            </div>
            {formError && <ErrorText>{formError}</ErrorText>}
            <div className="flex justify-end">
              {waiting ? (
                <div className="flex flex-col items-end gap-1 text-sm">
                  <span className="flex items-center gap-2">
                    <Loader2 className="size-4 animate-spin" />
                    {t("nhcx_waiting_for_payer", {
                      payer: claim?.payer_id || payer,
                    })}
                  </span>
                  <CorrelationId value={claim?.correlation_id} />
                  <Button
                    variant="link"
                    size="sm"
                    onClick={() => setPolling(false)}
                  >
                    {t("nhcx_stop_waiting")}
                  </Button>
                </div>
              ) : (
                <Button
                  variant="primary"
                  disabled={discover.isPending}
                  onClick={submit}
                >
                  {t("nhcx_discover")}
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        {claim && claim.status === "error" && claim.error_message && (
          <Card>
            <CardContent className="pt-6">
              <ErrorText>{claim.error_message}</ErrorText>
            </CardContent>
          </Card>
        )}

        {answered && claim && (
          <Card>
            <CardHeader>
              <CardTitle>{t("nhcx_cover_returned")}</CardTitle>
            </CardHeader>
            <CardContent>
              {claim.status === "not-eligible" ||
              (!claim.policy_code && !claim.member_id) ? (
                <Muted>{t("nhcx_no_cover_returned")}</Muted>
              ) : (
                <button
                  type="button"
                  className="w-full rounded-md border p-4 text-left hover:border-primary-500 hover:bg-primary-50 md:w-96"
                  onClick={() =>
                    navigate(
                      `/facility/${facilityId}/claims/${claim.id}/eligibility`,
                    )
                  }
                >
                  <div className="font-semibold">
                    {claim.product_name ||
                      claim.plan_name ||
                      claim.payer_name ||
                      claim.payer_id}
                  </div>
                  <div className="text-sm text-gray-600">
                    {claim.policy_code || "-"} · {claim.member_id || "-"}
                  </div>
                  <div className="mt-2 grid grid-cols-3 gap-2 text-xs">
                    <div>
                      <div className="text-gray-500">
                        {t("nhcx_sum_insured")}
                      </div>
                      {formatMoney(claim.allowed_amount)}
                    </div>
                    <div>
                      <div className="text-gray-500">
                        {t("nhcx_valid_until")}
                      </div>
                      {formatDate(claim.plan_period_end)}
                    </div>
                    <div>
                      <div className="text-gray-500">{t("status")}</div>
                      {claim.inforce === false
                        ? t("nhcx_inactive")
                        : t("nhcx_active")}
                    </div>
                  </div>
                </button>
              )}
            </CardContent>
          </Card>
        )}

        {discoveries.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>{t("nhcx_discoveries_sent")}</CardTitle>
            </CardHeader>
            <CardContent className="divide-y">
              {discoveries.map((c) => {
                const chip = discoveryChip(c);
                return (
                  <div key={c.id} className="space-y-1 py-3 text-sm">
                    <div className="flex flex-wrap items-center gap-2">
                      <Link
                        href={`/facility/${facilityId}/claims/${c.id}/eligibility`}
                        className="font-medium text-primary-700 hover:underline"
                      >
                        {t("nhcx_discovery")}
                      </Link>
                      <Chip tone={chip.tone}>{t(chip.label)}</Chip>
                      <span>{c.payer_id || "-"}</span>
                      <span className="text-gray-500">
                        {formatDateTime(c.checked_at || c.created_date)}
                      </span>
                    </div>
                    <div className="grid gap-2 text-xs md:grid-cols-3">
                      <div>
                        <span className="text-gray-500">
                          {t("nhcx_correlation_id")}{" "}
                        </span>
                        <CorrelationId value={c.correlation_id} />
                      </div>
                      <div>
                        <span className="text-gray-500">
                          {t("nhcx_transaction")}{" "}
                        </span>
                        <CorrelationId value={c.txn_id} />
                      </div>
                    </div>
                    <div className="text-xs text-gray-600">
                      {t("nhcx_additional_information")}: {t("nhcx_mobile")}{" "}
                      {c.mobile_number || "-"} · {t("nhcx_member_id")}{" "}
                      {c.member_id || "-"}
                    </div>
                  </div>
                );
              })}
            </CardContent>
          </Card>
        )}
      </div>
    </Page>
  );
}
