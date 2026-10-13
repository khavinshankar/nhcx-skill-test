import {
  Claim,
  ClaimQuery,
  ClaimState,
  ClaimStatus,
  ClaimSubStage,
  LegStatus,
  Money,
  NextSend,
  SearchIdType,
} from "@/types/nhcx/nhcx";
import { PatientIdentifier } from "@/types/patient/patientIdentifierConfig/patientIdentifierConfig";

export type Tone = "success" | "info" | "warning" | "danger" | "neutral";

export const TONE_VARIANT = {
  success: "green",
  info: "blue",
  warning: "yellow",
  danger: "destructive",
  neutral: "secondary",
} as const satisfies Record<Tone, string>;

export const CLAIM_STATUS: Record<ClaimStatus, { label: string; tone: Tone }> =
  {
    draft: { label: "nhcx_status_draft", tone: "warning" },
    checking: { label: "nhcx_awaiting_payer", tone: "info" },
    eligible: { label: "nhcx_status_eligible", tone: "success" },
    "not-eligible": { label: "nhcx_status_not_eligible", tone: "danger" },
    error: { label: "nhcx_status_error", tone: "danger" },
  };

export const STAGE_LABEL: Record<string, string> = {
  eligibility: "nhcx_stage_eligibility",
  preauth: "nhcx_stage_preauth",
  enhancement: "nhcx_stage_enhancement",
  claim: "nhcx_stage_claim",
  payment: "nhcx_stage_payment",
};

export const SUB_STAGE: Record<ClaimSubStage, { label: string; tone: Tone }> = {
  draft: { label: "nhcx_sub_drafted", tone: "warning" },
  checking: { label: "nhcx_sub_checking", tone: "info" },
  eligible: { label: "nhcx_sub_in_force", tone: "success" },
  "not-eligible": { label: "nhcx_sub_not_covered", tone: "danger" },
  requested: { label: "nhcx_sub_requested", tone: "info" },
  resubmitted: { label: "nhcx_sub_resubmitted", tone: "info" },
  answered: { label: "nhcx_sub_query_answered", tone: "info" },
  queried: { label: "nhcx_sub_queried", tone: "warning" },
  approved: { label: "nhcx_sub_approved", tone: "success" },
  partial: { label: "nhcx_sub_partial", tone: "warning" },
  rejected: { label: "nhcx_sub_rejected", tone: "danger" },
  cancelling: { label: "nhcx_sub_cancelling", tone: "warning" },
  cancelled: { label: "nhcx_sub_cancelled", tone: "danger" },
  refused: { label: "nhcx_sub_refused", tone: "danger" },
  noticed: { label: "nhcx_sub_noticed", tone: "info" },
  paid: { label: "nhcx_sub_paid", tone: "success" },
};

// S9 / S11 leg status labels.
export const LEG_STATUS: Record<LegStatus, { label: string; tone: Tone }> = {
  draft: { label: "nhcx_status_draft", tone: "warning" },
  submitting: { label: "nhcx_awaiting_payer", tone: "info" },
  approved: { label: "nhcx_sub_approved", tone: "success" },
  partial: { label: "nhcx_sub_partial", tone: "warning" },
  queried: { label: "nhcx_query_raised", tone: "warning" },
  rejected: { label: "nhcx_sub_rejected", tone: "danger" },
  cancelling: { label: "nhcx_cancelling", tone: "warning" },
  cancelled: { label: "nhcx_cancelled", tone: "danger" },
  error: { label: "nhcx_status_error", tone: "danger" },
};

export const ID_TYPES: { value: SearchIdType; label: string }[] = [
  { value: "MemberId", label: "nhcx_member_id" },
  { value: "MobileNo", label: "nhcx_mobile_number" },
  { value: "AbhaNumber", label: "nhcx_abha_number" },
];

export const DOCUMENT_CODES: { code: string; label: string }[] = [
  { code: "CD", label: "nhcx_doc_cd" },
  { code: "HDS", label: "nhcx_doc_hds" },
  { code: "DIA", label: "nhcx_doc_dia" },
  { code: "RAD", label: "nhcx_doc_rad" },
  { code: "PRE", label: "nhcx_doc_pre" },
  { code: "CER", label: "nhcx_doc_cer" },
  { code: "EST", label: "nhcx_doc_est" },
  { code: "MB", label: "nhcx_doc_mb" },
  { code: "INV", label: "nhcx_doc_inv" },
  { code: "OTR", label: "nhcx_doc_otr" },
  { code: "ICU", label: "nhcx_doc_icu" },
  { code: "IMP", label: "nhcx_doc_imp" },
  { code: "POI", label: "nhcx_doc_poi" },
  { code: "KYC", label: "nhcx_doc_kyc" },
  { code: "FCF", label: "nhcx_doc_fcf" },
  { code: "PAU", label: "nhcx_doc_pau" },
  { code: "ODN", label: "nhcx_doc_odn" },
];

export const UPLOAD_TYPES = [
  "application/pdf",
  "image/jpeg",
  "image/png",
  "image/webp",
];
export const UPLOAD_MAX_BYTES = 10 * 1024 * 1024;

export function toNumber(value: Money | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}

// Money shows as ₹12,345; a missing value as "-".
export function formatMoney(value: Money | undefined): string {
  const n = toNumber(value);
  if (n === null) return "-";
  return `₹${Math.round(n).toLocaleString("en-IN")}`;
}

export function formatDate(value?: string | null): string {
  if (!value) return "-";
  return value.slice(0, 10);
}

export function formatDateTime(value?: string | null): string {
  if (!value) return "-";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString("en-IN", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatSize(bytes?: number | null): string {
  if (!bytes && bytes !== 0) return "-";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function payerLabel(claim: {
  payer_name?: string | null;
  payer_id?: string | null;
}): string {
  return claim.payer_name || claim.payer_id || "-";
}

export function isRefused(send: NextSend | undefined): send is {
  refused: string;
} {
  return !!send && typeof send === "object" && "refused" in send;
}

export function openQueries(queries: ClaimQuery[]): ClaimQuery[] {
  return queries.filter((q) => q.status === "open" || q.status === "error");
}

export function unansweredCount(queries: ClaimQuery[]): number {
  return queries.filter(
    (q) =>
      q.kind === "query" && q.status !== "answered" && q.status !== "noted",
  ).length;
}

export function claimBalance(claim: Claim): number | null {
  const allowed = toNumber(claim.allowed_amount);
  if (allowed === null) return null;
  return allowed - (toNumber(claim.used_amount) ?? 0);
}

// The legs that are still out with the payer (S6 poll table).
export function isWaiting(state: ClaimState | undefined): boolean {
  if (!state) return false;
  return (
    state.claim.status === "checking" ||
    state.plan?.status === "fetching" ||
    state.ruling?.status === "checking" ||
    state.submission?.status === "submitting" ||
    state.preauth?.status === "submitting" ||
    state.preauth?.status === "cancelling" ||
    state.predeterminations.some((p) => p.status === "asking") ||
    state.enquiries.some((e) => e.status === "asking")
  );
}

export function claimForms(state: ClaimState, stage: "preauth" | "claim") {
  return state.forms?.[stage] ?? state.required_forms?.[stage] ?? [];
}

export function abhaDigits(value?: string | null): string {
  return (value || "").replace(/\D/g, "");
}

export const ABHA_SYSTEM = "https://healthid.abdm.gov.in";
export const ABHA_ADDRESS_SYSTEM = "https://healthid.abdm.gov.in/address";

export function formatAbha(value?: string | null): string {
  const d = abhaDigits(value);
  if (d.length !== 14) return value || "";
  return `${d.slice(0, 2)}-${d.slice(2, 6)}-${d.slice(6, 10)}-${d.slice(10)}`;
}

interface WithIdentifiers {
  instance_identifiers?: PatientIdentifier[];
  facility_identifiers?: PatientIdentifier[];
}

export function isAbhaSystem(system?: string | null): boolean {
  const s = (system || "").replace(/\/+$/, "");
  return s === ABHA_SYSTEM || s.endsWith("healthid.abdm.gov.in");
}

// The patient's ABHA number, read off the identifier typed with the ABHA system.
export function patientAbha(patient?: WithIdentifiers | null): string | null {
  const ids = [
    ...(patient?.instance_identifiers ?? []),
    ...(patient?.facility_identifiers ?? []),
  ];
  const hit = ids.find((i) => isAbhaSystem(i.config?.config?.system));
  return hit?.value || null;
}

export function patientMobile(phone?: string | null): string {
  const d = abhaDigits(phone);
  return d.length > 10 ? d.slice(-10) : d;
}

// S7.3 / S9 answer type labels; other types show as sent.
export const ANSWER_TYPE: Record<string, string> = {
  attachment: "nhcx_type_file",
  choice: "nhcx_type_choice",
  datetime: "nhcx_type_datetime",
  datetimeutc: "nhcx_type_datetime",
  date: "nhcx_type_date",
  time: "nhcx_type_time",
  string: "nhcx_type_text",
  text: "nhcx_type_long_text",
  boolean: "nhcx_type_boolean",
  integer: "nhcx_type_number",
  decimal: "nhcx_type_number",
  quantity: "nhcx_type_number",
  url: "nhcx_type_link",
};

export function answerTypeKey(type?: string | null): string | null {
  return ANSWER_TYPE[(type || "").toLowerCase()] ?? null;
}

// raviger's default serializer only drops `null`, so `undefined` would land in
// the URL as the literal string "undefined". Use with useQueryParams.
export const serializeQuery = (query: Record<string, unknown>) =>
  new URLSearchParams(
    Object.entries(query).flatMap(([k, v]) =>
      v === undefined || v === null || v === "" ? [] : [[k, String(v)]],
    ),
  ).toString();
