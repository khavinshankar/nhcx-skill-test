# C7. Cancel Reply

#### C7E. ENDPOINT
Delivered in-process by [G8. Receive](../gateway/G8-receive.md) for NHCX route `v1/task/on_submit`, passed to `C1.receive` with `delivery.type` `task`. Answers A6 sent as a cancel. A `task` message whose correlation id belongs to a status, reprocess or release enquiry goes to C8 first.

#### C7D. DESCRIPTION
The payer's answer to a request to withdraw the pre-authorisation. PMJAY answers an accepted cancel under workflow `PC02` with a Task pointing at a ClaimResponse adjudicated `cancelled`, and a refused one with a `ProtocolResponse` (PAYR-1252, PAYR-1257, PAYR-1258 and others) [PAYER](../references/PAYERS.md#markers).

**Matching.** By `x-hcx-correlation_id` against the pre-authorisation's cancel thread (D18 `cancel_correlation_id`, newest row). Nothing matching: `unmatched`.

**Which legs take it.** A pre-authorisation that is `cancelling`; one whose cancel was refused (back in its earlier status with the error "The payer did not accept the cancellation."); or one on record as a failed send (C1 `failed_send`). Anything else answers `ignored`.

**An acceptance wins.** Two payers can answer one cancel Task (the sandbox's deployed copy beside the live one) [SANDBOX](../references/PAYERS.md#markers), so a refusal that landed first does not close the thread: while the leg shows the refusal, a later acceptance is applied, and a further refusal or a `ProtocolResponse` is `ignored`. An accepted cancellation stands.

**The Task's own error.** When the payer says why it did not do it (`Task.statusReason`, an output typed as an error, or `ClaimResponse.error` on the response the Task points at), those words are kept in `disposition` and shown under the refusal. `error_message` stays the fixed refusal text, because the logic above matches on it.

**A `ProtocolResponse` to a cancel** is a refusal at the door for a fault on our side (a wrong input spelling, F10; a wrong workflow id), while the pre-authorisation is still approved at the payer. It does **not** leave the leg in `error`: that would stop a corrected cancel from being sent, because A6 allows a cancel only from `submitting`, `approved`, `partial` or `queried`. Instead the leg goes back to `pre_cancel_status` (else `approved`) with the refusal text in `error_message` and the cancel's ids kept, so the desk reads why and cancels again; the first build left the leg in `error` and it had to be restored by hand before the corrected cancel was accepted [SANDBOX](../references/PAYERS.md#markers).

**Redelivery.** Once accepted, the leg is `cancelled` and every later copy is `ignored`. A `ProtocolResponse` after the leg was restored is applied again the same way (the error text is replaced), so each redelivery of the same refusal settles with the same result.

#### C7Q. REQUEST
`fhir` is an F1 Bundle carrying an F10 Task (claim action reply) whose `output[].valueReference` points at an F9 ClaimResponse in the same bundle, with F15 Patient, F17 Organizations and F18 Coverage; or a `ProtocolResponse`.

A refused cancel restores the status the pre-authorisation had before the cancel (`pre_cancel_status`). The reference implementation always set `approved`, which showed an approval the payer never gave when the cancel was sent from `submitting` or `queried`; that is corrected here.

#### C7P. PSEUDOCODE

```
REFUSED = "The payer did not accept the cancellation."

C7(envelope, corr):
    row = newest D18 where cancel_correlation_id == corr
    if none: return "unmatched"
    refused = row.status != "cancelling" and row.error_message == REFUSED
    if row.status != "cancelling" and not refused and not failed_send(row):
        return "ignored"
    body = payload(envelope)
    if body.type == "ProtocolResponse":
        if refused: return "ignored"
        # a door refusal of OUR cancel: the pre-authorisation still stands at the payer,
        # so restore it and let the desk cancel again (A6 allows a cancel from the restored status)
        leg_write(D18, row, {status: row.pre_cancel_status or "approved", error_message: rejection(body)})
        return "settled"
    parsed = read_task_reply(body)
    if refused and not accepted(parsed): return "ignored"
    revive(D18, row, "cancelling")
    ok = accepted(parsed)
    in one transaction:
        leg_write(D18, row, {status: "cancelled" if ok else (row.pre_cancel_status or "approved"),
                             settled_at: now, disposition, outcome,
                             error_message: null if ok else REFUSED,
                             response_json: body})
        if ok:
            write D9: claim_no = next claim number (D30 counter)
            # the withdrawn number stays on D18.claim_ref
    return "settled"

read_task_reply(body):
    task = first Task in body.entry
    if none: raise Rejected("The payer reply carries no Task.")
    parsed = {task_status: task.status}
    for each output in task.output with valueReference.reference:
        find the entry whose fullUrl equals the reference, or whose resource id equals
        the part after "urn:uuid:"
        if that resource is a ClaimResponse: parsed += read_claim_response(it)   # C5
    return parsed

accepted(parsed):
    return parsed.task_status in {null, "completed", "accepted"}
       and lower(parsed.outcome) != "error"
```

#### C7S. RESPONSE
`settled`, `unmatched`, `ignored` (the leg moved on, or a refusal after a refusal), or `rejected` when the bundle carries no Task.

State changes (each D18 write restamps D9 `stage` / `sub_stage`):

| Reply | D18 claim_preauth | D9 claim |
|---|---|---|
| accepted | `status` `cancelled`, `settled_at`, `disposition`, `outcome`, `error_message` null, `response_json` | `claim_no` replaced by a freshly minted number; the episode carries on under it |
| refused (Task `rejected`, or ClaimResponse `outcome` `error`) | `status` back to `pre_cancel_status` (the status before the cancel; `approved` when none was recorded), `error_message` "The payer did not accept the cancellation.", `settled_at`, `disposition`, `outcome`, `response_json` | none |
| `ProtocolResponse` | `status` back to `pre_cancel_status` (`approved` when none was recorded), `error_message` `<code>: <message>`; the cancel can be sent again | none |

#### C7U. USED BY
- Screens: [S6. Claim Detail](../screens/S6-claim-detail.md), [S9. Pre-authorisation](../screens/S9-preauthorisation.md)
- APIs: [A6. Task Submit (cancel, status, reprocess, release)](../apis/A6-task-submit.md), [A10. Transaction Related](../apis/A10-txn-related.md), [A12. Transaction FHIR](../apis/A12-txn-fhir.md), [A17. Claim State](../apis/A17-claim-state.md)
- Callbacks: [C1. Callback Door](C1-callback-door.md), [C5. Pre-auth Reply](C5-preauth-on-submit.md), [C8. Enquiry Reply](C8-enquiry-on-submit.md)
- FHIR: [F10. Task (claim actions)](../fhir/F10-task-claim-actions.md)
- Database: [D9. claim](../database/D9-claim.md), [D18. claim_preauth](../database/D18-claim-preauth.md), [D30. counter](../database/D30-counter.md)
- Tests: [T2. Test Runners](../tests/T2-test-runners.md), [T9. IRDAI Status Enquiry and Cancel](../tests/T9-irdai-cancel-and-status.md), [T18. PMJAY Payment Notice, Status Refusal and Cancel](../tests/T18-pmjay-payment-status-cancel.md)
