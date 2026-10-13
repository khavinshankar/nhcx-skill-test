import { useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

import { DetailList } from "@/pages/Facility/claims/components/ClaimWidgets";
import { nhcxCall, refusalText } from "@/pages/Facility/claims/useClaimAction";
import { abhaDigits, formatAbha } from "@/pages/Facility/claims/utils";
import {
  AbhaAccount,
  AbhaAction,
  AbhaProfile,
  AbhaRequest,
  AbhaResponse,
} from "@/types/nhcx/nhcx";
import nhcxApi from "@/types/nhcx/nhcxApi";

type Mode = "verify" | "create";
type Step = "start" | "otp" | "choose" | "address" | "done";

// A19 sends "Male" / "Female" / "Other"; CARE has no "other", so that one is
// left for the desk to choose.
export function abhaGender(gender?: string | null): "male" | "female" | "" {
  const g = (gender || "").toLowerCase();
  if (g === "male" || g === "m") return "male";
  if (g === "female" || g === "f") return "female";
  return "";
}

export function abhaPhone(mobile?: string | null): string {
  const d = abhaDigits(mobile);
  return d.length === 10 ? `+91${d}` : "";
}

// S13-S15: verify an ABHA by number or mobile OTP, or create one from an
// Aadhaar OTP (A19). Only `txn_id` is held here; tokens stay on the server.
export default function AbhaDialog({
  open,
  onOpenChange,
  onProfile,
  initialAbha,
  confirmLabel,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onProfile: (profile: AbhaProfile, txnId: string) => void | Promise<void>;
  initialAbha?: string | null;
  confirmLabel?: string;
}) {
  const { t } = useTranslation();
  const [mode, setMode] = useState<Mode>("verify");
  const [step, setStep] = useState<Step>("start");
  const [busy, setBusy] = useState(false);
  const [txnId, setTxnId] = useState("");
  const [note, setNote] = useState("");
  const [loginId, setLoginId] = useState(initialAbha || "");
  const [aadhaar, setAadhaar] = useState("");
  const [consent, setConsent] = useState(false);
  const [otp, setOtp] = useState("");
  const [mobile, setMobile] = useState("");
  const [accounts, setAccounts] = useState<AbhaAccount[]>([]);
  const [chosen, setChosen] = useState("");
  const [addresses, setAddresses] = useState<string[]>([]);
  const [address, setAddress] = useState("");
  const [profile, setProfile] = useState<AbhaProfile | null>(null);
  const [isNew, setIsNew] = useState<boolean | null>(null);

  const reset = (next: Mode = mode) => {
    setMode(next);
    setStep("start");
    setTxnId("");
    setNote("");
    setOtp("");
    setMobile("");
    setAadhaar("");
    setConsent(false);
    setAccounts([]);
    setChosen("");
    setAddresses([]);
    setAddress("");
    setProfile(null);
    setIsNew(null);
  };

  const run = async (
    action: AbhaAction,
    body: AbhaRequest,
  ): Promise<AbhaResponse | null> => {
    setBusy(true);
    try {
      const res = await nhcxCall(nhcxApi.abha, {
        pathParams: { action },
        body,
      });
      if (res.ok === false) {
        toast.error(res.error || t("something_went_wrong"));
        return null;
      }
      if (res.txn_id) setTxnId(res.txn_id);
      setNote(res.message || "");
      return res;
    } catch (error) {
      toast.error(refusalText(error, t("something_went_wrong")));
      return null;
    } finally {
      setBusy(false);
    }
  };

  const showProfile = (p: AbhaProfile) => {
    setProfile(p);
    setStep("done");
  };

  const sendLoginOtp = async () => {
    const d = abhaDigits(loginId);
    const body: AbhaRequest = d.length === 10 ? { mobile: d } : { abha_no: d };
    const res = await run("mobile-otp", body);
    if (res) {
      setOtp("");
      setStep("otp");
    }
  };

  const verifyLoginOtp = async () => {
    const res = await run("mobile-verify", { txn_id: txnId, otp });
    if (!res) return;
    if (res.profile && res.hint !== "mobile") {
      showProfile(res.profile);
      return;
    }
    const listed = res.accounts || [];
    setAccounts(listed);
    setChosen(listed.length === 1 ? listed[0].abha_no : "");
    setStep("choose");
  };

  const chooseAccount = async () => {
    const res = await run("profile", {
      txn_id: txnId,
      abha_no: chosen,
    });
    if (res?.profile) showProfile(res.profile);
  };

  const sendAadhaarOtp = async () => {
    const res = await run("aadhaar-otp", { aadhaar: abhaDigits(aadhaar) });
    if (res) {
      setOtp("");
      setStep("otp");
    }
  };

  const verifyAadhaarOtp = async () => {
    const res = await run("aadhaar-verify", {
      txn_id: txnId,
      otp,
      mobile: abhaDigits(mobile) || undefined,
    });
    if (!res?.profile) return;
    setIsNew(!!res.is_new);
    if (!res.is_new) {
      showProfile(res.profile);
      return;
    }
    setProfile(res.profile);
    const offered = await run("suggestions", { txn_id: res.txn_id || txnId });
    setAddresses(offered?.addresses || []);
    setAddress(offered?.addresses?.[0] || "");
    setStep("address");
  };

  const claimAddress = async () => {
    const res = await run("address", { txn_id: txnId, abha_address: address });
    if (!res) return;
    const refreshed = await run("profile", { txn_id: txnId });
    showProfile({
      ...(profile as AbhaProfile),
      ...(refreshed?.profile || {}),
      abha_no: refreshed?.profile?.abha_no || res.abha_no || profile!.abha_no,
      abha_address:
        refreshed?.profile?.abha_address || res.abha_address || address,
    });
  };

  const confirm = async () => {
    if (!profile) return;
    setBusy(true);
    try {
      await onProfile(profile, txnId);
      onOpenChange(false);
      reset();
    } finally {
      setBusy(false);
    }
  };

  const close = (next: boolean) => {
    if (!next) reset();
    onOpenChange(next);
  };

  const otpField = (
    <div className="space-y-1">
      <Label htmlFor="abha-otp">{t("nhcx_abha_otp")}</Label>
      <Input
        id="abha-otp"
        inputMode="numeric"
        autoComplete="one-time-code"
        maxLength={6}
        value={otp}
        onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
      />
    </div>
  );

  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{t("nhcx_abha_dialog_title")}</DialogTitle>
          <DialogDescription>
            {t("nhcx_abha_dialog_description")}
          </DialogDescription>
        </DialogHeader>

        <Tabs
          value={mode}
          onValueChange={(v) => reset(v as Mode)}
          className="w-full"
        >
          <TabsList className="w-full">
            <TabsTrigger value="verify" className="flex-1" disabled={busy}>
              {t("nhcx_abha_tab_verify")}
            </TabsTrigger>
            <TabsTrigger value="create" className="flex-1" disabled={busy}>
              {t("nhcx_abha_tab_create")}
            </TabsTrigger>
          </TabsList>
        </Tabs>

        <div className="space-y-4">
          {note && step !== "start" && (
            <p className="text-sm text-gray-600">{note}</p>
          )}

          {mode === "verify" && step === "start" && (
            <div className="space-y-1">
              <Label htmlFor="abha-login">{t("nhcx_abha_login_id")}</Label>
              <Input
                id="abha-login"
                value={loginId}
                onChange={(e) => setLoginId(e.target.value)}
                placeholder="91-1234-5678-9012"
              />
              <p className="text-xs text-gray-500">
                {t("nhcx_abha_login_id_help")}
              </p>
            </div>
          )}

          {mode === "create" && step === "start" && (
            <>
              <div className="space-y-1">
                <Label htmlFor="abha-aadhaar">{t("nhcx_aadhaar_number")}</Label>
                <Input
                  id="abha-aadhaar"
                  inputMode="numeric"
                  autoComplete="off"
                  value={aadhaar}
                  onChange={(e) => setAadhaar(e.target.value)}
                />
              </div>
              <div className="flex items-start gap-2">
                <Checkbox
                  id="abha-consent"
                  checked={consent}
                  onCheckedChange={(v) => setConsent(v === true)}
                />
                <Label htmlFor="abha-consent" className="font-normal leading-5">
                  {t("nhcx_abha_consent")}
                </Label>
              </div>
            </>
          )}

          {step === "otp" && (
            <>
              {otpField}
              {mode === "create" && (
                <div className="space-y-1">
                  <Label htmlFor="abha-mobile">
                    {t("nhcx_abha_communication_mobile")}
                  </Label>
                  <Input
                    id="abha-mobile"
                    inputMode="numeric"
                    value={mobile}
                    onChange={(e) => setMobile(e.target.value)}
                  />
                </div>
              )}
            </>
          )}

          {step === "choose" && (
            <div className="space-y-2">
              <Label>{t("nhcx_abha_choose_account")}</Label>
              <RadioGroup value={chosen} onValueChange={setChosen}>
                {accounts.map((a) => (
                  <div key={a.abha_no} className="flex items-center gap-2">
                    <RadioGroupItem value={a.abha_no} id={`acc-${a.abha_no}`} />
                    <Label htmlFor={`acc-${a.abha_no}`} className="font-normal">
                      {a.name || "-"} · {a.abha_no}
                      {a.abha_address ? ` · ${a.abha_address}` : ""}
                    </Label>
                  </div>
                ))}
              </RadioGroup>
            </div>
          )}

          {step === "address" && (
            <div className="space-y-2">
              <Label htmlFor="abha-address">
                {t("nhcx_abha_choose_address")}
              </Label>
              {addresses.length > 0 && (
                <RadioGroup value={address} onValueChange={setAddress}>
                  {addresses.map((a) => (
                    <div key={a} className="flex items-center gap-2">
                      <RadioGroupItem value={a} id={`addr-${a}`} />
                      <Label htmlFor={`addr-${a}`} className="font-normal">
                        {a}
                      </Label>
                    </div>
                  ))}
                </RadioGroup>
              )}
              <Input
                id="abha-address"
                value={address}
                onChange={(e) => setAddress(e.target.value.trim())}
              />
            </div>
          )}

          {step === "done" && profile && (
            <div className="space-y-2">
              {mode === "create" && isNew === false && (
                <p className="text-sm text-yellow-700">
                  {t("nhcx_abha_existing_account")}
                </p>
              )}
              <DetailList
                columns={2}
                items={[
                  {
                    label: t("nhcx_abha_number"),
                    value: formatAbha(profile.abha_no) || "-",
                  },
                  {
                    label: t("nhcx_abha_address"),
                    value: profile.abha_address || "-",
                  },
                  { label: t("name"), value: profile.name || "-" },
                  { label: t("gender"), value: profile.gender || "-" },
                  { label: t("date_of_birth"), value: profile.dob || "-" },
                  { label: t("phone_number"), value: profile.mobile || "-" },
                ]}
              />
            </div>
          )}
        </div>

        <DialogFooter className="gap-2">
          {step !== "start" && step !== "done" && (
            <Button variant="outline" disabled={busy} onClick={() => reset()}>
              {t("nhcx_abha_start_over")}
            </Button>
          )}
          {step === "start" && mode === "verify" && (
            <Button disabled={busy || !loginId.trim()} onClick={sendLoginOtp}>
              {t("nhcx_abha_send_otp")}
            </Button>
          )}
          {step === "start" && mode === "create" && (
            <Button
              disabled={busy || !aadhaar.trim() || !consent}
              onClick={sendAadhaarOtp}
            >
              {t("nhcx_abha_send_otp")}
            </Button>
          )}
          {step === "otp" && (
            <Button
              disabled={busy || !otp}
              onClick={mode === "verify" ? verifyLoginOtp : verifyAadhaarOtp}
            >
              {t("nhcx_abha_verify_otp")}
            </Button>
          )}
          {step === "choose" && (
            <Button disabled={busy || !chosen} onClick={chooseAccount}>
              {t("nhcx_abha_use_account")}
            </Button>
          )}
          {step === "address" && (
            <Button disabled={busy || !address} onClick={claimAddress}>
              {t("nhcx_abha_set_address")}
            </Button>
          )}
          {step === "done" && (
            <Button disabled={busy} onClick={confirm}>
              {confirmLabel || t("nhcx_abha_use_details")}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
