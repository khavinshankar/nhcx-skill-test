import { HttpMethod, PaginatedResponse, Type } from "@/Utils/request/types";

import {
  AbhaRequest,
  AbhaResponse,
  AddLineRequest,
  Benefit,
  BiometricRequest,
  BiometricResponse,
  Claim,
  ClaimLine,
  ClaimState,
  ClaimSubmitRequest,
  DischargeRequest,
  DraftUpdate,
  EligibilityRequest,
  EnquiryRequest,
  FacilityProfile,
  FacilityProfileResponse,
  LedgerRow,
  NhcxOk,
  OpenClaimRequest,
  PolicySearchRequest,
  PolicySearchResponse,
  PractitionerProfile,
  PractitionerProfileResponse,
  UpdateLinesRequest,
} from "./nhcx";

const base = "/api/v1/facility/{facilityId}/nhcx";
const claimBase = `${base}/claims/{claimId}` as const;

// Every route of care/care/nhcx/api/CONTRACT.md.
export default {
  // services-core
  policySearch: {
    path: `${base}/policy-search/`,
    method: HttpMethod.POST,
    TRes: Type<PolicySearchResponse>(),
    TBody: Type<PolicySearchRequest>(),
  },
  openClaim: {
    path: `${base}/claims/`,
    method: HttpMethod.POST,
    TRes: Type<NhcxOk>(),
    TBody: Type<OpenClaimRequest>(),
  },
  listClaims: {
    path: `${base}/claims/`,
    method: HttpMethod.GET,
    TRes: Type<PaginatedResponse<Claim>>(),
  },
  claimState: {
    path: `${claimBase}/state/`,
    method: HttpMethod.GET,
    TRes: Type<ClaimState>(),
  },
  checkEligibility: {
    path: `${claimBase}/eligibility/`,
    method: HttpMethod.POST,
    TRes: Type<NhcxOk>(),
    TBody: Type<EligibilityRequest>(),
  },
  authRequirements: {
    path: `${claimBase}/auth-requirements/`,
    method: HttpMethod.POST,
    TRes: Type<NhcxOk>(),
    TBody: Type<Record<string, never>>(),
  },
  fetchPlan: {
    path: `${claimBase}/plan/`,
    method: HttpMethod.POST,
    TRes: Type<NhcxOk>(),
    TBody: Type<{ refresh?: boolean }>(),
  },
  getPlanBenefit: {
    path: `${claimBase}/plan/benefits/{benefitId}/`,
    method: HttpMethod.GET,
    TRes: Type<Benefit>(),
  },
  updateLines: {
    path: `${claimBase}/lines/`,
    method: HttpMethod.PUT,
    TRes: Type<NhcxOk>(),
    TBody: Type<UpdateLinesRequest>(),
  },
  addLine: {
    path: `${claimBase}/lines/`,
    method: HttpMethod.POST,
    TRes: Type<NhcxOk & { line?: ClaimLine }>(),
    TBody: Type<AddLineRequest>(),
  },
  removeLine: {
    path: `${claimBase}/lines/{lineId}/`,
    method: HttpMethod.DELETE,
    TRes: Type<NhcxOk>(),
  },
  linkAdmission: {
    path: `${claimBase}/admission/`,
    method: HttpMethod.POST,
    TRes: Type<NhcxOk>(),
    TBody: Type<{ encounter: string | null }>(),
  },
  listLedger: {
    path: `${base}/ledger/`,
    method: HttpMethod.GET,
    TRes: Type<PaginatedResponse<LedgerRow>>(),
  },
  getLedger: {
    path: `${base}/ledger/{ledgerId}/`,
    method: HttpMethod.GET,
    TRes: Type<LedgerRow>(),
  },

  // services-legs
  updateDraft: {
    path: `${claimBase}/draft/`,
    method: HttpMethod.PUT,
    TRes: Type<NhcxOk>(),
    TBody: Type<DraftUpdate>(),
  },
  uploadDocument: {
    path: `${claimBase}/documents/`,
    method: HttpMethod.POST,
    TRes: Type<NhcxOk & { document_id?: string }>(),
    TBody: Type<FormData>(),
  },
  removeDocument: {
    path: `${claimBase}/documents/{documentId}/`,
    method: HttpMethod.DELETE,
    TRes: Type<NhcxOk>(),
  },
  submitPreauth: {
    path: `${claimBase}/preauth/submit/`,
    method: HttpMethod.POST,
    TRes: Type<NhcxOk>(),
    TBody: Type<{ kind?: string; reply?: string }>(),
  },
  predetermination: {
    path: `${claimBase}/preauth/predetermination/`,
    method: HttpMethod.POST,
    TRes: Type<NhcxOk>(),
    TBody: Type<Record<string, never>>(),
  },
  cancelPreauth: {
    path: `${claimBase}/preauth/cancel/`,
    method: HttpMethod.POST,
    TRes: Type<NhcxOk>(),
    TBody: Type<{ reason: string; note: string }>(),
  },
  enquiry: {
    path: `${claimBase}/enquiry/`,
    method: HttpMethod.POST,
    TRes: Type<NhcxOk>(),
    TBody: Type<EnquiryRequest>(),
  },
  submitClaim: {
    path: `${claimBase}/claim/submit/`,
    method: HttpMethod.POST,
    TRes: Type<NhcxOk>(),
    TBody: Type<ClaimSubmitRequest>(),
  },
  // Backend extras beyond CONTRACT.md (care/nhcx/api/urls_legs.py).
  recordDischarge: {
    path: `${claimBase}/discharge/`,
    method: HttpMethod.POST,
    TRes: Type<NhcxOk>(),
    TBody: Type<DischargeRequest>(),
  },
  ackQuery: {
    path: `${claimBase}/queries/{queryId}/ack/`,
    method: HttpMethod.POST,
    TRes: Type<NhcxOk>(),
    TBody: Type<Record<string, never>>(),
  },
  replyQuery: {
    path: `${claimBase}/queries/{queryId}/reply/`,
    method: HttpMethod.POST,
    TRes: Type<NhcxOk>(),
    TBody: Type<{ text: string; document_ids: string[] }>(),
  },
  ackPayment: {
    path: `${claimBase}/payments/{paymentId}/ack/`,
    method: HttpMethod.POST,
    TRes: Type<NhcxOk>(),
    TBody: Type<Record<string, never>>(),
  },
  biometric: {
    path: `${claimBase}/biometric/{action}/`,
    method: HttpMethod.POST,
    TRes: Type<BiometricResponse>(),
    TBody: Type<BiometricRequest>(),
  },
  adjudicate: {
    path: `${claimBase}/adjudicate/`,
    method: HttpMethod.POST,
    TRes: Type<NhcxOk>(),
    TBody: Type<{ action: string; [key: string]: unknown }>(),
  },
  getFacilityProfile: {
    path: `${base}/profile/`,
    method: HttpMethod.GET,
    TRes: Type<FacilityProfileResponse>(),
  },
  updateFacilityProfile: {
    path: `${base}/profile/`,
    method: HttpMethod.PUT,
    TRes: Type<FacilityProfileResponse>(),
    TBody: Type<Partial<FacilityProfile>>(),
  },

  // outside facility scope
  getPractitioner: {
    path: "/api/v1/nhcx/practitioner/{userId}/",
    method: HttpMethod.GET,
    TRes: Type<PractitionerProfileResponse>(),
  },
  updatePractitioner: {
    path: "/api/v1/nhcx/practitioner/{userId}/",
    method: HttpMethod.PUT,
    TRes: Type<PractitionerProfileResponse>(),
    TBody: Type<Partial<PractitionerProfile>>(),
  },
  abha: {
    path: "/api/v1/nhcx/abha/{action}/",
    method: HttpMethod.POST,
    TRes: Type<AbhaResponse>(),
    TBody: Type<AbhaRequest>(),
  },
} as const;
