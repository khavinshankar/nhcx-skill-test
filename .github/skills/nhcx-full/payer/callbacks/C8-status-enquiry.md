# C8. Status Enquiry

#### C8E. ENDPOINT
Delivered in-process by [G8. Receive](../gateway/G8-receive.md) for NHCX route `v1/status` (the HCX shape: no bundle, the thread named in the `x-hcx-status_filters` header) or `v1/task/submit` (the NHCX shape: a `Task` coded `status` naming the claim, which is where the NHCX sandbox makes hospitals send it, refusing `v1/status` with NHCX-1012 [SANDBOX](../references/PAYERS.md#markers)). Classified `status` by C1 either way ([F10. Task (claim actions and answers)](../fhir/F10-task-claim-actions.md); a Task coded `status` whose output is `paymentack` is [C11. Payment Acknowledgement](C11-payment-acknowledgement.md) instead). Answered inside the same delivery by [A8. Status Answer](../apis/A8-status-answer.md), on the route that pairs with the one the ask came in on: `v1/on_status` for an ask on `v1/status`, `v1/task/on_submit` for a status Task, on the request's own correlation id. NHCX closes a thread with the callback that pairs with the route that opened it, so the other one would be refused.

#### C8D. DESCRIPTION
A hospital that has heard nothing asks where its submission stands. The answer is where the case is: as an `x-hcx-status_response` header, which is what the protocol reads, and as a Task bundle saying the same, which is what a FHIR reader expects.

**Which case.** The keys tried, in order, each against the pre-auth thread, the claim thread and the query thread of [D19. case](../database/D19-case.md) (`nhcx_correlation_id`, `nhcx_claim_correlation_id`, `nhcx_query_correlation_id`): the correlation id the enquiry names (`x-hcx-status_filters.correlation_id` or a Task input typed `correlationId`), the workflow id it names (`x-hcx-status_filters.workflow_id`), then the enquiry's own `x-hcx-workflow_id` (a hospital sends the leg's correlation id there [REF](../references/PAYERS.md#markers)). Then the claim number (`x-hcx-status_filters.claim_number`, or the Task's `CLN` identifier or `claimNumber` input) as `case_for_claim_ref` for this sender.

**The answer.** With a case: `entity_type` (`preauth` at stage `preauth`; `claim` at `claim`, `payment` or `settled`; else `claim` when a claim leg is filed, `preauth` otherwise), `entity_status` (the claim status of the case, [F10. Task (claim actions and answers)](../fhir/F10-task-claim-actions.md)), the claim number, stage, outcome (the adjudication status), the three totals and whether the thread has been answered, plus a line a person reads: "Pre-authorisation <status>: <remarks>", "Claim <status>", "Approved for <amount>; <paid> paid so far", "Settled: <paid> paid", "Rejected", "Withdrawn". Without one: the Task `rejected`, status `not-found`, "No submission on that thread is on record with this payer." A thread this payer does not hold is still answered, because "not found" is where it stands.

**Nothing changes** on the case. Two [D27. case_exchange_message](../database/D27-case-exchange-message.md) rows are written when a case matched: the enquiry (the bundle, or the filters when it had none) and the answer (the header and the bundle).

#### C8Q. REQUEST
Either no `fhir` and `x-hcx-status_filters` in `jwe_headers` (an object, or a JSON string of one) carrying `x-hcx-correlation_id` or `correlation_id`, `x-hcx-workflow_id` or `workflow_id`, and `claim_number`, `claimNumber` or `x-hcx-claim_number`; or an [F1. Bundle](../fhir/F1-bundle.md) Bundle carrying [F10. Task (claim actions and answers)](../fhir/F10-task-claim-actions.md) Task coded `status` with an identifier typed `CLN` or inputs typed `claimNumber` and `correlationId`. Headers read: `x-hcx-sender_code`, `x-hcx-recipient_code`, `x-hcx-correlation_id` (the enquiry's own thread), `x-hcx-workflow_id`, `x-hcx-status_filters`.

#### C8P. PSEUDOCODE

```
C8(in, task):                                             # task = F10 parse + status filters: correlation_ref, workflow_ref, claim_ref
    case, found = none, false
    for key in [task.correlation_ref, task.workflow_ref, in.workflow_id] if not blank:
        for column in [nhcx_correlation_id, nhcx_claim_correlation_id, nhcx_query_correlation_id]:
            case = D19 where column == key
            if case: found = true; break
        if found: break
    if not found and task.claim_ref:
        case = case_for_claim_ref(task.claim_ref, in.sender); found = case is not none

    answer = {payer: in.payer, payer_code: in.recipient, code: "status", status: "completed",
              claim_ref: task.claim_ref or task.correlation_ref, recipient: in.sender}
    status_response = {entity_type: "claim", correlation_id: task.correlation_ref or in.corr}
    if found:
        answer.case = case; answer.cover = cover_for(case); answer.claim_status = claim_status_of(case)
        answer.description = describe_status(case)
        status_response += {entity_type: entity_type_of(case), entity_status: answer.claim_status,
                            claim_no: case.claim_no, stage: case.stage, outcome: case.adjudication_status,
                            total_claimed, total_approved, total_paid,
                            answered: case.exchange.answer_txn_id or case.exchange.claim_answer_txn_id set}
    else:
        answer.status = "rejected"; answer.claim_status = "not-found"
        answer.description = "No submission on that thread is on record with this payer."
        status_response.entity_status = "not-found"

    bundle = A8.status_answer(answer)                      # F10 Task with the ClaimResponse on its output
    path = "v1/task/on_submit" if the ask came as a Task on the task route else "v1/on_status"
    ack = answer(in, bundle, path, workflow = in.workflow_id, status = "response.complete",
                 what = "status.answered", extra header x-hcx-status_response = status_response)
    if found:
        exchange_message(case, "in",  "status", in.corr, in.ledger_id, in.sender,
                         "Status enquiry about <claim_ref or correlation_ref or claim_no>",
                         payload(in.envelope) or {x-hcx-status_filters: filters})
        exchange_message(case, "out", "status", in.corr, ack.txn_id, in.sender,
                         "Status: <claim_status>, <description>", {x-hcx-status_response, fhir: bundle})
    return "settled"                                       # outcome {status: answered, entity_status, case_id, txn_id}
```

#### C8S. RESPONSE
`settled` whether a case was found or not; `rejected` when the gateway refuses the answer; `error` when the gateway is not configured or unreachable, so NHCX redelivers.

State changes: none on the case. Two [D27. case_exchange_message](../database/D27-case-exchange-message.md) rows (in and out) when a case matched; one [D31. audit_log](../database/D31-audit-log.md) audit row (`status.answered`). In the sandbox an answered enquiry ticks the checklist [SANDBOX](../references/PAYERS.md#markers).

#### C8U. USED BY
- APIs: [A3. Pre-auth Answer](../apis/A3-preauth-answer.md), [A4. Claim Answer](../apis/A4-claim-answer.md), [A8. Status Answer](../apis/A8-status-answer.md), [A11. Transaction Related](../apis/A11-txn-related.md), [A12. Transaction FHIR](../apis/A12-txn-fhir.md), [A18. Provider Driver](../apis/A18-provider-driver.md)
- Callbacks: [C1. Callback Door](C1-callback-door.md), [C3. Insurance Plan Request](C3-insurance-plan-request.md), [C7. Task Submit](C7-task-submit.md)
- FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F10. Task (claim actions and answers)](../fhir/F10-task-claim-actions.md)
- Database: [D27. case_exchange_message](../database/D27-case-exchange-message.md)
- Tests: [T17. Status Enquiry Answered](../tests/T17-status-answered.md)
