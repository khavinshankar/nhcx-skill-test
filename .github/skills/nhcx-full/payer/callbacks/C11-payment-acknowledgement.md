# C11. Payment Acknowledgement

#### C11E. ENDPOINT
Delivered in-process by [G8. Receive](../gateway/G8-receive.md) for NHCX route `v1/paymentnotice/on_request` (the hospital's answer to a notice this payer sent on `v1/paymentnotice/request`, [A6. Payment Notice](../apis/A6-payment-notice.md)), passed to `C1.receive`, classified `task` and handed here because the `Task` carries an output typed `status` whose value is `paymentack` ([F10. Task (claim actions and answers)](../fhir/F10-task-claim-actions.md)). Nothing goes back.

#### C11D. DESCRIPTION
When money moves on the desk ([A14. Disburse](../apis/A14-disburse.md)), this payer sends a PaymentNotice with its reconciliation ([A6. Payment Notice](../apis/A6-payment-notice.md)): once when the payment is initiated and once when the UTR is recorded, each on a fresh thread the gateway mints. The hospital acknowledges each with a Task, and this callback files the acknowledgement against the payments it names: every completed payment on the case that has not been acknowledged is stamped `nhcx_acknowledged_at`. A hospital that acknowledges the second notice acknowledges the payment; one that acknowledges only the first stamps nothing until the payment completes.

**Which case.** The claim number the Task names (`CLN` identifier, or an input or output typed `claimNumber`), as `case_for_claim_ref` for this sender. The correlation id of the acknowledgement is the notice's thread ([D30. payment](../database/D30-payment.md) `nhcx_notice_txn_id` holds the notice's ledger id; the thread can be read back through [A11. Transaction Related](../apis/A11-txn-related.md)) and is the fallback when the Task names no claim number [REF](../references/PAYERS.md#markers). A Task naming no case this payer holds is `unmatched` and, unlike a cancel or a reprocess ([C7. Task Submit](C7-task-submit.md)), not answered.

**A repeat** (C1 drops it by api call id; one that slips through) finds nothing left to stamp and writes a timeline line saying 0 payments were acknowledged; harmless.

**Polling.** A missed acknowledgement is found by [A11. Transaction Related](../apis/A11-txn-related.md) on the notice's thread when the case is opened and applied by this same handler.

#### C11Q. REQUEST
`fhir` is an [F1. Bundle](../fhir/F1-bundle.md) Bundle carrying [F10. Task (claim actions and answers)](../fhir/F10-task-claim-actions.md) Task: `status` `completed`, an identifier typed `CLN` or an input typed `claimNumber`, an output typed `status` with `valueCodeableConcept` code `paymentack` from the NDHM task-output-value system, `description`. Headers read: `x-hcx-sender_code`, `x-hcx-recipient_code`, `x-hcx-correlation_id` (the notice's thread), `x-hcx-workflow_id` (17 under the `pmjay` dialect, else the notice's own 30 echoed [PAYER](../references/PAYERS.md#markers); nothing routes on it).

#### C11P. PSEUDOCODE

```
C11(in, task):                                            # task = F10 parse with output_status == "paymentack"
    case = case_for_claim_ref(task.claim_ref, in.sender)  # C1 shared rule
    if none:
        notice = D30 whose notice thread (through A11 on nhcx_notice_txn_id) is in.corr   # [REF](../references/PAYERS.md#markers)
        if notice: case = D19[notice.case_id]
    if none: return "unmatched"                            # outcome {status: ignored, kind: task, reason: "no such claim"}

    stamped = D30 update set nhcx_acknowledged_at = now
              where case_id == case.id and status == "completed" and nhcx_acknowledged_at is null
    summary = "Payment acknowledged by <sender> (<stamped> payment(s))"
    D26 event {title: "Payment Acknowledged", description: summary, by: in.sender, type: success}
    exchange_message(case, "in", "task", in.corr, in.ledger_id, in.sender, summary, payload(in.envelope))
    D31 audit {action: "task.status", entity: "nhcx_txn", id: in.ledger_id,
               detail: "<sender> sent, correlation <corr>, case <case.id>: " + summary}
    return "settled"                                       # outcome {status: acknowledged, case_id, stage}
```

#### C11S. RESPONSE
`settled` when the acknowledgement was filed (even when nothing was left to stamp); `unmatched` when it names no case; `error` on an unexpected failure.

State changes: [D30. payment](../database/D30-payment.md) `nhcx_acknowledged_at` on every completed, unacknowledged payment of the case; [D26. case_timeline](../database/D26-case-timeline.md) "Payment Acknowledged"; [D27. case_exchange_message](../database/D27-case-exchange-message.md) the inbound Task; [D31. audit_log](../database/D31-audit-log.md) one audit row. The payments screen ([S10. Payments](../screens/S10-payments.md)) shows the acknowledgement beside the notice. In the sandbox the acknowledgement ticks the checklist [SANDBOX](../references/PAYERS.md#markers).

#### C11U. USED BY
- Screens: [S10. Payments](../screens/S10-payments.md)
- APIs: [A6. Payment Notice](../apis/A6-payment-notice.md), [A9. Task Answer](../apis/A9-task-answer.md), [A11. Transaction Related](../apis/A11-txn-related.md), [A12. Transaction FHIR](../apis/A12-txn-fhir.md), [A14. Disburse](../apis/A14-disburse.md), [A15. Case Exchange Log](../apis/A15-case-exchange.md), [A18. Provider Driver](../apis/A18-provider-driver.md)
- Callbacks: [C1. Callback Door](C1-callback-door.md), [C7. Task Submit](C7-task-submit.md), [C8. Status Enquiry](C8-status-enquiry.md), [C10. Payment Enquiry](C10-payment-enquiry.md)
- FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F10. Task (claim actions and answers)](../fhir/F10-task-claim-actions.md), [F13. PaymentNotice](../fhir/F13-paymentnotice.md)
- Database: [D27. case_exchange_message](../database/D27-case-exchange-message.md), [D30. payment](../database/D30-payment.md)
- Tests: [T2. Test Runners](../tests/T2-test-runners.md), [T15. Payment Notices and Acknowledgement](../tests/T15-payment-noticed.md)
