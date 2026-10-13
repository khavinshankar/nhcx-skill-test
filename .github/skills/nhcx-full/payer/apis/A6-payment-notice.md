# A6. Payment Notice

#### A6E. ENDPOINT
In-process: `gateway.send("v1/paymentnotice/request", envelope)`, [G7. Send](../gateway/G7-send.md), which encrypts it and posts it to NHCX for the hospital on a **new** thread: `POST {nhcx}/v1/paymentnotice/request`. No correlation id is passed; G7 mints one and the hospital's acknowledgement comes back under it ([C11. Payment Acknowledgement](../callbacks/C11-payment-acknowledgement.md)).

On the hospital's side it arrives as a payment notice, is matched to the claim by the claim number inside it, recorded, and acknowledged with a Task on `paymentnotice/on_request`.

#### A6D. DESCRIPTION
Sent by [A14. Disburse](A14-disburse.md) when money moves on a case that came off the exchange, and only when the deployment says so (`push_payment_notice` on, [REF](../references/PAYERS.md#markers)). A payment raised on a desk-only case has nobody to tell.

**Twice per payment.** The same notice goes out once when the payment is raised as `initiated` ("Payment initiated; the transfer has not completed yet.", no UTR) and once more when the UTR is recorded and the payment completes. A one-step disbursement (raised with a UTR) sends the completed notice only. The `PaymentNotice.id` is the same on both, the claim number, so the hospital reads the second as the first moving on rather than as a second payment; the provider skill's callback updates its row on a repeat and acknowledges it again [PAYER](../references/PAYERS.md#markers). A failed payment sends nothing.

**What it says** ([F13. PaymentNotice](../fhir/F13-paymentnotice.md) with [F14. PaymentReconciliation](../fhir/F14-paymentreconciliation.md)): a Task saying so in prose, the PaymentNotice with the amount paid and its status, the PaymentReconciliation with one line per completed movement (the net payment, and the TDS withheld when any) dated the completion date, the UTR as the payment identifier, and the two Organizations. The bundle is about this one payment, not the whole case. Status and disposition:

| The payment | `paymentStatus` | Disposition |
|---|---|---|
| completed and the case settled | `cleared` | "Settled in full: `<INR paid>` paid against `<INR approved>` approved." |
| completed, money still owed | `paid` | "`<INR paid>` paid so far against `<INR approved>` approved; `<INR outstanding>` outstanding." |
| initiated | `paid` | "Payment initiated; the transfer has not completed yet." |

**Headers set by the application.**

| Header | Value |
|---|---|
| `x-hcx-sender_code` | This payer's participant code ([D1. payer](../database/D1-payer.md)) |
| `x-hcx-recipient_code` | The case's `nhcx_sender_code` |
| `x-hcx-correlation_id` | not set: a fresh thread per notice |
| `x-hcx-workflow_id` | From the table below |
| `x-hcx-status` | `request.initiated` |

Workflow ids, per scheme dialect (see [PAYERS.md](../references/PAYERS.md)) [PAYER](../references/PAYERS.md#markers):

| Send | `pmjay` | `kyrocare` (Sandbox Payer) | `generic` | `x-hcx-status` |
|---|---|---|---|---|
| Payment notice, initiated and completed alike | 30 | 30 | 30 | `request.initiated` |

The reference sends 30 on both notices; NHA also publishes 31 (payment processed) and 33 (payment settled), which a deployment may prefer on the completed notice [REF](../references/PAYERS.md#markers). A hospital under the `pmjay` adapter acknowledges under 17, others echo 30 [PAYER](../references/PAYERS.md#markers).

**Checks before sending.** The payment must be `initiated` or `completed`; the case must have `nhcx_sender_code`; the gateway must be configured. None of these refuses the disbursement: the payment is recorded whatever the gateway does, and a notice that did not leave is logged.

#### A6Q. REQUEST

The arguments passed to G7 Send:

| Field | Type | Notes |
|---|---|---|
| `jwe_headers` | object | Sender, recipient, workflow id, status |
| `fhir` | Bundle | The notice bundle for this one payment |

FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F13. PaymentNotice](../fhir/F13-paymentnotice.md), [F14. PaymentReconciliation](../fhir/F14-paymentreconciliation.md), [F10. Task (claim actions and answers)](../fhir/F10-task-claim-actions.md) (the `deliver` Task in front), [F17. Organization](../fhir/F17-organization.md)

The claim number on the notice, the reconciliation and the Task is the hospital's own (`nhcx_claim_submission_ref`, else `nhcx_claim_ref`), typed `CLN`: it is what the hospital matches on.

Envelope, a completed payment:

```json
{
  "jwe_headers": {"x-hcx-sender_code": "<payer code>",
                  "x-hcx-recipient_code": "<facility code>",
                  "x-hcx-workflow_id": "30",
                  "x-hcx-status": "request.initiated"},
  "fhir": <F1 Bundle: F10 Task (deliver, requested, description the disposition, input the notice), F13 PaymentNotice (identifier CLN <claim number>, amount the net paid, paymentStatus paid or cleared), F14 PaymentReconciliation (paymentDate, paymentAmount, paymentIdentifier UTR, detail lines TDS and Payment), F17 provider and payer Organizations>
}
```

#### A6S. RESPONSE

**Acknowledgement:** the G7 result. Its `correlation_id` is the notice's thread; its `txn_id` the ledger row.

Recorded:
- [D30. payment](../database/D30-payment.md) `nhcx_notice_txn_id` = `txn_id` (the last notice sent for the payment).
- [D27. case_exchange_message](../database/D27-case-exchange-message.md) exchange message, direction `out`, kind `paymentnotice`, the minted correlation id, the transaction, summary "Payment notice: `<INR net>` paid, UTR `<utr>`" (the UTR blank on the initiated notice).
- [D31. audit_log](../database/D31-audit-log.md) audit `payment.notified` on the payment: "`<hospital>` told, txn `<id>`".

**Failed send.** Logged ("could not queue the payment notice for `<payment>` on case `<id>`: `<message>`"), nothing recorded; the payment stands. There is no resend in the reference: recording the UTR on an initiated payment sends the completed notice, which carries everything the first did [REF](../references/PAYERS.md#markers).

Data: [D30. payment](../database/D30-payment.md), [D19. case](../database/D19-case.md), [D27. case_exchange_message](../database/D27-case-exchange-message.md), [D31. audit_log](../database/D31-audit-log.md), [D1. payer](../database/D1-payer.md)

Reply: [C11. Payment Acknowledgement](../callbacks/C11-payment-acknowledgement.md), the hospital's `paymentack` Task, on this thread or naming the claim number; it stamps every completed, unacknowledged payment on the case (`nhcx_acknowledged_at`).

**Polling.** When the acknowledgement's callback was missed, opening the case ([A15. Case Exchange Log](A15-case-exchange.md)) polls each notice thread: [A11. Transaction Related](A11-txn-related.md) with the payment's `nhcx_notice_txn_id`, the newest inbound Task with output `paymentack` read through [A12. Transaction FHIR](A12-txn-fhir.md) and applied as C11 would.

#### A6P. PSEUDOCODE

```
// called by A14 after a payment is raised, completed in one step, or completed with a UTR
function push_payment_notice(payment):
    if push_payment_notice setting off or gateway not configured: return payment
    if payment.status not in {initiated, completed}: return payment
    case = D19[payment.case_id]
    if case.nhcx_sender_code empty: return payment          // nobody on the exchange to tell
    payer = D1 payer row
    claim_ref = case.nhcx_claim_submission_ref or case.nhcx_claim_ref
    bundle = F13 notice bundle(payer, payer code, case, payments = [payment], claim_ref,
                               recipient = case.nhcx_sender_code, about = payment)
    headers = {x-hcx-sender_code: payer code, x-hcx-recipient_code: case.nhcx_sender_code,
               x-hcx-workflow_id: "30", x-hcx-status: "request.initiated"}     // [PAYER](../references/PAYERS.md#markers)
    ack = SEND("v1/paymentnotice/request", {jwe_headers: headers, fhir: bundle}, case)   // A1: SEND
        on any failure f: log "could not queue the payment notice for <payment> on case <id>: <f>"; return payment
    UPDATE D30[payment.id] SET nhcx_notice_txn_id = ack.txn_id
    INSERT D27 {case_id: case.id, direction: out, kind: paymentnotice, correlation_id: ack.correlation_id,
                txn_id: ack.txn_id, counterparty: case.nhcx_sender_code,
                summary: "Payment notice: <INR payment.net_payable> paid, UTR <payment.utr_no>", payload: bundle}
    INSERT D31 audit {action: "payment.notified", entity_type: payment, entity_id: payment.id,
                      detail: "<hospital> told, txn " + ack.txn_id}
    return payment with nhcx_notice_txn_id set
```

#### A6U. USED BY
- Screens: [S10. Payments](../screens/S10-payments.md)
- APIs: [A4. Claim Answer](A4-claim-answer.md), [A7. Payment Enquiry Answer](A7-payment-enquiry-answer.md), [A11. Transaction Related](A11-txn-related.md), [A14. Disburse](A14-disburse.md)
- Callbacks: [C1. Callback Door](../callbacks/C1-callback-door.md), [C10. Payment Enquiry](../callbacks/C10-payment-enquiry.md), [C11. Payment Acknowledgement](../callbacks/C11-payment-acknowledgement.md)
- FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F13. PaymentNotice](../fhir/F13-paymentnotice.md), [F14. PaymentReconciliation](../fhir/F14-paymentreconciliation.md)
- Database: [D27. case_exchange_message](../database/D27-case-exchange-message.md), [D30. payment](../database/D30-payment.md), [D31. audit_log](../database/D31-audit-log.md)
- Gateway: [G7. Send](../gateway/G7-send.md)
- Tests: [T15. Payment Notices and Acknowledgement](../tests/T15-payment-noticed.md)
