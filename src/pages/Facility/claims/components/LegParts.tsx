import { Paperclip, Save, Send } from "lucide-react";
import { useEffect, useRef, useState } from "react";
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

import {
  ClaimDocument,
  ClaimForm,
  ClaimState,
  Enquiry,
  FormAnswer,
  FormQuestion,
  ItemVerdict,
} from "@/types/nhcx/nhcx";
import nhcxApi from "@/types/nhcx/nhcxApi";

import {
  Chip,
  ConfirmButton,
  Muted,
} from "@/pages/Facility/claims/components/ClaimWidgets";
import {
  nhcxCall,
  refusalText,
  useClaimAction,
} from "@/pages/Facility/claims/useClaimAction";
import {
  DOCUMENT_CODES,
  Tone,
  UPLOAD_MAX_BYTES,
  UPLOAD_TYPES,
  answerTypeKey,
  claimForms,
  formatDateTime,
  formatMoney,
} from "@/pages/Facility/claims/utils";

type Stage = "preauth" | "claim";
const BLANK = "__blank";

interface LegProps {
  facilityId: string;
  claimId: string;
  state: ClaimState;
  stage: Stage;
}

const TYPE_LABEL: Record<string, string> = {
  "application/pdf": "PDF",
  "image/jpeg": "JPEG image",
  "image/png": "PNG image",
  "image/webp": "WebP image",
};

export function fileSize(bytes: number): string {
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  return `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

// The upload rules of S9: PDF or image, at most 10 MB, not empty.
export function uploadError(
  file: File,
  t: (k: string) => string,
): string | null {
  if (!UPLOAD_TYPES.includes(file.type)) return t("nhcx_upload_types");
  if (!file.size) return t("nhcx_upload_empty");
  if (file.size > UPLOAD_MAX_BYTES) return t("nhcx_upload_too_big");
  return null;
}

export async function uploadOne(
  facilityId: string,
  claimId: string,
  file: File,
  fields: { code: string; stage: Stage; label?: string; category?: string },
) {
  const form = new FormData();
  form.append("file", file);
  form.append("code", fields.code);
  form.append("stage", fields.stage);
  if (fields.label) form.append("label", fields.label);
  if (fields.category) form.append("category", fields.category);
  const res = await nhcxCall(nhcxApi.uploadDocument, {
    pathParams: { facilityId, claimId },
    body: form,
  });
  if (res.ok === false) throw new Error(res.error || "");
  return res;
}

// Uploads a batch, reporting how many went up before a failure.
async function uploadMany(
  facilityId: string,
  claimId: string,
  jobs: {
    file: File;
    code: string;
    stage: Stage;
    label?: string;
    category?: string;
  }[],
  t: (k: string, o?: Record<string, unknown>) => string,
) {
  let done = 0;
  for (const job of jobs) {
    try {
      await uploadOne(facilityId, claimId, job.file, job);
      done += 1;
    } catch (error) {
      const text = refusalText(error, t("something_went_wrong"));
      throw new Error(
        done
          ? `${text}${t("nhcx_upload_partial", { done, total: jobs.length })}`
          : text,
      );
    }
  }
  return { ok: true, message: t("nhcx_documents_attached", { n: done }) };
}

export function DocumentLink({ doc }: { doc: ClaimDocument }) {
  if (!doc.url) return <span>{doc.filename}</span>;
  return (
    <a
      href={doc.url}
      target="_blank"
      rel="noreferrer"
      className="text-primary-700 underline"
    >
      {doc.filename}
    </a>
  );
}

// S9 / S11 Supporting documents card.
export function DocumentsCard({ facilityId, claimId, state, stage }: LegProps) {
  const { t } = useTranslation();
  const named = state.required_documents?.[stage] ?? [];
  // S11: the discharge summary is always the first claim requirement.
  const required =
    stage === "claim" && !named.some((r) => r.code === "HDS")
      ? [
          {
            code: "HDS",
            display: t("nhcx_doc_hds"),
            category: "HDS",
            package_code: null,
            attached_document_id: null,
          },
          ...named,
        ]
      : named;
  const documents = state.documents.filter(
    (d) => !d.stage || d.stage === stage,
  );
  const [picked, setPicked] = useState<Record<string, File | null>>({});
  const [files, setFiles] = useState<File[]>([]);
  const [code, setCode] = useState("CD");
  const [label, setLabel] = useState("");
  const [inputKey, setInputKey] = useState(0);

  const reset = () => {
    setPicked({});
    setFiles([]);
    setLabel("");
    setInputKey((k) => k + 1);
  };

  const attachRequired = useClaimAction(
    claimId,
    (
      jobs: {
        file: File;
        code: string;
        stage: Stage;
        label?: string;
        category?: string;
      }[],
    ) => uploadMany(facilityId, claimId, jobs, t),
    undefined,
    reset,
  );
  const attach = useClaimAction(
    claimId,
    (jobs: { file: File; code: string; stage: Stage; label?: string }[]) =>
      uploadMany(facilityId, claimId, jobs, t),
    undefined,
    reset,
  );
  const remove = useClaimAction(
    claimId,
    (documentId: string) =>
      nhcxCall(nhcxApi.removeDocument, {
        pathParams: { facilityId, claimId, documentId },
      }),
    t("nhcx_document_removed"),
  );

  const codeOptions = [
    ...required
      .filter((r) => !DOCUMENT_CODES.some((c) => c.code === r.code))
      .map((r) => ({ code: r.code, label: r.display })),
    ...DOCUMENT_CODES.map((c) => ({ code: c.code, label: t(c.label) })),
  ].filter((o, i, all) => all.findIndex((x) => x.code === o.code) === i);

  const submitRequired = () => {
    const jobs = Object.entries(picked)
      .filter(([, f]) => f)
      .map(([c, f]) => ({
        file: f as File,
        code: c,
        stage,
        label: required.find((r) => r.code === c)?.display,
        category: c === "HDS" ? "HDS" : undefined,
      }));
    if (!jobs.length) {
      toast.error(t("nhcx_choose_pdf_for_one"));
      return;
    }
    for (const job of jobs) {
      const error = uploadError(job.file, t);
      if (error) {
        toast.error(error);
        return;
      }
    }
    attachRequired.mutate(jobs);
  };

  const submitAny = () => {
    if (!files.length) {
      toast.error(t("nhcx_choose_file"));
      return;
    }
    for (const file of files) {
      const error = uploadError(file, t);
      if (error) {
        toast.error(error);
        return;
      }
    }
    attach.mutate(
      files.map((file) => ({ file, code, stage, label: label || undefined })),
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          {stage === "claim"
            ? t("nhcx_documents_for_claim")
            : t("nhcx_supporting_documents")}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {required.length > 0 && (
          <div className="space-y-3">
            <h4 className="text-sm font-semibold">
              {t("nhcx_documents_payer_named")}
            </h4>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t("nhcx_code")}</TableHead>
                    <TableHead>{t("nhcx_document")}</TableHead>
                    <TableHead>{t("nhcx_attached")}</TableHead>
                    <TableHead>{t("nhcx_choose_a_pdf")}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {required.map((r) => {
                    const doc = state.documents.find(
                      (d) =>
                        d.id === r.attached_document_id ||
                        (!r.attached_document_id &&
                          d.code === r.code &&
                          d.stage === stage),
                    );
                    return (
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
                          {doc ? (
                            <DocumentLink doc={doc} />
                          ) : (
                            <Muted>{t("nhcx_not_attached_yet")}</Muted>
                          )}
                        </TableCell>
                        <TableCell>
                          <Input
                            key={`${inputKey}-${r.code}`}
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
                    );
                  })}
                </TableBody>
              </Table>
            </div>
            <Muted>
              {stage === "preauth"
                ? t("nhcx_documents_payer_named_note")
                : named.length || documents.some((d) => d.code === "HDS")
                  ? t("nhcx_claim_documents_note")
                  : t("nhcx_claim_documents_only_hds")}
            </Muted>
            <Button
              size="sm"
              variant="primary"
              disabled={attachRequired.isPending}
              onClick={submitRequired}
            >
              <Paperclip className="size-4" />
              {t("nhcx_attach_chosen_files")}
            </Button>
          </div>
        )}

        <div className="space-y-3">
          {!documents.length ? (
            <Muted>
              {stage === "claim"
                ? t("nhcx_nothing_beyond_requirements")
                : t("nhcx_no_documents_yet")}
            </Muted>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t("nhcx_file")}</TableHead>
                    <TableHead>{t("nhcx_filed_as")}</TableHead>
                    <TableHead>{t("nhcx_type")}</TableHead>
                    <TableHead>{t("nhcx_size")}</TableHead>
                    <TableHead>{t("nhcx_uploaded")}</TableHead>
                    <TableHead />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {documents.map((d) => (
                    <TableRow key={d.id}>
                      <TableCell>
                        <DocumentLink doc={d} />
                      </TableCell>
                      <TableCell>
                        <div>{d.label || d.code}</div>
                        <div className="text-xs text-gray-500">{d.code}</div>
                      </TableCell>
                      <TableCell>
                        {TYPE_LABEL[d.content_type] ?? d.content_type}
                      </TableCell>
                      <TableCell>{fileSize(d.size)}</TableCell>
                      <TableCell>{formatDateTime(d.uploaded_at)}</TableCell>
                      <TableCell className="text-right">
                        <ConfirmButton
                          size="xs"
                          variant="destructive"
                          confirm={t("nhcx_remove_document_confirm")}
                          onConfirm={() => remove.mutate(d.id)}
                        >
                          {t("remove")}
                        </ConfirmButton>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </div>

        <div className="flex flex-wrap items-end gap-3">
          <div className="flex flex-col gap-1">
            <Label>{t("nhcx_files_pdf_or_image")}</Label>
            <Input
              key={inputKey}
              type="file"
              multiple
              accept={UPLOAD_TYPES.join(",")}
              onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
            />
          </div>
          <div className="flex flex-col gap-1">
            <Label>{t("nhcx_filed_as")}</Label>
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
            <Label>{t("nhcx_label")}</Label>
            <Input value={label} onChange={(e) => setLabel(e.target.value)} />
          </div>
          <Button
            variant="primary"
            disabled={attach.isPending}
            onClick={submitAny}
          >
            <Paperclip className="size-4" />
            {t("nhcx_attach")}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function savedAnswers(
  state: ClaimState,
  form: ClaimForm,
  stage: Stage,
): Record<string, string> {
  const out: Record<string, string> = {};
  form.questions.forEach((q) => {
    if (q.answer) out[q.linkId] = q.answer;
  });
  Object.assign(out, form.answers ?? {});
  (state.form_answers ?? [])
    .filter((a) => a.form_url === form.url && a.stage === stage)
    .forEach((a) => {
      if (a.answer !== null) out[a.link_id] = a.answer;
    });
  return out;
}

function QuestionField({
  question,
  value,
  onChange,
  onFile,
  attached,
}: {
  question: FormQuestion;
  value: string;
  onChange: (v: string) => void;
  onFile: (f: File | null) => void;
  attached?: ClaimDocument;
}) {
  const { t } = useTranslation();
  const type = (question.type || "").toLowerCase();
  const id = `nhcx-q-${question.linkId}`;
  const typeKey = answerTypeKey(question.type);
  let control;
  if (type === "attachment") {
    control = (
      <div className="flex flex-col gap-1">
        <Input
          id={id}
          type="file"
          accept={UPLOAD_TYPES.join(",")}
          onChange={(e) => onFile(e.target.files?.[0] ?? null)}
        />
        {attached && (
          <span className="text-xs">
            <DocumentLink doc={attached} /> {t("nhcx_attached_word")}
          </span>
        )}
      </div>
    );
  } else if (type === "choice" || question.options?.length) {
    control = (
      <Select
        value={value || BLANK}
        onValueChange={(v) => onChange(v === BLANK ? "" : v)}
      >
        <SelectTrigger id={id}>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={BLANK}>-</SelectItem>
          {(question.options ?? []).map((o) => (
            <SelectItem key={o} value={o}>
              {o}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    );
  } else if (type === "boolean") {
    control = (
      <Select
        value={value || BLANK}
        onValueChange={(v) => onChange(v === BLANK ? "" : v)}
      >
        <SelectTrigger id={id}>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={BLANK}>-</SelectItem>
          <SelectItem value="true">{t("yes")}</SelectItem>
          <SelectItem value="false">{t("no")}</SelectItem>
        </SelectContent>
      </Select>
    );
  } else if (type === "text") {
    control = (
      <Textarea
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  } else {
    const inputType =
      {
        date: "date",
        datetime: "datetime-local",
        time: "time",
        integer: "number",
        decimal: "number",
        quantity: "number",
        url: "url",
      }[type] ?? "text";
    control = (
      <Input
        id={id}
        type={inputType}
        step={type === "integer" ? 1 : type === "text" ? undefined : "any"}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  }
  return (
    <div className="flex flex-col gap-1">
      <Label htmlFor={id}>
        {question.text || question.linkId}
        {question.required && <span className="text-red-500"> *</span>}
      </Label>
      {control}
      <Muted className="text-xs">{typeKey ? t(typeKey) : question.type}</Muted>
    </div>
  );
}

function FormItem({
  facilityId,
  claimId,
  state,
  stage,
  form,
}: LegProps & { form: ClaimForm }) {
  const { t } = useTranslation();
  const saved = savedAnswers(state, form, stage);
  const [answers, setAnswers] = useState<Record<string, string>>(saved);
  const files = useRef<Record<string, File | null>>({});
  const savedKey = JSON.stringify(saved);
  useEffect(() => {
    setAnswers(JSON.parse(savedKey));
  }, [savedKey]);

  const answered = form.questions.filter((q) => !!saved[q.linkId]).length;

  const save = useClaimAction(claimId, async () => {
    const out: Record<string, string> = { ...answers };
    let attached = 0;
    for (const q of form.questions) {
      const file = files.current[q.linkId];
      if ((q.type || "").toLowerCase() !== "attachment" || !file) continue;
      const error = uploadError(file, t);
      if (error) throw new Error(error);
      const res = await uploadOne(facilityId, claimId, file, {
        code: "ODN",
        stage,
        label: q.text || q.linkId,
      });
      if (res.document_id) out[q.linkId] = res.document_id;
      attached += 1;
    }
    const formAnswers: FormAnswer[] = form.questions
      .filter(
        (q) =>
          (q.type || "").toLowerCase() !== "attachment" ||
          out[q.linkId] !== saved[q.linkId],
      )
      .map((q) => ({
        form_url: form.url,
        link_id: q.linkId,
        answer: out[q.linkId] || null,
        stage,
      }));
    const res = await nhcxCall(nhcxApi.updateDraft, {
      pathParams: { facilityId, claimId },
      body: { form_answers: formAnswers },
    });
    files.current = {};
    if (res.ok === false) return res;
    return {
      ok: true,
      message:
        t("nhcx_answers_saved") +
        (attached ? t("nhcx_files_attached_suffix", { n: attached }) : ""),
    };
  });

  return (
    <AccordionItem value={form.url}>
      <AccordionTrigger>
        {t("nhcx_form_answered", {
          title: form.title || form.url,
          answered,
          total: form.questions.length,
        })}
      </AccordionTrigger>
      <AccordionContent className="space-y-4">
        {!form.questions.length ? (
          <Muted>{t("nhcx_form_no_questions")}</Muted>
        ) : (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {form.questions.map((q) => (
              <QuestionField
                key={q.linkId}
                question={q}
                value={answers[q.linkId] ?? ""}
                onChange={(v) =>
                  setAnswers((cur) => ({ ...cur, [q.linkId]: v }))
                }
                onFile={(f) => {
                  files.current[q.linkId] = f;
                }}
                attached={state.documents.find((d) => d.id === saved[q.linkId])}
              />
            ))}
          </div>
        )}
        <div className="flex justify-end">
          <Button
            size="sm"
            variant="primary"
            disabled={save.isPending}
            onClick={() => save.mutate(undefined)}
          >
            <Save className="size-4" />
            {t("nhcx_save_answers")}
          </Button>
        </div>
      </AccordionContent>
    </AccordionItem>
  );
}

// S9 / S11 Forms the payer requires. Left out when no form applies.
export function FormsCard(props: LegProps) {
  const { t } = useTranslation();
  const forms = claimForms(props.state, props.stage);
  if (!forms.length) return null;
  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("nhcx_forms_payer_requires")}</CardTitle>
      </CardHeader>
      <CardContent>
        <Accordion type="multiple">
          {forms.map((form) => (
            <FormItem key={form.url} {...props} form={form} />
          ))}
        </Accordion>
      </CardContent>
    </Card>
  );
}

const VERDICT_TONE: Record<string, Tone> = {
  approved: "success",
  complete: "success",
  queried: "warning",
  partial: "warning",
  rejected: "danger",
  denied: "danger",
  pending: "info",
};

// Per-item verdict table (S9, S11).
export function ItemVerdictTable({ items }: { items: ItemVerdict[] }) {
  const { t } = useTranslation();
  if (!items.length) return null;
  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>{t("nhcx_item")}</TableHead>
            <TableHead>{t("status")}</TableHead>
            <TableHead className="text-right">{t("nhcx_eligible")}</TableHead>
            <TableHead className="text-right">
              {t("nhcx_eligible_percent")}
            </TableHead>
            <TableHead>{t("nhcx_deducted")}</TableHead>
            <TableHead>{t("nhcx_payers_note")}</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((i) => {
            const note = (i.reason || "").replace(/\|/g, " · ");
            const status = (i.status || "").toLowerCase();
            return (
              <TableRow key={i.sequence}>
                <TableCell>{i.sequence}</TableCell>
                <TableCell>
                  {i.status ? (
                    <Chip tone={VERDICT_TONE[status] ?? "info"}>
                      {i.status}
                    </Chip>
                  ) : (
                    "-"
                  )}
                </TableCell>
                <TableCell className="text-right">
                  {formatMoney(i.eligible)}
                </TableCell>
                <TableCell className="text-right">
                  {i.percent === null || i.percent === undefined
                    ? "-"
                    : `${i.percent}%`}
                </TableCell>
                <TableCell>
                  {formatMoney(i.deductible)}
                  {i.deduction_reason && (
                    <div className="text-xs text-gray-500">
                      {i.deduction_reason}
                    </div>
                  )}
                </TableCell>
                <TableCell className="max-w-md text-sm">
                  {note ? note.slice(0, 240) : "-"}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}

function enquiryTone(e: Enquiry): Tone {
  const a = (e.answer || "").toLowerCase();
  if (["approved", "reopened", "complete", "paid"].includes(a))
    return "success";
  if (["partial", "queried"].includes(a)) return "warning";
  if (["rejected", "refused", "not-found", "notfound"].includes(a))
    return "danger";
  return "info";
}

// Status / reprocess / release enquiry rows, newest first, at most 5.
export function EnquiryRows({
  enquiries,
  stage,
  kinds = ["status"],
}: {
  enquiries: Enquiry[];
  stage: Stage;
  kinds?: Enquiry["kind"][];
}) {
  const { t } = useTranslation();
  const rows = enquiries
    .filter((e) => e.stage === stage && kinds.includes(e.kind))
    .slice(0, 5);
  if (!rows.length) return null;
  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>{t("nhcx_asked")}</TableHead>
            <TableHead>{t("nhcx_payer_said")}</TableHead>
            <TableHead>{t("nhcx_answered_at")}</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((e) => (
            <TableRow key={e.id}>
              <TableCell>{formatDateTime(e.requested_at)}</TableCell>
              <TableCell>
                {e.status === "asking" ? (
                  <Chip tone="info">{t("nhcx_asking_use_refresh")}</Chip>
                ) : e.status === "error" ? (
                  <span className="flex flex-wrap items-center gap-2">
                    <Chip tone="danger">{t("nhcx_failed")}</Chip>
                    <span className="text-sm text-red-700">
                      {e.error_message}
                    </span>
                  </span>
                ) : (
                  <span className="flex flex-wrap items-center gap-2">
                    <Chip tone={enquiryTone(e)}>{e.answer || "-"}</Chip>
                    {e.amount !== null && e.amount !== undefined && (
                      <span>{formatMoney(e.amount)}</span>
                    )}
                    {e.detail && <Muted>{e.detail}</Muted>}
                  </span>
                )}
              </TableCell>
              <TableCell>{formatDateTime(e.answered_at)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

// "What the payer says": the query note as a code block (S9, S10, S11).
export function QueryNote({ text }: { text?: string | null }) {
  const { t } = useTranslation();
  if (!text) return null;
  return (
    <div className="space-y-1">
      <h4 className="text-sm font-semibold">{t("nhcx_what_payer_says")}</h4>
      <pre className="whitespace-pre-wrap rounded-md bg-gray-100 p-3 text-xs">
        {text}
      </pre>
    </div>
  );
}

// Inline reply for payers that take the query answer as a resubmission.
export function ResubmitReply({
  label,
  pending,
  onSend,
}: {
  label: string;
  pending: boolean;
  onSend: (reply: string) => void;
}) {
  const { t } = useTranslation();
  const [reply, setReply] = useState("");
  return (
    <form
      className="space-y-2"
      onSubmit={(e) => {
        e.preventDefault();
        if (!reply.trim()) {
          toast.error(t("nhcx_write_reply_first"));
          return;
        }
        onSend(reply);
      }}
    >
      <Label htmlFor="nhcx-resubmit-reply">
        {t("nhcx_reply_to_query")}
        <span className="text-red-500"> *</span>
      </Label>
      <Textarea
        id="nhcx-resubmit-reply"
        required
        value={reply}
        onChange={(e) => setReply(e.target.value)}
      />
      <Muted className="text-xs">{t("nhcx_reply_to_query_help")}</Muted>
      <Button type="submit" size="sm" variant="primary" disabled={pending}>
        <Send className="size-4" />
        {label}
      </Button>
    </form>
  );
}
