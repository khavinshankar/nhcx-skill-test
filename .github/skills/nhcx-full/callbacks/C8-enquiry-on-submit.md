# C8. Enquiry Reply

#### C8E. ENDPOINT
Delivered in-process by [G8. Receive](../gateway/G8-receive.md) for NHCX route `v1/task/on_submit` (type `task`) or a status route such as `v1/on_status` (type `status`), passed to `C1.receive`. Answers A6 sent as a status enquiry, a reprocess request or a balance release.

#### C8D. DESCRIPTION
The payer's answer to one of the small exchanges. Each enquiry waits on a correlation id of its own, so C1 looks for it before the main legs: a `task` or `status` message whose `x-hcx-correlation_id` matches an enquiry (D29 `correlation_id`) comes here, whatever else is on the case. A `status` message matching no enquiry is `unmatched`; a `task` message matching none goes to C7.

The live status reply arrives as `task` (the enquiry goes out on `task/submit`, because the sandbox refuses `v1/status`) [SANDBOX](../references/PAYERS.md#markers), and the payer usually redelivers the decision on the pre-authorisation's own thread right after it (C5) [SANDBOX](../references/PAYERS.md#markers).

Only an enquiry still `asking` takes the answer; an answered one answers `ignored`, which covers the payer's redeliveries. An enquiry on record as a failed send (`error`) is reopened and the answer applied.

#### C8Q. REQUEST
`fhir` is an F1 Bundle carrying an F10 Task, often pointing at an F9 ClaimResponse through `output[].valueReference`, with F15 Patient and F17 Organizations. For a status enquiry the answer can also ride on the protocol header `x-hcx-status_response` (a JSON object, or a string holding one).

A header seen on the sandbox reads as answer `preauth-pending`, detail "Pre-authorisation pending; stage: preauth; outcome: pending; total_approved: 0; total_paid: 0" [SANDBOX](../references/PAYERS.md#markers). A payer that answers with only a Task output coded `claimStatus` (`valueString`, for example `claim-approved`) is read from there.

#### C8P. PSEUDOCODE

```
C8(envelope, corr):
    row = newest D29 where correlation_id == corr
    if none: return "unmatched"
    if row.status != "asking" and not failed_send(row): return "ignored"
    body = payload(envelope)
    if body.type == "ProtocolResponse":
        write D29: status = "error", error_message = rejection(body)
        return "settled"
    revive(D29, row, "asking")
    values = {status: "answered", answered_at: now, error_message: null, response_json: body}
    if row.kind == "status":
        values += status_answer(envelope, body)
    else:                                               # reprocess and release
        parsed = read_task_reply(body)                  # C7; rejected when no Task
        reopened = parsed.task_status in {"completed", "accepted", "in-progress"}
        values.answer = "reopened" if reopened else "refused"
        values.detail = parsed.disposition or the Task's description or ""
        if reopened and the case has a D20 row:
            leg_write(D20, {status: "submitting", settled_at: null, error_message: null})
            # the new verdict arrives on the claim's own thread (C6)
    write D29: values
    return "settled"

status_answer(envelope, body):
    header = jwe_headers["x-hcx-status_response"], parsed as JSON when it is a string
    answer = header.entity_status or ""
    detail = ""
    task = first Task in body.entry
    if task:
        for each output coded "claimStatus" with a valueString:
            answer = answer or output.valueString
        if task.status == "rejected": answer = answer or "not-found"
        detail = task.description or ""
    if header:
        parts = "<k>: <v>" for k in (stage, outcome, total_approved, total_paid) when present
        detail = join non-empty [detail, join(parts, "; ")] with "; "
    return {answer: answer or "unknown", detail}
```

#### C8S. RESPONSE
`settled`, `unmatched` (no enquiry, or a `status` message on no enquiry), `ignored` for an enquiry no longer `asking`, or `rejected` for a reprocess or release answer that carries no Task (a status answer without a Task is read from the header alone).

State changes:

| Table | Change |
|---|---|
| D29 claim_enquiry | `status` `answered`, `answered_at`, `answer`, `detail`, `response_json`; or `error` with `error_message` `<code>: <message>` |
| D20 claim_submission | reprocess or release reopened: `status` `submitting`, `settled_at` null, `error_message` null (restamps D9 `stage` / `sub_stage`) |

A refused or failed Task that gives a reason (`Task.statusReason`, an output typed as an error, or `ClaimResponse.error` on the response it points at) has that reason kept in `detail` and shown with the answer; it stops nothing, and the ask can be sent again.

Status answers: the payer's `entity_status` (`preauth-pending`, `claim-approved`, `settled`, ...), `not-found`, or `unknown`. Reprocess and release answers: `reopened` or `refused`.

#### C8U. USED BY
- Screens: [S9. Pre-authorisation](../screens/S9-preauthorisation.md), [S11. Claim Submission](../screens/S11-claim-submission.md)
- APIs: [A6. Task Submit (cancel, status, reprocess, release)](../apis/A6-task-submit.md), [A10. Transaction Related](../apis/A10-txn-related.md), [A11. Transaction Dispatch](../apis/A11-txn-dispatch.md), [A12. Transaction FHIR](../apis/A12-txn-fhir.md), [A17. Claim State](../apis/A17-claim-state.md)
- Callbacks: [C1. Callback Door](C1-callback-door.md), [C6. Claim Reply](C6-claim-on-submit.md), [C7. Cancel Reply](C7-cancel-on-submit.md)
- FHIR: [F10. Task (claim actions)](../fhir/F10-task-claim-actions.md)
- Database: [D20. claim_submission](../database/D20-claim-submission.md), [D29. claim_enquiry](../database/D29-claim-enquiry.md)
- Gateway: [G7. Send](../gateway/G7-send.md)
- Tests: [T9. IRDAI Status Enquiry and Cancel](../tests/T9-irdai-cancel-and-status.md), [T12. IRDAI Reprocess and Balance Release](../tests/T12-irdai-reprocess-and-release.md)
