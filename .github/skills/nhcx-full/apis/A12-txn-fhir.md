# A12. Transaction FHIR

#### A12E. ENDPOINT
In-process: `ledger.fhir(txn_id)`, a synchronous query of the [G9. Ledger](../gateway/G9-ledger.md). Nothing goes on the wire.

#### A12D. DESCRIPTION
Returns the stored, decrypted envelope of one G9 ledger row: its protocol headers and its FHIR payload (decrypted by [G6. Encryption](../gateway/G6-encryption.md) when [G8. Receive](../gateway/G8-receive.md) took it in). A10 and A13 only list rows; this is how a poll reads what a row actually says.

Where it is called:
- Newest-reply legs (eligibility, plan, ruling, pre-authorisation, predetermination, claim, enquiries): for each inbound row from A10 not sent by the facility's own participant code, newest first, until one carries the resource the reply is made of (`CoverageEligibilityResponse`, `InsurancePlan`, `ClaimResponse` or `Task`, see A10). The first match is the reply; the rest are not read.
- Cancellation: for every Task reply on the thread in both directions (our own sends and repeated `api_call_id`s skipped), newest first; all are read and parsed so an acceptance can win over a refusal.
- Protocol rejections (A13): for each candidate inbound row, to look inside the stored body for a `ProtocolResponse` on this correlation id.

The envelope read here is applied exactly as if it had arrived through the callback ([C1. Callback Door](../callbacks/C1-callback-door.md)): the same parsers, the same statuses. The envelope's `x-hcx-api_call_id` is kept on the pre-authorisation and claim legs to tell a new reply from a redelivery.

Reply: [C2. Coverage Eligibility Verdict](../callbacks/C2-coverage-eligibility-on-check.md), [C3. Authorisation Requirements Ruling](../callbacks/C3-auth-requirements-on-check.md), [C4. Insurance Plan Reply](../callbacks/C4-insuranceplan-on-request.md), [C5. Pre-auth Reply](../callbacks/C5-preauth-on-submit.md), [C6. Claim Reply](../callbacks/C6-claim-on-submit.md), [C7. Cancel Reply](../callbacks/C7-cancel-on-submit.md), [C8. Enquiry Reply](../callbacks/C8-enquiry-on-submit.md).

#### A12Q. REQUEST

The argument passed to G9 fhir:

| Field | Type | Required | Value |
|---|---|---|---|
| `txn_id` | string | yes | a row `id` from A10 or A13 |

```
ledger.fhir("01CANCEL-NO")
```

#### A12S. RESPONSE
The envelope as an object (G9 also returns `meta`: direction, payload kind, path, time; not read):

| Field | Meaning |
|---|---|
| `jwe_headers` | the `x-hcx-*` protocol headers (`x-hcx-api_call_id`, `x-hcx-correlation_id`, `x-hcx-status`, `x-hcx-workflow_id`, sender and recipient codes, ...) |
| `fhir` | the payload: a FHIR Bundle ([F1. Bundle](../fhir/F1-bundle.md)), or a plain `ProtocolResponse`; `null` when the ledger stores no bodies or the message was refused before decryption (the row is then skipped) |
| `payload` | read in place of `fhir` when `fhir` is absent (reply lookups only; the protocol-rejection scan reads `fhir` only). G9 has no `payload` key, so this fallback is not reached |

```json
{
 "jwe_headers": {
  "x-hcx-api_call_id": "cd2395e9-a9a0-467c-86a4-d70f960c2843",
  "x-hcx-correlation_id": "a47400d6-0dfd-47d5-ab42-0d5578173c6a",
  "x-hcx-sender_code": "<payer code>",
  "x-hcx-recipient_code": "<facility code>",
  "x-hcx-status": "response.complete",
  "x-hcx-workflow_id": "NM-26-0SH000004"
 },
 "fhir": {"resourceType": "Bundle", "entry": ["..."]}
}
```

How it is read: a row whose payload is not a JSON object, or carries no entry of the resource looked for, is skipped and the next row is read. In the protocol-rejection scan a G9 error skips that row. On the reply lookups a G9 error is a poll failure (A10).

#### A12P. PSEUDOCODE

When: inside the A10 poll (reply lookups, cancellation) and the A13 scan. The loop is in A10P.

Data: [D1. organization](../database/D1-organization.md), [D18. claim_preauth](../database/D18-claim-preauth.md), [D20. claim_submission](../database/D20-claim-submission.md).

```text
FIND_REPLY(related, resource_type):               # every newest-reply leg
  own = facility participant code, trimmed, lower case (organization, D1)
  inbound = rows of related with direction == "in" and lower(trim(sender)) != own
  for entry in inbound, newest first (the order G9 lists them):
      envelope = ledger.fhir(entry.id)            # G9 Ledger, in-process
      on G9 error: raise                          # poll failure, text goes to poll_notes (A17)
      bundle = envelope.fhir, else envelope.payload
      if bundle is not an object: continue
      if any bundle.entry[].resource.resourceType == resource_type:
          return envelope, bundle                 # the reply; later rows are not read
  return none

TASK_REPLIES(related):                            # cancellation leg
  own = as above; seen = empty set; out = []
  for entry in related, newest first, both directions:
      if lower(trim(entry.sender)) == own: continue
      key = entry.api_call_id or entry.id
      if key in seen: continue
      add key to seen
      envelope = ledger.fhir(entry.id)            # on G9 error: raise
      bundle = envelope.fhir, else envelope.payload
      if bundle is an object and any bundle.entry[].resource.resourceType == "Task":
          append (envelope, bundle) to out
  return out                                      # every Task reply, newest first

In PROTOCOL_REJECTION (A13P) each candidate row is read the same way, but a
failure of this call skips the row, and only envelope.fhir is looked at.

After a match: the bundle is applied as C2 to C8 (A10P table). On the
pre-authorisation and claim legs envelope.jwe_headers."x-hcx-api_call_id" is
passed along and stored on the leg (claim_preauth D18, claim_submission D20).
```

#### A12U. USED BY
- Screens: [S3. Policy Discovery](../screens/S3-policy-discovery.md)
- APIs: [A4. Pre-auth Submit](A4-preauth-submit.md), [A5. Claim Submit](A5-claim-submit.md), [A6. Task Submit (cancel, status, reprocess, release)](A6-task-submit.md), [A10. Transaction Related](A10-txn-related.md), [A13. Transaction List](A13-txn-list.md), [A17. Claim State](A17-claim-state.md)
- FHIR: [F1. Bundle](../fhir/F1-bundle.md)
- Database: [D18. claim_preauth](../database/D18-claim-preauth.md)
- Gateway: [G7. Send](../gateway/G7-send.md), [G9. Ledger](../gateway/G9-ledger.md)
