# NHCX application API contract (care backend <-> care_fe)

Base: `/api/v1/facility/{facility_id}/nhcx/` (facility external_id). Auth: normal CARE JWT; user must have access to the facility.
Claim ids (`{claim_id}`) are the claim's `external_id` UUID. All sending endpoints are `transaction.non_atomic_requests`.

Conventions
- Mutation success: `200 {"ok": true, "message": "<flash text or null>", "claim_id": "<uuid>"}` (+ extra keys noted).
- Refusal (spec's verbatim message): `400 {"ok": false, "error": "<message>"}`. FE shows it as a toast/inline alert, never as a crash.
- After any mutation FE refetches `state`.
- Rows in JSON use the D column names (as in the database/ specs) plus `id` = external_id.

## Owned by services-core (care/nhcx/api/views_core.py, urls in care/nhcx/api/urls.py)
| Method | Path | Spec | Body / query | Response |
|---|---|---|---|---|
| POST | `policy-search/` | A1, S1, S2, S17 | `{identifiertype, identifiervalue}` or `{abha_number, mobile, aadhaar}` | `{ok, policies:[{payer_id, payer_name, policy_number/policy_code, member_id, beneficiary_name, ...normalised}], message}` |
| POST | `claims/` | A1 open case, S2 | `{policy: <one policy object from search>, encounter?: uuid}` | `{ok, claim_id}` |
| GET | `claims/` | S5 | `?status=&stage=&search=&limit=&offset=` | `{count, results:[claim rows]}` |
| GET | `claims/{claim_id}/state/` | A17, S6 | — runs polls | A17 JSON (claim, plan, benefits, admissions, lines, ruling, ... poll_notes, next_send, enhancement_lines, required_documents, required_forms) |
| POST | `claims/{claim_id}/eligibility/` | A2, S3, S17 | `{purpose: validation|benefits|discovery, ...}` | ok/refusal |
| POST | `claims/{claim_id}/auth-requirements/` | A2 auth, S8.2 | `{}` (uses current lines) | ok/refusal |
| POST | `claims/{claim_id}/plan/` | A3, S7 | `{refresh?: bool}` | ok/refusal |
| POST | `claims/{claim_id}/lines/` | S8, D16 | `{kind, code, ..., quantity}` | ok + `line` |
| DELETE | `claims/{claim_id}/lines/{line_id}/` | S8 | | ok |
| POST | `claims/{claim_id}/admission/` | S4 link encounter | `{encounter: uuid}` | ok |
| GET | `ledger/` , `ledger/{id}/` | A13 (admin/debug) | | rows |

## Owned by services-legs (care/nhcx/api/views_legs.py, urls in care/nhcx/api/urls_legs.py, included by urls.py)
| Method | Path | Spec | Body |
|---|---|---|---|
| PUT | `claims/{claim_id}/draft/` | S4/S9 draft: diagnoses (D25), care_team (D26), items (D27), dates, form answers (D17) | partial object of those lists/fields |
| POST | `claims/{claim_id}/documents/` | D28 upload (multipart `file`, `code`, `category`, `stage`) | |
| DELETE | `claims/{claim_id}/documents/{doc_id}/` | D28 | |
| POST | `claims/{claim_id}/preauth/submit/` | A4 | `{kind?: request|enhancement|...}` |
| POST | `claims/{claim_id}/preauth/predetermination/` | A4 predetermination | |
| POST | `claims/{claim_id}/preauth/cancel/` | A6 cancel | `{reason, note}` |
| POST | `claims/{claim_id}/enquiry/` | A6 status/reprocess/release | `{action: status|reprocess|release, leg: preauth|claim, reason?, note?, amount?}` |
| POST | `claims/{claim_id}/claim/submit/` | A5, S11 | `{discharge_mode, discharge_date, ...}` |
| POST | `claims/{claim_id}/queries/{query_id}/reply/` | A7, S10 | `{text, document_ids:[]}` |
| POST | `claims/{claim_id}/payments/{payment_id}/ack/` | A8, S12 | |
| POST | `claims/{claim_id}/biometric/{init|verify|refresh}/` | A18, S18 | per A18 |
| POST | `claims/{claim_id}/adjudicate/` | A14/A15 (sandbox only; 404 when console off) | `{action, ...}` |
| GET/PUT | `profile/` | D1 FacilityProfile (hfr_id, participant_code, email, gstin); PUT needs `can_update_facility`. A blank hfr_id falls back to the care_abdm HIP ID (`HealthFacility.hf_id`) | `{hfr_id?, participant_code?, email?, gstin?}`; answers `{profile, abdm_hf_id, effective_hfr_id, hfr_id_source: profile\|abdm\|null, can_edit}` |

## Outside facility scope
| Method | Path | Spec |
|---|---|---|
| GET/PUT | `/api/v1/nhcx/practitioner/{user_id}/` | D2 PractitionerProfile (hpr_id, qualification_code, specialty, department, active) — S16 |
| POST | `/api/v1/nhcx/abha/{action}/` | A19 server-side M1 flow: actions `aadhaar-otp`, `aadhaar-verify`, `mobile-otp`, `mobile-verify`, `profile`, `link` (sets PatientIdentifier on `{patient}`); returns `{txn_id, ...}` only, tokens stay server-side | S13-S15 |

## Shared hooks (A17)
`care/nhcx/services/hooks.py` (owned by services-core) exposes registries with defaults per A17D:
`next_send(claim, leg) `, `enhancement_lines(claim)`, `required_documents(claim, stage)`, `required_forms(claim, stage)`; services-legs registers real implementations via `hooks.register(name, fn)` at import (services/preauth.py, services/claim.py), and the AppConfig.ready imports those modules.

## C1 handler contract
`care.nhcx.callbacks.dispatch.receive(envelope, delivery) -> {"outcome": settled|unmatched|ignored|rejected|error, "detail": str}` (called by gateway G8; envelope = {meta, jwe_headers, fhir}; delivery = {path, type, flow, payload_kind, correlation_id, api_call_id, redelivery, participant}).
Dispatch (services-core) routes by path to handler modules exposing `handle(envelope, delivery) -> dict` with the same outcome shape:
- `coverageeligibility/on_check` -> callbacks/eligibility.py (C2, C3) [core]
- `insuranceplan/on_request` -> callbacks/plan.py (C4) [core]
- `preauth/on_submit` -> callbacks/preauth.py (C5) [legs]; `claim/on_submit` -> callbacks/claim.py (C6) [legs]
- `task/on_submit` -> callbacks/enquiry.py (C7 cancel + C8) [legs]
- `communication/request` -> callbacks/communication.py (C9) [legs]
- `paymentnotice/request` -> callbacks/payment.py (C10) [legs]
Polling (A10-A13, core) applies replies found in the ledger through the same `handle` functions.
Missing handler module => `unmatched`.
