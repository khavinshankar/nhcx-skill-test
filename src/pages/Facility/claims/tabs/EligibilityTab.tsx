import {
  RefreshCw,
  Send,
  ShieldCheck,
  TrendingDown,
  Wallet,
} from "lucide-react";
import { Link } from "raviger";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { Avatar } from "@/components/Common/Avatar";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import { EligibilityPurpose } from "@/types/nhcx/nhcx";
import nhcxApi from "@/types/nhcx/nhcxApi";

import {
  Chip,
  ConfirmButton,
  CorrelationId,
  DetailList,
  ErrorText,
  Muted,
  StatGrid,
  StatTile,
} from "@/pages/Facility/claims/components/ClaimWidgets";
import { ClaimTabProps } from "@/pages/Facility/claims/tabs/types";
import {
  nhcxCall,
  useClaimAction,
} from "@/pages/Facility/claims/useClaimAction";
import {
  CLAIM_STATUS,
  ID_TYPES,
  claimBalance,
  formatDate,
  formatDateTime,
  formatMoney,
} from "@/pages/Facility/claims/utils";

const PURPOSES: { value: EligibilityPurpose; label: string }[] = [
  { value: "validation", label: "nhcx_purpose_validation" },
  { value: "benefits", label: "nhcx_purpose_benefits" },
  { value: "discovery", label: "nhcx_purpose_discovery" },
];

const titleCase = (s?: string | null) =>
  s ? s.charAt(0).toUpperCase() + s.slice(1).toLowerCase() : "";

function photoSrc(photo?: string | null): string | undefined {
  if (!photo) return undefined;
  if (/^(https?:|data:)/.test(photo)) return photo;
  return `data:image/jpeg;base64,${photo}`;
}

// S3 Eligibility tab.
export default function EligibilityTab({
  facilityId,
  claimId,
  state,
}: ClaimTabProps) {
  const { t } = useTranslation();
  const { claim } = state;
  const [purpose, setPurpose] = useState<string>(claim.purpose || "validation");
  const [policyCode, setPolicyCode] = useState(claim.policy_code || "");
  const [memberId, setMemberId] = useState(claim.member_id || "");
  const [formError, setFormError] = useState<string>();

  useEffect(() => {
    setPolicyCode(claim.policy_code || "");
    setMemberId(claim.member_id || "");
  }, [claim.policy_code, claim.member_id]);

  const check = useClaimAction(
    claimId,
    (body: {
      purpose: EligibilityPurpose;
      policy_code: string;
      member_id: string;
    }) =>
      nhcxCall(nhcxApi.checkEligibility, {
        pathParams: { facilityId, claimId },
        body,
      }),
    t("nhcx_eligibility_queued"),
  );

  const send = () => {
    let error: string | undefined;
    if (!PURPOSES.some((p) => p.value === purpose))
      error = t("nhcx_choose_purpose");
    else if (!memberId.trim()) error = t("nhcx_member_id_required");
    else if (purpose === "validation" && !policyCode.trim())
      error = t("nhcx_policy_code_required_validation");
    else if (purpose === "benefits" && !policyCode.trim())
      error = t("nhcx_policy_code_required_benefits");
    setFormError(error);
    if (error) return;
    check.mutate({
      purpose: purpose as EligibilityPurpose,
      policy_code: policyCode.trim(),
      member_id: memberId.trim(),
    });
  };

  const status = CLAIM_STATUS[claim.status];
  const idLabel = ID_TYPES.find((o) => o.value === claim.search_id_type);
  const src = photoSrc(claim.patient_photo);
  const balance = claimBalance(claim);

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle>{t("nhcx_beneficiary")}</CardTitle>
        </CardHeader>
        <CardContent className="flex gap-4">
          <div className="size-20 shrink-0 overflow-hidden rounded-md">
            {src ? (
              <img src={src} alt="" className="size-20 object-cover" />
            ) : (
              <Avatar
                name={claim.beneficiary_name || claim.member_id || "?"}
                className="size-20"
              />
            )}
          </div>
          <div className="flex-1">
            <DetailList
              items={[
                { label: t("name"), value: claim.beneficiary_name },
                { label: t("nhcx_member_id"), value: claim.member_id },
                { label: t("nhcx_abha"), value: claim.abha_number },
                { label: t("nhcx_mobile"), value: claim.mobile_number },
                { label: t("gender"), value: titleCase(claim.patient_gender) },
                {
                  label: t("nhcx_date_of_birth"),
                  value: claim.patient_dob && formatDate(claim.patient_dob),
                },
                { label: t("address"), value: claim.patient_address },
                {
                  label: t("nhcx_found_by"),
                  value:
                    claim.search_id_value &&
                    `${idLabel ? t(idLabel.label) : claim.search_id_type || ""} · ${claim.search_id_value}`,
                },
              ]}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t("nhcx_policy")}</CardTitle>
        </CardHeader>
        <CardContent>
          <DetailList
            items={[
              { label: t("nhcx_policy_code"), value: claim.policy_code },
              {
                label: t("nhcx_product"),
                value: (
                  <>
                    <div>{claim.product_name || "-"}</div>
                    <div className="text-xs text-gray-500">
                      {claim.product_id || "-"}
                    </div>
                  </>
                ),
              },
              {
                label: t("nhcx_payer"),
                value: (
                  <>
                    <div>{claim.payer_name || claim.payer_id || "-"}</div>
                    <div className="text-xs text-gray-500">
                      {claim.payer_id || "-"}
                    </div>
                  </>
                ),
              },
              { label: t("nhcx_plan"), value: claim.plan_name },
              {
                label: t("nhcx_plan_period"),
                value:
                  (claim.plan_period_start || claim.plan_period_end) &&
                  `${formatDate(claim.plan_period_start)} → ${formatDate(claim.plan_period_end)}`,
              },
              {
                label: t("nhcx_relationship"),
                value: titleCase(claim.relationship),
              },
            ]}
          />
        </CardContent>
      </Card>

      {claim.status !== "draft" && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-2">
            <CardTitle className="flex items-center gap-2">
              {t("nhcx_payer_verdict")}
              {status && <Chip tone={status.tone}>{t(status.label)}</Chip>}
            </CardTitle>
            {claim.status === "checking" && (
              <ConfirmButton
                variant="secondary"
                confirm={t("nhcx_send_again_confirm")}
                disabled={check.isPending}
                onConfirm={() =>
                  check.mutate({
                    purpose: (claim.purpose ||
                      "validation") as EligibilityPurpose,
                    policy_code: claim.policy_code || "",
                    member_id: claim.member_id || "",
                  })
                }
              >
                <RefreshCw className="size-4" />
                {t("nhcx_send_again")}
              </ConfirmButton>
            )}
          </CardHeader>
          <CardContent className="space-y-4">
            {claim.status === "checking" && (
              <>
                <p className="text-sm">
                  {t("nhcx_eligibility_waiting", {
                    purpose: claim.purpose || t("nhcx_check_word"),
                  })}
                </p>
                {state.poll_notes.map((note) => (
                  <Muted key={note}>
                    {t("nhcx_could_not_poll", { error: note })}
                  </Muted>
                ))}
                <DetailList
                  items={[
                    {
                      label: t("nhcx_sent_at"),
                      value: formatDateTime(claim.checked_at),
                    },
                    {
                      label: t("nhcx_transaction"),
                      value: <CorrelationId value={claim.txn_id} />,
                    },
                    {
                      label: t("nhcx_correlation_id"),
                      value: <CorrelationId value={claim.correlation_id} />,
                    },
                  ]}
                />
              </>
            )}
            {claim.status === "error" && (
              <ErrorText>
                {claim.error_message || t("nhcx_exchange_failed")}
              </ErrorText>
            )}
            {(claim.status === "eligible" ||
              claim.status === "not-eligible") && (
              <>
                <StatGrid>
                  <StatTile
                    label={t("nhcx_sum_insured")}
                    value={
                      <span className="flex items-center gap-2">
                        <ShieldCheck className="size-4 text-gray-500" />
                        {formatMoney(claim.allowed_amount)}
                      </span>
                    }
                  />
                  <StatTile
                    label={t("nhcx_utilised")}
                    tone="warning"
                    value={
                      <span className="flex items-center gap-2">
                        <TrendingDown className="size-4 text-yellow-700" />
                        {formatMoney(claim.used_amount)}
                      </span>
                    }
                  />
                  <StatTile
                    label={t("nhcx_wallet_balance")}
                    tone={claim.status === "eligible" ? "success" : "danger"}
                    value={
                      <span className="flex items-center gap-2">
                        <Wallet className="size-4" />
                        {formatMoney(balance)}
                      </span>
                    }
                  />
                </StatGrid>
                <DetailList
                  items={[
                    { label: t("nhcx_disposition"), value: claim.disposition },
                    { label: t("nhcx_outcome"), value: claim.outcome },
                    {
                      label: t("nhcx_in_force"),
                      value:
                        claim.inforce === null
                          ? "-"
                          : claim.inforce
                            ? t("yes")
                            : t("no"),
                    },
                    {
                      label: t("nhcx_preauthorisation"),
                      value:
                        claim.auth_required === null
                          ? "-"
                          : claim.auth_required
                            ? t("nhcx_required")
                            : t("nhcx_not_required"),
                    },
                    {
                      label: t("nhcx_checked_at"),
                      value: formatDateTime(claim.checked_at),
                    },
                    {
                      label: t("nhcx_correlation_id"),
                      value: <CorrelationId value={claim.correlation_id} />,
                    },
                  ]}
                />
              </>
            )}
          </CardContent>
        </Card>
      )}

      {claim.status !== "checking" && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-2">
            <CardTitle>{t("nhcx_coverage_check")}</CardTitle>
            <Button variant="link" size="sm" asChild>
              <Link
                href={`/facility/${facilityId}/claims/discovery?case=${claimId}${
                  claim.patient ? `&patient=${claim.patient}` : ""
                }`}
              >
                {t("nhcx_discover_with_payer")}
              </Link>
            </Button>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid gap-4 md:grid-cols-3">
              <div className="flex flex-col gap-1">
                <Label>{t("nhcx_purpose")} *</Label>
                <Select value={purpose} onValueChange={setPurpose}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {PURPOSES.map((p) => (
                      <SelectItem key={p.value} value={p.value}>
                        {t(p.label)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex flex-col gap-1">
                <Label htmlFor="nhcx-elig-policy">
                  {t("nhcx_policy_code")}
                </Label>
                <Input
                  id="nhcx-elig-policy"
                  value={policyCode}
                  onChange={(e) => setPolicyCode(e.target.value)}
                />
                <Muted className="text-xs">{t("nhcx_policy_code_help")}</Muted>
              </div>
              <div className="flex flex-col gap-1">
                <Label htmlFor="nhcx-elig-member">
                  {t("nhcx_member_id")} *
                </Label>
                <Input
                  id="nhcx-elig-member"
                  value={memberId}
                  onChange={(e) => setMemberId(e.target.value)}
                />
              </div>
            </div>
            {formError && <ErrorText>{formError}</ErrorText>}
          </CardContent>
          <CardFooter className="justify-end">
            <Button variant="primary" disabled={check.isPending} onClick={send}>
              <Send className="size-4" />
              {claim.status === "draft"
                ? t("nhcx_send_to_payer")
                : t("nhcx_check_again")}
            </Button>
          </CardFooter>
        </Card>
      )}
    </div>
  );
}
