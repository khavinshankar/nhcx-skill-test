import { useMutation } from "@tanstack/react-query";
import { Check, Fingerprint, RefreshCw } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/Common/Table";

import {
  BiometricAuth,
  BiometricMethod,
  BiometricRequest,
  BiometricResponse,
  ClaimState,
} from "@/types/nhcx/nhcx";
import nhcxApi from "@/types/nhcx/nhcxApi";

import { Chip, Muted } from "@/pages/Facility/claims/components/ClaimWidgets";
import { ClaimTabProps } from "@/pages/Facility/claims/tabs/types";
import {
  nhcxCall,
  refusalText,
  useClaimAction,
} from "@/pages/Facility/claims/useClaimAction";
import { abhaDigits, formatDateTime } from "@/pages/Facility/claims/utils";

const METHODS: { value: BiometricMethod; label: string }[] = [
  { value: "FINGERPRINT", label: "nhcx_fingerprint" },
  { value: "IRIS", label: "nhcx_iris" },
  { value: "FACE_AUTH", label: "nhcx_face" },
];

const USER_TOKEN_HEADER = "x-hcx-user-token";

// The stage follows the stay: Discharge once the linked admission has ended.
export function verificationStage(state: ClaimState): "Preauth" | "Discharge" {
  const encounter = state.claim.encounter;
  if (!encounter) return "Preauth";
  const open = state.admissions.some((a) => a.id === encounter);
  const discharged =
    !!state.claim.discharge_date || !!state.submission?.discharge_date;
  return discharged || !open ? "Discharge" : "Preauth";
}

export function biometricRequired(state: ClaimState): boolean {
  return state.biometric_required ?? state.adapter === "pmjay";
}

function currentAuth(rows: BiometricAuth[], stage: string) {
  const now = Date.now();
  return rows
    .filter((r) => r.stage === stage && r.status === "verified")
    .sort((a, b) => (b.verified_at || "").localeCompare(a.verified_at || ""))
    .map((r) => ({
      row: r,
      live: !!r.token_expires_at && Date.parse(r.token_expires_at) > now,
      refreshable:
        !!r.refresh_expires_at && Date.parse(r.refresh_expires_at) > now,
    }))[0];
}

async function wadh(method: BiometricMethod): Promise<string> {
  const text = `2.5${method === "IRIS" ? "I" : "F"}YYNN`;
  const hash = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(text),
  );
  return btoa(String.fromCharCode(...new Uint8Array(hash)));
}

// Asks the RD service on this machine (ports 11100-11120) for a PID block.
async function captureFromDevice(method: BiometricMethod): Promise<string> {
  const options =
    `<PidOptions ver="1.0"><Opts fCount="${method === "IRIS" ? 0 : 1}" ` +
    `fType="2" iCount="${method === "IRIS" ? 1 : 0}" iType="0" pCount="0" ` +
    `format="0" pidVer="2.0" timeout="10000" posh="UNKNOWN" env="P" ` +
    `wadh="${await wadh(method)}" /></PidOptions>`;
  for (let port = 11100; port <= 11120; port++) {
    try {
      const res = await fetch(`http://127.0.0.1:${port}/rd/capture`, {
        method: "CAPTURE",
        headers: { "Content-Type": "text/xml" },
        body: options,
      });
      if (!res.ok) continue;
      const body = await res.text();
      if (body.includes("<PidData")) return body;
    } catch {
      // try the next port
    }
  }
  throw new Error("RD service not found");
}

// S18 Beneficiary verification.
export default function VerificationTab({
  facilityId,
  claimId,
  state,
}: ClaimTabProps) {
  const { t } = useTranslation();
  const stage = verificationStage(state);
  const required = biometricRequired(state);
  const attempts = state.biometric ?? [];
  const current = currentAuth(attempts, stage);
  const [method, setMethod] = useState<BiometricMethod>("FINGERPRINT");
  const [attempt, setAttempt] = useState<BiometricAuth | null>(null);
  const [qrUrl, setQrUrl] = useState<string | null>(null);
  const [captured, setCaptured] = useState(false);
  const [pid, setPid] = useState("");
  const [aadhaar, setAadhaar] = useState("");
  const [mobile, setMobile] = useState("");
  const [capturing, setCapturing] = useState(false);

  const call = (action: string, body: BiometricRequest) =>
    nhcxCall(nhcxApi.biometric, {
      pathParams: { facilityId, claimId, action },
      body,
    });

  const close = () => {
    setAttempt(null);
    setQrUrl(null);
    setCaptured(false);
    setPid("");
    setAadhaar("");
    setMobile("");
  };

  const init = useClaimAction(claimId, () =>
    call("init", {
      stage,
      method,
    }).then((res: BiometricResponse) => {
      if (res.ok !== false && res.attempt) {
        setAttempt(res.attempt);
        setQrUrl(res.qr_url ?? res.attempt.qr_url ?? null);
        setCaptured(false);
      }
      return { ...res, message: null };
    }),
  );

  const verify = useClaimAction(
    claimId,
    () =>
      call("verify", {
        attempt: attempt?.id,
        ...(attempt?.method === "FACE_AUTH"
          ? { aadhaar: abhaDigits(aadhaar), mobile: abhaDigits(mobile) }
          : { pid }),
      }),
    t("nhcx_beneficiary_verified_by", {
      method: t(
        METHODS.find((m) => m.value === attempt?.method)?.label ??
          "nhcx_fingerprint",
      ),
    }),
    close,
  );

  const refresh = useClaimAction(claimId, () =>
    call("refresh", { attempt: current?.row.id }),
  );

  // Face: poll the capture every few seconds until the phone completes it.
  const capturePoll = useMutation({
    mutationFn: () =>
      call("capture", { attempt: attempt?.id }) as Promise<
        BiometricResponse & { status?: string }
      >,
  });
  const facePending = !!attempt && attempt.method === "FACE_AUTH" && !captured;
  useEffect(() => {
    if (!facePending) return;
    const timer = window.setInterval(() => {
      capturePoll.mutate(undefined, {
        onSuccess: (res) => {
          if (res.status === "COMPLETE" || res.attempt?.status === "captured") {
            setCaptured(true);
          }
        },
      });
    }, 4000);
    return () => window.clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [facePending, attempt?.id]);

  const onVerify = () => {
    if (attempt?.method === "FACE_AUTH") {
      if (abhaDigits(aadhaar).length !== 12) {
        toast.error(t("nhcx_aadhaar_12_digits"));
        return;
      }
    } else if (!pid.trim()) {
      toast.error(
        attempt?.method === "IRIS"
          ? t("nhcx_capture_iris_first")
          : t("nhcx_capture_fingerprint_first"),
      );
      return;
    }
    verify.mutate(undefined);
  };

  const capture = async () => {
    if (!attempt) return;
    setCapturing(true);
    try {
      setPid(await captureFromDevice(attempt.method));
    } catch (error) {
      toast.error(refusalText(error, t("something_went_wrong")));
    } finally {
      setCapturing(false);
    }
  };

  let summary: { tone: "success" | "warning"; text: string } | null;
  if (current?.live) {
    summary = { tone: "success", text: t("nhcx_verified_token_live") };
  } else if (current) {
    summary = { tone: "warning", text: t("nhcx_verified_token_lapsed") };
  } else {
    summary = {
      tone: "warning",
      text: required
        ? t("nhcx_not_verified_consent")
        : t("nhcx_not_verified_no_token"),
    };
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          {stage === "Discharge"
            ? t("nhcx_discharge_verification")
            : t("nhcx_beneficiary_verification")}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <Chip tone={required ? "warning" : "neutral"}>
            {required
              ? t("nhcx_required_by_payer")
              : t("nhcx_optional_for_payer")}
          </Chip>
          <Chip tone={summary.tone}>{summary.text}</Chip>
          {current?.live && (
            <span className="text-sm text-gray-700">
              {t("nhcx_verified_by_at", {
                method: t(
                  METHODS.find((m) => m.value === current.row.method)?.label ??
                    current.row.method,
                ),
                at: formatDateTime(current.row.verified_at),
                until: formatDateTime(current.row.token_expires_at),
              })}
            </span>
          )}
          {current?.refreshable && (
            <Button
              size="sm"
              variant="outline"
              className="ml-auto"
              disabled={refresh.isPending}
              onClick={() => refresh.mutate(undefined)}
            >
              <RefreshCw className="size-4" />
              {t("nhcx_refresh_token")}
            </Button>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="flex gap-1">
            {METHODS.map((m) => (
              <Button
                key={m.value}
                size="sm"
                variant={method === m.value ? "primary" : "outline"}
                onClick={() => setMethod(m.value)}
              >
                {t(m.label)}
              </Button>
            ))}
          </div>
          <Button
            size="sm"
            variant="primary"
            disabled={init.isPending}
            onClick={() => init.mutate(undefined)}
          >
            {current || attempts.length
              ? t("nhcx_authenticate_again")
              : t("nhcx_authenticate_beneficiary")}
          </Button>
        </div>

        {attempt && attempt.method !== "FACE_AUTH" && (
          <div className="space-y-3 rounded-md border p-4">
            <p className="text-sm">
              {attempt.method === "IRIS"
                ? t("nhcx_iris_instruction")
                : t("nhcx_fingerprint_instruction")}
            </p>
            <Button
              size="sm"
              variant="outline"
              disabled={capturing}
              onClick={capture}
            >
              <Fingerprint className="size-4" />
              {t("nhcx_capture_from_device")}
            </Button>
            <div className="space-y-1">
              <Label htmlFor="nhcx-pid">{t("nhcx_pid_block_label")}</Label>
              <Textarea
                id="nhcx-pid"
                rows={4}
                value={pid}
                onChange={(e) => setPid(e.target.value)}
              />
            </div>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="primary"
                disabled={!pid.trim() || verify.isPending}
                onClick={onVerify}
              >
                <Check className="size-4" />
                {t("nhcx_verify")}
              </Button>
              <Button size="sm" variant="outline" onClick={close}>
                {t("cancel")}
              </Button>
            </div>
          </div>
        )}

        {attempt && attempt.method === "FACE_AUTH" && (
          <div className="flex flex-wrap gap-4 rounded-md border p-4">
            {qrUrl && (
              <div className="size-36 bg-white p-2">
                <QRCodeSVG value={qrUrl} className="size-full" />
              </div>
            )}
            <div className="flex flex-1 flex-col gap-3">
              <p className="text-sm">{t("nhcx_scan_with_abha_app")}</p>
              {!captured ? (
                <Muted>{t("nhcx_awaiting_capture")}</Muted>
              ) : (
                <>
                  <div className="space-y-1">
                    <Label htmlFor="nhcx-face-aadhaar">
                      {t("nhcx_aadhaar_number")}
                    </Label>
                    <Input
                      id="nhcx-face-aadhaar"
                      inputMode="numeric"
                      autoComplete="off"
                      value={aadhaar}
                      onChange={(e) => setAadhaar(e.target.value)}
                    />
                    <Muted className="text-xs">
                      {t("nhcx_aadhaar_sealed")}
                    </Muted>
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor="nhcx-face-mobile">
                      {t("nhcx_aadhaar_linked_mobile")}
                    </Label>
                    <Input
                      id="nhcx-face-mobile"
                      inputMode="numeric"
                      value={mobile}
                      onChange={(e) => setMobile(e.target.value)}
                    />
                  </div>
                </>
              )}
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="primary"
                  disabled={!captured || verify.isPending}
                  onClick={onVerify}
                >
                  <Check className="size-4" />
                  {t("nhcx_verify")}
                </Button>
                <Button size="sm" variant="outline" onClick={close}>
                  {t("cancel")}
                </Button>
              </div>
            </div>
          </div>
        )}

        <Accordion type="multiple">
          <AccordionItem value="attempts">
            <AccordionTrigger>
              {t("nhcx_every_attempt", { n: attempts.length })}
            </AccordionTrigger>
            <AccordionContent>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t("nhcx_stage")}</TableHead>
                      <TableHead>{t("nhcx_method")}</TableHead>
                      <TableHead>{t("status")}</TableHead>
                      <TableHead>{t("nhcx_time")}</TableHead>
                      <TableHead>{t("nhcx_transaction")}</TableHead>
                      <TableHead>{t("nhcx_reason")}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {attempts.map((a) => (
                      <TableRow key={a.id}>
                        <TableCell>{a.stage}</TableCell>
                        <TableCell>
                          {t(
                            METHODS.find((m) => m.value === a.method)?.label ??
                              a.method,
                          )}
                        </TableCell>
                        <TableCell>
                          <Chip
                            tone={
                              a.status === "verified"
                                ? "success"
                                : a.status === "failed"
                                  ? "danger"
                                  : "info"
                            }
                          >
                            {a.status}
                          </Chip>
                        </TableCell>
                        <TableCell>
                          {formatDateTime(a.verified_at || a.created_date)}
                        </TableCell>
                        <TableCell className="font-mono text-xs">
                          {a.txn_id || "-"}
                        </TableCell>
                        <TableCell>
                          {a.status === "failed" ? a.message || "-" : "-"}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </AccordionContent>
          </AccordionItem>
        </Accordion>
        <Muted>
          {t("nhcx_token_rides_under", { header: USER_TOKEN_HEADER })}
        </Muted>
      </CardContent>
    </Card>
  );
}
