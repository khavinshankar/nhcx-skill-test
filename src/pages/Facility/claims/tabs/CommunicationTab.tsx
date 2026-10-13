import { Paperclip, Send } from "lucide-react";
import { useState } from "react";
import { Trans, useTranslation } from "react-i18next";
import { toast } from "sonner";

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/Common/Table";

import { ClaimQuery, ClaimState } from "@/types/nhcx/nhcx";
import nhcxApi from "@/types/nhcx/nhcxApi";

import {
  Chip,
  CorrelationId,
  DetailList,
  ErrorText,
  Muted,
} from "@/pages/Facility/claims/components/ClaimWidgets";
import {
  DocumentLink,
  uploadError,
  uploadOne,
} from "@/pages/Facility/claims/components/LegParts";
import { ClaimTabProps } from "@/pages/Facility/claims/tabs/types";
import {
  nhcxCall,
  useClaimAction,
} from "@/pages/Facility/claims/useClaimAction";
import {
  DOCUMENT_CODES,
  Tone,
  UPLOAD_TYPES,
  formatDateTime,
} from "@/pages/Facility/claims/utils";

const QUERY_STATUS: Record<
  ClaimQuery["status"],
  { label: string; tone: Tone }
> = {
  open: { label: "nhcx_query_awaiting_reply", tone: "warning" },
  answered: { label: "nhcx_answered", tone: "success" },
  acknowledged: { label: "nhcx_acknowledged", tone: "success" },
  noted: { label: "nhcx_noted", tone: "info" },
  error: { label: "nhcx_reply_failed", tone: "danger" },
};

const REASONS: Record<string, string> = {
  tatquery: "nhcx_reason_tatquery",
  grievance: "nhcx_reason_grievance",
  walletupdate: "nhcx_reason_walletupdate",
  policychange: "nhcx_reason_policychange",
  additionalinfo: "nhcx_reason_additionalinfo",
  claimarbitration: "nhcx_reason_claimarbitration",
  claimarbitartion: "nhcx_reason_claimarbitration",
  questionnaire: "nhcx_reason_questionnaire",
  query: "nhcx_reason_query",
};

// The payer's reason code in words (S10); unknown codes as spelled.
export function reasonWords(
  t: (key: string) => string,
  code?: string | null,
): string {
  if (!code) return "-";
  const key = REASONS[code.toLowerCase()];
  return key ? t(key) : code;
}

const asList = (v: string[] | string | null | undefined): string[] =>
  Array.isArray(v) ? v : v ? [v] : [];

function payerLines(q: ClaimQuery): string[] {
  if (q.questions?.length) return q.questions;
  return q.remarks ? q.remarks.split("\n").filter(Boolean) : [];
}

function BaseDetails({ q, reason }: { q: ClaimQuery; reason?: boolean }) {
  const { t } = useTranslation();
  const status = QUERY_STATUS[q.status];
  const chip =
    q.kind === "notification" ? (
      q.acknowledged_at || q.status === "acknowledged" ? (
        <Chip tone="success">{t("nhcx_acknowledged")}</Chip>
      ) : q.status === "error" ? (
        <Chip tone="danger">{t("nhcx_ack_failed")}</Chip>
      ) : (
        <Chip tone="warning">{t("nhcx_awaiting_ack")}</Chip>
      )
    ) : (
      <Chip tone={status.tone}>{t(status.label)}</Chip>
    );
  const items = [
    { label: t("nhcx_received"), value: formatDateTime(q.received_at) },
    { label: t("nhcx_from"), value: q.sender_code },
    { label: t("nhcx_about"), value: q.claim_ref },
    ...(reason
      ? [{ label: t("nhcx_reason"), value: reasonWords(t, q.reason_code) }]
      : []),
    { label: t("status"), value: chip },
  ];
  return (
    <dl
      className={`grid grid-cols-1 gap-x-6 gap-y-3 sm:grid-cols-2 ${reason ? "lg:grid-cols-5" : "lg:grid-cols-4"}`}
    >
      {items.map((item) => (
        <div key={item.label} className="min-w-0">
          <dt className="text-xs font-medium text-gray-500">{item.label}</dt>
          <dd className="text-sm break-words text-gray-900">
            {item.value || "-"}
          </dd>
        </div>
      ))}
    </dl>
  );
}

function ReplyForm({
  facilityId,
  claimId,
  state,
  q,
}: {
  facilityId: string;
  claimId: string;
  state: ClaimState;
  q: ClaimQuery;
}) {
  const { t } = useTranslation();
  const [text, setText] = useState(q.reply_text ?? "");
  const [chosen, setChosen] = useState<string[]>([]);
  const [picked, setPicked] = useState<Record<string, File | null>>({});
  const [files, setFiles] = useState<File[]>([]);
  const [code, setCode] = useState("CD");
  const [label, setLabel] = useState("");
  const required = state.required_documents?.[q.stage] ?? [];

  const reply = useClaimAction(
    claimId,
    async () => {
      const named = Object.entries(picked).filter(([, f]) => f) as [
        string,
        File,
      ][];
      const uploaded: string[] = [];
      for (const [c, file] of named) {
        const res = await uploadOne(facilityId, claimId, file, {
          code: c,
          stage: q.stage,
          label: required.find((r) => r.code === c)?.display,
        });
        if (res.document_id) uploaded.push(res.document_id);
      }
      for (const file of files) {
        const res = await uploadOne(facilityId, claimId, file, {
          code,
          stage: q.stage,
          label: label || undefined,
        });
        if (res.document_id) uploaded.push(res.document_id);
      }
      const res = await nhcxCall(nhcxApi.replyQuery, {
        pathParams: { facilityId, claimId, queryId: q.id },
        body: { text, document_ids: [...chosen, ...uploaded] },
      });
      if (
        res.ok !== false &&
        !res.message &&
        (chosen.length || uploaded.length)
      ) {
        return {
          ...res,
          message: `${t("nhcx_reply_sent")}${t("nhcx_reply_sent_with", {
            old: chosen.length,
            new: uploaded.length,
          })}`,
        };
      }
      return res;
    },
    t("nhcx_reply_sent"),
  );

  const submit = (e: React.SyntheticEvent) => {
    e.preventDefault();
    const newFiles = [
      ...(Object.values(picked).filter(Boolean) as File[]),
      ...files,
    ];
    for (const file of newFiles) {
      const error = uploadError(file, t);
      if (error) {
        toast.error(error);
        return;
      }
    }
    if (!text.trim() && !chosen.length && !newFiles.length) {
      toast.error(t("nhcx_reply_empty"));
      return;
    }
    reply.mutate(undefined);
  };

  const codeOptions = [
    ...required.map((r) => ({ code: r.code, label: r.display })),
    ...DOCUMENT_CODES.map((c) => ({ code: c.code, label: t(c.label) })),
  ].filter((o, i, all) => all.findIndex((x) => x.code === o.code) === i);

  return (
    <form className="space-y-4" onSubmit={submit}>
      <div className="flex flex-col gap-1">
        <Label htmlFor={`nhcx-reply-${q.id}`}>{t("nhcx_reply")}</Label>
        <Textarea
          id={`nhcx-reply-${q.id}`}
          rows={4}
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
      </div>

      {state.documents.length > 0 && (
        <div className="space-y-2">
          <Label>{t("nhcx_send_claim_documents")}</Label>
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
              <span className="text-xs text-gray-500">
                {d.code || "-"} · {d.stage}
              </span>
            </label>
          ))}
          <Muted className="text-xs">
            {t("nhcx_send_claim_documents_help")}
          </Muted>
        </div>
      )}

      {required.length > 0 && (
        <div className="space-y-2">
          <Label>{t("nhcx_documents_payer_named")}</Label>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("nhcx_code")}</TableHead>
                  <TableHead>{t("nhcx_document")}</TableHead>
                  <TableHead>{t("nhcx_choose_a_pdf")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {required.map((r) => (
                  <TableRow key={`${r.code}-${r.package_code}`}>
                    <TableCell>{r.code}</TableCell>
                    <TableCell>
                      <div>{r.display}</div>
                      {r.package_code && (
                        <div className="text-xs text-gray-500">
                          {r.package_code}
                        </div>
                      )}
                    </TableCell>
                    <TableCell>
                      <Input
                        type="file"
                        accept={UPLOAD_TYPES.join(",")}
                        onChange={(e) =>
                          setPicked((cur) => ({
                            ...cur,
                            [r.code]: e.target.files?.[0] ?? null,
                          }))
                        }
                      />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <Muted className="text-xs">{t("nhcx_reply_named_help")}</Muted>
        </div>
      )}

      <div className="space-y-2">
        <Label>{t("nhcx_attach_anything_else")}</Label>
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex flex-col gap-1">
            <Label className="text-xs">{t("nhcx_add_files")}</Label>
            <Input
              type="file"
              multiple
              accept={UPLOAD_TYPES.join(",")}
              onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
            />
          </div>
          <div className="flex flex-col gap-1">
            <Label className="text-xs">{t("nhcx_filed_as")}</Label>
            <Select value={code} onValueChange={setCode}>
              <SelectTrigger className="w-72">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {codeOptions.map((o) => (
                  <SelectItem key={o.code} value={o.code}>
                    {o.code} - {o.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-1">
            <Label className="text-xs">{t("nhcx_label")}</Label>
            <Input value={label} onChange={(e) => setLabel(e.target.value)} />
          </div>
        </div>
        <Muted className="text-xs">{t("nhcx_attach_anything_help")}</Muted>
      </div>

      <div className="flex justify-end">
        <Button type="submit" variant="primary" disabled={reply.isPending}>
          <Send className="size-4" />
          {t("nhcx_send_reply")}
        </Button>
      </div>
    </form>
  );
}

function PayerSays({ q }: { q: ClaimQuery }) {
  const { t } = useTranslation();
  const lines = payerLines(q);
  return (
    <div className="space-y-1">
      <h4 className="text-sm font-semibold">{t("nhcx_what_payer_says")}</h4>
      {lines.length ? (
        <ul className="list-disc pl-6 text-sm">
          {lines.map((l, i) => (
            <li key={i}>{l}</li>
          ))}
        </ul>
      ) : (
        <Muted>{t("nhcx_payer_sent_no_text")}</Muted>
      )}
    </div>
  );
}

function QueryItem({
  facilityId,
  claimId,
  state,
  q,
}: {
  facilityId: string;
  claimId: string;
  state: ClaimState;
  q: ClaimQuery;
}) {
  const { t } = useTranslation();
  const date = formatDateTime(q.received_at);
  const ack = useClaimAction(
    claimId,
    () =>
      nhcxCall(nhcxApi.ackQuery, {
        pathParams: { facilityId, claimId, queryId: q.id },
        body: {},
      }),
    t("nhcx_ack_sent"),
  );
  const docs = asList(q.reply_documents)
    .map((id) => state.documents.find((d) => d.id === id))
    .filter((d) => !!d);

  let title: string;
  let body: React.ReactNode;
  if (q.kind === "query" && (q.status === "open" || q.status === "error")) {
    title = t("nhcx_query_raised_title", { date });
    const lines = payerLines(q);
    body = (
      <>
        <BaseDetails q={q} />
        <div className="space-y-1">
          <h4 className="text-sm font-semibold">
            {t("nhcx_what_payer_asked")}
          </h4>
          {lines.length ? (
            <ul className="list-disc pl-6 text-sm">
              {lines.map((l, i) => (
                <li key={i}>{l}</li>
              ))}
            </ul>
          ) : (
            <Muted>{t("nhcx_payer_asked_nothing")}</Muted>
          )}
        </div>
        {q.status === "error" && (
          <ErrorText>
            {q.error_message} {t("nhcx_reply_nothing_reached")}
          </ErrorText>
        )}
        <ReplyForm
          facilityId={facilityId}
          claimId={claimId}
          state={state}
          q={q}
        />
      </>
    );
  } else if (q.kind === "query") {
    title = t("nhcx_query_answered_title", {
      date: formatDateTime(q.answered_at || q.received_at),
    });
    const lines = payerLines(q);
    body = (
      <>
        <BaseDetails q={q} />
        <div className="space-y-1">
          <h4 className="text-sm font-semibold">
            {t("nhcx_what_payer_asked")}
          </h4>
          {lines.length ? (
            <ul className="list-disc pl-6 text-sm">
              {lines.map((l, i) => (
                <li key={i}>{l}</li>
              ))}
            </ul>
          ) : (
            <Muted>{t("nhcx_payer_asked_nothing")}</Muted>
          )}
        </div>
        <div className="space-y-1">
          <h4 className="text-sm font-semibold">{t("nhcx_our_reply")}</h4>
          <pre className="rounded-md bg-gray-100 p-3 text-xs whitespace-pre-wrap">
            {q.reply_text || "-"}
          </pre>
        </div>
        {docs.length > 0 && (
          <div className="space-y-1">
            <h4 className="text-sm font-semibold">{t("nhcx_attached")}</h4>
            <ul className="space-y-1 text-sm">
              {docs.map((d) => (
                <li key={d!.id} className="flex items-center gap-1">
                  <Paperclip className="size-3" />
                  <DocumentLink doc={d!} />
                </li>
              ))}
            </ul>
          </div>
        )}
        <DetailList
          items={[
            { label: t("nhcx_sent_at"), value: formatDateTime(q.answered_at) },
            { label: t("nhcx_transaction"), value: q.reply_txn_id },
            {
              label: t("nhcx_thread"),
              value: <CorrelationId value={q.reply_correlation_id} />,
            },
          ]}
        />
      </>
    );
  } else if (q.kind === "notification") {
    const acked = !!q.acknowledged_at || q.status === "acknowledged";
    title = acked
      ? t("nhcx_notification_acked_title", {
          reason: reasonWords(t, q.reason_code),
          date,
        })
      : t("nhcx_notification_pending_title", {
          reason: reasonWords(t, q.reason_code),
          date,
        });
    body = (
      <>
        <BaseDetails q={q} reason />
        <PayerSays q={q} />
        <Muted>{t("nhcx_notification_note")}</Muted>
        {acked ? (
          <DetailList
            items={[
              {
                label: t("nhcx_acknowledged_at"),
                value: formatDateTime(q.acknowledged_at),
              },
              { label: t("nhcx_transaction"), value: q.reply_txn_id },
              {
                label: t("nhcx_thread"),
                value: <CorrelationId value={q.reply_correlation_id} />,
              },
            ]}
          />
        ) : (
          <div className="space-y-2">
            <ErrorText>
              {q.error_message ? `${q.error_message} ` : ""}
              {t("nhcx_ack_not_heard")}
            </ErrorText>
            <Button
              size="sm"
              variant="primary"
              disabled={ack.isPending}
              onClick={() => ack.mutate(undefined)}
            >
              <Send className="size-4" />
              {t("nhcx_send_ack")}
            </Button>
          </div>
        )}
      </>
    );
  } else {
    title = t("nhcx_note_from_payer_title", { date });
    body = (
      <>
        <BaseDetails q={q} />
        <PayerSays q={q} />
        <Muted>{t("nhcx_note_kept")}</Muted>
      </>
    );
  }

  return (
    <AccordionItem value={q.id}>
      <AccordionTrigger>{title}</AccordionTrigger>
      <AccordionContent className="space-y-4">{body}</AccordionContent>
    </AccordionItem>
  );
}

// S10 Communication tab.
export default function CommunicationTab({
  facilityId,
  claimId,
  state,
}: ClaimTabProps) {
  const { t } = useTranslation();
  const newest = (a: ClaimQuery, b: ClaimQuery) =>
    (b.received_at || "").localeCompare(a.received_at || "");
  const legs = (["preauth", "claim"] as const)
    .map((stage) => ({
      stage,
      rows: state.queries.filter((q) => q.stage === stage).sort(newest),
    }))
    .filter((l) => l.rows.length);

  if (!legs.length) {
    const resubmit = state.adapter === "pmjay";
    return (
      <Card>
        <CardHeader>
          <CardTitle>{t("nhcx_communication")}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm">
            <Trans
              i18nKey={
                resubmit
                  ? "nhcx_communication_empty_resubmit"
                  : "nhcx_communication_empty_communication"
              }
              values={{ adapter: state.adapter || "-" }}
              components={{ code: <code /> }}
            />
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {legs.map(({ stage, rows }) => (
        <Card key={stage}>
          <CardHeader>
            <CardTitle>
              {t("nhcx_payer_queries")}{" "}
              <span className="text-sm font-normal text-gray-500">
                {stage === "preauth"
                  ? t("nhcx_preauthorisation")
                  : t("nhcx_claim")}
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Accordion
              type="multiple"
              defaultValue={rows
                .filter((q) => q.status === "open" || q.status === "error")
                .map((q) => q.id)}
            >
              {rows.map((q) => (
                <QueryItem
                  key={q.id}
                  facilityId={facilityId}
                  claimId={claimId}
                  state={state}
                  q={q}
                />
              ))}
            </Accordion>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
