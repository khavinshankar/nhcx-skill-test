# A14. Adjudicator User Role

#### A14E. ENDPOINT

Outbound, application to the payer side. Asks which role is holding a case in the payer's adjudication workflow. There are two transports. Which one is used depends on the payer's adapter (`desk`, see [PAYERS.md](../references/PAYERS.md)) [PAYER](../references/PAYERS.md#markers). The embedded gateway, [G](../gateway/INDEX.md), has no adjudicator relay, so the payer service is always called directly.

| Transport | Call | Chosen when |
|---|---|---|
| Payer service | `POST https://apisbx.abdm.gov.in/pmjay/sbxhcx/nhcxpayerservice/v1/get/user-role` (the URL can be overridden per deployment), with a bearer token (a configured payer service token, else the [G3. Session Token](../gateway/G3-session-token.md) through A16) | The desk is `nhcx-payer-service`. |
| IRDAI payer desk | Token login, `POST https://nhcxai.abdm.gov.in/api/payer/auth/token/login`, then `GET https://nhcxai.abdm.gov.in/api/payer/cases?search=<case number>`. The desk is fixed, not a setting: its screens are at `https://nhcxai.abdm.gov.in/uat/`, its API at `/api/payer` on the same origin [SANDBOX](../references/PAYERS.md#markers) | The desk is `irdai-payer`. |

A payer whose adapter has no desk is refused before any call with "`<payer name>` has no adjudication desk this EMR can drive; the decision is taken on the payer's own console." A blank case number is refused with "A case number is needed to read who is holding it."

#### A14D. DESCRIPTION

On PMJAY the decision on a pre-authorisation or a claim is taken in the NHCX Payer Service, outside the exchange [PAYER](../references/PAYERS.md#markers). A case sits at exactly one step, and only the role holding it may act. So the role is always read first, and the actions offered are that role's only. The lookup is a live call. It is made only when the operator asks ("Read the current role"), and before every action of a cycle (see A15), never on a plain page view.

The case number sent is the number the payer knows the leg by:

- For the `nhcx-payer-service` desk: the last `/`-separated segment of the pre-authorisation's payer reference (for example the 16 digits at the end of `PMJAY/HP/S/2024/R2/<16 digits>`), or the whole reference when it has no `/` [PAYER](../references/PAYERS.md#markers). The claim leg uses the same number, since the scheme keeps one case per episode [PAYER](../references/PAYERS.md#markers).
- For the `irdai-payer` desk: the payer's own reference for the case, which comes back on the payer's first reply to the leg (the case number in the ClaimResponse, kept as the leg's payer reference, for example `CL/26/0T00000VS`) [SANDBOX](../references/PAYERS.md#markers). Until the first reply has arrived there is no payer reference yet, and the claim number the leg went out under (`claim_ref`, else the claim's current number) is sent instead; the desk lists a freshly filed case under that number until it answers.

The payer code is the payer's participant code with everything from `@` removed (the numeric part of `<payer code>`) [PAYER](../references/PAYERS.md#markers).

#### A14Q. REQUEST

**Payer service.** Direct HTTP call from the application, outside NHCX and outside G. Headers: `Content-Type: application/json`, `accept: application/json`, `Authorization: Bearer <token>` and `bearer_auth: Bearer <token>` (the same token in both). Timeout 30 s [REF](../references/PAYERS.md#markers).

| Field | Type | Required | Notes |
|---|---|---|---|
| `caseid` | string | yes | The case number, as above. |
| `payerid` | string | yes | Payer code without the `@` suffix. |

```json
{"caseid": "1234567890123456", "payerid": "<payer code without @hcx>"}
```

**IRDAI payer desk.** Token login only: no username, no password, no desk account to configure. Sign in with `POST https://nhcxai.abdm.gov.in/api/payer/auth/token/login` `{"token": "<ABDM session token>"}`, the facility's own session token ([G3. Session Token](../gateway/G3-session-token.md) through A16). The desk opens an account for the token's client id and answers `{"token", "user"}`; its `token` is kept for later calls. Then say which payer this account works, so the desk shows that payer's cases: `PUT https://nhcxai.abdm.gov.in/api/payer/auth/participants` `{"participant_codes": ["<payer code>"]}`, once per sign-in (a client id sees no case until it names the participant it works) [SANDBOX](../references/PAYERS.md#markers). Then `GET https://nhcxai.abdm.gov.in/api/payer/cases?search=<case number>` with `Authorization: Bearer <token>`. The case is the row whose `claim_no` equals the case number.

#### A14S. RESPONSE

The application reduces every transport to one reply object:

| Key | Meaning |
|---|---|
| `role` | The role holding the case, or blank. |
| `step` | The published workflow step for that role (`step`, `stage`, `role`, `actions`, `usecase`), present only when the role is one of the seven below. |
| `warning` | Set when the role is not in the workflow ("`<role>` is not a role in the published workflow, read the raw response before acting."), or when no role came back and there is no error ("the payer service returned no role field this EMR recognises, read the raw response."). |
| `error` | The payer service's own error text, when there is one. |
| `response` | The decoded reply body, shown raw on the screen. |
| `raw` | The reply text when it was not JSON (payer service only). |
| `status` | HTTP status. |
| `caseNumber`, `payerCode` | What was asked (payer service; `caseNumber` on IRDAI). |
| `transport` | Which transport answered: `nhcx-payer-service` or `irdai-payer`. |

**Reading the role (payer service).** The published guide does not show the reply, and the sandbox has used more than one field name [SANDBOX](../references/PAYERS.md#markers). The role is found by comparing keys with case and punctuation ignored, in this order: `currentUserRole`, `currentRole`, `userRole`, `currentRoleName`, `assignedRole`, `roleName`, `role`. Then any string field whose name contains "role". Then the same search inside `data`, `result`, `response` or `payload`. A list reply is read from its first element. Example replies: `{"currentUserRole": "CPD-Trust"}`, `{"data": {"rolename": "SHA-Trust"}}`, `[{"userRole": "ACO-Trust"}]`. An empty role (`{"currentUserRole": ""}`) means nobody holds the case any more.

**Errors.**
- Payer service, non-2xx: `error` is "the payer service returned `<status>`: `<text>`". The text is the body's `errorMessage`, `error`, `errorDesc`, `errorDescription` or `message` (the first found), else the first 200 characters of the body.
- Payer service, 2xx: an `errorMessage`, `error`, `errorDesc` or `errorDescription` in the body is still set as `error`. A bare `message` on a 2xx is not an error, because the service says "processed" in that field when it succeeds [SANDBOX](../references/PAYERS.md#markers).
- Payer service host unreachable: refused with "`<url>` is unreachable, `<reason>`".
- No token: the A16 failure is the lookup's failure.
- IRDAI: a failed sign-in gives "The IRDAI payer desk refused the sign-in (HTTP `<status>`): ...". A failed case list gives "The IRDAI payer desk could not list cases (HTTP `<status>`): ...", and the kept sign-in token is dropped. No matching row gives "The IRDAI payer holds no case under `<case number>`."

**Legal actions by role.** The role decides which actions A15 may send; the roles and actions below are the PMJAY workflow's [PAYER](../references/PAYERS.md#markers). Names are matched loosely (`ppd-trust` and `CPD Trust` both match), but the action is always sent spelled as below.

| Step | Stage | Role | Legal actions | `usecase` sent in A15 |
|---|---|---|---|---|
| 0 | PREAUTH | PPD-Trust | `Approve`, `Reject`, `Query` | `PREAUTH` |
| 1 | CLAIM | CEX-Trust | `Forward` | `CLAIM` |
| 2 | CLAIM | CPD-Trust | `cpdApprove`, `cpdReject`, `Pending` | `CLAIM` |
| 3 | CLAIM | Medical Audit Committee | `Approve`, `Reject`, `iQuery` | `Medical Audit Committee` |
| 4 | CLAIM | ACO-Trust | `Approve`, `Reject`, `Pending` | `CLAIM` |
| 5 | CLAIM | SHA-Trust | `Approve`, `Reject`, `Pending` | `CLAIM` |
| 6 | CLAIM | Claim Review Committee | `Approve`, `Reject`, `Pending` | `Claim Review Committee` |

A role outside this table gets no actions. The screen says "`<role>` is not a role in the published workflow, so no action can be offered for it."

**IRDAI desk reply.** Always `role: "Adjudicator"`, `status: 200` [REF](../references/PAYERS.md#markers). The `step` is `{"stage": "<case stage in upper case, or CASE>", "usecase": "<case stage>", "role": "Adjudicator", "actions": ["approve", "reject", "query"]}`. The `response` is `{"id", "stage", "adjudication"}` taken from the matched case.

```json
{
  "caseNumber": "1234567890123456",
  "payerCode": "<payer code without @hcx>",
  "status": 200,
  "response": {"currentuserrole": "CPD-Trust"},
  "raw": null,
  "transport": "nhcx-payer-service",
  "role": "CPD-Trust",
  "step": {"step": 2, "stage": "CLAIM", "role": "CPD-Trust",
           "actions": ["cpdApprove", "cpdReject", "Pending"], "usecase": "CLAIM"}
}
```

#### A14P. PSEUDOCODE

When: the operator presses "Read the current role" or "Read again" on the adjudicator case page, and at the start of every round of a cycle (A15P). Never on a plain page view. Nothing is written to the database.

Data: [D9. claim](../database/D9-claim.md), [D18. claim_preauth](../database/D18-claim-preauth.md), [D20. claim_submission](../database/D20-claim-submission.md), [D1. organization](../database/D1-organization.md).

```text
LEG(claim_id, stage):                             # stage "preauth" -> claim_preauth, "claim" -> claim_submission
  only legs whose correlation_id is not blank exist
  case_number = leg.claim_ref or claim.claim_no
  if the payer adapter's desk == "nhcx-payer-service":
      reference = claim_preauth.preauth_ref for the claim
      if reference contains "/": case_number = part after the last "/"
      else if reference: case_number = reference
  payer_code = (claim.payer_id or the default payer code) up to the first "@"

ROLE_FOR(case_number, payer_code, claim_id):
  case_number = trim(case_number)
  if blank: fail "A case number is needed to read who is holding it."
  payer_code = (payer_code or the default payer code) up to the first "@"
  desk = payer adapter desk for the claim
  if desk == "irdai-payer": return IRDAI_ROLE(case_number)
  if desk != "nhcx-payer-service":
      fail "<payer name> has no adjudication desk this EMR can drive; the decision is taken on the payer's own console."

  token = TOKEN()                                 # A16P (G3 Session Token); its failure is the lookup's failure
  status, data, raw = POST role URL {"caseid": case_number, "payerid": payer_code}
                      headers Authorization and bearer_auth = "Bearer " + token, timeout 30 s
  on unreachable: fail "<url> is unreachable, <reason>"
  reply = {caseNumber, payerCode, status, response: data,
           raw: raw when data is not JSON, transport: "nhcx-payer-service"}
  if status >= 300:
      reply.error = "the payer service returned <status>: " + (EXTRACT_ERROR(data, failed) or first 200 characters of raw)
  else:
      reply.role = EXTRACT_ROLE(data)
      if EXTRACT_ERROR(data, not failed): reply.error = it

  role = trim(reply.role)
  if role and role matches a workflow row (loose match): reply.step = that row
  else if role: reply.warning = "<role> is not a role in the published workflow, read the raw response before acting."
  else if no reply.error: reply.warning = "the payer service returned no role field this EMR recognises, read the raw response."
  return reply

EXTRACT_ROLE(payload):
  list -> EXTRACT_ROLE(first element), or "" when empty
  not an object -> ""
  keys compared lower case with non-alphanumerics removed; only non-blank string values
  first found of: currentuserrole, currentrole, userrole, currentrolename, assignedrole, rolename, role
  else first key containing "role"
  else EXTRACT_ROLE of data, result, response, payload (first non-blank)
  else ""

EXTRACT_ERROR(payload, failed):
  keys (compared as above): errormessage, error, errordesc, errordescription, plus message when failed
  first non-blank string value found, trimmed; else ""

IRDAI_ROLE(case_number):
  DESK = "https://nhcxai.abdm.gov.in/api/payer"      // fixed, not a setting
  token = kept desk token, else:
      session = gateway.token()                           // G3, the facility's ABDM session token
      POST DESK/auth/token/login {"token": session}
      status >= 300 or no token: fail "The IRDAI payer desk refused the token sign-in (HTTP <status>): <error or first 200 characters>"
      keep token
      PUT DESK/auth/participants {"participant_codes": [payer code]} with Authorization: Bearer token
      status >= 300: fail "The IRDAI payer desk would not show <payer code>'s cases (HTTP <status>): <first 200 characters>"
  status, data = GET DESK/cases?search=<case_number> with Authorization: Bearer token
  if status >= 300: drop kept token; fail "The IRDAI payer desk could not list cases (HTTP <status>): <first 200 characters>"
  rows = data.items (the desk answers {"items": [...], "total": n}), or data when it is a list
  found = first row with claim_no == case_number
          else fail "The IRDAI payer holds no case under <case_number>."
  return {caseNumber, status: 200, transport: "irdai-payer", role: "Adjudicator",
          step: {stage: upper(found.stage) or "CASE", usecase: found.stage, role: "Adjudicator",
                 actions: ["approve", "reject", "query"]},
          response: {id: found.id, stage: found.stage, adjudication: found.adjudication}}

Screen: any failure above is shown as the lookup's error; the legal actions offered are reply.step.actions.
```

#### A14U. USED BY
- APIs: [A15. Adjudicator Process Case](A15-adjudicator-process-case.md), [A16. Gateway Token](A16-gateway-token.md), [A17. Claim State](A17-claim-state.md)
- Database: [D24. claim_adjudication](../database/D24-claim-adjudication.md)
- Tests: [T1. Test Configuration](../tests/T1-test-configuration.md), [T2. Test Runners](../tests/T2-test-runners.md), [T5. IRDAI Pre-authorisation Approved](../tests/T5-irdai-preauth-approved.md), [T6. IRDAI Pre-authorisation Rejected and Sent Again](../tests/T6-irdai-preauth-rejected.md), [T7. IRDAI Query Answered](../tests/T7-irdai-query-answered.md), [T8. IRDAI Enhancement](../tests/T8-irdai-enhancement.md), [T9. IRDAI Status Enquiry and Cancel](../tests/T9-irdai-cancel-and-status.md), [T10. IRDAI Claim Approved, Part-approved and Rejected](../tests/T10-irdai-claim.md), [T12. IRDAI Reprocess and Balance Release](../tests/T12-irdai-reprocess-and-release.md), [T14. PMJAY Pre-authorisation Through the Payer Service](../tests/T14-pmjay-preauth-adjudicated.md), [T15. PMJAY Query Answered by Resubmission](../tests/T15-pmjay-query-by-resubmission.md), [T16. PMJAY Rejection and Enhancement](../tests/T16-pmjay-rejection-and-enhancement.md), [T17. PMJAY Claim Through the Role Walk](../tests/T17-pmjay-claim-adjudicated.md), [T18. PMJAY Payment Notice, Status Refusal and Cancel](../tests/T18-pmjay-payment-status-cancel.md)
