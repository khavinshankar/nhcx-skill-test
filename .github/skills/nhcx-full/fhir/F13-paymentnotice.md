# F13. PaymentNotice

#### F13R. RESOURCE
- Resources read: `PaymentNotice`, `PaymentReconciliation`, `Task`, inside a `Bundle` `type: collection`. Real notices also carry the provider and payer `Organization`s, which are not read.
- Profiles: none is required or checked on arrival. The live notices carry no `meta.profile` (only a `SUBSETTED` tag under `http://terminology.hl7.org/CodeSystem/v3-ObservationValue`) [SANDBOX](../references/PAYERS.md#markers).
- Direction: **received**, payer to provider, on NHCX route `v1/paymentnotice/request`, received by [G8. Receive](../gateway/G8-receive.md) and handled by C10. Answered by F14 (A8).

#### F13D. DESCRIPTION
The payer tells the facility money has moved. The three resources carry the story between them: the Task says what happened in words, the PaymentNotice the amount and status, the PaymentReconciliation the date, the UTR and the breakdown.

**Shapes that arrive**

| Sender | Entries |
|---|---|
| PMJAY and Sandbox Payer (see [PAYERS.md](../references/PAYERS.md)) [SANDBOX](../references/PAYERS.md#markers) | Task, PaymentNotice, PaymentReconciliation, provider Organization, payer Organization |
| Other payers seen [SANDBOX](../references/PAYERS.md#markers) | Task, PaymentNotice, PaymentReconciliation (identifiers untyped); PaymentNotice and PaymentReconciliation only; PaymentNotice only |

A bundle with neither a PaymentNotice nor a PaymentReconciliation is refused: "That is not a payment notice." Only the **first** resource of each type is read.

**Which claim.** The claim number is taken from, in order: the PaymentNotice's identifier typed `CLN`, the PaymentReconciliation's, the Task's, the first entry's. On each resource a typed `CLN` identifier wins; when none is typed `CLN`, the first identifier with **no `type` at all** is taken (one live payer sends the value untyped under a system that spells the resource name [SANDBOX](../references/PAYERS.md#markers)). The bundle's own `identifier` is never tried. The number is looked up as the current `D9 claim.claim_no`, else a historical `claim_ref` on `D20 claim_submission` then `D18 claim_preauth`. No match: outcome `unmatched`, nothing stored.

**Redelivery and updates.**
- A notice on a correlation id already in `D21 claim_payment.correlation_id` is `ignored`.
- A notice whose `PaymentNotice.id` matches `D21 claim_payment.notice_id` on the same claim is the same payment further along (initiated, then cleared): that row is overwritten, its details replaced, and its acknowledgement reset to `pending` so it is acknowledged again on the new thread.
- Otherwise a new row.

Every recorded notice is acknowledged at once (F14); a failed acknowledgement is kept on the row and the notice stays recorded.

**What counts as paid.** A row counts toward the paid total when `payment_status` is `paid` or `cleared` and it is not "initiated only" (no UTR and the disposition contains `initiat`). Rows sharing a UTR count once.

#### F13F. FIELDS
Read and stored (`D21 claim_payment` unless stated):

| Element path | Stored in | Notes |
|---|---|---|
| `PaymentNotice.identifier[type CLN]` (fallbacks above) | `claim_ref` | Match key |
| `PaymentNotice.id` | `notice_id` | Empty when absent (the live notices carry none [SANDBOX](../references/PAYERS.md#markers)) |
| `PaymentNotice.amount.value`, `.currency` | `amount`, `currency` | Else `PaymentReconciliation.paymentAmount` |
| `PaymentNotice.paymentStatus` first coding `code` | `payment_status` | `paid`, `adjusted`, `cleared`, ... |
| `PaymentReconciliation.disposition` | `disposition` | Else `Task.description`, else the paymentStatus display (or text), else `PaymentReconciliation.outcome`, else `Payment notice` |
| `PaymentReconciliation.paymentDate` | `payment_date` | Else the first 10 characters of `PaymentNotice.created` |
| `PaymentReconciliation.paymentIdentifier.value` | `utr` | Typed `UTR` by PMJAY; value may be `Not available` [PAYER](../references/PAYERS.md#markers) |
| `PaymentReconciliation.detail[]` | `D22 claim_payment_detail`, one row each | `seq` from 1 in order |
| `detail[].id`, else `detail[].identifier.value` | `D22 .reference` | |
| `detail[].type` first coding `code`, `display` (else text) | `D22 .type_code`, `.type_display` | `Payment`, `RF`, `Adjustment` |
| `detail[].date` | `D22 .date` | |
| `detail[].amount.value` | `D22 .amount` | |
| `Task.description` | `disposition` fallback only | |
| `Task` identifier | claim number fallback only | |
| `Organization` entries | not read | |
| header `x-hcx-correlation_id` | `correlation_id` | Also the acknowledgement's thread |
| header `x-hcx-sender_code` | `sender_code` | The acknowledgement goes back to it |
| header `x-hcx-workflow_id` | `workflow_id` | Echoed when the adapter names no ack workflow |
| whole bundle | `notice_json` | |
| (derived) | `claim_id`, `received_at` now, `ack_status` `pending` | |

Not read: `PaymentNotice.status`, `.payment`, `.recipient`, `.created` (except as date fallback); `PaymentReconciliation.status`, `.created`, `.identifier` (except as claim number fallback); the Task's code, intent, requester, owner, input.

#### F13U. USED BY
- Callbacks: [C10. Payment Notice](../callbacks/C10-paymentnotice-request.md)
- FHIR: [F14. Payment acknowledgement](F14-payment-acknowledgement.md)
