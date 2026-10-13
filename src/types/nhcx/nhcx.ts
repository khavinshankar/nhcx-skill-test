// NHCX claim types. Rows use the D column names of the database specs
// (D9-D31) plus `id` (the row's external id). Money arrives as decimal
// strings or numbers; `Money` covers both.

export type Money = string | number | null;

export type ClaimStatus =
  "draft" | "checking" | "eligible" | "not-eligible" | "error";

export type ClaimStage =
  "eligibility" | "preauth" | "enhancement" | "claim" | "payment";

export type ClaimSubStage =
  | "draft"
  | "checking"
  | "eligible"
  | "not-eligible"
  | "requested"
  | "resubmitted"
  | "answered"
  | "queried"
  | "approved"
  | "partial"
  | "rejected"
  | "cancelling"
  | "cancelled"
  | "refused"
  | "noticed"
  | "paid";

export type SearchIdType = "MemberId" | "MobileNo" | "AbhaNumber";

export type EligibilityPurpose = "validation" | "benefits" | "discovery";

// D9 claim
export interface Claim {
  id: string;
  claim_no: string;
  status: ClaimStatus;
  search_id_type: SearchIdType | "" | null;
  search_id_value: string | null;
  member_id: string | null;
  policy_code: string | null;
  beneficiary_name: string | null;
  abha_number: string | null;
  mobile_number: string | null;
  processing_id: string | null;
  payer_id: string | null;
  payer_name: string | null;
  product_id: string | null;
  product_name: string | null;
  policy_json?: unknown;
  purpose: EligibilityPurpose | "" | null;
  txn_id: string | null;
  correlation_id: string | null;
  checked_at: string | null;
  error_message: string | null;
  inforce: boolean | null;
  outcome: string | null;
  disposition: string | null;
  auth_required: boolean | null;
  allowed_amount: Money;
  used_amount: Money;
  plan_name: string | null;
  plan_period_start: string | null;
  plan_period_end: string | null;
  relationship: string | null;
  patient_gender: string | null;
  patient_dob: string | null;
  patient_address: string | null;
  patient_photo: string | null;
  response_json?: unknown;
  patient: string | null;
  patient_name?: string | null;
  encounter: string | null;
  admission_date: string | null;
  expected_discharge_date: string | null;
  case_type: "package" | "nonpackage" | "" | null;
  package_code: string | null;
  package_name: string | null;
  preauth_total: Money;
  preauth_saved_at: string | null;
  stage: ClaimStage;
  sub_stage: ClaimSubStage;
  created_date: string;
  // Discharge as recorded on the claim leg (D20); some backends echo it here.
  discharge_mode?: DischargeMode | null;
  discharge_stage?: DischargeStage | null;
  discharge_date?: string | null;
  surgery_date?: string | null;
  death_date?: string | null;
}

// D10 claim_plan
export interface ClaimPlan {
  id: string;
  status: "fetching" | "ready" | "empty" | "error";
  txn_id: string | null;
  correlation_id: string | null;
  requested_at: string | null;
  fetched_at: string | null;
  error_message: string | null;
  policy_code: string | null;
  provider_id: string | null;
  plan_identifier: string | null;
  plan_title: string | null;
  plan_type: string | null;
  sum_insured: Money;
  policy_documents?: unknown;
}

export type BenefitKind = "Procedure" | "Implant";

// D11 claim_plan_benefit. The claim state lists every column but conditions and
// supporting_info, which come from getPlanBenefit (they run to MBs on PMJAY).
// A package listed under several specialities has one row per speciality.
export interface Benefit {
  id: string;
  kind: BenefitKind;
  code: string;
  display: string;
  category_code: string | null;
  category_display: string | null;
  rate: Money;
  seq?: number;
  currency?: string | null;
  cost_type?: string | null;
  requirement?: string | null;
  conditions?: Record<string, unknown> | null;
  extras?: BenefitExtra[] | null;
  supporting_info?: BenefitRequirement[] | null;
}

export interface BenefitExtra {
  type: string;
  code: string;
  label: string | null;
  rate: Money;
  currency?: string | null;
}

export interface BenefitRequirement {
  code: string;
  display: string | null;
  category: string | null;
  category_display?: string | null;
  form?: string | null;
}

// D12 claim_plan_form question
export interface FormQuestion {
  linkId: string;
  type: string;
  text: string | null;
  required?: boolean;
  depth?: number;
  options?: string[];
  initial?: string | null;
  answer?: string | null;
}

export interface ClaimForm {
  url: string;
  title: string;
  questions: FormQuestion[];
  answers?: Record<string, string>;
}

// D13 claim_auth + D14/D15 (optionally nested)
export interface AuthItem {
  seq: number;
  code: string;
  display: string | null;
  category_code: string | null;
  auth_required: boolean | null;
  excluded: boolean | null;
  benefit_type: string | null;
  allowed_amount: Money;
}

export interface AuthRequirement {
  seq: number;
  kind: "document" | "form";
  code: string | null;
  display: string | null;
  form_url: string | null;
  stage: string | null;
  for_code: string | null;
  at_preauth: boolean | null;
}

export interface ClaimAuth {
  id: string;
  status: "checking" | "ready" | "error";
  txn_id: string | null;
  correlation_id: string | null;
  requested_at: string | null;
  settled_at: string | null;
  error_message: string | null;
  outcome: string | null;
  disposition: string | null;
  inforce: boolean | null;
  asked_codes: string | string[] | null;
  items?: AuthItem[];
  requirements?: AuthRequirement[];
}

export type LineKind = "Procedure" | "Implant" | "Stratification";

// D16 claim_line
export interface ClaimLine {
  id: string;
  seq: number;
  kind: LineKind;
  code: string;
  display: string | null;
  category_code: string | null;
  category_display: string | null;
  unit_price: Money;
  quantity: number;
  amount: Money;
  parent_code: string | null;
}

// D25 claim_diagnosis
export interface Diagnosis {
  id?: string;
  seq?: number;
  snomed_code: string | null;
  snomed_display: string | null;
  icd10_code: string | null;
  icd10_display: string | null;
}

export type CareTeamRole =
  "admitting" | "treating" | "surgeon" | "anaesthetist" | "nurse";

// D26 claim_care_team
export interface CareTeamMember {
  id?: string;
  seq?: number;
  practitioner: string;
  practitioner_name?: string | null;
  role: CareTeamRole;
}

// D27 claim_item
export interface ClaimItem {
  id?: string;
  seq?: number;
  code: string;
  display: string;
  unit_price: Money;
  quantity: number;
  amount?: Money;
}

// D17 claim_form_answer
export interface FormAnswer {
  form_url: string;
  link_id: string;
  answer: string | null;
  stage: "preauth" | "claim";
}

// D28 claim_document (A17 subset)
export interface ClaimDocument {
  id: string;
  code: string;
  label: string | null;
  filename: string;
  content_type: string;
  size: number;
  stage: string;
  category?: string | null;
  uploaded_at?: string | null;
  url?: string | null;
}

export interface RequiredDocument {
  code: string;
  display: string;
  category: string | null;
  package_code: string | null;
  attached_document_id: string | null;
}

export type LegStatus =
  | "draft"
  | "submitting"
  | "approved"
  | "partial"
  | "queried"
  | "rejected"
  | "cancelling"
  | "cancelled"
  | "error";

interface LegBase {
  id: string;
  txn_id: string | null;
  correlation_id: string | null;
  submitted_at: string | null;
  settled_at: string | null;
  error_message: string | null;
  claim_ref: string | null;
  api_call_id: string | null;
  adjudication: string | null;
  query_note: string | null;
  outcome: string | null;
  disposition: string | null;
  approved_amount: Money;
  eligible_amount: Money;
  submitted_amount: Money;
  requested_amount: Money;
  submission_kind: string | null;
  workflow_id: string | null;
  thread_correlation_id: string | null;
  reply_text: string | null;
}

// D18 claim_preauth
export interface Preauth extends LegBase {
  status: LegStatus;
  preauth_ref: string | null;
  cancel_txn_id: string | null;
  cancel_correlation_id: string | null;
  cancel_requested_at: string | null;
  cancel_reason: string | null;
  cancel_note: string | null;
  pre_cancel_status: string | null;
  enhancement_no: number | null;
}

// D20 claim_submission
export type DischargeMode = "normal" | "lama" | "dama" | "death";
export type DischargeStage =
  "Before Surgery" | "During Surgery" | "After Surgery";

export interface Submission extends LegBase {
  status: LegStatus;
  discharge_mode: DischargeMode | null;
  discharge_stage: DischargeStage | null;
  discharge_date: string | null;
  surgery_date: string | null;
  death_date: string | null;
}

// Per-item verdict (A17 preauth_items / submission_items)
export interface ItemVerdict {
  sequence: number;
  status: string | null;
  eligible: Money;
  percent: Money;
  quantity: Money;
  deductible: Money;
  deduction_reason: string | null;
  reason: string | null;
  benefit?: string | null;
  submitted?: Money;
  display?: string | null;
  code?: string | null;
}

// D19 claim_predetermination
export interface Predetermination {
  id: string;
  status: "asking" | "answered" | "error";
  txn_id: string | null;
  correlation_id: string | null;
  requested_at: string | null;
  answered_at: string | null;
  error_message: string | null;
  outcome: string | null;
  adjudication: string | null;
  disposition: string | null;
  allowed_amount: Money;
  requested_amount: Money;
}

// D23 claim_query
export interface ClaimQuery {
  id: string;
  stage: "preauth" | "claim";
  correlation_id: string | null;
  request_id: string | null;
  claim_ref: string | null;
  sender_code: string | null;
  workflow_id: string | null;
  received_at: string | null;
  status: "open" | "answered" | "acknowledged" | "noted" | "error";
  kind: "query" | "notification" | "note";
  reason_code: string | null;
  remarks: string | null;
  questions: string[];
  reply_text: string | null;
  reply_documents: string[] | string | null;
  reply_txn_id: string | null;
  reply_correlation_id: string | null;
  answered_at: string | null;
  acknowledged_at: string | null;
  error_message: string | null;
}

// D22 claim_payment_detail
export interface PaymentDetail {
  seq: number;
  reference: string | null;
  type_code: string | null;
  type_display: string | null;
  date: string | null;
  amount: Money;
}

// D21 claim_payment
export interface Payment {
  id: string;
  claim_ref: string | null;
  correlation_id: string | null;
  sender_code: string | null;
  workflow_id: string | null;
  received_at: string | null;
  disposition: string | null;
  payment_status: string | null;
  payment_date: string | null;
  amount: Money;
  currency: string | null;
  utr: string | null;
  ack_status: "pending" | "sent" | "error";
  ack_txn_id: string | null;
  ack_correlation_id: string | null;
  acknowledged_at: string | null;
  ack_error: string | null;
  notice_id: string | null;
  details?: PaymentDetail[];
}

// D29 claim_enquiry
export interface Enquiry {
  id: string;
  kind: "status" | "reprocess" | "release";
  stage: "preauth" | "claim";
  txn_id: string | null;
  correlation_id: string | null;
  requested_at: string | null;
  status: "asking" | "answered" | "error";
  answer: string | null;
  detail: string | null;
  amount: Money;
  reason: string | null;
  reason_code: string | null;
  document_ids: string[] | string | null;
  error_message: string | null;
  answered_at: string | null;
}

// D31 biometric_auth
export type BiometricMethod = "FINGERPRINT" | "IRIS" | "FACE_AUTH";

export interface BiometricAuth {
  id: string;
  payer_code: string | null;
  stage: "Preauth" | "Discharge";
  method: BiometricMethod;
  status: "initiated" | "captured" | "verified" | "failed";
  txn_id: string | null;
  abha_number: string | null;
  token_expires_at: string | null;
  refresh_expires_at: string | null;
  message: string | null;
  verified_at: string | null;
  created_date?: string | null;
  qr_url?: string | null;
}

// A current inpatient stay (D4 encounter) matching the claim's ABHA.
export interface Admission {
  id: string;
  patient?: { id: string; name: string } | string | null;
  patient_name?: string | null;
  mrn?: string | null;
  encounter_no?: string | null;
  external_identifier?: string | null;
  location?: string | null;
  bed?: string | null;
  period_start?: string | null;
  period?: { start?: string | null; end?: string | null } | null;
  doctor?: string | null;
  consultant?: string | null;
}

export type NextSend = string | { refused: string };

// A17 claim state
export interface ClaimState {
  claim: Claim;
  plan: ClaimPlan | null;
  benefits: Benefit[];
  admissions: Admission[];
  lines: ClaimLine[];
  ruling: ClaimAuth | null;
  required_documents: {
    preauth: RequiredDocument[];
    claim: RequiredDocument[];
  };
  forms: { preauth: ClaimForm[]; claim: ClaimForm[] };
  required_forms?: { preauth: ClaimForm[]; claim: ClaimForm[] };
  documents: ClaimDocument[];
  stage: ClaimStage;
  sub_stage: ClaimSubStage;
  preauth: Preauth | null;
  preauth_items: ItemVerdict[];
  next_send: { preauth: NextSend; claim: NextSend };
  adapter: string;
  desk: string | null;
  predeterminations: Predetermination[];
  enhancement_lines: ClaimLine[];
  queries: ClaimQuery[];
  submission: Submission | null;
  submission_items: ItemVerdict[];
  payments: Payment[];
  paid_total: Money;
  enquiries: Enquiry[];
  poll_notes: string[];
  // Optional extras some backends add; read when present.
  diagnoses?: Diagnosis[];
  care_team?: CareTeamMember[];
  items?: ClaimItem[];
  form_answers?: FormAnswer[];
  biometric?: BiometricAuth[];
  biometric_required?: boolean;
  plan_forms?: ClaimForm[];
}

// Policy as normalised by policy-search (A1)
export interface PolicyResult {
  payer_id: string;
  payer_name?: string | null;
  policy_code?: string | null;
  policy_number?: string | null;
  product_id?: string | null;
  product_name?: string | null;
  member_id?: string | null;
  name?: string | null;
  beneficiary_name?: string | null;
  abha_number?: string | null;
  mobile_number?: string | null;
  photo?: string | null;
  raw?: unknown;
  [key: string]: unknown;
}

export interface PolicySearchRequest {
  identifiertype?: SearchIdType;
  identifiervalue?: string;
  abha_number?: string;
  mobile?: string;
  aadhaar?: string;
}

export interface PolicySearchResponse {
  ok: boolean;
  policies: PolicyResult[];
  message: string | null;
  error?: string;
}

export interface NhcxOk {
  ok: boolean;
  message: string | null;
  claim_id?: string;
  error?: string;
}

export interface NhcxRefusal {
  ok: false;
  error: string;
}

export interface OpenClaimRequest {
  policy?: PolicyResult;
  encounter?: string;
  patient?: string;
  id_type?: SearchIdType;
  id_value?: string;
  // S17: a discovery case is opened around the payer, not a policy.
  purpose?: "discovery";
  payer_id?: string;
  aadhaar_number?: string;
  mobile_number?: string;
  member_id?: string;
}

export interface EligibilityRequest {
  purpose: EligibilityPurpose;
  policy_code?: string;
  member_id?: string;
  payer_id?: string;
  identifier_type?: SearchIdType;
  identifier_value?: string;
  aadhaar_number?: string;
  mobile_number?: string;
}

export interface AddLineRequest {
  kind: LineKind;
  code: string;
  parent_code?: string;
  // The speciality the package was picked under.
  category_code?: string;
  quantity: number;
}

export interface UpdateLinesRequest {
  // unit_price only for an open-priced line.
  lines: { id: string; quantity?: number; unit_price?: string }[];
}

export interface DraftUpdate {
  admission_date?: string | null;
  expected_discharge_date?: string | null;
  case_type?: "package" | "nonpackage";
  package_code?: string | null;
  diagnoses?: Diagnosis[];
  care_team?: CareTeamMember[];
  items?: ClaimItem[];
  form_answers?: FormAnswer[];
  discharge_mode?: DischargeMode | null;
  discharge_stage?: DischargeStage | null;
  discharge_date?: string | null;
  surgery_date?: string | null;
  death_date?: string | null;
}

export interface EnquiryRequest {
  action: "status" | "reprocess" | "release";
  leg: "preauth" | "claim";
  reason?: string;
  note?: string;
  amount?: string;
  document_ids?: string[];
}

export interface DischargeRequest {
  discharge_mode: DischargeMode | "";
  discharge_stage: DischargeStage | "";
  discharge_date: string;
  surgery_date?: string;
  death_date?: string;
}

export interface ClaimSubmitRequest {
  kind?: string;
  reply?: string;
  discharge_mode?: DischargeMode;
  discharge_stage?: DischargeStage;
  discharge_date?: string;
  surgery_date?: string;
  death_date?: string;
}

export interface BiometricRequest {
  attempt?: string;
  stage?: "Preauth" | "Discharge";
  method?: BiometricMethod;
  pid?: string;
  aadhaar_encrypted?: string;
  aadhaar?: string;
  mobile?: string;
}

export interface BiometricResponse extends NhcxOk {
  attempt?: BiometricAuth;
  qr_url?: string | null;
  token_valid?: boolean;
}

// D1 facility profile
export interface FacilityProfile {
  hfr_id: string | null;
  participant_code: string | null;
  email: string | null;
  gstin: string | null;
}

// GET/PUT profile/: a blank hfr_id falls back to the care_abdm HIP ID.
export interface FacilityProfileResponse extends NhcxOk {
  profile: FacilityProfile;
  abdm_hf_id: string | null;
  effective_hfr_id: string | null;
  hfr_id_source: "profile" | "abdm" | null;
  can_edit: boolean;
}

// D2 practitioner profile
export interface PractitionerProfile {
  user_id?: string;
  username?: string;
  name?: string;
  prefix?: string | null;
  identifier_type_code?: string | null;
  identifier_type_display?: string | null;
  hpr_id: string | null;
  qualification_code: string | null;
  qualification_display: string | null;
  role_code?: string | null;
  role_display?: string | null;
  specialty_code: string | null;
  specialty_display: string | null;
  department: string | null;
  active: boolean;
}

export interface PractitionerProfileResponse {
  ok?: boolean;
  message?: string | null;
  profile: PractitionerProfile;
}

// A19 ABHA flow
export type AbhaAction =
  | "aadhaar-otp"
  | "aadhaar-verify"
  | "mobile-otp"
  | "mobile-verify"
  | "suggestions"
  | "address"
  | "profile"
  | "link";

export interface AbhaProfile {
  abha_no: string;
  abha_address: string | null;
  name: string | null;
  gender: string | null;
  dob: string | null;
  mobile: string | null;
  status?: string | null;
}

export interface AbhaAccount {
  abha_no: string;
  name: string | null;
  abha_address: string | null;
  status?: string | null;
}

export interface AbhaRequest {
  aadhaar?: string;
  txn_id?: string;
  otp?: string;
  mobile?: string;
  abha_number?: string;
  abha_no?: string;
  patient?: string;
  abha_address?: string;
}

export interface AbhaResponse {
  ok?: boolean;
  txn_id?: string;
  message?: string | null;
  hint?: "abha-number" | "mobile";
  is_new?: boolean;
  profile?: AbhaProfile;
  accounts?: AbhaAccount[];
  addresses?: string[];
  abha_no?: string;
  abha_address?: string;
  patient_id?: string;
  error?: string;
}

export interface LedgerRow {
  id: string;
  [key: string]: unknown;
}
