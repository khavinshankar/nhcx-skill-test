# A18. Provider Driver

#### A18E. ENDPOINT

Outbound, from the test harness to the sandbox provider EMR, over HTTPS, outside NHCX and outside G. The provider EMR is fixed, not a setting [SANDBOX](../references/PAYERS.md#markers): its screens are at `https://nhcxai.abdm.gov.in/uat/`, its API at `https://nhcxai.abdm.gov.in/api/provider`. It is the hospital the end-to-end tests ([T3. Eligibility Validation and Discovery Answered](../tests/T3-eligibility-answered.md) to [T18. Redelivery and Duplicates](../tests/T18-redelivery-ignored.md)) play, so every message this payer must handle arrives the way a real hospital sends it: built by an NHCX provider, encrypted for this payer's certificate, delivered by the exchange.

The driver is sandbox testing only. It lives with the tests (`tests/nhcx/e2e/provider/`, [T2. Test Runners](../tests/T2-test-runners.md)), never in the application, and is off in production. Nothing about the provider EMR is configured or asked for: it is signed in to by token login with this payer's own ABDM session token ([G3. Session Token](../gateway/G3-session-token.md)).

| Step | Call |
|---|---|
| Sign in | `POST /auth/token/login` `{"token": "<ABDM session token>"}`; the EMR opens an account for the token's client id and answers `{"token", "user"}` |
| Name the facility | `PUT /auth/participants` `{"participant_codes": ["<facility code>"]}`; the account sends as that facility from then on |
| The hospital's messages | the claim endpoints below, with `Authorization: Bearer <EMR token>` |

The provider skill's tests decide this payer's side through this payer's desk the same way, by token login ([A14. Disburse](A14-disburse.md) there), so the two harnesses mirror each other.

#### A18D. DESCRIPTION

One driver object per test run, holding the EMR token. Every action is reduced to one reply object (below), so a test reads `ok`, the ids the message went out under, and the EMR's own record, and never the EMR's raw JSON.

**Sign-in.** The token is proof of the client id: the EMR presents it to ABDM's `bridge-services`, and what comes back is the bridge the client id fronts. A token ABDM will not accept is refused with "ABDM rejected the session token (expired or not issued by ABDM)" (401); a forged or expired token draws a 500 "Unclassified Authentication Failure" from ABDM, which the EMR reads as the same refusal [SANDBOX](../references/PAYERS.md#markers). The EMR's token is kept for the run and dropped on the first 401.

**The facility.** The test's `NHCX_TEST_FACILITY` ([T1. Test Configuration](../tests/T1-test-configuration.md)) is the hospital participant code the EMR sends as. It is a code registered on the sandbox whose `endpoint_url` points at the EMR, so this payer's answers reach it. Its policy search and eligibility checks are addressed to this payer's participant code, `NHCX_TEST_PAYER`.

**The hospital's messages**, the EMR endpoints the driver calls, and what arrives here:

| Driver action | EMR call | Arrives as |
|---|---|---|
| `check(purpose, identifier, items)` | `POST /coverage-eligibility` `{"patient_id", "payer_code", "identifier_type", "identifier_value", "policy_code", "purpose", "preauth_id"}`; then `GET /coverage-eligibility/:txn` for the verdict | [C2. Coverage Eligibility Check](../callbacks/C2-coverage-eligibility-check.md) |
| `plan(policy_no)` | `POST /nhcx/insurance-plans` `{"payer_code", "policy_no", "refresh"}`; `GET /nhcx/insurance-plans/:id/packages` for the package master | [C3. Insurance Plan Request](../callbacks/C3-insurance-plan-request.md) |
| `preauth(dossier)` | `POST /preauths` (patient, admission, doctor, payer code, processor code, policy and member id, diagnosis, package, planned date, estimated stay, requested amount), then `POST /preauths/:id/submit` | [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md) |
| `enhancement(preauth_id, lines)` | `POST /preauths/:id/enhancement` `{"procedure_name", "package_code", "requested_amount", "doctor_id", "remarks"}` | [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md) (enhancement) |
| `answer_query_by_resubmit(preauth_id, reply)` | `POST /preauths/:id/submit` with `reply` (PMJAY query mode) [PAYER](../references/PAYERS.md#markers) | [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md) (resubmission) |
| `cancel(preauth_id, reason, note)` | `POST /preauths/:id/cancel` `{"reason", "note"}` | [C7. Task Submit](../callbacks/C7-task-submit.md) (cancel) |
| `status(preauth_id or claim_id)` | `POST /preauths/:id/status`, `POST /claims/:id/status` | [C8. Status Enquiry](../callbacks/C8-status-enquiry.md) |
| `predetermination(preauth_id)` | `POST /preauths/:id/predetermination` | [C6. Predetermination](../callbacks/C6-predetermination.md) |
| `claim(preauth_id, items, discharge)` | `POST /claims` (patient, admission, pre-auth, doctor, claim type, payer code, policy and member id, diagnosis, treatment period, items), then `POST /claims/:id/submit` | [C5. Claim Submit](../callbacks/C5-claim-submit.md) |
| `reprocess(claim_id, reason, reason_code)` | `POST /claims/:id/reprocess` `{"reason", "reason_code"}`; `reason_code` is `claimrejected`, `partialpayment` or `rejectiondisputed` | [C7. Task Submit](../callbacks/C7-task-submit.md) (reprocess) |
| `release(claim_id, amount, note)` | `POST /claims/:id/release` `{"amount", "note"}` | [C7. Task Submit](../callbacks/C7-task-submit.md) (release) |
| `reply(kind, id, req_id, text, attachments)` | `POST /preauths/:id/communications/:reqId/reply` or `POST /claims/:id/communications/:reqId/reply` `{"text", "attachments": [{"title", "content_type", "data"}]}` | [C9. Communication](../callbacks/C9-communication.md) |
| `payment_ack(claim_id)` | the EMR acknowledges a payment notice by itself on receipt; the driver reads `GET /claims/:id/nhcx` until the notice and its acknowledgement are on the claim's trail | [C11. Payment Acknowledgement](../callbacks/C11-payment-acknowledgement.md) |
| `payment_enquiry(claim_id)` | `POST /claims/:id/status` with stage `payment` [REF](../references/PAYERS.md#markers) | [C10. Payment Enquiry](../callbacks/C10-payment-enquiry.md) |

**Reading the EMR's side.** `GET /preauths/:id/nhcx`, `GET /claims/:id/nhcx` and `GET /coverage-eligibility/:txn/nhcx` list what the EMR sent and received on each leg, with correlation ids and ledger ids; the driver waits on them for this payer's answers to arrive, so a test proves the answer reached the hospital, not only that it left.

**Refusals the EMR makes**, passed through as the driver's error: "This request is already with the payer", "The payer has answered this request; raise a fresh one", "This claim is already with the payer", "The payer has answered this claim", "The payer has decided this claim; it goes back for another look as a reprocess request, not as a claim sent again", "That message is not a question: a notification is acknowledged and a note is read, neither takes an answer", "Only a notification is acknowledged; a query is answered from the communication tab".

Data: none written here. The driver reads this payer's side through [A15. Case Exchange Log](A15-case-exchange.md).

#### A18Q. REQUEST

Every call: `Content-Type: application/json`, `Accept: application/json`, `Authorization: Bearer <EMR token>` (the sign-in itself carries the ABDM session token in the body). Timeout 30 s [REF](../references/PAYERS.md#markers). The EMR runs behind a password gate on `Authorization` in some deployments; then the token goes on `X-Auth-Token` instead [SANDBOX](../references/PAYERS.md#markers).

Sign-in:

```json
{"token": "<ABDM session token minted for this payer's client id>"}
```

A pre-authorisation, the smallest dossier the EMR accepts and this payer files:

```json
{"patient_id": "<EMR patient>", "admission_id": "<EMR admission>", "doctor_id": "<EMR doctor>",
 "payer_code": "<payer code>", "processor_code": "<payer code>",
 "policy_no": "SANDBOX-DEFAULT-01", "member_id": "MBR-OK-0001",
 "treatment_type": "Surgical", "room_type": "General Ward",
 "diagnosis": "Primary osteoarthritis, knee", "diagnosis_code": "M17.1",
 "procedure_name": "Total Knee Replacement (Unilateral)", "package_code": "PROC-KNEE-01",
 "planned_at": "2026-10-02", "estimated_stay": 4, "requested_amount": 150000}
```

The member ids are the ones this payer seeds for its scenarios ([A19. Sandbox Scenarios](A19-sandbox-scenarios.md)): the driver submits under them to reach a known outcome.

#### A18S. RESPONSE

The driver reduces every EMR reply to one object:

| Key | Meaning |
|---|---|
| `ok` | the EMR accepted the action |
| `status` | HTTP status |
| `id` | the EMR's record id (pre-auth, claim, transaction), for the next call |
| `correlation_id`, `txn_id` | the ids the message went out under, from the EMR's send acknowledgement; what this payer's exchange log ([A15. Case Exchange Log](A15-case-exchange.md)) shows on the matching inbound row |
| `record` | the EMR's record as it answered it |
| `error` | the EMR's `error` text, when `ok` is false |
| `fields` | the EMR's per-field problems on a 422 |

```json
{"ok": true, "status": 202, "id": "PA-7UQ2P0AB",
 "correlation_id": "5b1f0c1e-7c8a-4c1b-9d3e-2f6a1d0e9b44", "txn_id": "7UPG002K",
 "record": {"id": "PA-7UQ2P0AB", "status": "submitted", "payer_code": "<payer code>"}}
```

Errors: the sign-in's refusal ("ABDM rejected the session token (expired or not issued by ABDM)"; "Signing in with a token needs an ABDM gateway and none is configured" when the EMR itself has none [SANDBOX](../references/PAYERS.md#markers)); the EMR unreachable, "`<url>` is unreachable, `<reason>`"; a 401 on any later call drops the kept token and fails the action with "The sandbox provider EMR refused the token; sign in again."

#### A18P. PSEUDOCODE

When: the CLI and GUI runners ([T2. Test Runners](../tests/T2-test-runners.md)) between their steps on this payer's desk. Never from the application.

```text
EMR = "https://nhcxai.abdm.gov.in/api/provider"          // fixed, not a setting [SANDBOX](../references/PAYERS.md#markers)

SIGN_IN(driver):
    if driver.token: return
    session = gateway.token()                                // G3: this payer's ABDM session token
    status, body = POST EMR/auth/token/login {"token": session}
    if status >= 300 or body.token blank:
        fail "The sandbox provider EMR refused the token sign-in (HTTP <status>): <error or first 200 characters>"
    driver.token = body.token
    status, body = PUT EMR/auth/participants {"participant_codes": [NHCX_TEST_FACILITY]} with Bearer driver.token
    if status >= 300: fail "The sandbox provider EMR would not send as <facility code> (HTTP <status>): <first 200 characters>"

CALL(driver, method, path, body):
    SIGN_IN(driver)
    status, data = method EMR/path body, Authorization: Bearer driver.token, timeout 30 s
    on unreachable: fail "<url> is unreachable, <reason>"
    if status == 401: driver.token = none; fail "The sandbox provider EMR refused the token; sign in again."
    return REDUCE(status, data)

REDUCE(status, data):
    ok = 200 <= status < 300
    return {ok, status, id: data.id, correlation_id: data.correlation_id or data.nhcx.correlation_id,
            txn_id: data.txn_id or data.nhcx.txn_id, record: data if ok,
            error: data.error if not ok, fields: data.fields if not ok}

PREAUTH(driver, dossier):
    r = CALL(POST /preauths dossier);           if not r.ok: return r
    return CALL(POST /preauths/<r.id>/submit {})

CLAIM(driver, preauth_id, items, discharge):
    r = CALL(POST /claims {preauth_id, items, treatment_from, treatment_to, claim_type: discharge, ...}); if not r.ok: return r
    return CALL(POST /claims/<r.id>/submit {})

REPLY(driver, kind, id, req_id, text, attachments):
    return CALL(POST /<kind>s/<id>/communications/<req_id>/reply {text, attachments})

WAIT_ANSWERED(driver, kind, id, want, seconds):           // the payer's answer reached the hospital
    until seconds elapse, every 5 s:
        trail = CALL(GET /<kind>s/<id>/nhcx).record
        if any inbound row of trail carries want (a ClaimResponse outcome, a Task status, a PaymentNotice):
            return that row
    fail "no <want> reached the hospital within <seconds> s; correlation <id>, ledger <ids>"
```

The tests pair every driver action with a read of this payer's side ([A15. Case Exchange Log](A15-case-exchange.md)) and, where a person decides, with the desk's decision service ([A13. Adjudicate](A13-adjudicate.md)) or disbursement ([A14. Disburse](A14-disburse.md)).

#### A18U. USED BY
- APIs: [A20. ABHA Create and Verify (ABDM M1)](A20-abha-m1.md)
- Gateway: [G1. Embedding](../gateway/G1-embedding.md), [G3. Session Token](../gateway/G3-session-token.md)
- Tests: [T1. Test Configuration](../tests/T1-test-configuration.md), [T2. Test Runners](../tests/T2-test-runners.md), [T3. Eligibility Validation and Discovery Answered](../tests/T3-eligibility-answered.md), [T4. Auth-requirements Ruling Answered](../tests/T4-auth-requirements-ruled.md), [T5. Insurance Plan Served](../tests/T5-insurance-plan-served.md), [T6. Pre-auth Received and Approved](../tests/T6-preauth-approved.md), [T7. Pre-auth Rejected](../tests/T7-preauth-rejected.md), [T8. Pre-auth Queried and Answered](../tests/T8-preauth-queried.md), [T9. Enhancement Received and Approved](../tests/T9-enhancement-approved.md), [T10. Pre-auth Cancelled](../tests/T10-preauth-cancelled.md), [T11. Predetermination Quoted](../tests/T11-predetermination-quoted.md), [T12. Claim Received and Approved](../tests/T12-claim-approved.md), [T13. LAMA and Death Claims](../tests/T13-claim-lama-death.md), [T14. Reprocess and Balance Release](../tests/T14-reprocess-and-release.md), [T15. Payment Notices and Acknowledgement](../tests/T15-payment-noticed.md), [T16. Payment Enquiry Answered](../tests/T16-payment-enquiry-answered.md), [T17. Status Enquiry Answered](../tests/T17-status-answered.md), [T18. Redelivery and Duplicates](../tests/T18-redelivery-ignored.md)
