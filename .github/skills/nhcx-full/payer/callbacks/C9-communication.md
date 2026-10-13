# C9. Communication

#### C9E. ENDPOINT
Delivered in-process by [G8. Receive](../gateway/G8-receive.md) for NHCX route `v1/communication/on_request`, passed to `C1.receive`, classified `communication` because the bundle holds a `Communication` ([F12. Communication](../fhir/F12-communication.md)), bare or behind a Task coded `poll`. It answers [A5. Query Request](../apis/A5-query-request.md), the CommunicationRequest this payer sent when a person queried the case. Nothing goes back: the verdict that follows the reply ([A3. Pre-auth Answer](../apis/A3-preauth-answer.md), [A4. Claim Answer](../apis/A4-claim-answer.md)) is the answer.

#### C9D. DESCRIPTION
When an adjudicator queries a case, the hospital is asked on a thread of its own ([A5. Query Request](../apis/A5-query-request.md)): the gateway mints the correlation id and it is written on the case ([D19. case](../database/D19-case.md) `nhcx_query_correlation_id`), because the Communication comes back under it. This callback files that reply the way the desk's own query response is filed: the documents attached, the text on the timeline, the queried lines back to pending, the case back in front of an adjudicator.

**Matching is forgiving**, because a reply that reaches the wrong case is bad and a reply that reaches no case is worse:

1. The query thread: `nhcx_query_correlation_id` equals the reply's correlation id.
2. The hospital may have replied on the submission's thread instead: the claim leg's correlation id, then the pre-auth leg's.
3. Anything the reply names: its own identifier, the `CLN` identifier and identifier of a Task in front of it, and every `basedOn`, `about`, `inResponseTo` and `partOf` reference, display and identifier value; each is tried whole, without its `Claim/`, `CommunicationRequest/` or `ClaimResponse/` prefix (this payer's numbers carry slashes, so everything after the type counts), and by its last path segment; each as `case_for_claim_ref` for this sender.
4. The sender's open query: a case whose `nhcx_query_correlation_id` equals the reply's `x-hcx-workflow_id`.

None: "No case is waiting on this communication" (`rejected`; the same envelope redelivered would find the same nothing).

**What is filed.** The attachments belong to whichever half of the case is under query: phase `claim` at stage `claim`, else `preauth`; codes are resolved as [C4. Pre-auth Submit](C4-preauth-submit.md) does, unknown codes as `ODN` with the timeline warning. The text is every `payload[].contentString` joined by newlines, else the `reasonCode`, else "<n> document(s) received over NHCX". Then, through the same transition the desk uses: the queried [D25. case_line_item](../database/D25-case-line-item.md) lines go back to `pending` with their query remarks cleared (the question has been answered, and leaving them queried would hide an answered question among open ones), the documents are inserted, totals recomputed, the case's adjudication goes back to `pending` (the verdict that raised the query no longer stands), and "Query Answered" goes on the timeline. The query thread is cleared.

**A reply nobody asked for.** When the case is not under query, the documents are still kept (a hospital sending more is never wrong) and the text goes on the timeline as "Communication Received"; nothing else changes. A case that has moved past adjudication answers "That case has moved past adjudication" (`rejected`).

**A CommunicationRequest from a hospital** (a hospital asking this payer for something) is classified `communicationrequest` by C1 and ignored with a log line: the reference did not answer one [REF](../references/PAYERS.md#markers).

**PMJAY mode.** Under the `resubmit` query mode a hospital does not send a Communication: it submits the leg again with the answer riding on the Claim, which [C4. Pre-auth Submit](C4-preauth-submit.md) and [C5. Claim Submit](C5-claim-submit.md) take as the query answer [PAYER](../references/PAYERS.md#markers). Both modes lead to the same case state.

**Redelivery.** C1 drops a repeat by api call id. A repeat that slips through finds the case no longer under query and files its documents again only if they are not already on the case under the same code, title and size.

#### C9Q. REQUEST
`fhir` is an [F1. Bundle](../fhir/F1-bundle.md) Bundle carrying [F12. Communication](../fhir/F12-communication.md) Communication: `identifier`, `basedOn` (the CommunicationRequest), `about` (the Claim), `inResponseTo`, `payload[]` with `contentString` texts and `contentAttachment` documents (title, contentType, url or inline data, the document code in the payload's extension), `reasonCode`, `sent`; sometimes behind a Task coded `poll` carrying the claim number. Headers read: `x-hcx-sender_code`, `x-hcx-recipient_code`, `x-hcx-correlation_id` (the query thread, or a submission thread), `x-hcx-workflow_id` (the query's own workflow id 24, 241 or 27 echoed, or the query's correlation id [REF](../references/PAYERS.md#markers)).

#### C9P. PSEUDOCODE

```
C9(in, reply):                                            # reply = F12 parse: reference, refs, texts, documents, reason, sent
    case = D19 where nhcx_query_correlation_id == in.corr
        or D19 where nhcx_claim_correlation_id == in.corr
        or D19 where nhcx_correlation_id == in.corr
        or first case_for_claim_ref(ref, in.sender) for ref in reply.refs
        or D19 where nhcx_query_correlation_id == in.workflow_id
    if none: raise Rejected("No case is waiting on this communication")

    documents, dropped = resolve_documents(reply.documents)
    phase = "claim" if case.stage == "claim" else "preauth"
    for d in documents: d.phase = phase
    text = join(reply.texts, "\n") or reply.reason or "<n> document(s) received over NHCX"

    try:
        updated = D19.respond_to_query(case, {remarks: text, documents}, actor {name: in.sender})
            # queried D25 lines -> pending, query_remarks null; documents inserted; totals; adjudication pending,
            # adjudicated_by and adjudicated_at null; D26 "Query Answered: <text> (<n> document(s) attached)"
    catch not queried:                                     # nobody asked
        for d in documents: D23.add(case, d, by in.sender)   # kept anyway; a duplicate (code, title, size) is skipped
        D26 event {title: "Communication Received", description: text, by: in.sender, type: info}
        updated = case
    catch closed: raise Rejected("That case has moved past adjudication")

    if dropped: D26 event "Attachments Filed as Other" (as C4)
    D19.nhcx_query_correlation_id = null
    exchange_message(case, "in", "communication", in.corr, in.ledger_id, in.sender,
                     "Reply: <text> (<n> document(s))", payload(in.envelope))
    D31 audit {action: "communication.received", entity: "nhcx_txn", id: in.ledger_id,
               detail: "<sender> replied, correlation <corr>, case <case.id>, <n> document(s)"}
    return "settled"                                       # outcome {status: filed, case_id, claim_no, documents: n}
```

#### C9S. RESPONSE
`settled` when the reply was filed (as the query's answer, or as a communication on a case not under query); `rejected` when no case is waiting on it or the case has moved past adjudication; `error` on an unexpected failure.

State changes:

| Case | Writes |
|---|---|
| under query | [D25. case_line_item](../database/D25-case-line-item.md) queried lines `pending`, `query_remarks` null; [D23. case_document](../database/D23-case-document.md) documents with [D24. case_document_file](../database/D24-case-document-file.md) bytes at the case's phase; [D19. case](../database/D19-case.md) adjudication `pending`, `adjudicated_by` and `adjudicated_at` null, `nhcx_query_correlation_id` null; totals; [D26. case_timeline](../database/D26-case-timeline.md) "Query Answered"; [D27. case_exchange_message](../database/D27-case-exchange-message.md) the inbound message; [D31. audit_log](../database/D31-audit-log.md) `communication.received` |
| not under query | [D23. case_document](../database/D23-case-document.md) documents; [D26. case_timeline](../database/D26-case-timeline.md) "Communication Received"; [D19. case](../database/D19-case.md) `nhcx_query_correlation_id` null; [D27. case_exchange_message](../database/D27-case-exchange-message.md); [D31. audit_log](../database/D31-audit-log.md) |

#### C9U. USED BY
- Screens: [S3. Case Desk](../screens/S3-case-desk.md)
- APIs: [A5. Query Request](../apis/A5-query-request.md), [A11. Transaction Related](../apis/A11-txn-related.md), [A12. Transaction FHIR](../apis/A12-txn-fhir.md), [A15. Case Exchange Log](../apis/A15-case-exchange.md), [A18. Provider Driver](../apis/A18-provider-driver.md)
- Callbacks: [C1. Callback Door](C1-callback-door.md)
- FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F11. CommunicationRequest](../fhir/F11-communicationrequest.md), [F12. Communication](../fhir/F12-communication.md)
- Database: [D3. document_type](../database/D3-document-type.md), [D19. case](../database/D19-case.md), [D23. case_document](../database/D23-case-document.md), [D24. case_document_file](../database/D24-case-document-file.md), [D25. case_line_item](../database/D25-case-line-item.md), [D26. case_timeline](../database/D26-case-timeline.md), [D27. case_exchange_message](../database/D27-case-exchange-message.md), [D31. audit_log](../database/D31-audit-log.md)
- Tests: [T2. Test Runners](../tests/T2-test-runners.md), [T8. Pre-auth Queried and Answered](../tests/T8-preauth-queried.md)
