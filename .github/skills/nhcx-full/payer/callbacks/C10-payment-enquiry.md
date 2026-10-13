# C10. Payment Enquiry

#### C10E. ENDPOINT
Delivered in-process by [G8. Receive](../gateway/G8-receive.md) for NHCX route `v1/paymentnotice/request`, passed to `C1.receive`, classified `paymentnotice` because the bundle holds a `PaymentNotice` ([F13. PaymentNotice](../fhir/F13-paymentnotice.md)); a `PaymentReconciliation` on its own is an answer, not a question, and is ignored. Answered inside the same delivery by [A7. Payment Enquiry Answer](../apis/A7-payment-enquiry-answer.md) on `v1/paymentnotice/on_request`, on the request's own correlation id, with the reconciliation of what was paid ([F14. PaymentReconciliation](../fhir/F14-paymentreconciliation.md)).

#### C10D. DESCRIPTION
The exchange runs payment notices in two directions. This payer tells a hospital that money moved ([A6. Payment Notice](../apis/A6-payment-notice.md), a fresh thread each time, acknowledged by [C11. Payment Acknowledgement](C11-payment-acknowledgement.md)). And a hospital may send a PaymentNotice of its own, asking about a claim: the state of payment on that claim goes back on the enquiry's thread.

**Which case.** The claim number the notice names: the identifier typed `CLN` on the PaymentNotice, on the reconciliation beside it, or on a Task in front of it, else the first untyped identifier on the notice; looked up as `case_for_claim_ref` for this sender.

**The answer.** With a case: every payment on it ([D30. payment](../database/D30-payment.md)), reconciled: status, amount, TDS, net, UTR and date per payment, and the totals approved and paid, as [F14. PaymentReconciliation](../fhir/F14-paymentreconciliation.md) renders them. An unknown claim is answered, not refused: an OperationOutcome-shaped error bundle ("No claim numbered <ref> is on record with this payer.") so the hospital's poll ends with a reason rather than a timeout; the delivery is `unmatched`.

**What the notice says about itself** (amount, `paymentStatus` `paid` or `cleared`, `created`, the reconciliation's disposition or the Task's description) is read for the audit line and the exchange log; nothing on the payments changes.

**Redelivery.** C1 drops a repeat by api call id; a repeat that slips through is answered again with the same reconciliation.

#### C10Q. REQUEST
`fhir` is an [F1. Bundle](../fhir/F1-bundle.md) Bundle carrying [F13. PaymentNotice](../fhir/F13-paymentnotice.md) PaymentNotice (identifier typed `CLN`, `amount`, `paymentStatus`, `created`), sometimes with a PaymentReconciliation or a Task beside it, and the [F17. Organization](../fhir/F17-organization.md) Organizations. Headers read: `x-hcx-sender_code`, `x-hcx-recipient_code`, `x-hcx-correlation_id`, `x-hcx-workflow_id` (echoed).

#### C10P. PSEUDOCODE

```
C10(in, enquiry):                                         # enquiry = F13 parse: claim_ref, amount, status, created, note
    case = case_for_claim_ref(enquiry.claim_ref, in.sender)   # C1 shared rule
    if none:
        bundle = A7.unknown_claim({payer: in.payer, payer_code: in.recipient, claim_ref: enquiry.claim_ref,
                                   reason: "No claim numbered <enquiry.claim_ref> is on record with this payer."})
        answer(in, bundle, "v1/paymentnotice/on_request", workflow = in.workflow_id,
               status = "response.complete", what = "paymentnotice.unknown")
        D31 detail: "<sender> asked about <claim_ref>, correlation <corr>, no case matched"
        return "unmatched"                                 # outcome {status: unknown_claim, txn_id}

    payments = D30 where case_id == case.id (up to 100)
    claim_ref = case.exchange.claim_submission_ref or case.exchange.claim_ref or enquiry.claim_ref
    bundle = A7.reconciliation({payer: in.payer, payer_code: in.recipient, case, payments,
                                claim_ref, recipient: in.sender})
    ack = answer(in, bundle, "v1/paymentnotice/on_request", workflow = in.workflow_id,
                 status = "response.complete", what = "paymentnotice.answered")
    D31 detail: "<sender> asked about <enquiry.claim_ref>, correlation <corr>, case <case.id>, paid <total_paid>"
    exchange_message(case, "in",  "paymentnotice", in.corr, in.ledger_id, in.sender,
                     "Payment enquiry for <enquiry.claim_ref>", payload(in.envelope))
    exchange_message(case, "out", "paymentreconciliation", in.corr, ack.txn_id, in.sender,
                     "Reconciliation: <total_paid> paid of <total_approved> approved", bundle)
    return "settled"                                       # outcome {status: answered, case_id, txn_id}
```

#### C10S. RESPONSE
`settled` when the reconciliation went back; `unmatched` when the claim is unknown (an error bundle still goes back); `rejected` when the bundle cannot be read or the gateway refuses the answer; `error` when the gateway is not configured or unreachable, so NHCX redelivers.

State changes: none on the payments. Two [D27. case_exchange_message](../database/D27-case-exchange-message.md) rows (the enquiry in, the reconciliation out) when a case matched; one [D31. audit_log](../database/D31-audit-log.md) audit row (`paymentnotice.answered` or `paymentnotice.unknown`).

#### C10U. USED BY
- APIs: [A4. Claim Answer](../apis/A4-claim-answer.md), [A7. Payment Enquiry Answer](../apis/A7-payment-enquiry-answer.md), [A11. Transaction Related](../apis/A11-txn-related.md), [A18. Provider Driver](../apis/A18-provider-driver.md)
- Callbacks: [C1. Callback Door](C1-callback-door.md)
- FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F13. PaymentNotice](../fhir/F13-paymentnotice.md)
- Database: [D27. case_exchange_message](../database/D27-case-exchange-message.md), [D30. payment](../database/D30-payment.md)
- Tests: [T16. Payment Enquiry Answered](../tests/T16-payment-enquiry-answered.md)
