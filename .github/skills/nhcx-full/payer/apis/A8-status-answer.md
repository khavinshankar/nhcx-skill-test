# A8. Status Answer

#### A8E. ENDPOINT
In-process, one of two paths through [G7. Send](../gateway/G7-send.md), chosen by where the ask arrived:

| The ask arrived on | Answer path | Why |
|---|---|---|
| `v1/status` (the HCX shape: no bundle, `x-hcx-status_filters` in the headers) | `gateway.send("v1/on_status", envelope)` | NHCX closes a thread with the callback that pairs with the route that opened it |
| `v1/task/submit` with a Task coded `status` (the NHCX shape) | `gateway.send("v1/task/on_submit", envelope)` | the sandbox refuses `v1/status` outright (NHCX-1012) and makes hospitals send status as a Task [SANDBOX](../references/PAYERS.md#markers) |

No answer to it is awaited. It answers [C8. Status Enquiry](../callbacks/C8-status-enquiry.md). On the hospital's side both land in its enquiry callback, which reads the `x-hcx-status_response` header and the Task.

#### A8D. DESCRIPTION
Sent at once, inside the callback. A hospital that has heard nothing asks where its submission stands; the case is found and its stage and outcome go back two ways: as the `x-hcx-status_response` protected header, which is what the protocol reads, and as a Task bundle saying the same, which is what a FHIR reader expects.

**Finding the case** ([C8. Status Enquiry](../callbacks/C8-status-enquiry.md)): by the correlation id the ask names (`x-hcx-status_filters`, or a Task input `correlationId`) against the pre-authorisation, claim and query threads of [D19. case](../database/D19-case.md); then by the workflow id the ask names, and the envelope's own workflow id, the same way (a hospital that sends the leg's correlation id as the workflow id is answered [REF](../references/PAYERS.md#markers)); then by the claim number the Task names among that sender's cases.

**What is answered.**

Found: the Task `completed`, coded `approve`, its output pointing at a ClaimResponse that states the case (outcome and status as the leg stands, totals benefit and submitted), the description "`<Stage>` `<adjudication status>`: `<remarks>`" in the forms below, and beside them the Patient, both Organizations and the Coverage. The header:

```json
{"entity_type": "preauth" | "claim",
 "correlation_id": "<the thread asked about, else the ask's own>",
 "entity_status": "<claim status>", "claim_no": "<case number>", "stage": "<stage>",
 "outcome": "<adjudication status>", "total_claimed": 0, "total_approved": 0, "total_paid": 0,
 "answered": true}
```

`entity_status` is one code for where the case stands: `preauth-pending`, `preauth-approved`, `preauth-queried`, `preauth-rejected`, `claim-pending`, `claim-approved`, `claim-queried`, `claim-rejected`, `payment-pending`, `payment-partial`, `settled`, `rejected`, `cancelled`. `answered` is whether a verdict has gone out on either thread. `entity_type` is `preauth` at stage `preauth`, `claim` from the claim on.

Descriptions by stage: "Pre-authorisation `<status>`", "Claim `<status>`", "Approved for `<INR approved>`; `<INR paid>` paid so far", "Settled: `<INR paid>` paid", "Rejected", "Withdrawn", each followed by ": `<remarks>`" when the adjudicator wrote any.

Not found: the Task `rejected`, coded `reject`, description "No submission on that thread is on record with this payer.", no ClaimResponse, and the header `entity_status` `not-found`. A thread this payer does not hold is answered too: "not found" is where it stands.

**Headers set by the application.** As every answer ([A1. Eligibility Answer](A1-eligibility-answer.md)): sender and recipient swapped, the ask's correlation id verbatim, its workflow id echoed, `x-hcx-status` `response.complete`, plus `x-hcx-status_response` as a JSON object (a header G7 passes through as it is, [G5. Protocol Headers](../gateway/G5-protocol-headers.md)). No scheme table [PAYER](../references/PAYERS.md#markers).

**Checks before sending.** None of its own.

#### A8Q. REQUEST

The arguments passed to G7 Send:

| Field | Type | Notes |
|---|---|---|
| `jwe_headers` | object | Sender, recipient, correlation id, workflow id, status, and `x-hcx-status_response` as an object |
| `fhir` | Bundle | The Task answer bundle |

FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F10. Task (claim actions and answers)](../fhir/F10-task-claim-actions.md) (the completed or rejected Task; the ClaimResponse on its output, [F9. ClaimResponse](../fhir/F9-claimresponse.md)), [F15. Patient](../fhir/F15-patient.md), [F17. Organization](../fhir/F17-organization.md), [F18. Coverage](../fhir/F18-coverage.md)

Envelope, a claim approved and part paid, asked on the task route:

```json
{
  "jwe_headers": {"x-hcx-sender_code": "<payer code>",
                  "x-hcx-recipient_code": "<facility code>",
                  "x-hcx-correlation_id": "9c1d2e3f-4a5b-4c6d-8e7f-0a1b2c3d4e5f",
                  "x-hcx-workflow_id": "13",
                  "x-hcx-status": "response.complete",
                  "x-hcx-status_response": {"entity_type": "claim", "correlation_id": "0b398fdf-...",
                                            "entity_status": "payment-partial", "claim_no": "CL/26/0SE0000V9",
                                            "stage": "payment", "outcome": "approved",
                                            "total_claimed": 118000, "total_approved": 118000,
                                            "total_paid": 60000, "answered": true}},
  "fhir": <F1 Bundle: F10 Task (completed, approve, output include ClaimResponse), F9 ClaimResponse (use claim, outcome complete, status approved), F15 Patient, F17 Organizations, F18 Coverage>
}
```

#### A8S. RESPONSE

**Acknowledgement:** the G7 result.

Recorded:
- [D31. audit_log](../database/D31-audit-log.md) audit `status.answered`, entity `nhcx_txn`: "`<hospital>` asked, correlation `<id>`, status `<entity_status>`, case `<id>`, answer txn `<txn_id>`".
- When found, [D27. case_exchange_message](../database/D27-case-exchange-message.md) two exchange messages: `in`, kind `status`, "Status enquiry about `<claim ref, correlation or case number>`" with the ask's bundle (or its filters when it had none); `out`, kind `status`, "Status: `<entity_status>`, `<description>`" with the header object and the bundle.
- Nothing on the case: a status enquiry changes nothing.

The callback answers the gateway `{"status": "answered", "entity_status", "case_id", "txn_id"}`.

**Failed send.** As [A1. Eligibility Answer](A1-eligibility-answer.md): `rejected` on a refusal, `error` so NHCX redelivers when the gateway was unreachable.

Data: [D19. case](../database/D19-case.md), [D27. case_exchange_message](../database/D27-case-exchange-message.md), [D31. audit_log](../database/D31-audit-log.md), [D1. payer](../database/D1-payer.md)

Reply: none.

#### A8P. PSEUDOCODE

```
function answer_status(in, task, arrived_on):       // called by C8; task is the parsed ask (F10 or the filters)
    case = find_case_for_status(in, task)            // C8: correlation, workflow, then claim number
    answer = {payer: in.payer, payer code: in.recipient, code: "status", status: "completed",
              claim_ref: task.claim_ref or task.correlation_ref, recipient: in.sender}
    header = {entity_type: "claim", correlation_id: task.correlation_ref or in.correlation_id}
    if case:
        answer.case = case; answer.cover = cover(case)                     // A3 cover
        answer.claim_status = claim_status_of(case)
        answer.description = describe_status(case)
        header += {entity_type: entity_type_of(case), entity_status: answer.claim_status,
                   claim_no: case.claim_no, stage: case.stage, outcome: case.adjudication_status,
                   total_claimed, total_approved, total_paid,
                   answered: case.nhcx_answer_txn_id set or case.nhcx_claim_answer_txn_id set}
    else:
        answer.status = "rejected"; answer.claim_status = "not-found"
        answer.description = "No submission on that thread is on record with this payer."
        header.entity_status = "not-found"
        log "status enquiry from <sender> matched no case (correlation <corr>, asked about <refs>)"
    bundle = F10 Task answer bundle(answer)
    path = "v1/task/on_submit" if arrived_on names the task route (or the delivery type is task)
           else "v1/on_status"
    headers = ANSWER_HEADERS(in) + {x-hcx-status_response: header}        // A1
    ack = SEND(path, {jwe_headers: headers, fhir: bundle}, case)
        on Refused r:     return rejected("The gateway refused the answer: " + r.message)
        on Unreachable u: return error("The gateway could not queue the answer")
    INSERT D31 audit {action: "status.answered", entity_type: "nhcx_txn", entity_id: in.txn_id,
                      detail: "<sender> asked, correlation <corr>, status <claim_status>[, case <id>], answer txn " + ack.txn_id}
    if case:
        INSERT D27 {case_id, direction: in, kind: status, correlation_id: in.correlation_id, txn_id: in.txn_id,
                    counterparty: in.sender, summary: "Status enquiry about <ref>", payload: in.fhir or {x-hcx-status_filters}}
        INSERT D27 {case_id, direction: out, kind: status, correlation_id: in.correlation_id, txn_id: ack.txn_id,
                    counterparty: in.sender, summary: "Status: <claim_status>, <description>",
                    payload: {x-hcx-status_response: header, fhir: bundle}}
    return settled {status: "answered", entity_status: answer.claim_status, case_id: case.id or "", txn_id: ack.txn_id}

function claim_status_of(case):
    if case.stage in {preauth, claim}: return case.stage + "-" + case.adjudication_status
    if case.stage == payment: return "payment-partial" if 0 < total_paid < total_approved else "payment-pending"
    return case.stage                                    // settled, rejected, cancelled

function entity_type_of(case):
    if case.stage == preauth: return "preauth"
    if case.stage in {claim, payment, settled}: return "claim"
    return "claim" if case.nhcx_claim_correlation_id set else "preauth"

function describe_status(case):
    preauth:  "Pre-authorisation " + status + remarks
    claim:    "Claim " + status + remarks
    payment:  "Approved for <INR approved>; <INR paid> paid so far"
    settled:  "Settled: <INR paid> paid"
    rejected: "Rejected" + remarks;  cancelled: "Withdrawn" + remarks
    where remarks = ": " + adjudication_remarks when set
```

#### A8U. USED BY
- APIs: [A9. Task Answer](A9-task-answer.md)
- Callbacks: [C8. Status Enquiry](../callbacks/C8-status-enquiry.md)
- FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F10. Task (claim actions and answers)](../fhir/F10-task-claim-actions.md)
- Database: [D27. case_exchange_message](../database/D27-case-exchange-message.md), [D31. audit_log](../database/D31-audit-log.md)
- Tests: [T17. Status Enquiry Answered](../tests/T17-status-answered.md)
