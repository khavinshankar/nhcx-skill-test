# F13. PaymentNotice

#### F13R. RESOURCE
`PaymentNotice`, no profile, the `SUBSETTED` tag (F1).

- **Sent** on `v1/paymentnotice/request` by [A6. Payment Notice](../apis/A6-payment-notice.md), on a fresh thread the gateway mints, when a payment is raised and again when it completes with the UTR ([A14. Disburse](../apis/A14-disburse.md)); the same bundle answers a hospital's enquiry on `v1/paymentnotice/on_request` ([A7. Payment Enquiry Answer](../apis/A7-payment-enquiry-answer.md)). Entries under `<payer base>/v1/paymentnotice/request`: the Task at `<payer base>/task/v1/paymentnotice/request/<claim number>`, the PaymentNotice, the PaymentReconciliation (F14), the hospital Organization and the payer Organization without its name (F17), in that order, as the scheme sends them [REF](../references/PAYERS.md#markers).
- **Received** on `v1/paymentnotice/request` from a hospital asking where the money is, read by [C10. Payment Enquiry](../callbacks/C10-payment-enquiry.md) and answered by [A7. Payment Enquiry Answer](../apis/A7-payment-enquiry-answer.md). Beside it a hospital may send a PaymentReconciliation and a Task; a reconciliation on its own is somebody's answer, not a question, and is ignored.

#### F13D. DESCRIPTION
**Sent.** Three resources tell the story: the Task says it in words, the PaymentNotice gives the amount and status, the PaymentReconciliation (F14) the date, the UTR and the split between what was paid and what was withheld as TDS. Every resource carries the hospital's claim number as a `CLN` identifier, which is what the hospital matches the notice on (it holds no thread for a payer-started message) [PAYER](../references/PAYERS.md#markers).

When the notice is about one payment ([D30. payment](../database/D30-payment.md), the push finance triggers), only that payment counts; when it answers an enquiry, every completed payment on the case counts. The status and the words:

| Payments on the case | `paymentStatus` | `disposition` and Task `description` |
|---|---|---|
| completed, case `settled` | `cleared` "Cleared" | "Settled in full: INR <paid> paid against INR <approved> approved." |
| completed, money still owed | `paid` "Paid" | "INR <paid> paid so far against INR <approved> approved; INR <outstanding> outstanding." |
| initiated only | `paid` | "Payment initiated; the transfer has not completed yet." |
| none, case `payment` | `paid` | "Claim approved for INR <approved>; disbursement has not been initiated." |
| none, case `rejected` or `cancelled` | `paid` | "Nothing is payable: the claim was <stage>." |
| none, undecided | `paid` | "The claim has not been decided; nothing has been paid." |

`amount` is the net paid so far (the sum of `net_payable` over completed payments), zero when nothing moved. The Task is `requested`, `intent` `order`, coded `deliver` (`https://nrces.in/ndhm/fhir/r4/CodeSystem/ndhm-task-codes`), `requester` the payer, `owner` the hospital, with one `input` typed `status` "Status code" (`http://terminology.hl7.org/CodeSystem/financialtaskinputtype`) pointing at the PaymentNotice. The notice goes out under workflow 30 with `x-hcx-status` `request.initiated`; the enquiry answer echoes the enquiry's workflow id with `response.complete` ([PAYERS.md](../references/PAYERS.md)) [PAYER](../references/PAYERS.md#markers). The hospital acknowledges with a Task carrying `paymentack` on the notice's thread (F10, [C11. Payment Acknowledgement](../callbacks/C11-payment-acknowledgement.md)); the acknowledgement is recorded on the payment (`D30.nhcx_acknowledged_at`).

**Received.** A hospital's PaymentNotice is a question: which claim, and what the hospital believes about the payment. The claim number is read from the PaymentNotice's identifier typed `CLN`, then the PaymentReconciliation's, then the Task's, then the PaymentNotice's first identifier of any kind; a note for the audit line is the reconciliation's `disposition`, else the Task's `description`. The case is found by that number as the hospital's claim number or submission reference ([D19. case](../database/D19-case.md)); an unknown claim is answered with the error bundle of F14 rather than left silent ([A7. Payment Enquiry Answer](../apis/A7-payment-enquiry-answer.md)).

#### F13F. FIELDS
Sent:

| Element written | From | Notes |
|---|---|---|
| `identifier[0]` | type `CLN` "Claim number" (`https://nrces.in/ndhm/fhir/r4/CodeSystem/ndhm-identifier-type-code`), `system` `<payer base>/v1/claim`, `value` the hospital's claim number: `D19.nhcx_claim_submission_ref`, else `D19.nhcx_claim_ref` | on the Task, the notice and the reconciliation alike |
| `status` | `active` | |
| `created` | now, IST | |
| `payment.reference` | `<base>/paymentreconciliation/<claim number>` | the F14 entry |
| `recipient.reference` | `<base>/organization/provider/<D19.hospital_hfr_id>` | |
| `amount` | sum of `D30.net_payable` over completed payments, `INR` | one payment when the notice is about one |
| `paymentStatus.coding[0]` | `paid` or `cleared` (`http://terminology.hl7.org/CodeSystem/paymentstatus`) | the table |
| Task `status`, `intent`, `code` | `requested`, `order`, `deliver` | |
| Task `description` | the disposition sentence | |
| Task `requester`, `owner` | `<base>/organization/payer/<payer code without @hcx>`, the provider anchor | |
| Task `input[0]` | type `status`, `valueReference` the notice anchor | |

Received (read):

| Element read | Stored in | Notes |
|---|---|---|
| `PaymentNotice.identifier[type CLN].value`, else the reconciliation's, the Task's, the first identifier | the claim number the case is found by; `D31.detail` | the match key |
| `PaymentNotice.amount.value` | the audit line | what the hospital believes was paid |
| `PaymentNotice.paymentStatus.coding[0].code` | the audit line | `paid` or `cleared` |
| `PaymentNotice.created` | the audit line | as sent |
| `PaymentReconciliation.disposition`, else `Task.description` | the audit line | |
| the whole bundle | `D27.payload`, kind `paymentnotice`, direction `in` | |

#### F13U. USED BY
- APIs: [A6. Payment Notice](../apis/A6-payment-notice.md), [A7. Payment Enquiry Answer](../apis/A7-payment-enquiry-answer.md)
- Callbacks: [C1. Callback Door](../callbacks/C1-callback-door.md), [C10. Payment Enquiry](../callbacks/C10-payment-enquiry.md)
- FHIR: [F1. Bundle](F1-bundle.md), [F14. PaymentReconciliation](F14-paymentreconciliation.md), [F15. Patient](F15-patient.md), [F17. Organization](F17-organization.md), [F18. Coverage](F18-coverage.md)
- Database: [D30. payment](../database/D30-payment.md)
- Tests: [T15. Payment Notices and Acknowledgement](../tests/T15-payment-noticed.md)
