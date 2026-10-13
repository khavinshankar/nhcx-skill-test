# F14. Payment acknowledgement

#### F14R. RESOURCE
- `resourceType`: `Task` in a `Bundle` (`type: collection`), followed by the provider and payer `Organization`s (F17).
- Profiles in `meta.profile`: bundle `https://nrces.in/ndhm/fhir/r4/StructureDefinition/TaskBundle`; Task `https://nrces.in/ndhm/fhir/r4/StructureDefinition/Task`; Organizations `.../StructureDefinition/Organization`.
- Direction: **sent**, on NHCX route `v1/paymentnotice/on_request`, sent by A8 through [G7. Send](../gateway/G7-send.md), on the payment notice's own correlation id.

#### F14D. DESCRIPTION
Tells the payer the money was seen. One per recorded payment notice (F13): sent automatically the moment the notice is recorded, again when a later notice updates the same payment, and by hand from the payments screen when the last attempt is pending or failed. The acknowledgement is a status Task: `completed`, coded `status`, with the output `paymentack` and the claim number.

Built the same way for every payer; only the envelope headers differ (A8): the workflow id is the adapter's `payment_ack` (see [PAYERS.md](../references/PAYERS.md)) [PAYER](../references/PAYERS.md#markers), else the notice's own workflow id, else the claim number [REF](../references/PAYERS.md#markers).

Refusals: "Payment notice not found."; "Set the facility's HFR ID and NHCX participant code under Settings first."

The claim number used is the one the notice named (`D21 claim_payment.claim_ref`), else the current `D9 claim.claim_no`.

#### F14F. FIELDS
**Bundle**

| Element path | Value or source | Notes |
|---|---|---|
| `id` | `payment-notice-ack-generic` | constant [REF](../references/PAYERS.md#markers) |
| `meta.profile` | `.../StructureDefinition/TaskBundle` | |
| `type` | `collection` | |
| `identifier`, `timestamp` | not set | |
| `entry[0]` | Task at `https://nhcx.abdm.gov.in/payment/notice-ack` | |
| `entry[1]` | provider Organization at `https://nhcx.abdm.gov.in/provider` | F17: NPI = `D1 organization.identifier_value`, name `D1 organization.name` |
| `entry[2]` | payer Organization at `https://nhcx.abdm.gov.in/payer` | F17: NIIP = `D9 claim.payer_id` (else the configured default payer code) without `@hcx`; name `D9 claim.payer_name` (else the configured default payer name) |

**Task**

| Element path | Value or source | Notes |
|---|---|---|
| `meta.profile` | `.../StructureDefinition/Task` | no `id` |
| `status` | `completed` | |
| `intent` | `order` | |
| `code` | `status` under `http://terminology.hl7.org/CodeSystem/financialtaskcode` | no display |
| `authoredOn` | now | |
| `requester` | `https://nhcx.abdm.gov.in/provider` | |
| `owner` | `https://nhcx.abdm.gov.in/payer` | |
| `description` | `Received the payment for claim <claim number>` | |
| `output[0].type` | `status` "Status" under `https://nrces.in/ndhm/fhir/r4/CodeSystem/ndhm-task-output-type` | |
| `output[0].valueCodeableConcept` | `paymentack` "Payment is acknowledged" under `https://nrces.in/ndhm/fhir/r4/CodeSystem/ndhm-task-output-value` | |
| `output[1].type` | `claimNumber` "ClaimNumber" under `https://nrces.in/ndhm/fhir/r4/CodeSystem/ndhm-task-input-type-code` | |
| `output[1].valueString` | the claim number | |

Not set: `input`, `reasonCode`, `basedOn`, `focus`. The Task does not point at the payer's PaymentNotice; the correlation id in the header ties them.

After the send, `D21 claim_payment` gets `ack_status` `sent`, `ack_txn_id`, `ack_correlation_id`, `acknowledged_at`; on failure `ack_status` `error` and `ack_error`.

#### F14U. USED BY
- APIs: [A8. Payment Notice Acknowledgement](../apis/A8-paymentnotice-on-request.md)
- FHIR: [F1. Bundle](F1-bundle.md), [F10. Task (claim actions)](F10-task-claim-actions.md), [F13. PaymentNotice](F13-paymentnotice.md), [F17. Organization](F17-organization.md)
