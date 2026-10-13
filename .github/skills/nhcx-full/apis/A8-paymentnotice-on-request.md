# A8. Payment Notice Acknowledgement

#### A8E. ENDPOINT
In-process: `gateway.send("v1/paymentnotice/on_request", envelope)`, [G7. Send](../gateway/G7-send.md), which encrypts it and posts it to NHCX for whoever sent the payment notice, on the notice's own thread: `POST {nhcx}/v1/paymentnotice/on_request`. No answer to it is awaited.

#### A8D. DESCRIPTION
The payer starts the payment leg: it posts a payment notice on `paymentnotice/request` when money moves (arrives through callback C10, type `payment` or `paymentnotice`). The notice is matched to a claim by the claim number inside it and recorded (see C10), and this call tells the payer the money was seen.

It is sent:
- **automatically**, the moment a notice is recorded, including a later notice about the same payment (same `PaymentNotice.id` on the same claim), which resets the row's acknowledgement to pending and is acknowledged again on its new thread;
- **by hand** from the Payments tab, only when the acknowledgement is still pending or failed.

**Headers.**

| Header | Value |
|---|---|
| `x-hcx-sender_code` | The facility's participant code |
| `x-hcx-recipient_code` | The notice's `x-hcx-sender_code`, else the case's processing id, else the claim's payer id, else the configured default payer code. A scheme can pay through a different participant than the one the claim went to, and the live sandbox does [SANDBOX](../references/PAYERS.md#markers) |
| `x-hcx-workflow_id` | From the adapter's `payment_ack` [PAYER](../references/PAYERS.md#markers), else the notice's own `x-hcx-workflow_id`, else the notice's claim number, else the current claim number (the claim-number fallbacks are [REF](../references/PAYERS.md#markers)) |
| `x-hcx-correlation_id` | The correlation id the notice arrived on |

Per adapter (see [PAYERS.md](../references/PAYERS.md)) [PAYER](../references/PAYERS.md#markers):

| Adapter | `payment_ack` | Workflow id sent |
|---|---|---|
| `pmjay` | 17 (PAYMENT_RECEIVED) | `17` |
| `kyrocare` (Sandbox Payer) | none | the notice's own workflow id echoed back (for example `30`) |
| `generic` | none | the notice's own workflow id echoed back |

A per-environment override (a JSON object of kind to workflow id) can set `payment_ack` too; an empty value there means "echo the notice's own".

G7 completes the other headers ([G5. Protocol Headers](../gateway/G5-protocol-headers.md)); when the correlation id is blank, G7 takes it from the newest inbound payment notice from the recipient in the [G9. Ledger](../gateway/G9-ledger.md).

**Checks.** "Payment notice not found." (the route answers the not-found page when the notice is not on this claim); "Set the facility's HFR ID and NHCX participant code under Settings first."

#### A8Q. REQUEST

The arguments passed to G7 Send:

| Field | Type | Notes |
|---|---|---|
| `jwe_headers` | object | The four headers above |
| `fhir` | Bundle | The payment acknowledgement Task, then the provider and payer Organizations |

The claim number it names is the one the notice named, else the claim's current number.

FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F14. Payment acknowledgement](../fhir/F14-payment-acknowledgement.md), [F17. Organization](../fhir/F17-organization.md)

Envelope, a real acknowledgement (PMJAY):

```json
{
  "jwe_headers": {"x-hcx-sender_code": "<facility code>",
                  "x-hcx-recipient_code": "<payer code>",
                  "x-hcx-workflow_id": "17",
                  "x-hcx-correlation_id": "066d6860-3717-44fe-9c81-13c4e81928db"},
  "fhir": <F1 Bundle carrying F14 Payment acknowledgement Task (paymentack, claim NM-26-0SH00000R), F17 provider and payer Organizations>
}
```

The same notice from the Sandbox Payer is acknowledged with `"x-hcx-recipient_code": "<payer code>"` and `"x-hcx-workflow_id": "30"` (the notice's own) [SANDBOX](../references/PAYERS.md#markers).

#### A8S. RESPONSE

**Acknowledgement:** the G7 result, `{"ok": true, "gateway_status": 202, "txn_id", "correlation_id", "request_id", "headers", "response", ...}`. The payment row's acknowledgement becomes `sent` under its ids (`txn_id` as `ack_txn_id`, `correlation_id`), and its error is cleared.

**Failure.** Any G7 error, or a result NHCX did not accept (`ok` false), sets the acknowledgement to `error` with the message, plus the ids when the failure named them. A failed automatic acknowledgement never rejects the notice: the notice stays recorded, the callback still answers 2xx, and the Payments tab offers "Acknowledge again". A failed manual one flashes the error.

Data: [D21. claim_payment](../database/D21-claim-payment.md)

**What comes back from the payer.** Nothing is waited for. The next thing on this leg is another payment notice (for example the clearing notice after the initiation notice), acknowledged again here.

Reply: [C10. Payment Notice](../callbacks/C10-paymentnotice-request.md)

#### A8P. PSEUDOCODE

```
// called by C10 right after a notice is recorded, or by hand from S12
function acknowledge_payment(payment_id):
    money = claim_payment[payment_id]      or refuse "Payment notice not found."
    case  = claim[money.claim_id]

    // build
    org = default organization
    if org missing or HFR ID or participant code empty:
        refuse "Set the facility's HFR ID and NHCX participant code under Settings first."
    bundle = F1 Bundle carrying F14 Payment acknowledgement Task
             (claim number = money.claim_ref or case.claim_no, authored now),
             F17 provider (org HFR ID, name) and payer (case.payer_id or default) Organizations

    // call (no ids-kept convention: any failure is the failure)
    try:
        result = gateway.send("v1/paymentnotice/on_request", {    // G7 Send
            jwe_headers: {
                x-hcx-sender_code:    org.participant_code,
                x-hcx-recipient_code: money.sender_code or case.processing_id or case.payer_id or default payer code,
                x-hcx-workflow_id:    workflow_id(adapter, payment_ack)   // env override, else adapter; may be none
                                      or money.workflow_id or money.claim_ref or case.claim_no,
                x-hcx-correlation_id: money.correlation_id or ""},
            fhir: bundle})
              (archived with the case)
        if not result.ok: fail with NHCX's refusal (APIs conventions)
        ack = {txn_id: result.txn_id, correlation_id: result.correlation_id}
    catch send_error or NHCX refusal:
        UPDATE claim_payment[payment_id] SET ack_status = error, ack_error = its message
            (+ ack_txn_id, ack_correlation_id when it named them); recompute case stage
        raise it                                     // the automatic caller swallows it

    UPDATE claim_payment[payment_id] SET ack_status = sent, ack_txn_id = ack.txn_id,
        ack_correlation_id = ack.correlation_id, acknowledged_at = now, ack_error = null
    recompute case stage
```

#### A8U. USED BY
- Screens: [S12. Payments](../screens/S12-payments.md)
- APIs: [A6. Task Submit (cancel, status, reprocess, release)](A6-task-submit.md)
- Callbacks: [C1. Callback Door](../callbacks/C1-callback-door.md), [C10. Payment Notice](../callbacks/C10-paymentnotice-request.md)
- FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F13. PaymentNotice](../fhir/F13-paymentnotice.md), [F14. Payment acknowledgement](../fhir/F14-payment-acknowledgement.md)
- Database: [D21. claim_payment](../database/D21-claim-payment.md)
- Gateway: [G1. Embedding](../gateway/G1-embedding.md), [G7. Send](../gateway/G7-send.md)
- Tests: [T11. IRDAI Payment Notice and Acknowledgement](../tests/T11-irdai-payment.md), [T18. PMJAY Payment Notice, Status Refusal and Cancel](../tests/T18-pmjay-payment-status-cancel.md)
