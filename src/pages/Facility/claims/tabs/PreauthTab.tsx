import { HelpCircle, MessageSquare, Send, XCircle } from "lucide-react";
import { useState } from "react";
import { Trans, useTranslation } from "react-i18next";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
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

import { ClaimState, NextSend, Preauth } from "@/types/nhcx/nhcx";
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
import {
  DraftCard,
  LinkAdmissionCard,
  LinkedAdmissionCard,
  NotEligibleCard,
} from "@/pages/Facility/claims/components/PreauthDraft";
import { linesTotal } from "@/pages/Facility/claims/tabs/LineItemsTab";
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
  payerLabel,
} from "@/pages/Facility/claims/utils";

export const CANCEL_REASONS = [
  { value: "treatmentplanchanged", label: "nhcx_cancel_treatmentplanchanged" },
  { value: "patientrequest", label: "nhcx_cancel_patientrequest" },
  { value: "financialconstraints", label: "nhcx_cancel_financialconstraints" },
  { value: "alternativetreatment", label: "nhcx_cancel_alternativetreatment" },
  { value: "duplicateclaim", label: "nhcx_cancel_duplicateclaim" },
  { value: "administrativeerror", label: "nhcx_cancel_administrativeerror" },
  { value: "other", label: "nhcx_cancel_other" },
];

// The send button words for a next_send kind (S9 send kinds).
export function sendLabel(
  t: (key: string, opts?: Record<string, unknown>) => string,
  kind: string,
  amount?: string,
): string {
  switch (kind) {
    case "preauth_query_response":
      return t("nhcx_send_preauth_query_response");
    case "enhancement":
      return t("nhcx_send_enhancement", { amount });
    case "enhancement_resubmit":
      return t("nhcx_send_enhancement_resubmit");
    default:
      return t("nhcx_send_preauth");
  }
}

const reasonLabel = (
  t: (key: string) => string,
  value?: string | null,
): string | null => {
  const r = CANCEL_REASONS.find((x) => x.value === value);
  return r ? t(r.label) : value || null;
};

function PreauthCancelForm({
  facilityId,
  claimId,
}: {
  facilityId: string;
  claimId: string;
}) {
  const { t } = useTranslation();
  const [reason, setReason] = useState("");
  const [note, setNote] = useState("");
  const cancel = useClaimAction(
    claimId,
    () =>
      nhcxCall(nhcxApi.cancelPreauth, {
        pathParams: { facilityId, claimId },
        body: { reason, note },
      }),
    t("nhcx_cancel_sent"),
  );
  const check = () => {
    if (!reason) {
      toast.error(t("nhcx_cancel_choose_reason"));
      return false;
    }
    if (reason === "other" && !note.trim()) {
      toast.error(t("nhcx_cancel_describe_other"));
      return false;
    }
    return true;
  };
  return (
    <div className="flex flex-wrap items-end gap-3 border-t pt-4">
      <div className="flex flex-col gap-1">
        <Label>{t("nhcx_cancel_because")}</Label>
        <Select value={reason} onValueChange={setReason}>
          <SelectTrigger className="w-80">
            <SelectValue placeholder={t("nhcx_select_reason")} />
          </SelectTrigger>
          <SelectContent>
            {CANCEL_REASONS.map((r) => (
              <SelectItem key={r.value} value={r.value}>
                {t(r.label)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="flex flex-col gap-1">
        <Label htmlFor="nhcx-cancel-note">{t("nhcx_note")}</Label>
        <Input
          id="nhcx-cancel-note"
          className="w-72"
          value={note}
          onChange={(e) => setNote(e.target.value)}
        />
      </div>
      <ConfirmButton
        variant="destructive"
        confirm={t("nhcx_cancel_preauth_confirm")}
        disabled={cancel.isPending}
        onConfirm={() => check() && cancel.mutate(undefined)}
      >
        <XCircle className="size-4" />
        {t("nhcx_cancel_preauth")}
      </ConfirmButton>
    </div>
  );
}

// S9 Predetermination card.
function PredeterminationCard({
  facilityId,
  claimId,
  state,
}: Omit<ClaimTabProps, "goTo">) {
  const { t } = useTranslation();
  const latest = state.predeterminations[0] ?? null;
  const ask = useClaimAction(
    claimId,
    () =>
      nhcxCall(nhcxApi.predetermination, {
        pathParams: { facilityId, claimId },
        body: {},
      }),
    t("nhcx_predetermination_sent"),
  );
  const action =
    latest?.status === "asking" ? null : (
      <ConfirmButton
        variant={latest ? "outline" : "primary"}
        confirm={latest ? t("nhcx_predetermination_confirm") : undefined}
        disabled={ask.isPending}
        onConfirm={() => ask.mutate(undefined)}
      >
        <HelpCircle className="size-4" />
        {latest ? t("nhcx_ask_again") : t("nhcx_ask_for_quote")}
      </ConfirmButton>
    );
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-2">
        <CardTitle>{t("nhcx_predetermination")}</CardTitle>
        {action}
      </CardHeader>
      <CardContent className="space-y-4">
        {!latest && (
          <p className="text-sm">
            <Trans
              i18nKey="nhcx_predetermination_intro"
              components={{ code: <code /> }}
            />
          </p>
        )}
        {latest?.status === "asking" && (
          <>
            <p className="text-sm">{t("nhcx_predetermination_asking")}</p>
            <DetailList
              items={[
                {
                  label: t("nhcx_sent_at"),
                  value: formatDateTime(latest.requested_at),
                },
                {
                  label: t("nhcx_requested"),
                  value: formatMoney(latest.requested_amount),
                },
                { label: t("nhcx_transaction"), value: latest.txn_id },
                {
                  label: t("nhcx_correlation"),
                  value: <CorrelationId value={latest.correlation_id} />,
                },
              ]}
            />
          </>
        )}
        {latest?.status === "error" && (
          <ErrorText>
            {latest.error_message || t("nhcx_exchange_failed")}
          </ErrorText>
        )}
        {latest?.status === "answered" && (
          <>
            <div className="grid grid-cols-2 gap-3">
              <StatTile
                label={t("nhcx_requested")}
                value={formatMoney(latest.requested_amount)}
              />
              <StatTile
                label={t("nhcx_would_be_allowed")}
                value={formatMoney(latest.allowed_amount)}
                tone={latest.outcome === "complete" ? "success" : "warning"}
              />
            </div>
            <DetailList
              columns={2}
              items={[
                {
                  label: t("nhcx_outcome"),
                  value: [latest.outcome, latest.adjudication]
                    .filter(Boolean)
                    .join(" · "),
                },
                { label: t("nhcx_disposition"), value: latest.disposition },
                {
                  label: t("nhcx_quoted_at"),
                  value: formatDateTime(latest.answered_at),
                },
                {
                  label: t("nhcx_quotes_asked"),
                  value: state.predeterminations.length,
                },
              ]}
            />
            <Muted>{t("nhcx_quote_binds_nobody")}</Muted>
          </>
        )}
      </CardContent>
    </Card>
  );
}

// S10 Communication pointer on the S9 / S11 leg cards.
export function CommunicationPointer({
  state,
  stage,
  goTo,
}: {
  state: ClaimState;
  stage: "preauth" | "claim";
  goTo: ClaimTabProps["goTo"];
}) {
  const { t } = useTranslation();
  const open = state.queries.filter(
    (q) =>
      q.stage === stage &&
      q.kind === "query" &&
      (q.status === "open" || q.status === "error"),
  ).length;
  return (
    <div className="space-y-2 rounded-md border border-yellow-300 bg-yellow-50 p-3">
      <p className="text-sm">
        {open
          ? t("nhcx_communication_pointer_open", { count: open })
          : t("nhcx_communication_pointer", {
              payer: payerLabel(state.claim),
            })}
      </p>
      <Button size="sm" variant="primary" onClick={() => goTo("communication")}>
        <MessageSquare className="size-4" />
        {t("nhcx_open_communication_tab")}
      </Button>
    </div>
  );
}

function EnhancementBlock({ state }: { state: ClaimState }) {
  const { t } = useTranslation();
  const added = state.enhancement_lines;
  if (!added.length) return null;
  return (
    <div className="space-y-2">
      <Badge variant="yellow">
        {t("nhcx_enhancement_pending", {
          count: added.length,
          amount: formatMoney(linesTotal(added)),
        })}
      </Badge>
      <ul className="list-disc pl-6 text-sm">
        {added.map((l) => (
          <li key={l.id}>
            {l.display || l.code} × {l.quantity} ·{" "}
            {formatMoney(
              l.amount ?? Number(l.unit_price ?? 0) * Number(l.quantity ?? 0),
            )}
          </li>
        ))}
      </ul>
      <Muted>{t("nhcx_enhancement_added_since")}</Muted>
    </div>
  );
}

// S9 Pre-authorisation (submit) card.
function PreauthCard({ facilityId, claimId, state, goTo }: ClaimTabProps) {
  const { t } = useTranslation();
  const { claim } = state;
  const preauth: Preauth | null = state.preauth;
  const status = preauth?.status;
  const next: NextSend = state.next_send.preauth;
  const refused = isRefused(next);
  const kind = refused ? null : next;
  const enhancementAmount = formatMoney(linesTotal(state.enhancement_lines));
  const label = kind ? sendLabel(t, kind, enhancementAmount) : "";
  const pmjay = state.adapter === "pmjay";

  const submit = useClaimAction(
    claimId,
    (vars: { kind?: string; reply?: string }) =>
      nhcxCall(nhcxApi.submitPreauth, {
        pathParams: { facilityId, claimId },
        body: vars,
      }),
    t("nhcx_preauth_submitted"),
  );
  const enquire = useClaimAction(
    claimId,
    () =>
      nhcxCall(nhcxApi.enquiry, {
        pathParams: { facilityId, claimId },
        body: { action: "status", leg: "preauth" },
      }),
    t("nhcx_status_enquiry_sent"),
  );

  const notSaved = !claim.preauth_saved_at;
  const isQueryReply =
    kind === "preauth_query_response" || kind === "enhancement_resubmit";
  const showSend =
    !!kind &&
    !isQueryReply &&
    (!status ||
      status === "draft" ||
      ["cancelled", "error", "rejected", "approved", "partial"].includes(
        status,
      ));
  const sendConfirm =
    kind === "enhancement"
      ? t("nhcx_enhancement_confirm")
      : status === "cancelled"
        ? t("nhcx_send_preauth_confirm")
        : undefined;
  const showEnquire =
    !pmjay &&
    !!status &&
    ["submitting", "approved", "partial", "queried", "rejected"].includes(
      status,
    );
  const showCancel =
    !!status &&
    ["submitting", "approved", "partial", "queried"].includes(status);

  const statusChip = status ? LEG_STATUS[status] : null;

  const actions = (
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
        <div className="flex flex-col items-end gap-1">
          <ConfirmButton
            confirm={sendConfirm}
            disabled={submit.isPending || (notSaved && !preauth)}
            onConfirm={() => submit.mutate({ kind: kind ?? undefined })}
          >
            <Send className="size-4" />
            {label}
          </ConfirmButton>
          {notSaved && !preauth && (
            <Muted className="text-xs">{t("nhcx_save_draft_first")}</Muted>
          )}
        </div>
      )}
    </div>
  );

  const withdrawnUnder =
    preauth?.claim_ref && preauth.claim_ref !== claim.claim_no
      ? preauth.claim_ref
      : null;

  return (
    <Card>
      <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <CardTitle>{t("nhcx_preauthorisation")}</CardTitle>
          {statusChip && status !== "draft" && (
            <Chip tone={statusChip.tone}>{t(statusChip.label)}</Chip>
          )}
        </div>
        {actions}
      </CardHeader>
      <CardContent className="space-y-4">
        {(!preauth || status === "draft") && (
          <p className="text-sm">
            {t("nhcx_preauth_not_sent", {
              count: state.lines.length,
              amount: formatMoney(linesTotal(state.lines)),
            })}
          </p>
        )}

        {preauth && status === "submitting" && (
          <>
            {preauth.workflow_id ? (
              <p className="text-sm">
                {t("nhcx_preauth_acknowledged")}{" "}
                <Chip tone="info">{preauth.workflow_id}</Chip>
              </p>
            ) : (
              <p className="text-sm">
                <Trans
                  i18nKey="nhcx_preauth_submitting"
                  components={{ code: <code /> }}
                />
              </p>
            )}
            <DetailList
              items={[
                {
                  label: t("nhcx_sent_at"),
                  value: formatDateTime(preauth.submitted_at),
                },
                {
                  label: t("nhcx_requested"),
                  value: formatMoney(
                    preauth.requested_amount ?? preauth.submitted_amount,
                  ),
                },
                { label: t("nhcx_transaction"), value: preauth.txn_id },
                {
                  label: t("nhcx_correlation"),
                  value: <CorrelationId value={preauth.correlation_id} />,
                },
              ]}
            />
            {state.queries.some(
              (q) => q.stage === "preauth" && q.status === "open",
            ) && (
              <CommunicationPointer state={state} stage="preauth" goTo={goTo} />
            )}
          </>
        )}

        {preauth && status === "cancelling" && (
          <>
            <p className="text-sm">{t("nhcx_preauth_cancelling")}</p>
            <DetailList
              items={[
                {
                  label: t("nhcx_reason"),
                  value: reasonLabel(t, preauth.cancel_reason),
                },
                { label: t("nhcx_note"), value: preauth.cancel_note },
                {
                  label: t("nhcx_sent_at"),
                  value: formatDateTime(preauth.cancel_requested_at),
                },
                { label: t("nhcx_transaction"), value: preauth.cancel_txn_id },
                {
                  label: t("nhcx_correlation"),
                  value: (
                    <CorrelationId value={preauth.cancel_correlation_id} />
                  ),
                },
              ]}
            />
          </>
        )}

        {preauth && status === "cancelled" && (
          <>
            <p className="text-sm">{t("nhcx_preauth_cancelled_text")}</p>
            {withdrawnUnder && (
              <p className="text-sm">
                <Trans
                  i18nKey="nhcx_preauth_number_retired"
                  values={{ old: withdrawnUnder, new: claim.claim_no }}
                  components={{ b: <strong /> }}
                />
              </p>
            )}
            <DetailList
              items={[
                {
                  label: t("nhcx_reason"),
                  value: reasonLabel(t, preauth.cancel_reason),
                },
                { label: t("nhcx_note"), value: preauth.cancel_note },
                { label: t("nhcx_withdrawn_under"), value: withdrawnUnder },
                {
                  label: t("nhcx_preauth_reference"),
                  value: preauth.preauth_ref,
                },
                {
                  label: t("nhcx_cancelled_at"),
                  value: formatDateTime(preauth.settled_at),
                },
                { label: t("nhcx_disposition"), value: preauth.disposition },
              ]}
            />
          </>
        )}

        {preauth && status === "error" && (
          <ErrorText>
            {preauth.error_message || t("nhcx_exchange_failed")}
          </ErrorText>
        )}

        {preauth &&
          status &&
          ["approved", "partial", "rejected", "queried"].includes(status) && (
            <>
              <StatGrid>
                <StatTile
                  label={t("nhcx_requested")}
                  value={formatMoney(
                    preauth.requested_amount ?? preauth.submitted_amount,
                  )}
                />
                <StatTile
                  label={t("nhcx_approved")}
                  value={formatMoney(preauth.approved_amount)}
                  tone={status === "approved" ? "success" : "warning"}
                />
                <StatTile
                  label={t("nhcx_preauth_reference")}
                  value={preauth.preauth_ref || "-"}
                />
              </StatGrid>
              <DetailList
                items={[
                  {
                    label: t("status"),
                    value: statusChip ? t(statusChip.label) : status,
                  },
                  { label: t("nhcx_disposition"), value: preauth.disposition },
                  {
                    label: t("nhcx_outcome"),
                    value: [preauth.outcome, preauth.adjudication]
                      .filter(Boolean)
                      .join(" · "),
                  },
                  {
                    label: t("nhcx_settled_at"),
                    value: formatDateTime(preauth.settled_at),
                  },
                  {
                    label: t("nhcx_correlation"),
                    value: <CorrelationId value={preauth.correlation_id} />,
                  },
                  {
                    label: t("nhcx_enhancements"),
                    value: preauth.enhancement_no || null,
                  },
                  {
                    label: t("nhcx_sent_as"),
                    value: preauth.submission_kind
                      ? sendLabel(t, preauth.submission_kind, enhancementAmount)
                      : null,
                  },
                  { label: t("nhcx_our_reply"), value: preauth.reply_text },
                  {
                    label: t("nhcx_case_stands_at"),
                    value:
                      preauth.eligible_amount !== null &&
                      preauth.eligible_amount !== undefined
                        ? formatMoney(preauth.eligible_amount)
                        : null,
                  },
                ]}
              />
              <ItemVerdictTable items={state.preauth_items} />
              {["approved", "partial"].includes(status) && (
                <EnhancementBlock state={state} />
              )}
              <QueryNote text={preauth.query_note} />
              {status === "queried" &&
                (isQueryReply && kind ? (
                  <ResubmitReply
                    label={label}
                    pending={submit.isPending}
                    onSend={(reply) => submit.mutate({ kind, reply })}
                  />
                ) : (
                  <CommunicationPointer
                    state={state}
                    stage="preauth"
                    goTo={goTo}
                  />
                ))}
            </>
          )}

        {refused && preauth && status !== "draft" && (
          <Muted className="text-xs">{next.refused}</Muted>
        )}

        <EnquiryRows enquiries={state.enquiries} stage="preauth" />
        {showCancel && (
          <PreauthCancelForm facilityId={facilityId} claimId={claimId} />
        )}
      </CardContent>
    </Card>
  );
}

// S9 Pre-authorisation tab (hosts the S4 link and draft cards).
export default function PreauthTab(props: ClaimTabProps) {
  const { state } = props;
  const { claim } = state;
  if (!claim.encounter) {
    if (claim.status !== "eligible") return <NotEligibleCard />;
    return <LinkAdmissionCard {...props} />;
  }
  const sent = !!state.preauth && state.preauth.status !== "draft";
  const preauthCard = <PreauthCard {...props} />;
  return (
    <div className="space-y-4">
      {sent && preauthCard}
      <LinkedAdmissionCard {...props} />
      <DraftCard {...props} />
      <FormsCard {...props} stage="preauth" />
      <DocumentsCard {...props} stage="preauth" />
      <PredeterminationCard {...props} />
      {!sent && preauthCard}
    </div>
  );
}
