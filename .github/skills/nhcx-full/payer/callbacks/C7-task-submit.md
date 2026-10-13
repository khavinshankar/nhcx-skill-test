# C7. Task Submit

#### C7E. ENDPOINT
Delivered in-process by [G8. Receive](../gateway/G8-receive.md) for NHCX route `v1/task/submit`, passed to `C1.receive`, classified `task` because the bundle holds a `Task` that is neither a plan request ([C3. Insurance Plan Request](C3-insurance-plan-request.md)) nor a status enquiry ([C8. Status Enquiry](C8-status-enquiry.md)) nor a payment acknowledgement ([C11. Payment Acknowledgement](C11-payment-acknowledgement.md)) ([F10. Task (claim actions and answers)](../fhir/F10-task-claim-actions.md)). Answered inside the same delivery by [A9. Task Answer](../apis/A9-task-answer.md) on `v1/task/on_submit`, on the Task's own correlation id: a cancellation as `completed` (PC02), a reprocess or release as `accepted` (37, `response.partial`) with the decision to follow on the same thread when a person decides ([A13. Adjudicate](../apis/A13-adjudicate.md), [A9. Task Answer](../apis/A9-task-answer.md)).

#### C7D. DESCRIPTION
A Task is a hospital asking for something short of a submission. Three codes are acted on: `cancel` withdraws the pre-authorisation, `reprocess` and `release` reopen a decided claim. Any other code is noted on the case timeline and not acted on. The claim it is about is the identifier typed `CLN` on the Task, or an input or output typed `claimNumber` (also `intimationNumber`, `initimationNumber`), looked up as `case_for_claim_ref` for this sender.

**No such claim.** A cancel, reprocess or release naming a claim this payer does not hold is answered (`rejected` Task, claim status `not-found`, "No claim numbered <ref> is on record with this payer.") so the hospital's poll ends with a reason; the delivery is `unmatched`. Any other Task naming no case is `unmatched` without an answer.

**Cancel.** Allowed while the case is open (stage `preauth` or `claim`): the case goes to stage `cancelled`, adjudication `cancelled`, with the Task's description or reason as the remarks and "Pre-Authorization Withdrawn" on the timeline. A withdrawn pre-authorisation is `cancelled`, not `rejected`: nobody decided against it. It is refused once the case has reached payment: money committed against a decision cannot be undone by withdrawing the request behind it ("<claim_no> is <stage> and cannot be withdrawn.", Task `rejected`). Every thread the hospital is still waiting on is closed with a verdict adjudicated `cancelled`: [A3. Pre-auth Answer](../apis/A3-preauth-answer.md) on the pre-auth thread when unanswered, [A4. Claim Answer](../apis/A4-claim-answer.md) on the claim thread when unanswered, then [A9. Task Answer](../apis/A9-task-answer.md) on the Task's thread as `completed` under PC02.

**Reprocess and release.** Only a decided case reopens: stage `payment` (approved, unpaid) or `rejected`. A case still open is refused ("<claim_no> is still open, there is nothing to reopen."), a case with money paid is refused ("<claim_no> has been paid and cannot be reprocessed."): a recovery is not a reprocess. A release names the balance the hospital says it is still owed (`Task.input` typed `amount`, `valueMoney`), appended to the reason ("(balance of INR <amount> asked for)"). Reopening gives back whatever was drawn against the cover (a rejected claim never drew on it), puts every line back to pending with nothing approved, moves the case to stage `claim`, adjudication `pending`, counts the round (`reprocess_count`) and clears the claim's answer transaction. Then the Task's thread is kept on the case (`nhcx_reprocess_correlation_id`, `nhcx_reprocess_claim_ref`): the hospital is told now that the claim is queued (`accepted`, workflow 37, `response.partial` so the thread stays open [REF](../references/PAYERS.md#markers); NHA pairs 37 with `response.complete`, see [A9. Task Answer](../apis/A9-task-answer.md)), and the decision that follows goes back on that same thread as a completed Task carrying the ClaimResponse ([A9. Task Answer](../apis/A9-task-answer.md), workflow 252 or 253). The claim's own thread was completed by the verdict being disputed, and the exchange refuses a second answer on it: the reference sent the new decision there once and the hospital's claim stayed "submitted" for good [REF](../references/PAYERS.md#markers).

**Redelivery.** C1 drops a repeat by api call id. A repeated cancel finds the case already cancelled (refused as closed, harmless); a repeated reprocess finds it open again (refused as "still open").

#### C7Q. REQUEST
`fhir` is an [F1. Bundle](../fhir/F1-bundle.md) Bundle carrying [F10. Task (claim actions and answers)](../fhir/F10-task-claim-actions.md) Task: `code` from the financial task code system (`cancel`, `reprocess`, `release`), `status` `requested`, `description`, `reasonCode` (the cancel reason), identifier typed `CLN` or an input typed `claimNumber`, and on a release an input typed `amount`. Headers read: `x-hcx-sender_code`, `x-hcx-recipient_code`, `x-hcx-correlation_id`, `x-hcx-workflow_id` (PC01 cancel, 36 reprocess and release [PAYER](../references/PAYERS.md#markers); echoed as the Task's own for any other code).

#### C7P. PSEUDOCODE

```
C7(in, task):                                             # task = F10 parse: code, status, description, claim_ref, reason, amount
    case = case_for_claim_ref(task.claim_ref, in.sender)  # C1 shared rule
    if none:
        if task.code in {cancel, reprocess, release}:
            A9.answer_task(in, no case, task, status "rejected", claim_status "not-found",
                           "No claim numbered <task.claim_ref> is on record with this payer.")
        return "unmatched"                                 # outcome {status: ignored, reason: "no such claim"}

    reason = task.description or task.reason or "Requested by <sender> over NHCX"
    actor  = {name: in.sender, role: adjudicator}

    if task.code == "cancel":
        exchange_message(case, "in", "task", in.corr, in.ledger_id, in.sender,
                         "Cancellation requested: " + reason, payload(in.envelope))
        cancelled = D19.cancel_preauth(case, reason, actor)
            # stage cancelled, adjudication cancelled, remarks, adjudicated_by, adjudicated_at; D26 "Pre-Authorization Withdrawn"
            on closed:
                A9.answer_task(in, case, task, "rejected", claim_status_of(case),
                               "<case.claim_no> is <case.stage> and cannot be withdrawn.")
                return "settled"                           # outcome {status: refused, reason: "case is closed"}
        if cancelled awaits the pre-auth verdict (correlation set, no answer txn): A3.verdict(cancelled)   # adjudicated cancelled, PC02
        if cancelled awaits the claim verdict:                                     A4.verdict(cancelled)
        A9.answer_task(in, cancelled, task, "completed", "cancelled",
                       "Pre-authorisation withdrawn by <sender>: " + reason)       # PC02, response.complete
        D31 audit {action: "task.cancel", ...}
        return "settled"                                   # outcome {status: cancelled, case_id, stage}

    if task.code in {reprocess, release}:
        exchange_message(case, "in", "task", in.corr, in.ledger_id, in.sender,
                         "Reprocessing requested: " + reason, payload(in.envelope))
        if task.code == "release" and task.amount > 0:
            reason += " (balance of INR <amount> asked for)"
        reopened = D19.reprocess_claim(case, reason, actor)
            # refuse when stage in {preauth, claim}: "<claim_no> is still open, there is nothing to reopen."
            # refuse when total_paid > 0:             "<claim_no> has been paid and cannot be reprocessed."
            # stage payment with approved > 0: credit D6 wallet by total_approved, D8 entry
            #   "Claim <case.id> reopened for reprocessing"
            # D25 every line pending, approved 0, remarks cleared; totals recomputed
            # D19 stage claim, adjudication pending, remarks = reason, reprocess_count + 1,
            #   nhcx_claim_answer_txn_id null; D26 "Claim Reopened for Reprocessing (round n)"
            on refusal:
                A9.answer_task(in, case, task, "rejected", claim_status_of(case), refusal)
                return "settled"                           # outcome {status: refused, reason}
        D19.open_reprocess_thread(reopened, in.corr, task.claim_ref)
        A9.answer_task(in, reopened, task, "accepted", claim_status_of(reopened),
                       "Claim reopened for reprocessing (round <n>) at the request of <sender>: " + reason)
                                                           # 37, response.partial: the thread stays open for the decision
        D31 audit {action: "task." + task.code, ...}
        return "settled"                                   # outcome {status: reprocessing, case_id, stage}

    # any other code: noted, not acted on
    D26 event {title: "Exchange Message Received", description: "Task <code>: <description>", by: in.sender, type: info}
    exchange_message(case, "in", "task", in.corr, in.ledger_id, in.sender, "Task <code>: <description>", payload(in.envelope))
    D31 audit {action: "task." + (task.code or "received"), ...}
    return "settled"                                       # outcome {status: noted}
```

The answer on the Task's thread is built and sent by [A9. Task Answer](../apis/A9-task-answer.md) (the completed or rejected Task with a ClaimResponse saying where the case stands, beside the Patient, both Organizations and the Coverage); it reports rather than fails, because the case has already changed.

#### C7S. RESPONSE
`settled` whether the Task was done, refused with a reason, or only noted; `unmatched` when it names no case this payer holds (a cancel, reprocess or release is still answered `rejected`, `not-found`); `error` on an unexpected failure.

State changes:

| Task | Writes |
|---|---|
| cancel, done | [D19. case](../database/D19-case.md) stage `cancelled`, adjudication `cancelled`, remarks; [D26. case_timeline](../database/D26-case-timeline.md) "Pre-Authorization Withdrawn"; [D27. case_exchange_message](../database/D27-case-exchange-message.md) the Task in, the verdicts out on any open thread (A3, A4) and the Task answer out (A9); [D31. audit_log](../database/D31-audit-log.md) `task.cancel`, `task.cancel.answered` |
| cancel, refused | nothing on the case; [D27. case_exchange_message](../database/D27-case-exchange-message.md) the Task in and the `rejected` answer out; [D31. audit_log](../database/D31-audit-log.md) |
| reprocess or release, done | [D6. subscription](../database/D6-subscription.md) wallet credited and a [D8. wallet_entry](../database/D8-wallet-entry.md) entry when cover was drawn; [D25. case_line_item](../database/D25-case-line-item.md) all lines pending; [D19. case](../database/D19-case.md) stage `claim`, adjudication `pending`, `reprocess_count`, `nhcx_claim_answer_txn_id` null, `nhcx_reprocess_correlation_id` and `nhcx_reprocess_claim_ref` set; [D26. case_timeline](../database/D26-case-timeline.md) "Claim Reopened for Reprocessing"; [D27. case_exchange_message](../database/D27-case-exchange-message.md); [D31. audit_log](../database/D31-audit-log.md) `task.reprocess` or `task.release` |
| reprocess or release, refused | nothing on the case; [D27. case_exchange_message](../database/D27-case-exchange-message.md) the Task in and the `rejected` answer out; [D31. audit_log](../database/D31-audit-log.md) |
| other | [D26. case_timeline](../database/D26-case-timeline.md) "Exchange Message Received"; [D27. case_exchange_message](../database/D27-case-exchange-message.md); [D31. audit_log](../database/D31-audit-log.md) |

#### C7U. USED BY
- Screens: [S2. Cases](../screens/S2-cases.md), [S3. Case Desk](../screens/S3-case-desk.md)
- APIs: [A3. Pre-auth Answer](../apis/A3-preauth-answer.md), [A4. Claim Answer](../apis/A4-claim-answer.md), [A9. Task Answer](../apis/A9-task-answer.md), [A13. Adjudicate](../apis/A13-adjudicate.md), [A18. Provider Driver](../apis/A18-provider-driver.md)
- Callbacks: [C1. Callback Door](C1-callback-door.md), [C3. Insurance Plan Request](C3-insurance-plan-request.md), [C11. Payment Acknowledgement](C11-payment-acknowledgement.md)
- FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F10. Task (claim actions and answers)](../fhir/F10-task-claim-actions.md)
- Database: [D6. subscription](../database/D6-subscription.md), [D8. wallet_entry](../database/D8-wallet-entry.md), [D19. case](../database/D19-case.md), [D25. case_line_item](../database/D25-case-line-item.md), [D26. case_timeline](../database/D26-case-timeline.md), [D27. case_exchange_message](../database/D27-case-exchange-message.md)
- Tests: [T10. Pre-auth Cancelled](../tests/T10-preauth-cancelled.md), [T14. Reprocess and Balance Release](../tests/T14-reprocess-and-release.md)
