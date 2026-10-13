# C5. Pre-auth Reply

#### C5E. ENDPOINT
Delivered in-process by [G8. Receive](../gateway/G8-receive.md) for NHCX route `v1/preauth/on_submit`, passed to `C1.receive` with `delivery.type` `preauth`. Answers A4 in all its sends: a pre-authorisation, a query answer, an enhancement, an enhancement query answer, and a predetermination (quote).

#### C5D. DESCRIPTION
A pre-authorisation is answered several times on one correlation id: an acknowledgement (PMJAY workflow `20`, `outcome: queued`), sometimes a query, then the decision (workflow `21`) [PAYER](../references/PAYERS.md#markers). Every reply the leg has not already taken in is applied; a guard that refused anything after the first reply would throw the approval away.

**Matching.** By `x-hcx-correlation_id` against the pre-authorisation (D18 `correlation_id`, newest row). When none matches, against the predetermination quotes (D19 `correlation_id`, newest row). Neither: `unmatched`.

**Redelivery.** On the pre-authorisation, the same `x-hcx-api_call_id` as the last applied reply is a redelivery (`ignored`). The `redelivery` flag G8 takes from [G9. Ledger](../gateway/G9-ledger.md) is not used for this: the leg's own `api_call_id` decides. Without an api_call_id, a reply with the same outcome and adjudication as the leg already holds is treated as the same message, unless the leg is still `submitting`. On a quote, anything after the first answer is `ignored`.

**Legs that have moved on.** A `cancelled` pre-authorisation ignores every reply. While a cancel is out (`cancelling`), only a ClaimResponse adjudicated `cancelled` is applied, as the payer confirming the withdrawal on the pre-authorisation's own thread; anything else is left for the cancel Task (C7).

**Errors.** A reply that is an error (`response.error` on the envelope, `ClaimResponse.error`, or an `error` outcome that is not a rejection, [F9. ClaimResponse](../fhir/F9-claimresponse.md)) is not a decision. The leg goes to `error` with the payer's errors, disposition and process notes as its message, nothing else on it changes, and the same send is offered again. An enhancement in error leaves the approved pre-authorisation standing, as a refusal at the door does.

**Status by workflow id.** The reply's `x-hcx-workflow_id` gives the status when it is one of the payer-side codes (20 acknowledgement, 21 or 22 approved, 23 or 231 rejected, 24 or 241 queried, see [PAYERS.md](../references/PAYERS.md)) [PAYER](../references/PAYERS.md#markers); otherwise the bundle does. So a reply under 20 is an acknowledgement whatever its ClaimResponse restates, and the screen shows the case as under adjudication.

**Failed sends.** A leg whose send was reported failed (C1 `failed_send`) is reopened as `submitting` when the payer answers it, then the reply applied.

**A denied enhancement.** A rejection that answers an enhancement leg denies the enhancement only: the approved pre-authorisation keeps its status, its approved amount and every other approval column (`request_json` of the last accepted send, `eligible_amount`, `outcome`, `adjudication`, `disposition`, `preauth_ref`, `items_json`, `settled_at`); the payer's reason is recorded in `error_message`, the reply in `response_json`, and nothing is added to the approved total (D18, A4). Only a rejection of the pre-authorisation itself ends the leg `rejected`.

#### C5Q. REQUEST
`fhir` is an F1 Bundle carrying the payer's F9 ClaimResponse (`use: preauthorization`, or `predetermination` for a quote), usually beside F15 Patient, F17 Organizations and F18 Coverage; some payers send the ClaimResponse alone.

A pre-authorisation usually gets two replies on its thread: an acknowledgement, which leaves the leg `submitting`, then the decision, which settles it. Refusals arrive as a `ProtocolResponse` (for example PAYR-1255, PAYR-1008 [PAYER](../references/PAYERS.md#markers)).

#### C5P. PSEUDOCODE

```
C5(envelope, corr):
    row = newest D18 where correlation_id == corr
    if none: return quote(envelope, corr)
    if row.status == "cancelled": return "ignored"
    body = payload(envelope)
    if body.type == "ProtocolResponse":
        leg_write(D18, row, door_refusal(row, rejection(body)))
        return "settled"
    parsed = read_claim_response(body)
    if row.status == "cancelling":
        if parsed.adjudication == "cancelled":
            leg_write(D18, row, {status: "cancelled", settled_at: now, error_message: null,
                                 outcome, adjudication, disposition,
                                 api_call_id: x-hcx-api_call_id or null, response_json: body})
            return "settled"
        return "ignored"
    api_call_id = x-hcx-api_call_id or ""
    if already_applied(row, api_call_id, parsed): return "ignored"
    revive(D18, row, "submitting")
    status = status_on(envelope, parsed)
    if status == "error":
        # shown, never obeyed: nothing is decided and the send is offered again
        leg_write(D18, row, door_refusal(row, error_text(parsed)) +
                            {api_call_id: api_call_id or null, response_json: body})
        return "settled"
    if status == "rejected" and row.submission_kind in {enhancement, enhancement_resubmit}:
        # PMJAY denies the enhancement only (workflow 231): the approved
        # pre-authorisation and its amounts stand. The denial is kept as the
        # payer's reason, and the enhancement's amount is not added.
        # the approval's own columns were not cleared by the enhancement send (D18), so
        # they are not touched here; the status goes back to what those columns say
        leg_write(D18, row, {status: "partial" if (row.outcome == "partial" and row.adjudication == "approved") else "approved",
                             error_message: parsed.reason or disposition,
                             api_call_id: api_call_id or null,
                             response_json: body})      # the denial lives in error_message; D18 has no enhancement_status column
        return "settled"
    values = parsed, dropping preauth_ref when the reply carries none (the stored one stays)
    leg_write(D18, row, values + {status,
        api_call_id: api_call_id or null,
        settled_at: null if status == "submitting" else now,
        error_message: null, response_json: body,
        thread_correlation_id: row.correlation_id})     # the thread the case lives on
    return "settled"

door_refusal(row, message):
    values = {status: "error", error_message: message}
    if row.submission_kind in {enhancement, enhancement_resubmit}:
        values.status = "approved"                      # the approved pre-auth stands
    if row.thread_correlation_id: values.correlation_id = row.thread_correlation_id
    return values

quote(envelope, corr):
    row = newest D19 where correlation_id == corr
    if none: return "unmatched"
    if row.status != "asking" and not failed_send(row): return "ignored"
    body = payload(envelope)
    if body.type == "ProtocolResponse":
        write D19: status = "error", error_message = rejection(body)
        return "settled"
    revive(D19, row, "asking")
    parsed = read_claim_response(body)
    write D19: status = "answered", answered_at = now, error_message = null,
               outcome, adjudication, disposition,
               allowed_amount = parsed.approved_amount, response_json = body
    return "settled"

read_claim_response(body):
    cr = first ClaimResponse in body.entry
    if none: raise Rejected("The payer reply carries no ClaimResponse.")
    adjudication = lower(first claim-level adjudication[].reason code whose category is
                         "status", else the first reason code at all), or null
    totals = total[] by category code, lower case             # never by position
    return {outcome, adjudication, disposition, preauth_ref: preAuthRef,
            approved_amount: totals.benefit, eligible_amount: totals.eligible,
            submitted_amount: totals.submitted,
            items_json: per item: sequence, and by adjudication category
                        eligible (amount), status (reason code or display), reason (payer words),
                        eligpercent, eligquant (value), deductible (amount, reason code and display),
                        benefit, submitted (amount),
            errors: error[].code as "<code>: <display or text>",
            notes: every processNote[].text,
            query_note: the "reason" item adjudications' displays split on "|" [PAYER](../references/PAYERS.md#markers),
                        each piece stripped of a leading ":", pieces that are then empty,
                        only dots, or null / none / nil / "-" dropped, joined " · ",
                        plus every processNote[].text; distinct lines joined by newline}

status_on(envelope, parsed):                                   // the envelope first, then the bundle
    if parsed.errors or x-hcx-status == "response.error" or verdict_status(parsed) == "error":
        return "error"
    by_workflow = {20, 25, 18, 251, 28, 29, 37: "submitting"; 21, 22, 26, 252: "approved";
                   23, 231, 291, 253: "rejected"; 24, 241, 27, 254: "queried"}[x-hcx-workflow_id]
    if by_workflow:
        if by_workflow == "approved" and verdict_status(parsed) == "partial": return "partial"
        return by_workflow
    return verdict_status(parsed)

error_text(parsed):
    lines = parsed.errors + [disposition unless empty or "ok"] + parsed.notes
    return lines joined by newline, or "The payer answered with an error and gave no reason"

verdict_status(parsed):
    o = lower(outcome); r = lower(adjudication)
    if o in {queued, acknowledged} or r in {submitted, acknowledged}: return "submitting"
    if r in {cancelled, rejected, denied}: return "rejected"   // corrected: the reference read a `rejected` reason as queried
    if r == "queried":   return "queried"
    if o == "error" or parsed.errors: return "error"
    if o == "partial":   return "partial" if r == "approved" else "queried"
    if o == "complete":  return "approved" if r in {approved, ""} else "queried"
    return "queried"
```

#### C5S. RESPONSE
`settled`, `unmatched`, `ignored` (redelivery, cancelled leg, a non-cancel reply while cancelling, a quote no longer `asking`), or `rejected` when the bundle carries no ClaimResponse.

State changes, D18 claim_preauth (each write restamps D9 `stage` / `sub_stage`):

| Reply | `status` | Columns |
|---|---|---|
| acknowledgement (`queued`, `submitted`) | `submitting` | parsed columns, `api_call_id`, `settled_at` null, `response_json`, `thread_correlation_id` |
| decision | `approved`, `partial`, `queried` or `rejected` | as above, `settled_at` now |
| error (`response.error`, `ClaimResponse.error`, an `error` outcome) | `error`, or `approved` for an enhancement | `error_message` the payer's errors, disposition and process notes, one per line; `api_call_id`, `response_json`. The send is offered again |
| ClaimResponse adjudicated `cancelled` while `cancelling` | `cancelled` | `outcome`, `adjudication`, `disposition`, `api_call_id`, `settled_at`, `response_json`. The claim number is not retired here (C7 does that) |
| `ProtocolResponse` | `error`, or `approved` for an enhancement | `error_message` `<code>: <message>`; `correlation_id` back to `thread_correlation_id` when one is held |

Parsed columns: `outcome`, `adjudication`, `disposition`, `preauth_ref`, `approved_amount`, `eligible_amount`, `submitted_amount`, `items_json`, `query_note`.

D19 claim_predetermination: `answered` whatever the outcome, with `outcome`, `adjudication`, `disposition`, `allowed_amount` (the `benefit` total), `answered_at`, `response_json`; or `error` with `<code>: <message>`. Nothing on the pre-authorisation changes.

#### C5U. USED BY
- Screens: [S9. Pre-authorisation](../screens/S9-preauthorisation.md)
- APIs: [A4. Pre-auth Submit](../apis/A4-preauth-submit.md), [A7. Communication Reply](../apis/A7-communication-on-request.md), [A10. Transaction Related](../apis/A10-txn-related.md), [A12. Transaction FHIR](../apis/A12-txn-fhir.md), [A17. Claim State](../apis/A17-claim-state.md)
- Callbacks: [C1. Callback Door](C1-callback-door.md), [C6. Claim Reply](C6-claim-on-submit.md), [C7. Cancel Reply](C7-cancel-on-submit.md), [C8. Enquiry Reply](C8-enquiry-on-submit.md), [C9. Payer Communication](C9-communication-request.md)
- Database: [D18. claim_preauth](../database/D18-claim-preauth.md), [D19. claim_predetermination](../database/D19-claim-predetermination.md)
- Tests: [T5. IRDAI Pre-authorisation Approved](../tests/T5-irdai-preauth-approved.md), [T6. IRDAI Pre-authorisation Rejected and Sent Again](../tests/T6-irdai-preauth-rejected.md), [T7. IRDAI Query Answered](../tests/T7-irdai-query-answered.md), [T8. IRDAI Enhancement](../tests/T8-irdai-enhancement.md), [T9. IRDAI Status Enquiry and Cancel](../tests/T9-irdai-cancel-and-status.md), [T14. PMJAY Pre-authorisation Through the Payer Service](../tests/T14-pmjay-preauth-adjudicated.md), [T15. PMJAY Query Answered by Resubmission](../tests/T15-pmjay-query-by-resubmission.md), [T16. PMJAY Rejection and Enhancement](../tests/T16-pmjay-rejection-and-enhancement.md)
