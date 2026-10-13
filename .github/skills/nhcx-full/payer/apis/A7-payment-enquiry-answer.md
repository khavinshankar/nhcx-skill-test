# A7. Payment Enquiry Answer

#### A7E. ENDPOINT
In-process: `gateway.send("v1/paymentnotice/on_request", envelope)`, [G7. Send](../gateway/G7-send.md), which encrypts it and posts it to NHCX for the hospital, on the thread the hospital's notice arrived on: `POST {nhcx}/v1/paymentnotice/on_request`. No answer to it is awaited.

It answers [C10. Payment Enquiry](../callbacks/C10-payment-enquiry.md). This is the opposite direction from [A6. Payment Notice](A6-payment-notice.md): there this payer starts the thread; here the hospital asked, on `paymentnotice/request`, and this payer answers on the `on_` route.

#### A7D. DESCRIPTION
Sent at once, inside the callback, when a hospital's PaymentNotice ([F13. PaymentNotice](../fhir/F13-paymentnotice.md), received) asks about a claim. The case is found by the claim number the notice carries (typed `CLN`, else the first identifier on the notice, the reconciliation or the Task) among the cases from that sender ([D19. case](../database/D19-case.md) `nhcx_claim_submission_ref` or `nhcx_claim_ref`, and the case's own `claim_no`).

**Found:** the whole case's payments ([D30. payment](../database/D30-payment.md)) are reconciled ([F14. PaymentReconciliation](../fhir/F14-paymentreconciliation.md)): every completed payment as lines, the totals paid and withheld, the last UTR and date, the status and disposition of the standing:

| Standing | `paymentStatus` | Disposition |
|---|---|---|
| settled | `cleared` | "Settled in full: `<INR paid>` paid against `<INR approved>` approved." |
| paid in part | `paid` | "`<INR paid>` paid so far against `<INR approved>` approved; `<INR outstanding>` outstanding." |
| a payment initiated, none completed | `paid` | "Payment initiated; the transfer has not completed yet." |
| approved, nothing initiated (stage `payment`) | `paid` | "Claim approved for `<INR approved>`; disbursement has not been initiated." |
| rejected or withdrawn | `paid` | "Nothing is payable: the claim was `<stage>`." |
| not decided | `paid` | "The claim has not been decided; nothing has been paid." |

Nothing completed is still an answer: the reconciliation carries a zero amount and the disposition says why.

**Not found:** answered, not refused, because the hospital's poll is waiting: a PaymentReconciliation with `outcome` `error` and the disposition "No claim numbered `<ref>` is on record with this payer.", beside an OperationOutcome (severity `error`, code `not-found`) saying the same, so a reader looking for either finds it. PMJAY never answers a notice this way, so the shape follows the notice bundle's conventions [REF](../references/PAYERS.md#markers).

**Headers set by the application.** As every answer ([A1. Eligibility Answer](A1-eligibility-answer.md)): sender and recipient swapped, the notice's correlation id verbatim, its workflow id echoed, `x-hcx-status` `response.complete`. No scheme table [PAYER](../references/PAYERS.md#markers).

**Checks before sending.** None of its own beyond the door's ([C1. Callback Door](../callbacks/C1-callback-door.md)).

#### A7Q. REQUEST

The arguments passed to G7 Send:

| Field | Type | Notes |
|---|---|---|
| `jwe_headers` | object | Sender, recipient, correlation id, workflow id, status |
| `fhir` | Bundle | The reconciliation bundle, or the not-found bundle |

FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F10. Task (claim actions and answers)](../fhir/F10-task-claim-actions.md) (the `deliver` Task), [F13. PaymentNotice](../fhir/F13-paymentnotice.md) (this payer's PaymentNotice restating the standing), [F14. PaymentReconciliation](../fhir/F14-paymentreconciliation.md), [F17. Organization](../fhir/F17-organization.md)

Envelope, a claim paid in full:

```json
{
  "jwe_headers": {"x-hcx-sender_code": "<payer code>",
                  "x-hcx-recipient_code": "<facility code>",
                  "x-hcx-correlation_id": "5b1f0c1e-2c5e-4a0f-9a11-7c3f2d9e8b21",
                  "x-hcx-workflow_id": "17",
                  "x-hcx-status": "response.complete"},
  "fhir": <F1 Bundle: F10 Task (deliver), F13 PaymentNotice (CLN <claim number>, amount paid, status cleared), F14 PaymentReconciliation (every completed payment as TDS and Payment lines, UTR), F17 Organizations>
}
```

#### A7S. RESPONSE

**Acknowledgement:** the G7 result (`ok`, `gateway_status` 202, `txn_id`, `correlation_id`, `request_id`, `headers`, `response`).

Recorded, when the case was found:
- [D31. audit_log](../database/D31-audit-log.md) audit `paymentnotice.answered`, entity `nhcx_txn`: "`<hospital>` asked about `<ref>`, correlation `<id>`, case `<id>`, paid `<INR>`, answer txn `<txn_id>`". The door's receipt against a retried delivery.
- [D27. case_exchange_message](../database/D27-case-exchange-message.md) two exchange messages: direction `in`, kind `paymentnotice`, "Payment enquiry for `<ref>`" with the hospital's bundle; direction `out`, kind `paymentreconciliation`, "Reconciliation: `<INR paid>` paid of `<INR approved>` approved" with the answer.
- Nothing on the payments: an enquiry moves no money.

Not found: [D31. audit_log](../database/D31-audit-log.md) audit `paymentnotice.unknown` only.

The callback answers the gateway `{"status": "answered", "case_id", "txn_id"}` or `{"status": "unknown_claim", "txn_id"}`.

**Failed send.** As [A1. Eligibility Answer](A1-eligibility-answer.md): a refusal answers `rejected` with "The gateway refused the answer: `<message>`"; unreachable or 5xx answers `error` so NHCX redelivers the enquiry.

Data: [D19. case](../database/D19-case.md), [D30. payment](../database/D30-payment.md), [D27. case_exchange_message](../database/D27-case-exchange-message.md), [D31. audit_log](../database/D31-audit-log.md), [D1. payer](../database/D1-payer.md)

Reply: none. A hospital that reads `initiated` asks again later, or waits for this payer's own notice ([A6. Payment Notice](A6-payment-notice.md)).

#### A7P. PSEUDOCODE

```
function answer_payment_notice(in, enquiry):        // called by C10; enquiry is the parsed F13
    case = D19 case for claim ref enquiry.claim_ref from sender in.sender
           // matched on nhcx_claim_submission_ref, nhcx_claim_ref or claim_no
    if none: return answer_unknown_payment(in, enquiry)
    payments = D30 rows for case.id (up to 100)
    claim_ref = case.nhcx_claim_submission_ref or case.nhcx_claim_ref or enquiry.claim_ref
    bundle = F14 reconciliation bundle(payer = in.payer, payer code = in.recipient, case, payments,
                                       claim_ref, recipient = in.sender)
    ack = SEND("v1/paymentnotice/on_request", {jwe_headers: ANSWER_HEADERS(in), fhir: bundle}, case)   // A1
        on Refused r:     return rejected("The gateway refused the answer: " + r.message)
        on Unreachable u: return error("The gateway could not queue the answer")
    INSERT D31 audit {action: "paymentnotice.answered", entity_type: "nhcx_txn", entity_id: in.txn_id,
                      detail: "<sender> asked about <ref>, correlation <corr>, case <id>, paid <INR total_paid>, answer txn " + ack.txn_id}
    INSERT D27 {case_id, direction: in, kind: paymentnotice, correlation_id: in.correlation_id,
                txn_id: in.txn_id, counterparty: in.sender, summary: "Payment enquiry for " + enquiry.claim_ref,
                payload: in.fhir}
    INSERT D27 {case_id, direction: out, kind: paymentreconciliation, correlation_id: in.correlation_id,
                txn_id: ack.txn_id, counterparty: in.sender,
                summary: "Reconciliation: <INR total_paid> paid of <INR total_approved> approved", payload: bundle}
    return settled {status: "answered", case_id: case.id, txn_id: ack.txn_id}

function answer_unknown_payment(in, enquiry):
    log "payment notice for <ref> from <sender> matched no case (correlation <corr>)"
    bundle = F14 error bundle(in.payer, in.recipient, enquiry.claim_ref,
                              "No claim numbered " + enquiry.claim_ref + " is on record with this payer.")
    ack = SEND("v1/paymentnotice/on_request", {jwe_headers: ANSWER_HEADERS(in), fhir: bundle}, none)
        on Refused r:     return rejected("The gateway refused the answer: " + r.message)
        on Unreachable u: return error("The gateway could not queue the answer")
    INSERT D31 audit {action: "paymentnotice.unknown", entity_type: "nhcx_txn", entity_id: in.txn_id,
                      detail: "<sender> asked about <ref>, correlation <corr>, no case matched, answer txn " + ack.txn_id}
    return settled {status: "unknown_claim", txn_id: ack.txn_id}
```

#### A7U. USED BY
- Screens: [S11. FHIR Preview](../screens/S11-fhir-preview.md)
- Callbacks: [C10. Payment Enquiry](../callbacks/C10-payment-enquiry.md)
- FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F13. PaymentNotice](../fhir/F13-paymentnotice.md), [F14. PaymentReconciliation](../fhir/F14-paymentreconciliation.md)
- Database: [D27. case_exchange_message](../database/D27-case-exchange-message.md), [D30. payment](../database/D30-payment.md), [D31. audit_log](../database/D31-audit-log.md)
- Gateway: [G5. Protocol Headers](../gateway/G5-protocol-headers.md), [G7. Send](../gateway/G7-send.md)
- Tests: [T16. Payment Enquiry Answered](../tests/T16-payment-enquiry-answered.md)
