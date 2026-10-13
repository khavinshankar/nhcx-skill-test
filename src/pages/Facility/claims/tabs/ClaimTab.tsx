import { HelpCircle, RotateCcw, Save, Send, Wallet } from "lucide-react";
import { useEffect, useState } from "react";
import { Trans, useTranslation } from "react-i18next";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

import {
  ClaimLine,
  ClaimState,
  DischargeMode,
  DischargeRequest,
  DischargeStage,
} from "@/types/nhcx/nhcx";
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
import {
  DocumentsCard,
  EnquiryRows,
  FormsCard,
  ItemVerdictTable,
  QueryNote,
  ResubmitReply,
} from "@/pages/Facility/claims/components/LegParts";
import { QuotedLinesTable } from "@/pages/Facility/claims/tabs/LineItemsTab";
import { CommunicationPointer } from "@/pages/Facility/claims/tabs/PreauthTab";
import { ClaimTabProps } from "@/pages/Facility/claims/tabs/types";
import {
  nhcxCall,
  useClaimAction,
} from "@/pages/Facility/claims/useClaimAction";
import {
  LEG_STATUS,
  formatDateTime,
  formatMoney,
  isRefused,
  toNumber,
} from "@/pages/Facility/claims/utils";

const BLANK = "__blank";

export const DISCHARGE_MODES: { value: DischargeMode; label: string }[] = [
  { value: "normal", label: "nhcx_discharge_normal" },
  { value: "lama", label: "nhcx_discharge_lama" },
  { value: "dama", label: "nhcx_discharge_dama" },
  { value: "death", label: "nhcx_discharge_death" },
];

export const DISCHARGE_STAGES: DischargeStage[] = [
  "Before Surgery",
  "During Surgery",
  "After Surgery",
];

const REPROCESS_REASONS = [
  { value: "claimrejected", label: "nhcx_reprocess_claimrejected" },
  { value: "partialpayment", label: "nhcx_reprocess_partialpayment" },
  { value: "rejectiondisputed", label: "nhcx_reprocess_rejectiondisputed" },
];

function discharge(state: ClaimState) {
  const s = state.submission;
  const c = state.claim;
  return {
    mode: s?.discharge_mode ?? c.discharge_mode ?? null,
    stage: s?.discharge_stage ?? c.discharge_stage ?? null,
    date: s?.discharge_date ?? c.discharge_date ?? null,
    surgery: s?.surgery_date ?? c.surgery_date ?? null,
    death: s?.death_date ?? c.death_date ?? null,
  };
}

export const isLama = (mode?: string | null, stage?: string | null): boolean =>
  (mode === "lama" || mode === "dama") &&
  (stage === "Before Surgery" || stage === "During Surgery");

// S11: a LAMA / DAMA case before or during surgery claims LM100 only.
function claimLines(state: ClaimState): ClaimLine[] {
  const d = discharge(state);
  if (!isLama(d.mode, d.stage)) return state.lines;
  const from = state.claim.admission_date;
  const days =
    from && d.date
      ? Math.max(
          1,
          Math.round(
            (new Date(d.date.slice(0, 10)).getTime() -
              new Date(from.slice(0, 10)).getTime()) /
              86400000,
          ),
        )
      : 1;
  const benefit = state.benefits.find((b) => b.code === "LM100");
  const rate = toNumber(benefit?.rate) ?? 0;
  return [
    {
      id: "LM100",
      seq: 1,
      kind: "Procedure",
      code: "LM100",
      display: benefit?.display || "LAMA / DAMA procedure",
      category_code: null,
      category_display: null,
      unit_price: String(rate),
      quantity: days,
      amount: String(rate * days),
      parent_code: null,
    },
  ];
}

const dateOnly = (v?: string | null) => (v ? v.slice(0, 10) : "");
const dateTimeLocal = (v?: string | null) => (v ? v.slice(0, 16) : "");

// S11 Discharge card.
function DischargeCard({ facilityId, claimId, state }: ClaimTabProps) {
  const { t } = useTranslation();
  const d = discharge(state);
  const [mode, setMode] = useState<DischargeMode | "">("");
  const [stage, setStage] = useState<DischargeStage | "">("");
  const [date, setDate] = useState("");
  const [surgery, setSurgery] = useState("");
  const [death, setDeath] = useState("");
  const seed = JSON.stringify(d);
  useEffect(() => {
    setMode(d.mode ?? "");
    setStage(d.stage ?? "");
    setDate(dateOnly(d.date));
    setSurgery(dateOnly(d.surgery));
    setDeath(dateTimeLocal(d.death));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seed]);

  const save = useClaimAction(
    claimId,
    (body: DischargeRequest) =>
      nhcxCall(nhcxApi.recordDischarge, {
        pathParams: { facilityId, claimId },
        body,
      }),
    t("nhcx_discharge_recorded"),
  );
  const busy = state.submission?.status === "submitting";

  const submit = (e: React.SyntheticEvent) => {
    e.preventDefault();
    const admitted = dateOnly(state.claim.admission_date);
    const check = [
      [!mode, "nhcx_discharge_choose_mode"],
      [!stage, "nhcx_discharge_choose_stage"],
      [!date, "nhcx_discharge_enter_date"],
      [admitted && date && date < admitted, "nhcx_discharge_before_admission"],
      [
        admitted && surgery && surgery < admitted,
        "nhcx_surgery_before_admission",
      ],
      [surgery && date && date < surgery, "nhcx_discharge_before_surgery"],
      [mode === "death" && !death, "nhcx_enter_death_time"],
    ].find(([bad]) => bad);
    if (check) {
      toast.error(t(check[1] as string));
      return;
    }
    save.mutate({
      discharge_mode: mode,
      discharge_stage: stage,
      discharge_date: date,
      surgery_date: surgery || undefined,
      death_date: mode === "death" ? death : undefined,
    });
  };

  return (
    <Card>
      <form onSubmit={submit}>
        <CardHeader>
          <CardTitle>{t("nhcx_discharge")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {isLama(mode, stage) && (
            <div className="space-y-2">
              <Badge variant="yellow">{t("nhcx_lm100_only")}</Badge>
              <p className="text-sm">
                <Trans
                  i18nKey="nhcx_lm100_text"
                  components={{ b: <strong /> }}
                />
              </p>
            </div>
          )}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="flex flex-col gap-1">
              <Label>
                {t("nhcx_discharge_type")}
                <span className="text-red-500"> *</span>
              </Label>
              <Select
                value={mode || BLANK}
                onValueChange={(v) =>
                  setMode(v === BLANK ? "" : (v as DischargeMode))
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={BLANK}>{t("nhcx_select")}</SelectItem>
                  {DISCHARGE_MODES.map((m) => (
                    <SelectItem key={m.value} value={m.value}>
                      {t(m.label)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Muted className="text-xs">{t("nhcx_discharge_type_help")}</Muted>
            </div>
            <div className="flex flex-col gap-1">
              <Label>
                {t("nhcx_stage")}
                <span className="text-red-500"> *</span>
              </Label>
              <Select
                value={stage || BLANK}
                onValueChange={(v) =>
                  setStage(v === BLANK ? "" : (v as DischargeStage))
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={BLANK}>{t("nhcx_select")}</SelectItem>
                  {DISCHARGE_STAGES.map((s) => (
                    <SelectItem key={s} value={s}>
                      {s}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Muted className="text-xs">
                {t("nhcx_discharge_stage_help")}
              </Muted>
            </div>
            <div className="flex flex-col gap-1">
              <Label htmlFor="nhcx-discharge-on">
                {t("nhcx_discharge_date")}
                <span className="text-red-500"> *</span>
              </Label>
              <Input
                id="nhcx-discharge-on"
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-1">
              <Label htmlFor="nhcx-surgery-on">{t("nhcx_surgery_date")}</Label>
              <Input
                id="nhcx-surgery-on"
                type="date"
                value={surgery}
                onChange={(e) => setSurgery(e.target.value)}
              />
              <Muted className="text-xs">{t("nhcx_surgery_date_help")}</Muted>
            </div>
            <div className="flex flex-col gap-1">
              <Label htmlFor="nhcx-death-at">{t("nhcx_death_time")}</Label>
              <Input
                id="nhcx-death-at"
                type="datetime-local"
                value={death}
                onChange={(e) => setDeath(e.target.value)}
              />
              <Muted className="text-xs">{t("nhcx_death_time_help")}</Muted>
            </div>
          </div>
        </CardContent>
        {!busy && (
          <CardFooter className="justify-end">
            <Button type="submit" variant="primary" disabled={save.isPending}>
              <Save className="size-4" />
              {t("nhcx_save_discharge")}
            </Button>
          </CardFooter>
        )}
      </form>
    </Card>
  );
}

function ReprocessForm({ facilityId, claimId, state }: ClaimTabProps) {
  const { t } = useTranslation();
  const paid = toNumber(state.paid_total) ?? 0;
  const [reason, setReason] = useState(
    paid > 0 || state.submission?.status === "partial"
      ? "partialpayment"
      : "claimrejected",
  );
  const [note, setNote] = useState("");
  const [chosen, setChosen] = useState<string[]>([]);
  const send = useClaimAction(
    claimId,
    () =>
      nhcxCall(nhcxApi.enquiry, {
        pathParams: { facilityId, claimId },
        body: {
          action: "reprocess",
          leg: "claim",
          reason,
          note,
          document_ids: chosen,
        },
      }),
    t("nhcx_reprocess_sent"),
    () => {
      setNote("");
      setChosen([]);
    },
  );
  return (
    <form
      className="space-y-3 border-t pt-4"
      onSubmit={(e) => {
        e.preventDefault();
        if (!note.trim()) {
          toast.error(t("nhcx_reprocess_say_why"));
          return;
        }
        send.mutate(undefined);
      }}
    >
      <h4 className="text-sm font-semibold">{t("nhcx_reprocess")}</h4>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="flex flex-col gap-1">
          <Label>
            {t("nhcx_why")}
            <span className="text-red-500"> *</span>
          </Label>
          <Select value={reason} onValueChange={setReason}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {REPROCESS_REASONS.map((r) => (
                <SelectItem key={r.value} value={r.value}>
                  {t(r.label)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor="nhcx-reprocess-note">{t("nhcx_reprocess_ask")}</Label>
          <Textarea
            id="nhcx-reprocess-note"
            rows={2}
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
          <Muted className="text-xs">{t("nhcx_reprocess_help")}</Muted>
        </div>
      </div>
      {state.documents.length > 0 && (
        <div className="space-y-2">
          <Label>{t("nhcx_reprocess_evidence")}</Label>
          {state.documents.map((d) => (
            <label key={d.id} className="flex items-center gap-2 text-sm">
              <Checkbox
                checked={chosen.includes(d.id)}
                onCheckedChange={(v) =>
                  setChosen((cur) =>
                    v ? [...cur, d.id] : cur.filter((x) => x !== d.id),
                  )
                }
              />
              <span>{d.label || d.filename}</span>
              <span className="text-xs text-gray-500">{d.code}</span>
            </label>
          ))}
          <Muted className="text-xs">{t("nhcx_reprocess_evidence_help")}</Muted>
        </div>
      )}
      <div className="flex justify-end">
        <Button type="submit" variant="primary" disabled={send.isPending}>
          <RotateCcw className="size-4" />
          {t("nhcx_send_reprocess")}
        </Button>
      </div>
      <EnquiryRows
        enquiries={state.enquiries}
        stage="claim"
        kinds={["reprocess"]}
      />
    </form>
  );
}

function ReleaseForm({
  facilityId,
  claimId,
  state,
  claimed,
  balance,
}: Omit<ClaimTabProps, "goTo"> & { claimed: number; balance: number }) {
  const { t } = useTranslation();
  const paid = toNumber(state.paid_total) ?? 0;
  const [amount, setAmount] = useState(balance.toFixed(2));
  const [note, setNote] = useState("");
  const send = useClaimAction(
    claimId,
    () =>
      nhcxCall(nhcxApi.enquiry, {
        pathParams: { facilityId, claimId },
        body: { action: "release", leg: "claim", amount, note },
      }),
    t("nhcx_release_sent"),
  );
  return (
    <form
      className="space-y-3 border-t pt-4"
      onSubmit={(e) => {
        e.preventDefault();
        const n = Number(amount);
        if (!amount || isNaN(n) || n <= 0) {
          toast.error(t("nhcx_release_say_how_much"));
          return;
        }
        send.mutate(undefined);
      }}
    >
      <h4 className="text-sm font-semibold">{t("nhcx_balance_release")}</h4>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="flex flex-col gap-1">
          <Label htmlFor="nhcx-release-amount">
            {t("nhcx_balance_to_release")}
            <span className="text-red-500"> *</span>
          </Label>
          <Input
            id="nhcx-release-amount"
            type="number"
            step="0.01"
            min="0.01"
            max={balance}
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
          />
          <Muted className="text-xs">
            {t("nhcx_paid_of", {
              paid: formatMoney(paid),
              claimed: formatMoney(claimed),
            })}
          </Muted>
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor="nhcx-release-note">{t("nhcx_note_to_payer")}</Label>
          <Textarea
            id="nhcx-release-note"
            rows={2}
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
          <Muted className="text-xs">{t("nhcx_release_help")}</Muted>
        </div>
      </div>
      <div className="flex justify-end">
        <Button type="submit" variant="primary" disabled={send.isPending}>
          <Wallet className="size-4" />
          {t("nhcx_ask_for_balance")}
        </Button>
      </div>
      <EnquiryRows
        enquiries={state.enquiries}
        stage="claim"
        kinds={["release"]}
      />
    </form>
  );
}

export function claimSendLabel(
  t: (key: string, opts?: Record<string, unknown>) => string,
  kind?: string | null,
  workflow?: string | null,
): string {
  if (kind === "claim_query_response")
    return t("nhcx_send_claim_query_response", { workflow: workflow || "151" });
  if (kind === "claim_resubmit") return t("nhcx_send_claim_resubmit");
  return t("nhcx_submit_claim");
}

// S11 Claim card.
function ClaimCard({ facilityId, claimId, state, goTo }: ClaimTabProps) {
  const { t } = useTranslation();
  const sub = state.submission;
  const status = sub?.status;
  const next = state.next_send.claim;
  const kind = isRefused(next) ? null : next;
  const label = claimSendLabel(t, kind, sub?.workflow_id);
  const pmjay = state.adapter === "pmjay";
  const lines = claimLines(state);

  const submit = useClaimAction(
    claimId,
    (reply?: string) =>
      nhcxCall(nhcxApi.submitClaim, {
        pathParams: { facilityId, claimId },
        body: reply ? { kind: kind ?? undefined, reply } : {},
      }),
    t("nhcx_claim_submitted"),
  );
  const enquire = useClaimAction(
    claimId,
    () =>
      nhcxCall(nhcxApi.enquiry, {
        pathParams: { facilityId, claimId },
        body: { action: "status", leg: "claim" },
      }),
    t("nhcx_status_enquiry_sent"),
  );

  const notSent = !sub || status === "draft";
  const decided =
    !!status && ["approved", "partial", "rejected", "queried"].includes(status);
  const showSend = !!kind && status !== "queried" && status !== "submitting";
  const showEnquire = !pmjay && !!sub && !notSent;
  const claimed =
    toNumber(sub?.requested_amount) ?? toNumber(sub?.submitted_amount) ?? 0;
  const paid = toNumber(state.paid_total) ?? 0;
  const balance = Math.round((claimed - paid) * 100) / 100;
  const chip = status ? LEG_STATUS[status] : null;
  const isQueryReply = kind === "claim_query_response";

  return (
    <Card>
      <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <CardTitle>{t("nhcx_claim")}</CardTitle>
          {chip && (
            <Chip tone={status === "draft" ? "warning" : chip.tone}>
              {t(chip.label)}
            </Chip>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          {showEnquire && (
            <Button
              size="sm"
              variant="outline"
              disabled={enquire.isPending}
              onClick={() => enquire.mutate(undefined)}
            >
              <HelpCircle className="size-4" />
              {t("nhcx_ask_where_it_stands")}
            </Button>
          )}
          {showSend && (
            <ConfirmButton
              confirm={notSent ? t("nhcx_submit_claim_confirm") : undefined}
              disabled={submit.isPending}
              onConfirm={() => submit.mutate(undefined)}
            >
              <Send className="size-4" />
              {label}
            </ConfirmButton>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {notSent && (
          <QuotedLinesTable lines={lines} empty={t("nhcx_nothing_to_claim")} />
        )}

        {sub && status === "submitting" && (
          <>
            {sub.workflow_id ? (
              <p className="text-sm">
                {t("nhcx_claim_acknowledged")}{" "}
                <Chip tone="info">{sub.workflow_id}</Chip>
              </p>
            ) : (
              <p className="text-sm">
                <Trans
                  i18nKey="nhcx_claim_submitting"
                  components={{ code: <code /> }}
                />
              </p>
            )}
            <DetailList
              items={[
                {
                  label: t("nhcx_sent_at"),
                  value: formatDateTime(sub.submitted_at),
                },
                { label: t("nhcx_claimed"), value: formatMoney(claimed) },
                { label: t("nhcx_transaction"), value: sub.txn_id },
                {
                  label: t("nhcx_correlation"),
                  value: <CorrelationId value={sub.correlation_id} />,
                },
              ]}
            />
            {state.queries.some(
              (q) => q.stage === "claim" && q.status === "open",
            ) && (
              <CommunicationPointer state={state} stage="claim" goTo={goTo} />
            )}
            <EnquiryRows
              enquiries={state.enquiries}
              stage="claim"
              kinds={["reprocess"]}
            />
          </>
        )}

        {sub && status === "error" && (
          <ErrorText>
            {sub.error_message || t("nhcx_exchange_failed")}
          </ErrorText>
        )}

        {sub && decided && (
          <>
            <StatGrid>
              <StatTile
                label={t("nhcx_claimed")}
                value={formatMoney(claimed)}
              />
              <StatTile
                label={t("nhcx_approved")}
                value={formatMoney(sub.approved_amount)}
                tone={status === "approved" ? "success" : "warning"}
              />
              <StatTile
                label={t("status")}
                value={chip ? t(chip.label) : status}
              />
            </StatGrid>
            <DetailList
              items={[
                { label: t("nhcx_disposition"), value: sub.disposition },
                {
                  label: t("nhcx_outcome"),
                  value: [sub.outcome, sub.adjudication]
                    .filter(Boolean)
                    .join(" · "),
                },
                { label: t("nhcx_claimed_under"), value: sub.claim_ref },
                {
                  label: t("nhcx_settled_at"),
                  value: formatDateTime(sub.settled_at),
                },
                {
                  label: t("nhcx_correlation"),
                  value: <CorrelationId value={sub.correlation_id} />,
                },
                {
                  label: t("nhcx_sent_as"),
                  value: sub.submission_kind
                    ? claimSendLabel(t, sub.submission_kind, sub.workflow_id)
                    : null,
                },
                { label: t("nhcx_our_reply"), value: sub.reply_text },
                {
                  label: t("nhcx_submitted_eligible"),
                  value:
                    sub.eligible_amount !== null &&
                    sub.eligible_amount !== undefined
                      ? `${formatMoney(sub.submitted_amount ?? claimed)} / ${formatMoney(sub.eligible_amount)}`
                      : null,
                },
              ]}
            />
            <ItemVerdictTable items={state.submission_items} />
            <QueryNote text={sub.query_note} />
            {status === "queried" ? (
              isQueryReply ? (
                <ResubmitReply
                  label={label}
                  pending={submit.isPending}
                  onSend={(reply) => submit.mutate(reply)}
                />
              ) : (
                <CommunicationPointer state={state} stage="claim" goTo={goTo} />
              )
            ) : (
              state.queries.some(
                (q) => q.stage === "claim" && q.status === "open",
              ) && (
                <CommunicationPointer state={state} stage="claim" goTo={goTo} />
              )
            )}
          </>
        )}

        {isRefused(next) && !notSent && (
          <Muted className="text-xs">{next.refused}</Muted>
        )}

        <EnquiryRows enquiries={state.enquiries} stage="claim" />
        {sub &&
          status &&
          ["rejected", "partial", "approved"].includes(status) &&
          paid < claimed && (
            <ReprocessForm
              facilityId={facilityId}
              claimId={claimId}
              state={state}
              goTo={goTo}
            />
          )}
        {sub &&
          status &&
          ["approved", "partial"].includes(status) &&
          paid > 0 &&
          balance > 0 && (
            <ReleaseForm
              facilityId={facilityId}
              claimId={claimId}
              state={state}
              claimed={claimed}
              balance={balance}
            />
          )}
      </CardContent>
    </Card>
  );
}

// S11 Claim tab.
export default function ClaimTab(props: ClaimTabProps) {
  const { t } = useTranslation();
  const { state } = props;
  const preauthStatus = state.preauth?.status;
  const open =
    !!state.submission ||
    preauthStatus === "approved" ||
    preauthStatus === "queried";
  if (!open) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{t("nhcx_claim")}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm">
            <Trans
              i18nKey="nhcx_claim_needs_preauth"
              components={{ b: <strong /> }}
            />
          </p>
        </CardContent>
      </Card>
    );
  }
  const sent = !!state.submission && state.submission.status !== "draft";
  const claimCard = <ClaimCard {...props} />;
  return (
    <div className="space-y-4">
      {sent && claimCard}
      <DischargeCard {...props} />
      <DocumentsCard {...props} stage="claim" />
      <FormsCard {...props} stage="claim" />
      {!sent && claimCard}
    </div>
  );
}
