# A13. Transaction List

#### A13E. ENDPOINT
In-process: `ledger.list()`, a synchronous query of the [G9. Ledger](../gateway/G9-ledger.md). Nothing goes on the wire.

#### A13D. DESCRIPTION
Lists the G9 ledger, newest first. It is used for one thing: finding an NHCX or payer rejection addressed to one of our sends.

A rejection (for example `PAYR-1008` when the bundle's HFR ID does not match the registry id NHCX holds for the sender [PAYER](../references/PAYERS.md#markers)) arrives as a plain-JSON `ProtocolResponse`, not as an encrypted reply. [G8. Receive](../gateway/G8-receive.md) records the body's top-level `x-hcx-*` keys as the row's headers, so the rejection is linked by its correlation id and appears among A10's related rows. A10's reply lookup, though, looks only for a bundle carrying the reply resource and passes over a `ProtocolResponse`. So a poll that found no reply lists the ledger and looks for it by the `x-hcx-correlation_id` inside the stored body:

1. Keep rows with `direction` `in`, `type` equal to the leg's kind, and `created_at` not earlier than the leg's send time. Take the first 20 of them in the order G9 lists them (newest first).
2. Read each through A12. A body with `type` `ProtocolResponse`, `x-hcx-correlation_id` equal to the leg's correlation id and `x-hcx-status` `response.error` is the rejection.
3. The leg becomes `error` with `<x-hcx-error_details.code>: <x-hcx-error_details.message>` (`NHCX` and "The gateway rejected the request." when absent; the text names NHCX's gateway, not G).

The same rejection is applied at once when it arrives through the callback ([C1. Callback Door](../callbacks/C1-callback-door.md)); this is the polling half.

| Leg | Row `type` | Correlation | Since |
|---|---|---|---|
| Eligibility check (A2) | `coverageeligibility` | the case's | `checked_at` |
| Auth-requirements ruling (A2) | `coverageeligibility` | the ruling's | `requested_at` |
| Insurance plan (A3) | `insuranceplan` | the plan's | `requested_at` |
| Pre-authorisation (A4) | `preauth` | the pre-authorisation's | `submitted_at` |
| Predetermination (A4) | `preauth` | the quote's | `requested_at` |
| Claim (A5) | `claim` | the submission's | `submitted_at` |
| Cancellation (A6) | `task` | the cancel correlation | `cancel_requested_at` |
| Status, reprocess, release (A6) | `task` (status enquiries go out on the task route) | the enquiry's | `requested_at` |

On the pre-authorisation, predetermination, claim and enquiry legs this runs after the peer dispatch check (A11) and only when that found nothing. It runs before our own dispatch check (A11).

#### A13Q. REQUEST
No arguments.

```
ledger.list()
```

#### A13S. RESPONSE
An array of G9 ledger rows, newest first. The fields the app reads:

| Field | Meaning |
|---|---|
| `id` | the row id, passed to A12 |
| `direction` | `in` or `out` |
| `type` | the entity of the row's NHCX path: `coverageeligibility`, `insuranceplan`, `preauth`, `claim`, `task`, `communication`, `payment`, ... |
| `created_at` | when the row was written, compared as a time with the leg's send time |

```json
[{"id": "<row id>", "direction": "in", "type": "coverageeligibility", "created_at": "<timestamp>"}]
```

The stored body of a rejection row, as A12 returns it:

```json
{"fhir": {"type": "ProtocolResponse", "x-hcx-status": "response.error",
          "x-hcx-correlation_id": "<the leg's correlation id>",
          "x-hcx-error_details": {"code": "PAYR-1008", "message": "HFR ID mismatch"}}}
```

Errors: a G9 error from this call means "no rejection found", never a poll failure; the poll goes on to A11.

#### A13P. PSEUDOCODE

When: inside the A10 poll, after no reply was found (and, on the pre-authorisation, predetermination, claim and enquiry legs, after the peer dispatch check found nothing); on the cancellation leg only when no Task reply is on the thread. The loop is in A10P.

Data: the leg's row supplies `correlation_id` and the send time: [D9. claim](../database/D9-claim.md), [D10. claim_plan](../database/D10-claim-plan.md), [D13. claim_auth](../database/D13-claim-auth.md), [D18. claim_preauth](../database/D18-claim-preauth.md), [D19. claim_predetermination](../database/D19-claim-predetermination.md), [D20. claim_submission](../database/D20-claim-submission.md), [D29. claim_enquiry](../database/D29-claim-enquiry.md).

```text
PROTOCOL_REJECTION(correlation_id, since, kind):   # kind and since per leg, table in A13D
  if correlation_id is blank: return none
  try:
      rows = ledger.list()                        # G9 Ledger, in-process, newest first
  on G9 error:
      return none                                 # never a poll failure
  candidates = rows with direction == "in" and type == kind
               and (no since, or created_at not earlier than since)
  candidates = first 20 of them, in the listed order
  for entry in candidates:
      try:
          envelope = ledger.fhir(entry.id)          # A12
      on G9 error:
          continue
      body = envelope.fhir
      if body.type == "ProtocolResponse"
         and body."x-hcx-correlation_id" == correlation_id
         and body."x-hcx-status" == "response.error":
          code = body."x-hcx-error_details".code or "NHCX"
          message = body."x-hcx-error_details".message or "The gateway rejected the request."
          return code + ": " + message
  return none

On a rejection the poll writes the leg's refusal with that text (A10P WRITE_REFUSAL;
on the cancellation leg claim_preauth.status = "error", error_message = text)
and stops. With none, the poll goes on to the own dispatch check (A11P) on the
legs that have one; the predetermination and cancellation legs keep waiting.
```

#### A13U. USED BY
- Screens: [S3. Policy Discovery](../screens/S3-policy-discovery.md)
- APIs: [A2. Coverage Eligibility Check](A2-coverage-eligibility-check.md), [A3. Insurance Plan Request](A3-insurance-plan-request.md), [A4. Pre-auth Submit](A4-preauth-submit.md), [A5. Claim Submit](A5-claim-submit.md), [A6. Task Submit (cancel, status, reprocess, release)](A6-task-submit.md), [A10. Transaction Related](A10-txn-related.md), [A11. Transaction Dispatch](A11-txn-dispatch.md), [A12. Transaction FHIR](A12-txn-fhir.md), [A17. Claim State](A17-claim-state.md)
- Callbacks: [C1. Callback Door](../callbacks/C1-callback-door.md)
- Gateway: [G1. Embedding](../gateway/G1-embedding.md), [G9. Ledger](../gateway/G9-ledger.md)
- Tests: [T1. Test Configuration](../tests/T1-test-configuration.md), [T2. Test Runners](../tests/T2-test-runners.md)
