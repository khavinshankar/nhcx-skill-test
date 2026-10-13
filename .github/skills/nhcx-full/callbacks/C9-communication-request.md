# C9. Payer Communication

#### C9E. ENDPOINT
Delivered in-process by [G8. Receive](../gateway/G8-receive.md) for NHCX route `v1/communication/request`, passed to `C1.receive` with `delivery.type` `communication`. Payer-initiated: a query is answered by A7 (reply), a notification is acknowledged by A7 automatically, a note takes no answer.

#### C9D. DESCRIPTION
The payer speaking first, on a thread the payer mints, so nothing here waits on the message's correlation id. Three kinds are filed on the case:

| Bundle carries | Filed as | Effect |
|---|---|---|
| a CommunicationRequest, classified as a query | `query`, `open` | the case shows `queried` while the leg is with the payer; the desk answers through A7 |
| a CommunicationRequest, classified as a notification | `notification` | acknowledged at once through A7; the case is untouched |
| a Communication and no CommunicationRequest | `note`, `noted` | shown, never acted on; nothing goes back |

**Classification** (by the sender's payer adapter: `x-hcx-sender_code` when present, else the case's payer; an unknown sender gets the generic adapter; query modes in [PAYERS.md](../references/PAYERS.md)) [PAYER](../references/PAYERS.md#markers). A `resubmit`-mode payer (PMJAY) queries inside the ClaimResponse (C5, C6), so every CommunicationRequest from it is a notification [PAYER](../references/PAYERS.md#markers). For a `communication`-mode payer: Task `intent` `proposal` is a notification and `order` a query; with no intent, a Task reason code of empty, `additionalinfo`, `questionnaire` or `query` is a query and anything else a notification [REF](../references/PAYERS.md#markers).

**Matching**, first hit wins:
1. each claim reference the resource names (reference, its last path segment, display, identifier value; from `about`, `basedOn`, `identifier` on a request, plus `inResponseTo` and `partOf` on a note) against the case number (D9 `claim_no`), then the number a leg went out under (D20 `claim_ref`, then D18 `claim_ref`), because a cancel retires a number;
2. each reference against a payer request already held (D23 `request_id`), which also gives the leg;
3. the message's correlation id against any leg (C1 `claim_for_correlation`);
4. `x-hcx-workflow_id` against the claim leg's correlation id (D20), then the pre-authorisation's (D18). This names the leg asked about even when an earlier step found the case, and finds the case when nothing else did.

The leg (`stage`) is the one step 2 or 4 named; otherwise `claim` when a claim has been filed (D20 status not `draft`), else `preauth`.

**Redelivery.** A request whose correlation id is already on a D23 row is `ignored`. A note is `ignored` when the same Communication id is already filed as a note on that case. A `ProtocolResponse` is `ignored`.

Archiving (C1) happens before matching and reads less: only a `CLN`-typed identifier, a display or a reference. A message that names the case some other way (an untyped identifier, or only the workflow id) is filed under the `unmatched` folder even when it settles.

#### C9Q. REQUEST
`fhir` is an F1 TaskBundle: a Task (`code` `poll`, `intent`, `reasonCode`) whose `input` points at an F11 CommunicationRequest, with F17 Organizations and sometimes the Claim, F15 Patient, F16 Practitioner and F18 Coverage it is about. A note carries a Communication instead. Every `payload[].contentString` is one thing asked for.

A policy-wide notification (Task `intent: proposal`, for example reason `policychange`) names no case, so it is usually `unmatched`.

#### C9P. PSEUDOCODE

```
C9(envelope, corr):
    body = payload(envelope)
    if body.type == "ProtocolResponse": return "ignored"
    carried = resourceType of every entry
    sender = jwe_headers["x-hcx-sender_code"] or ""
    workflow = jwe_headers["x-hcx-workflow_id"] or ""
    if "CommunicationRequest" in carried: return record_query(body, corr, sender, workflow)
    if "Communication" in carried:        return record_note(body, corr, sender, workflow)
    return "ignored"

record_query(body, corr, sender, workflow):
    request = first CommunicationRequest; task = first Task (may be none)
    references = names(request, about, basedOn, identifier)
    questions = request.payload[].contentString
                else request.reasonCode[].text
                else [task.description]                          # distinct, non-empty
    reason = task.reasonCode first coding code, else its text
    intent = lower(task.intent)
    if corr and a D23 row has correlation_id == corr: return "ignored"
    claim, stage = match_claim(references, corr, workflow)
    if none: return "unmatched"
    stage = stage or leg_asked_about(claim)
    adapter = adapter_for(sender) if sender else adapter of the case's payer
    kind = classify(adapter, reason, intent)                     # "query" | "notification"
    id = insert D23 {claim_id, stage, kind,
                     reason_code: normalised reason ("claimarbitartion" -> "claimarbitration") [SANDBOX](../references/PAYERS.md#markers),
                     correlation_id: corr or null, request_id: request.id,
                     claim_ref: first reference without "/", sender_code, workflow_id,
                     received_at: now, status: "open",
                     remarks: questions joined by newline, questions: JSON list,
                     request_json: body}
    if kind == "query":
        restamp the case stage                                   # open query -> sub_stage "queried"
    else:
        try: send the acknowledgement through A7
             write D23: status "acknowledged", error_message null, reply_txn_id,
                        reply_correlation_id, acknowledged_at, reply_json
        except a G7 send error:
             write D23: status "error", error_message, and reply_txn_id /
                        reply_correlation_id when the error named them   # never raised
    return "settled"

record_note(body, corr, sender, workflow):
    note = first Communication; task = first Task (may be none)
    references = names(note, about, basedOn, inResponseTo, partOf, identifier)
    lines = payload contentString; "Attachment: <title or contentType>" (or "Attachment")
            per contentAttachment; note[].text                   # distinct
    claim, stage = match_claim(references, corr, workflow)
    if none: return "unmatched"
    if note.id and a D23 row on that claim has kind "note" and request_id == note.id:
        return "ignored"
    thread = corr unless a D23 row already holds it
    insert D23 {claim_id, stage: stage or leg_asked_about(claim), kind: "note",
                reason_code: task's reason, else the Communication's,
                correlation_id: thread, request_id: note.id, claim_ref, sender_code,
                workflow_id, received_at, status: "noted", remarks, questions, request_json}
    return "settled"

leg_asked_about(claim):
    return "claim" if the case has a D20 row whose status is set and not "draft" else "preauth"
```

A request or note that cannot be read raises `The payer message carries no CommunicationRequest.` / `The payer message carries no Communication.` (`rejected`); in practice the dispatch above only calls each when its resource is present.

#### C9S. RESPONSE
`settled` for a new query, notification or note; `unmatched` when nothing here answers to what it names; `ignored` for a redelivery, a `ProtocolResponse`, or a bundle with neither resource. A failed automatic acknowledgement is still `settled`, so G8 accepts the message.

State changes, D23 claim_query (one new row):

| Kind | `status` | Notes |
|---|---|---|
| `query` | `open` | D9 `stage` / `sub_stage` restamped: an open query on a leg with the payer shows `queried` |
| `notification` | `acknowledged`, or `error` when the A7 send failed | `reply_txn_id`, `reply_correlation_id`, `acknowledged_at`, `reply_json` |
| `note` | `noted` | `correlation_id` left empty when an earlier row already holds that thread |

The pre-authorisation (D18) and claim (D20) legs themselves are not written.

#### C9U. USED BY
- Screens: [S10. Communication](../screens/S10-communication.md)
- APIs: [A7. Communication Reply](../apis/A7-communication-on-request.md)
- Callbacks: [C1. Callback Door](C1-callback-door.md)
- FHIR: [F11. CommunicationRequest](../fhir/F11-communicationrequest.md)
- Database: [D23. claim_query](../database/D23-claim-query.md)
- Gateway: [G7. Send](../gateway/G7-send.md)
- Tests: [T7. IRDAI Query Answered](../tests/T7-irdai-query-answered.md), [T15. PMJAY Query Answered by Resubmission](../tests/T15-pmjay-query-by-resubmission.md)
