# A12. Transaction FHIR

#### A12E. ENDPOINT
In-process: `ledger.fhir(txn_id)`, a synchronous query of the [G9. Ledger](../gateway/G9-ledger.md). Nothing goes on the wire.

#### A12D. DESCRIPTION
Returns the stored, decrypted envelope of one G9 ledger row: its protocol headers and its FHIR payload (decrypted by [G6. Encryption](../gateway/G6-encryption.md) when [G8. Receive](../gateway/G8-receive.md) took it in, or as [G7. Send](../gateway/G7-send.md) sent it). A11 only lists rows; this is how a poll reads what a row actually says.

Where it is called:
- The query thread and the payment notice threads ([A11. Transaction Related](A11-txn-related.md)): for each inbound row not sent by one of this payer's own participant codes, newest first, until one carries the resource the reply is made of (`Communication`, or a `Task` whose output status is `paymentack`). The first match is the reply; the rest are not read.
- The exchange log ([A15. Case Exchange Log](A15-case-exchange.md)) when a message on the case's trail ([D27. case_exchange_message](../database/D27-case-exchange-message.md)) was recorded without its bundle (an answer sent after a deliberate delay [SANDBOX](../references/PAYERS.md#markers), or a row written before the trail kept payloads): the bundle is read back from the ledger by the trail row's `txn_id` and shown as it went over the wire.

The envelope read here is applied exactly as if it had arrived through the callback ([C1. Callback Door](../callbacks/C1-callback-door.md)): the same parsers, the same outcomes. Its `x-hcx-api_call_id` is what [C9. Communication](../callbacks/C9-communication.md) and [C11. Payment Acknowledgement](../callbacks/C11-payment-acknowledgement.md) record in [D28. nhcx_delivery](../database/D28-nhcx-delivery.md) to tell a new reply from a redelivery.

Reply: [C9. Communication](../callbacks/C9-communication.md), [C11. Payment Acknowledgement](../callbacks/C11-payment-acknowledgement.md).

**What is not read here.** The poll never reads this payer's own outbound rows for their bundles: what this payer sent is on the case's exchange log ([D27. case_exchange_message](../database/D27-case-exchange-message.md)) already. And it never reads a row the door refused before decryption (`rejected`, kind `unknown` in [G8. Receive](../gateway/G8-receive.md)): such a row has no `fhir`, and is skipped.

**When one gateway hosts both participants.** On the sandbox loopback the hospital's copy of this payer's own query is on the same thread as an inbound row whose sender is the hospital's code, and it carries a `CommunicationRequest`, not a `Communication`; the resource check skips it. A Task on a payment notice thread that is not a `paymentack` (a status enquiry the hospital raised by mistake on that thread) is skipped the same way, and arrives in its own right through [C8. Status Enquiry](../callbacks/C8-status-enquiry.md).

#### A12Q. REQUEST

The argument passed to G9 fhir:

| Field | Type | Required | Value |
|---|---|---|---|
| `txn_id` | string | yes | a row `id` from A11, or the `txn_id` on a D27 trail row |

```
ledger.fhir("7UPG002R")
```

#### A12S. RESPONSE
The envelope as an object (G9 also returns `meta`: direction, payload kind, path, time; the exchange log shows `path` and `time`, the poll does not read them):

| Field | Meaning |
|---|---|
| `jwe_headers` | the `x-hcx-*` protocol headers (`x-hcx-api_call_id`, `x-hcx-correlation_id`, `x-hcx-status`, `x-hcx-workflow_id`, sender and recipient codes, ...) |
| `fhir` | the payload: a FHIR Bundle ([F1. Bundle](../fhir/F1-bundle.md)), or a plain `ProtocolResponse`; `null` when the ledger stores no bodies or the message was refused before decryption (the row is then skipped) |
| `payload` | read in place of `fhir` when `fhir` is absent. G9 has no `payload` key, so this fallback is not reached |

```json
{
 "jwe_headers": {
  "x-hcx-api_call_id": "cd2395e9-a9a0-467c-86a4-d70f960c2843",
  "x-hcx-correlation_id": "a47400d6-0dfd-47d5-ab42-0d5578173c6a",
  "x-hcx-sender_code": "<facility code>",
  "x-hcx-recipient_code": "<payer code>",
  "x-hcx-status": "response.complete",
  "x-hcx-workflow_id": "24"
 },
 "fhir": {"resourceType": "Bundle", "entry": ["..."]}
}
```

How it is read: a row whose payload is not a JSON object, or carries no entry of the resource looked for, is skipped and the next row is read. On the poll a G9 error is a poll failure (A11). On the exchange log a G9 error leaves the bundle out and shows "The gateway no longer holds this message." beside the row.

#### A12P. PSEUDOCODE

When: inside the A11 poll, and on an A15 read of a trail row without a stored bundle. The loop is in A11P.

Data: [D1. payer](../database/D1-payer.md), [D27. case_exchange_message](../database/D27-case-exchange-message.md).

```text
OWN_CODES():   the payer's participant codes, trimmed, lower case:
               D1.nhcx_participant_id, D1.nhcx_processing_id, and every hosted code (G2)

FIND_REPLY(related, resource_type):               # A11, both threads
  own = OWN_CODES()
  inbound = rows of related with direction == "in" and lower(trim(sender)) not in own
  for entry in inbound, newest first (the order G9 lists them):
      envelope = ledger.fhir(entry.id)            # G9 Ledger, in-process
      on G9 error: raise                          # poll failure, text goes to poll_notes (A15)
      bundle = envelope.fhir, else envelope.payload
      if bundle is not an object: continue
      if resource_type == "Task":
          # a payment acknowledgement is a Task whose output[status] is paymentack (F10);
          # any other Task on a notice thread is not the reply
          if no bundle.entry[].resource is a Task with output status "paymentack": continue
          return envelope, bundle
      if any bundle.entry[].resource.resourceType == resource_type:
          return envelope, bundle                 # the reply; later rows are not read
  return none

TRAIL_BUNDLE(trail_row):                          # A15, a D27 row with payload null and txn_id set
  try envelope = ledger.fhir(trail_row.txn_id)
  on G9 error: return none, "The gateway no longer holds this message."
  return envelope.fhir, none
```

After a match on the poll, the envelope is handed to `C1.receive` with `redelivery` true (A11P), so C9 or C11 applies it and records its `api_call_id` in D28.

#### A12U. USED BY
- APIs: [A5. Query Request](A5-query-request.md), [A6. Payment Notice](A6-payment-notice.md), [A11. Transaction Related](A11-txn-related.md), [A15. Case Exchange Log](A15-case-exchange.md)
- FHIR: [F1. Bundle](../fhir/F1-bundle.md)
- Gateway: [G1. Embedding](../gateway/G1-embedding.md), [G7. Send](../gateway/G7-send.md), [G9. Ledger](../gateway/G9-ledger.md)
- Tests: [T2. Test Runners](../tests/T2-test-runners.md), [T3. Eligibility Validation and Discovery Answered](../tests/T3-eligibility-answered.md), [T4. Auth-requirements Ruling Answered](../tests/T4-auth-requirements-ruled.md), [T5. Insurance Plan Served](../tests/T5-insurance-plan-served.md), [T11. Predetermination Quoted](../tests/T11-predetermination-quoted.md), [T16. Payment Enquiry Answered](../tests/T16-payment-enquiry-answered.md), [T17. Status Enquiry Answered](../tests/T17-status-answered.md)
