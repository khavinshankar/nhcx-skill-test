# A15. Adjudicator Process Case

#### A15E. ENDPOINT

Outbound, application to the payer side. Takes one action on a case for the role holding it. The transports and how one is chosen (per payer adapter, see [PAYERS.md](../references/PAYERS.md)) [PAYER](../references/PAYERS.md#markers) are the same as A14 (the embedded gateway, [G](../gateway/INDEX.md), has no adjudicator relay, so the payer service is always called directly):

| Transport | Call | Chosen when |
|---|---|---|
| Payer service | `POST https://apisbeta.nha.gov.in/pmjay/hcx/nhcxpayerservice/wrapper/process/case` (the URL can be overridden per deployment), with a bearer token (configured, else the [G3. Session Token](../gateway/G3-session-token.md) through A16). This is a different host from the A14 role lookup, as the guide publishes it. | The leg's desk is `nhcx-payer-service`. |
| IRDAI payer desk | `POST https://nhcxai.abdm.gov.in/api/payer/cases/{id}/adjudicate` after the token sign-in and case lookup of A14 (fixed desk, no password) [SANDBOX](../references/PAYERS.md#markers) | The leg's desk is `irdai-payer`. |

A leg whose payer has no desk is refused with the same sentence as A14.

#### A15D. DESCRIPTION

A claim raises two legs, each its own exchange with its own correlation id, and each is adjudicated separately: the pre-authorisation (stage `preauth`) and the claim (stage `claim`). The correlation id is never asked for and never invented. It is read off the leg being decided.

Checks made before any HTTP call, each refused with its message:

| Check | Message |
|---|---|
| The leg was never sent | "That case was never sent from here." |
| The leg has no correlation id | "That leg has no correlation id, it never reached the gateway, so there is nothing to decide on." (no G7 send minted one) |
| No role given (payer service desk) | "Read who is holding the case before acting on it." |
| The role is not in the workflow | "`<role>` is not a role in the published workflow." |
| The action is not legal for that role | "`<role>` may take `<actions>`, not "`<action>`"." |
| IRDAI desk, action not approve, reject or query | "The IRDAI payer desk takes approve, reject or query, not "`<action>`"." |
| IRDAI desk, reject or query with no remarks | "Say why, the IRDAI payer refuses a rejection or a query that says nothing." |

The action is matched loosely against the role's legal actions (A14 table) and sent spelled the guide's way. For example CPD-Trust takes `cpdApprove`, not `Approve`. The payer service answers a wrong name with a generic failure that does not say which name it wanted [SANDBOX](../references/PAYERS.md#markers).

Every action taken, accepted or refused, is recorded against the claim. NHCX keeps no record of a decision taken outside the exchange, so this is the only trace.

Data: [D24. claim_adjudication](../database/D24-claim-adjudication.md).

**The role walk (cycle).** One decision (`approve`, `reject` or `query`) walks the case by itself through the PMJAY roles [PAYER](../references/PAYERS.md#markers). Each round reads the role afresh (A14), then takes that role's action for the decision:

| Role | approve | reject | query |
|---|---|---|---|
| PPD-Trust | `Approve` | `Reject` | `Query` |
| CEX-Trust | `Forward` | `Forward` | `Forward` |
| CPD-Trust | `cpdApprove` | `cpdReject` | `Pending` |
| Medical Audit Committee | `Approve` | `Reject` | `iQuery` |
| ACO-Trust | `Approve` | `Reject` | `Pending` |
| SHA-Trust | `Approve` | `Reject` | `Pending` |
| Claim Review Committee | `Approve` | `Reject` | `Pending` |

A pre-authorisation is decided in one step, at PPD-Trust. An approved claim walks CEX-Trust, CPD-Trust, Medical Audit Committee, ACO-Trust, SHA-Trust, then Claim Review Committee. CEX can only forward, so a rejection or a query goes through CEX first and is then taken once, at the role holding the case. A cycle runs at most 8 rounds (the seven steps plus one re-read). All actions in one run share a `cycle_id`. Nothing is retried. The run stops with one of these reasons:

| `stopped` | When |
|---|---|
| `completed` | The action was taken at Claim Review Committee, or at PPD-Trust on a pre-authorisation. |
| `decided` | A reject or query was taken at a role other than CEX-Trust. |
| `no-role` | The role came back blank: nobody holds the case any more. |
| `not-moved` | The same role came back twice in a row. Nothing is acted on twice. |
| `refused` | The last action was not accepted. |
| `role-unreadable` | The role lookup returned an error and no role. |
| `unknown-role` | The role is not in the published workflow. |
| `exhausted` | The round limit was reached. |

The cycle returns `{"cycle_id", "decision", "steps": [{"role", "action", "success", "error"}], "stopped", "final_role"}`. `completed`, `decided` and `no-role` are shown as success, the rest as failure. The flash reads "Cycle `<stopped>`: `<reason>`. Taken: `<action>` as `<role>`, ..." or "Nothing was taken."

A decision other than the three is refused with "Choose whether to approve, reject or query the case." A check above that fails part way through ends the run with its message in red, and no trail is shown.

On the IRDAI desk the cycle is one call: the decision word itself (`approve`, `reject`, `query`) is sent as the action, and `stopped` is `decided` when accepted, `refused` otherwise.

#### A15Q. REQUEST

**Payer service.** Direct HTTP call from the application, outside NHCX and outside G. Headers: `Content-Type: application/json`, `accept: application/json`, `Authorization: Bearer <token>`, `bearer_auth: Bearer <token>`. Timeout 30 s [REF](../references/PAYERS.md#markers).

| Field | Type | Required | Notes |
|---|---|---|---|
| `casenumber` | string | yes | The case number, as in A14. |
| `action` | string | yes | Legal action for the role, spelled as in the A14 table. |
| `receivercode` | string | yes | Payer code without the `@` suffix. |
| `usecase` | string | yes | The role's usecase literal: `PREAUTH`, `CLAIM`, `Medical Audit Committee` or `Claim Review Committee`. |
| `correlationid` | string | yes | The leg's `x-hcx-correlation_id`. |
| `sendercode` | string | yes | The facility's participant code without the `@` suffix. Blank when none is set. |
| `memberid` | string | yes | The claim's member id, or blank. |
| `remarks` | string | yes | Operator's remarks, trimmed. Sends `ok` when empty [REF](../references/PAYERS.md#markers). |

```json
{
  "casenumber": "1234567890123456",
  "action": "cpdApprove",
  "receivercode": "<payer code without @hcx>",
  "usecase": "CLAIM",
  "correlationid": "5b1f0c1e-7c8a-4c1b-9d3e-2f6a1d0e9b44",
  "sendercode": "<facility code without @hcx>",
  "memberid": "MD5SLS4X5",
  "remarks": "ok"
}
```

**IRDAI payer desk.** `Authorization: Bearer <desk token>`.

| Field | Type | Required | Notes |
|---|---|---|---|
| `action` | string | yes | `approve`, `reject` or `query`, lower case. |
| `remarks` | string | for reject and query | Trimmed, may be empty on approve. |

```json
{"action": "query", "remarks": "Discharge summary missing"}
```

**IRDAI payer desk, the payer's other acts (sandbox testing only).** The end-to-end tests ([T10. IRDAI Claim Approved, Part-approved and Rejected](../tests/T10-irdai-claim.md), [T11. IRDAI Payment Notice and Acknowledgement](../tests/T11-irdai-payment.md), [T12. IRDAI Reprocess and Balance Release](../tests/T12-irdai-reprocess-and-release.md)) also need the payer to decide a claim line by line and to pay. Both are the desk's own calls, on the same origin and token as above, made by the test's payer driver ([T2. Test Runners](../tests/T2-test-runners.md)) and never by the application [SANDBOX](../references/PAYERS.md#markers):

| Act | Call | Body |
|---|---|---|
| Decide one line | `PATCH https://nhcxai.abdm.gov.in/api/payer/cases/{id}/line-items/{lineId}` | `{"status", "approved_amount", "remarks", "query_remarks"}`; `status` is `approved`, `partially_approved`, `rejected` or `queried`; `approved_amount` is what the payer allows for the line; `query_remarks` only with `queried`. Decide the lines first, then take `approve` on the case: the case's approved amount is the sum of what the lines allow. |
| Raise a payment | `POST https://nhcxai.abdm.gov.in/api/payer/payments` | `{"case_id", "payment_amount", "mode", "beneficiary": {"name", "account_no", "ifsc"}, "utr_no"}`; `mode` for example `NEFT`; `tds_percent` optional (the desk's default applies when left out). With `utr_no` the payment is raised and completed in one step and the payment notice goes out at once; without it the payment waits as `initiated`. Answers 201 with the payment's `id`. |
| Complete a payment | `POST https://nhcxai.abdm.gov.in/api/payer/payments/{id}/complete` | `{"utr_no"}`: records the bank's reference and sends the payment notice ([C10. Payment Notice](../callbacks/C10-paymentnotice-request.md) at the provider). |

The case `{id}` and the line `{lineId}` are read off the case the A14 lookup returned (`id`, and each row of its `line_items`).

#### A15S. RESPONSE

The application reduces every transport to one reply:

| Key | Meaning |
|---|---|
| `success` | Payer service: HTTP 2xx and no error text in the body. IRDAI: HTTP 2xx. |
| `status` | HTTP status. |
| `action`, `role`, `usecase` | What was sent. On IRDAI, `role` is `Adjudicator` and `usecase` is the case's stage. |
| `correlationId` | The leg's correlation id. |
| `request` | The body sent (payer service). |
| `response` | The decoded reply body. |
| `raw` | The reply text when it was not JSON. |
| `error` | Set when not accepted. |
| `transport` | `nhcx-payer-service` or `irdai-payer`. |
| `cycle_id` | IRDAI only. |

A successful payer service reply seen from the service is `{"message": "processed"}` [SANDBOX](../references/PAYERS.md#markers). A bare `message` on a 2xx is not read as an error.

**Errors.**
- Payer service: the error text is, in order, an `errorMessage`, `error`, `errorDesc` or `errorDescription` in a 2xx body. On a non-2xx it is those or `message` (for example `{"errorMessage": "Invalid action"}`). Otherwise it is "the payer service returned `<status>`: `<first 200 characters>`". An unreachable host is refused with "`<url>` is unreachable, `<reason>`".
- No token: the A16 failure is the action's failure.
- IRDAI: `error` is the body's error text, else "HTTP `<status>`: `<first 200 characters>`".

A refused action is still recorded. The console redirects back to the case page and re-reads the role. It shows "Decision sent to the payer service." on success, or the error in red.

#### A15P. PSEUDOCODE

When: the operator submits "Take this action" (one PROCESS) or "Run the cycle" (CYCLE) on the adjudicator case page. The page then redirects back to the case with the role read again (A14).

Data: [D24. claim_adjudication](../database/D24-claim-adjudication.md) (written), [D18. claim_preauth](../database/D18-claim-preauth.md), [D20. claim_submission](../database/D20-claim-submission.md), [D9. claim](../database/D9-claim.md), [D1. organization](../database/D1-organization.md) (read).

```text
PROCESS(claim_id, stage, role, action, remarks, cycle_id = ""):
  leg = LEG(claim_id, stage)                      # A14P; legs without a correlation id do not exist
  if no leg: fail "That case was never sent from here."
  if leg.correlation_id blank: fail "That leg has no correlation id, it never reached the gateway, so there is nothing to decide on."
  if leg.desk == "irdai-payer": return IRDAI_PROCESS(leg, action, remarks, cycle_id)
  if leg.desk != "nhcx-payer-service": fail <no desk sentence, A14>
  role = trim(role)
  if blank: fail "Read who is holding the case before acting on it."
  step = workflow row matching role (loose match)
  if none: fail "<role> is not a role in the published workflow."
  spelled = the step's action matching action (loose match)
  if none: fail "<role> may take <step actions joined by ", ">, not \"<action>\"."

  sender = facility participant code up to the first "@", or ""
  remarks_sent = trim(remarks) or "ok"
  token = TOKEN()                                 # A16P (G3 Session Token)
  body = {casenumber: leg.case_number, action: spelled, receivercode: leg.payer_code,
          usecase: step.usecase, correlationid: leg.correlation_id, sendercode: sender,
          memberid: leg.member_id or "", remarks: remarks_sent}
  status, data, raw = POST process URL body, headers Authorization and bearer_auth = "Bearer " + token, timeout 30 s
  on unreachable: fail "<url> is unreachable, <reason>"
  service_error = EXTRACT_ERROR(data, not failed) when status < 300, else ""
  reply = {success: status < 300 and not service_error, status, action: spelled, role: step.role,
           usecase: step.usecase, correlationId: leg.correlation_id, request: body,
           response: data, raw: raw when data is not JSON, transport: "nhcx-payer-service"}
  if not success:
      reply.error = service_error or EXTRACT_ERROR(data, failed)
                    or "the payer service returned <status>: <first 200 characters of raw>"
  RECORD(claim_id, stage, leg, reply, remarks, reply.transport, cycle_id)
  return reply

RECORD(...):                                      # every action, accepted or refused
  insert claim_adjudication: claim_id, stage, case_number, role, action, usecase,
      correlation_id, remarks (trimmed, or null), success (1 or 0), http_status,
      response_json (the whole reply), desk (the transport), cycle_id (or null), taken_at = now

IRDAI_PROCESS(leg, action, remarks, cycle_id):
  action = lower(trim(action))
  if action not in (approve, reject, query):
      fail "The IRDAI payer desk takes approve, reject or query, not \"<action>\"."
  if action in (reject, query) and trim(remarks) blank:
      fail "Say why, the IRDAI payer refuses a rejection or a query that says nothing."
  found = the desk's case for leg.case_number (A14P IRDAI_ROLE lookup, same failures)
  status, data, raw = POST DESK/cases/{found.id}/adjudicate {"action": action, "remarks": trim(remarks)}
                      with Authorization: Bearer <desk token>
  reply = {success: status < 300, status, action, role: "Adjudicator", usecase: found.stage,
           correlationId: leg.correlation_id, response: data, raw, transport: "irdai-payer", cycle_id}
  if not success: reply.error = EXTRACT_ERROR(data, failed) or "HTTP <status>: <first 200 characters>"
  RECORD(..., desk "irdai-payer", cycle_id)
  return reply

CYCLE(claim_id, stage, decision, remarks):
  if decision not in (approve, reject, query): fail "Choose whether to approve, reject or query the case."
  leg = LEG(claim_id, stage); if none: fail "That case was never sent from here."
  if leg.desk == "irdai-payer":
      reply = IRDAI_PROCESS(leg, decision, remarks, new uuid)
      return {cycle_id: reply.cycle_id, decision, steps: [{role, action: decision, success, error}],
              stopped: "decided" if reply.success else "refused", final_role: null}
  if leg.desk != "nhcx-payer-service": fail <no desk sentence, A14>

  cycle_id = new uuid; steps = []; seen = []; stopped = "exhausted"; final_role = null
  repeat at most 8 times:                          # 7 workflow steps + 1 re-read
      lookup = ROLE_FOR(leg.case_number, leg.payer_code, claim_id)   # A14P; a failure ends the run
      role = trim(lookup.role); final_role = role or null
      if lookup.error and not role:
          steps += {role: null, action: null, success: false, error: lookup.error}
          stopped = "role-unreadable"; stop
      if not role: stopped = "no-role"; stop
      if role not in the workflow:
          steps += {role, action: null, success: false, error: lookup.warning}
          stopped = "unknown-role"; stop
      if seen not empty and last of seen matches role: stopped = "not-moved"; stop
      append role to seen
      action = the decision's action for role (table in A15D)
      reply = PROCESS(claim_id, stage, role, action, remarks, cycle_id)  # a failed check ends the run
      steps += {role: reply.role or role, action: reply.action or action,
                success: reply.success, error: reply.error}
      if not reply.success: stopped = "refused"; stop
      if decision != "approve" and role is not CEX-Trust: stopped = "decided"; stop
      if role is Claim Review Committee, or stage == "preauth" and role is PPD-Trust:
          stopped = "completed"; stop
  return {cycle_id, decision, steps, stopped, final_role}

Screen after CYCLE:
  taken = "<action> as <role>" for each step with an action, joined by ", "
  flash "Cycle <stopped>: <reason>." + (" Taken: <taken>." or " Nothing was taken.")
        reasons: completed "the case went through every role"; decided "the decision was taken at the role holding it";
                 no-role "nobody holds the case any more"; not-moved "the payer service kept the case at the same role";
                 refused "the payer service refused the last action"; role-unreadable "the role could not be read";
                 unknown-role "the role holding it is not in the published workflow"; exhausted "the step limit was reached"
  green for completed, decided, no-role; red otherwise
  any failure raised during the run: its message in red, no trail
Screen after PROCESS:
  success: "Decision sent to the payer service." (green); else reply.error or "The payer service refused it." (red)
```

#### A15U. USED BY
- APIs: [A14. Adjudicator User Role](A14-adjudicator-user-role.md), [A16. Gateway Token](A16-gateway-token.md)
- Database: [D1. organization](../database/D1-organization.md), [D24. claim_adjudication](../database/D24-claim-adjudication.md)
- Tests: [T2. Test Runners](../tests/T2-test-runners.md), [T5. IRDAI Pre-authorisation Approved](../tests/T5-irdai-preauth-approved.md), [T6. IRDAI Pre-authorisation Rejected and Sent Again](../tests/T6-irdai-preauth-rejected.md), [T7. IRDAI Query Answered](../tests/T7-irdai-query-answered.md), [T8. IRDAI Enhancement](../tests/T8-irdai-enhancement.md), [T9. IRDAI Status Enquiry and Cancel](../tests/T9-irdai-cancel-and-status.md), [T10. IRDAI Claim Approved, Part-approved and Rejected](../tests/T10-irdai-claim.md), [T11. IRDAI Payment Notice and Acknowledgement](../tests/T11-irdai-payment.md), [T12. IRDAI Reprocess and Balance Release](../tests/T12-irdai-reprocess-and-release.md), [T14. PMJAY Pre-authorisation Through the Payer Service](../tests/T14-pmjay-preauth-adjudicated.md), [T15. PMJAY Query Answered by Resubmission](../tests/T15-pmjay-query-by-resubmission.md), [T16. PMJAY Rejection and Enhancement](../tests/T16-pmjay-rejection-and-enhancement.md), [T17. PMJAY Claim Through the Role Walk](../tests/T17-pmjay-claim-adjudicated.md)
