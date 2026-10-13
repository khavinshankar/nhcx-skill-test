# A9. Task Answer

#### A9E. ENDPOINT
In-process: `gateway.send("v1/task/on_submit", envelope)`, [G7. Send](../gateway/G7-send.md), which encrypts it and posts it to NHCX for the hospital, on the thread the hospital's Task arrived on: `POST {nhcx}/v1/task/on_submit`. No answer to it is awaited.

It answers [C7. Task Submit](../callbacks/C7-task-submit.md): a cancel, a reprocess, a balance release. A status Task is answered by [A8. Status Answer](A8-status-answer.md) on the same route; a payment acknowledgement Task ([C11. Payment Acknowledgement](../callbacks/C11-payment-acknowledgement.md)) needs no answer. On the hospital's side the cancel answer settles its cancel leg and the reprocess answers settle its enquiry rows.

#### A9D. DESCRIPTION
A Task is a hospital asking for something short of a submission, and the answer is a Task in the shape PMJAY sends back: coded `approve` when this payer did what was asked and `reject` when it could not, its output an `include` pointing at a ClaimResponse that says where the case now stands, with the Patient, both Organizations and the Coverage beside it ([F10. Task (claim actions and answers)](../fhir/F10-task-claim-actions.md)) [PAYER](../references/PAYERS.md#markers).

**Three Tasks, four sends.**

| Task | When answered | Task status | Workflow id | `x-hcx-status` | Description |
|---|---|---|---|---|---|
| `cancel`, done | at once, after [C7. Task Submit](../callbacks/C7-task-submit.md) withdrew the case | `completed` | PC02 | `response.complete` | "Pre-authorisation withdrawn by `<hospital>`: `<reason>`" |
| `cancel`, refused (the case is closed) | at once | `rejected` | PC02 | `response.complete` | "`<case number>` is `<stage>` and cannot be withdrawn." |
| `reprocess` or `release`, taken in | at once, after C7 reopened the claim | `accepted` | 37 | `response.partial` | "Claim reopened for reprocessing (round `<n>`) at the request of `<hospital>`: `<reason>`" |
| `reprocess` or `release`, refused | at once | `rejected` | 37 | `response.complete` | "`<case number>` is still open, there is nothing to reopen." or "`<case number>` has been paid and cannot be reprocessed." |
| `reprocess` or `release`, decided | when the adjudicator decides the reopened claim ([A13. Adjudicate](A13-adjudicate.md)) | `completed` | 252 approved, 253 rejected | `response.complete` | "Claim `<number>` reprocessed: `<status>`, `<INR approved>` approved of `<INR claimed>` claimed. `<remarks>`" |
| any of the three, no such claim | at once | `rejected` | PC02 or 37 | `response.complete` | "No claim numbered `<ref>` is on record with this payer." (no case, so no ClaimResponse, Patient or Coverage) |

**`accepted` is `response.partial`** [REF](../references/PAYERS.md#markers). NHA's workflow sheet pairs 37 with `response.complete` only ([PAYERS.md](../references/PAYERS.md)); the reference departs from it on purpose. It is not an answer to what was asked: it says the request is in and queued for a person. The exchange closes a thread on `response.complete` and refuses whatever follows, so an acknowledgement sent as complete would leave the decision with no thread to travel on [SANDBOX](../references/PAYERS.md#markers). Sent as partial the thread stays open, exactly as a submission's acknowledgement does for its verdict ([A3. Pre-auth Answer](A3-preauth-answer.md)).

**The reprocess verdict** is a claim verdict in every respect but the road it takes. The claim's own thread was completed by the verdict the hospital disputed, and the exchange takes nothing more on it, so the new decision goes back on the thread the reprocess Task opened, kept on the case as [D19. case](../database/D19-case.md) `nhcx_reprocess_correlation_id` and `nhcx_reprocess_claim_ref` between the Task being taken in and its decision being sent. [A13. Adjudicate](A13-adjudicate.md) routes a claim decision here whenever that column is set. The decision is a completed Task whichever way the claim went: what was asked was a second look, and it has been given; the ClaimResponse on its output says what the second look found.

**A cancellation also closes the submission threads.** Beside the Task's answer, a cancelled case whose pre-authorisation or claim was still unanswered gets its ClaimResponse on that thread too, adjudicated `cancelled` under PC02 ([A3. Pre-auth Answer](A3-preauth-answer.md), [A4. Claim Answer](A4-claim-answer.md)), so every thread the hospital opened is closed on the wire.

**Headers set by the application.**

| Header | Value |
|---|---|
| `x-hcx-sender_code` | The Task's `x-hcx-recipient_code` (this payer) on the immediate answers; this payer's participant code on the reprocess verdict |
| `x-hcx-recipient_code` | The Task's `x-hcx-sender_code`: the hospital |
| `x-hcx-correlation_id` | The Task's own; on the reprocess verdict, `nhcx_reprocess_correlation_id` |
| `x-hcx-workflow_id` | From the table above; a Task that is none of the three echoes the Task's own |
| `x-hcx-status` | From the table above |

Per scheme dialect (see [PAYERS.md](../references/PAYERS.md)) [PAYER](../references/PAYERS.md#markers):

| Send | `pmjay` | `kyrocare` (Sandbox Payer) | `generic` | `x-hcx-status` |
|---|---|---|---|---|
| Cancellation accomplished or refused | PC02 | PC02 | PC02 | `response.complete` |
| Reprocess or release taken in | 37 | 37 | 37 | `response.partial` |
| Reprocess or release refused | 37 | 37 | 37 | `response.complete` |
| Reprocess approved | 252 | 252 | 252 | `response.complete` |
| Reprocess rejected | 253 | 253 | 253 | `response.complete` |

**Checks before sending.** The immediate answers refuse nothing: the case has already changed, and a gateway that is down does not change it back; a missing gateway is logged, "task `<code>` from `<hospital>` was acted on but no gateway is configured, so it was not answered". The reprocess verdict follows [A3. Pre-auth Answer](A3-preauth-answer.md)'s rules: sent once (the reprocess thread is cleared when it goes), never on a case with no thread.

Sandbox faults apply to the reprocess verdict as to any verdict [SANDBOX](../references/PAYERS.md#markers) ([A19. Sandbox Scenarios](A19-sandbox-scenarios.md)).

#### A9Q. REQUEST

The arguments passed to G7 Send:

| Field | Type | Notes |
|---|---|---|
| `jwe_headers` | object | The five headers above |
| `fhir` | Bundle | The Task answer bundle |

FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F10. Task (claim actions and answers)](../fhir/F10-task-claim-actions.md) (the answering Task; its output the [F9. ClaimResponse](../fhir/F9-claimresponse.md) ClaimResponse stating the case), [F15. Patient](../fhir/F15-patient.md), [F17. Organization](../fhir/F17-organization.md), [F18. Coverage](../fhir/F18-coverage.md). A not-found answer carries the Task and the two Organizations only.

Envelope, a cancellation accomplished:

```json
{
  "jwe_headers": {"x-hcx-sender_code": "<payer code>",
                  "x-hcx-recipient_code": "<facility code>",
                  "x-hcx-correlation_id": "2f6a9b1c-7d3e-4f80-a5b2-9c8d7e6f5a4b",
                  "x-hcx-workflow_id": "PC02",
                  "x-hcx-status": "response.complete"},
  "fhir": <F1 Bundle: F10 Task (completed, approve, description "Pre-authorisation withdrawn by <facility code>: Admission did not take place", output include ClaimResponse), F9 ClaimResponse (outcome complete, status cancelled), F15 Patient, F17 Organizations, F18 Coverage>
}
```

#### A9S. RESPONSE

**Acknowledgement:** the G7 result.

Recorded, immediate answers:
- [D27. case_exchange_message](../database/D27-case-exchange-message.md) exchange message, direction `out`, kind `task`, the Task's thread, the transaction, summary "Task `<code>` `<status>`: `<description>`" (only when a case matched).
- [D31. audit_log](../database/D31-audit-log.md) audit `task.<code>.answered`, entity `nhcx_txn`: "`<hospital>` told `<status>`, correlation `<id>`, answer txn `<txn_id>`".

Recorded, the reprocess verdict:
- [D19. case](../database/D19-case.md) `nhcx_claim_answer_txn_id` = `txn_id`, and `nhcx_reprocess_correlation_id` and `nhcx_reprocess_claim_ref` cleared: the thread is closed, and the transaction stands as the claim's answer, which it is.
- [D27. case_exchange_message](../database/D27-case-exchange-message.md) exchange message, kind `task`, on the reprocess thread, summary "Reprocess verdict: `<status>`, `<INR approved>` approved of `<INR claimed>`".
- [D31. audit_log](../database/D31-audit-log.md) audit `reprocess.answered` on the case.

**Failed send.** Logged, nothing recorded. An immediate answer that did not leave is not retried: the case has changed and the hospital learns it from the next message or a status enquiry. A reprocess verdict that did not leave keeps its thread on the case, so deciding again sends it.

Data: [D19. case](../database/D19-case.md), [D27. case_exchange_message](../database/D27-case-exchange-message.md), [D31. audit_log](../database/D31-audit-log.md), [D1. payer](../database/D1-payer.md)

Reply: none on the Task's thread after `completed`. After `accepted`, this payer's own verdict on the same thread (above).

#### A9P. PSEUDOCODE

```
function task_workflow(task, asked):                // [PAYER](../references/PAYERS.md#markers): the pmjay column
    if task.code == cancel: return "PC02"
    if task.code in {reprocess, release}: return "37"
    return asked                                     // the Task's own workflow id

function task_status_word(status):
    return "response.partial" if status == accepted else "response.complete"

// immediate answers, called by C7 with the case it acted on (an empty case when none matched)
function answer_task(in, case, task, status, claim_status, description):
    if gateway not configured:
        log "task <code> from <sender> was acted on but no gateway is configured, so it was not answered"; return
    answer = {payer: in.payer, payer code: in.recipient, case, code: task.code, status,
              claim_ref: task.claim_ref, claim_status, description, recipient: in.sender}
    if case: answer.cover = cover(case)                                  // A3
    bundle = F10 Task answer bundle(answer)      // Task approve/reject; with a case, the F9 ClaimResponse on its output
    headers = {x-hcx-sender_code: in.recipient, x-hcx-recipient_code: in.sender,
               x-hcx-correlation_id: in.correlation_id,
               x-hcx-workflow_id: task_workflow(task, in.workflow_id), x-hcx-status: task_status_word(status)}
    ack = SEND("v1/task/on_submit", {jwe_headers: headers, fhir: bundle}, case)    // A1: SEND
        on any failure f: log "could not queue the answer to task <code> from <sender> (correlation <corr>): <f>"; return
    if case:
        INSERT D27 {case_id, direction: out, kind: task, correlation_id: in.correlation_id, txn_id: ack.txn_id,
                    counterparty: in.sender, summary: "Task <code> <status>: <description>", payload: bundle}
    INSERT D31 audit {action: "task." + task.code + ".answered", entity_type: "nhcx_txn", entity_id: in.txn_id,
                      detail: "<sender> told <status>, correlation <corr>, answer txn " + ack.txn_id}

// what C7 calls, per Task (the case changes are C7's; only the sends are here):
//   cancel done:     answer_preauth(cancelled) if nhcx_answer_txn_id empty (A3);
//                    answer_claim(cancelled) if a claim thread is unanswered (A4);
//                    answer_task(in, cancelled, task, "completed", "cancelled", "Pre-authorisation withdrawn by <sender>: <reason>")
//   cancel refused:  answer_task(in, case, task, "rejected", claim_status_of(case), "<claim_no> is <stage> and cannot be withdrawn.")
//   reprocess taken: UPDATE D19 SET nhcx_reprocess_correlation_id = in.correlation_id, nhcx_reprocess_claim_ref = task.claim_ref
//                    answer_task(in, reopened, task, "accepted", claim_status_of(reopened), "Claim reopened for reprocessing (round <n>) at the request of <sender>: <reason>")
//   reprocess refused: answer_task(in, case, task, "rejected", claim_status_of(case), "<claim_no> is still open, there is nothing to reopen." | "<claim_no> has been paid and cannot be reprocessed.")
//   no such claim:   answer_task(in, none, task, "rejected", "not-found", "No claim numbered <ref> is on record with this payer.")

// the reprocess verdict, called by A13 when the claim decided has nhcx_reprocess_correlation_id set
LEG reprocess: use "claim", route "v1/task/on_submit", kind task,
               thread D19.nhcx_reprocess_correlation_id, answered: none (an open thread is an unanswered one),
               claim_ref D19.nhcx_reprocess_claim_ref or nhcx_claim_submission_ref or nhcx_claim_ref,
               audit "reprocess.answered", what "reprocess verdict"
function answer_reprocess(case):
    render(current) = F10 Task answer bundle({payer, payer code, case: current, cover(current),
                        code: "reprocess", status: "completed", claim_ref: LEG.claim_ref(case),
                        claim_status: claim_status_of(current), recipient: case.nhcx_sender_code,
                        description: "Claim <claim_no> reprocessed: <status>, <INR approved> approved of <INR claimed> claimed. <remarks>"})
    txn = send_verdict(case, reprocess) with that render      // A3 send_verdict; workflow 252 or 253
    on record: UPDATE D19 SET nhcx_claim_answer_txn_id = txn,
                              nhcx_reprocess_correlation_id = null, nhcx_reprocess_claim_ref = null
    return txn
```

#### A9U. USED BY
- Screens: [S3. Case Desk](../screens/S3-case-desk.md)
- APIs: [A3. Pre-auth Answer](A3-preauth-answer.md), [A4. Claim Answer](A4-claim-answer.md), [A13. Adjudicate](A13-adjudicate.md), [A19. Sandbox Scenarios](A19-sandbox-scenarios.md)
- Callbacks: [C7. Task Submit](../callbacks/C7-task-submit.md)
- FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F9. ClaimResponse](../fhir/F9-claimresponse.md), [F10. Task (claim actions and answers)](../fhir/F10-task-claim-actions.md)
- Database: [D19. case](../database/D19-case.md), [D27. case_exchange_message](../database/D27-case-exchange-message.md), [D31. audit_log](../database/D31-audit-log.md)
- Tests: [T10. Pre-auth Cancelled](../tests/T10-preauth-cancelled.md), [T14. Reprocess and Balance Release](../tests/T14-reprocess-and-release.md)
