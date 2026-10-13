# C6. Claim Reply

#### C6E. ENDPOINT
Delivered in-process by [G8. Receive](../gateway/G8-receive.md) for NHCX route `v1/claim/on_submit`, passed to `C1.receive` with `delivery.type` `claim`. Answers A5 (a claim, a query answer, a resubmission).

#### C6D. DESCRIPTION
The payer's verdict on the claim, read exactly as a pre-authorisation reply (C5): the same ClaimResponse reading, the same verdict mapping, several replies per thread (PMJAY acknowledges under workflow `25`, decides under `26` [PAYER](../references/PAYERS.md#markers)). The status follows the reply's workflow id when it is a payer-side code (25 acknowledgement, 26 approved, 27 queried, 291 rejected) and the bundle otherwise, as in C5.

**Errors.** A reply that is an error (`response.error`, `ClaimResponse.error`, or an `error` outcome that is not a rejection, [F9. ClaimResponse](../fhir/F9-claimresponse.md)) decides nothing: the leg goes to `error` with the payer's words, and the claim can be sent again as the same kind.

**Matching.** By `x-hcx-correlation_id` against the claim leg (D20 `correlation_id`, newest row). Nothing matching: `unmatched`.

**Redelivery.** The same `x-hcx-api_call_id` as the last applied reply is `ignored`; without one, a reply with the same outcome and adjudication as the leg holds, on a leg not `submitting`. After a reprocess (C8) the leg waits again on the same thread, and a verdict carrying a new api_call_id is applied. The `redelivery` flag G8 takes from [G9. Ledger](../gateway/G9-ledger.md) is not used for this: the leg's own `api_call_id` decides.

Unlike C5 there is no status gate: any reply not already applied is applied, whatever the leg's status. A leg on record as a failed send (C1 `failed_send`) is reopened as `submitting` first.

#### C6Q. REQUEST
`fhir` is an F1 Bundle carrying the payer's F9 ClaimResponse (`use: claim`), usually beside F15 Patient, F17 Organizations and F18 Coverage.

Refusals arrive as a `ProtocolResponse` (for example PAYR-1322 [PAYER](../references/PAYERS.md#markers)).

#### C6P. PSEUDOCODE

```
C6(envelope, corr):
    row = newest D20 where correlation_id == corr
    if none: return "unmatched"
    body = payload(envelope)
    if body.type == "ProtocolResponse":
        leg_write(D20, row, claim_door_refusal(row, rejection(body)))
        return "settled"
    parsed = read_claim_response(body)                  # C5; rejected when no ClaimResponse
    api_call_id = x-hcx-api_call_id or ""
    if already_applied(row, api_call_id, parsed): return "ignored"
    revive(D20, row, "submitting")
    status = status_on(envelope, parsed)                # C5: workflow id first, then the bundle
    if status == "error":
        leg_write(D20, row, claim_door_refusal(row, error_text(parsed)) +
                            {api_call_id: api_call_id or null, response_json: body})
        return "settled"
    leg_write(D20, row, parsed + {status,
        api_call_id: api_call_id or null,
        settled_at: null if status == "submitting" else now,
        error_message: null, response_json: body,
        thread_correlation_id: row.correlation_id})
    return "settled"

claim_door_refusal(row, message):
    values = {status: "error", error_message: message}
    if row.submission_kind == "claim_query_response":
        values.status = "queried"                        # the query still stands
        values.disposition = row.disposition or row.query_note
    if row.thread_correlation_id: values.correlation_id = row.thread_correlation_id
    return values
```

#### C6S. RESPONSE
`settled`, `unmatched`, `ignored` for a redelivery, or `rejected` when the bundle carries no ClaimResponse.

State changes, D20 claim_submission (each write restamps D9 `stage` / `sub_stage`):

| Reply | `status` | Columns |
|---|---|---|
| acknowledgement | `submitting` | `outcome`, `adjudication`, `disposition`, `preauth_ref`, `approved_amount`, `eligible_amount`, `submitted_amount`, `items_json`, `query_note`, `api_call_id`, `settled_at` null, `response_json`, `thread_correlation_id` |
| decision | `approved`, `partial`, `queried` or `rejected` | as above, `settled_at` now |
| error (`response.error`, `ClaimResponse.error`, an `error` outcome) | `error`, or `queried` for a query answer | `error_message` the payer's errors, disposition and process notes; `api_call_id`, `response_json`. The send is offered again |
| `ProtocolResponse` | `error`, or `queried` for a query answer (question restored in `disposition`) | `error_message` `<code>: <message>`; `correlation_id` back to `thread_correlation_id` when one is held |

A reply without `preAuthRef` writes `preauth_ref` empty here (only C5 keeps the stored one).

#### C6U. USED BY
- Screens: [S11. Claim Submission](../screens/S11-claim-submission.md)
- APIs: [A5. Claim Submit](../apis/A5-claim-submit.md), [A7. Communication Reply](../apis/A7-communication-on-request.md), [A10. Transaction Related](../apis/A10-txn-related.md), [A12. Transaction FHIR](../apis/A12-txn-fhir.md), [A17. Claim State](../apis/A17-claim-state.md)
- Callbacks: [C1. Callback Door](C1-callback-door.md), [C8. Enquiry Reply](C8-enquiry-on-submit.md), [C9. Payer Communication](C9-communication-request.md)
- Database: [D20. claim_submission](../database/D20-claim-submission.md)
- Tests: [T10. IRDAI Claim Approved, Part-approved and Rejected](../tests/T10-irdai-claim.md), [T12. IRDAI Reprocess and Balance Release](../tests/T12-irdai-reprocess-and-release.md), [T17. PMJAY Claim Through the Role Walk](../tests/T17-pmjay-claim-adjudicated.md)
