# A7. Communication Reply

#### A7E. ENDPOINT
In-process: `gateway.send("v1/communication/on_request", envelope)`, [G7. Send](../gateway/G7-send.md), which encrypts it and posts it to NHCX for the payer, on the thread the payer's CommunicationRequest arrived on: `POST {nhcx}/v1/communication/on_request`. No answer to it is awaited: NHCX's acceptance, returned by G7, settles it.

#### A7D. DESCRIPTION
The payer starts a communication by sending a CommunicationRequest on `communication/request` (arrives through callback C9, type `communication`), on a thread of its own. When it is recorded, it is filed on a claim leg as either a **query** or a **notification** (see C9 for how it is classified). This route carries the application's answer to both:

| Variant | For | When sent |
|---|---|---|
| Reply | a query | when the desk sends the reply form (S10) |
| Acknowledgement | a notification | automatically, the moment the notification is recorded; again by hand only after a failure |

Reply: [C9. Payer Communication](../callbacks/C9-communication-request.md) (how a request is classified as a query or a notification)

**Headers.** Both variants use the same four:

| Header | Value |
|---|---|
| `x-hcx-sender_code` | The facility's participant code |
| `x-hcx-recipient_code` | The request's `x-hcx-sender_code`, else the case's processing id, else the claim's payer id, else the configured default payer code |
| `x-hcx-correlation_id` | The correlation id the request arrived on. This is how the payer ties the answer to the question |
| `x-hcx-workflow_id` | The request's own `x-hcx-workflow_id`, else the queried leg's correlation id, else the claim number (the fallbacks are [REF](../references/PAYERS.md#markers)) |

The workflow id does not come from the payer adapter. G7 completes the other headers ([G5. Protocol Headers](../gateway/G5-protocol-headers.md)); when the correlation id is blank, G7 takes it from the newest inbound communication request from the recipient in the [G9. Ledger](../gateway/G9-ledger.md).

**Checks.**

Reply, in order:
1. "Query not found." / "That query is not on this claim." (the route checks the claim)
2. "That message is not a question: a notification is acknowledged and a note is read, neither takes an answer."
3. New files chosen on the form are filed on the claim first, at the queried leg's stage; the document upload errors apply and one bad file refuses the whole reply before anything is sent.
4. "Set the facility's HFR ID and NHCX participant code under Settings before answering a query."
5. "Write a reply or attach a document, an empty answer tells the payer nothing."
6. "One of the chosen documents is not on this claim."

Acknowledgement: "That message is not on this claim." (route), "Only a notification is acknowledged; a query is answered from the communication tab.", "Set the facility's HFR ID and NHCX participant code under Settings first."

#### A7Q. REQUEST

The arguments passed to G7 Send:

| Field | Type | Notes |
|---|---|---|
| `jwe_headers` | object | The four headers above |
| `fhir` | Bundle | The reply bundle or the acknowledgement bundle |

**Reply bundle.** A new Task and a new Communication carrying the reply text and the chosen documents, the payer's CommunicationRequest echoed, then the case resources lifted from the queried leg's own sent bundle (A4 or A5), or built from the case when that leg never went out.

**Acknowledgement bundle.** The request bundle as the payer sent it, sent back with the payer's Task marked completed.

FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F10. Task (claim actions)](../fhir/F10-task-claim-actions.md), [F12. Communication](../fhir/F12-communication.md), [F11. CommunicationRequest](../fhir/F11-communicationrequest.md), [F8. Claim](../fhir/F8-claim.md), [F15. Patient](../fhir/F15-patient.md), [F17. Organization](../fhir/F17-organization.md), [F16. Practitioner and PractitionerRole](../fhir/F16-practitioner.md), [F18. Coverage](../fhir/F18-coverage.md)

Envelope, a real reply (Sandbox Payer):

```json
{
  "jwe_headers": {"x-hcx-sender_code": "<facility code>",
                  "x-hcx-recipient_code": "<payer code>",
                  "x-hcx-correlation_id": "50c822b5-6923-4765-8bb0-65615e019e00",
                  "x-hcx-workflow_id": "24"},
  "fhir": <F1 Bundle carrying F10 Task (deliver, completed), F12 Communication (reply text and one attachment coded RAD), F11 CommunicationRequest echoed, F8 Claim, F15 Patient, F17 provider and payer Organizations, F16 Practitioner, F18 Coverage>
}
```

#### A7S. RESPONSE

**Acknowledgement:** the G7 result, `{"ok": true, "gateway_status": 202, "txn_id", "correlation_id", "request_id", "headers", "response", ...}`. Its `txn_id` is kept as the reply's transaction id.

- Reply: the query becomes `answered`, with the reply and its ids. The case's stage is recomputed, so it is no longer `queried`.
- Acknowledgement: the notification becomes `acknowledged`, with the same reply ids.

**Failure.** Any G7 error, or a result NHCX did not accept (`ok` false), sets the row to `error` with the message (a reply also keeps its text and document ids for the next try), plus the reply ids when the failure named them. The error is shown on the screen. An automatic acknowledgement that fails is kept on the row and never raised, so the notification is still recorded and the callback still answers 2xx.

Data: [D23. claim_query](../database/D23-claim-query.md), [D28. claim_document](../database/D28-claim-document.md)

**What comes back from the payer.** Nothing is waited for on this route. After a reply the queried leg waits for the payer's next verdict on its own thread.

Reply: [C5. Pre-auth Reply](../callbacks/C5-preauth-on-submit.md), [C6. Claim Reply](../callbacks/C6-claim-on-submit.md) (the next verdict), [C9. Payer Communication](../callbacks/C9-communication-request.md) (a follow-up query or note)

#### A7P. PSEUDOCODE

```
function reply_headers(asked, case, org):
    leg = claim_submission if asked.stage == claim else claim_preauth, for the case
    return {x-hcx-sender_code:    org.participant_code,
            x-hcx-recipient_code: asked.sender_code or case.processing_id or case.payer_id or default payer code,
            x-hcx-correlation_id: asked.correlation_id or "",
            x-hcx-workflow_id:    asked.workflow_id or leg.correlation_id or case.claim_no}   // fallbacks [REF](../references/PAYERS.md#markers)

// ---- reply to a query
function answer_query(query_id, text, document_ids, uploads):
    asked = claim_query[query_id]          or refuse "Query not found."
    if asked.kind != query:
        refuse "That message is not a question: a notification is acknowledged and a note is read, neither takes an answer."
    case = claim[asked.claim_id]
    for each upload: INSERT claim_document at stage asked.stage (upload errors refuse
                     the whole reply); add its id to document_ids
    document_ids = unique(document_ids)

    // build (each refusal in this order)
    org = default organization
    if org missing or HFR ID or participant code empty:
        refuse "Set the facility's HFR ID and NHCX participant code under Settings before answering a query."
    text = trim(text)
    if text empty and document_ids empty:
        refuse "Write a reply or attach a document, an empty answer tells the payer nothing."
    payload = [text] if text
    for each id in document_ids:
        doc = claim_document[id]; if missing or doc.claim_id != case.id:
            refuse "One of the chosen documents is not on this claim."
        payload += attachment (content type, label or filename, uploaded_at, base64 data,
                   document code as the adapter's document-type extension when coded)
    request   = the stored CommunicationRequest (asked.request_json)
    case_part = Claim, Patient, Organizations, Practitioner, Coverage from the queried
                leg's sent bundle (claim_submission or claim_preauth request_json),
                else built from claim, patient and organization rows
    bundle = F1 Bundle carrying F10 Task (deliver, completed, reason from the request),
             F12 Communication (payload, about the claim asked.claim_ref or case.claim_no),
             F11 CommunicationRequest echoed, case_part

    // call (no ids-kept convention: any failure is the failure)
    try:
        result = gateway.send("v1/communication/on_request",           // G7 Send
                     {jwe_headers: reply_headers(asked, case, org), fhir: bundle})
              (archived with the case)
        if not result.ok: fail with NHCX's refusal (APIs conventions)
        ack = {txn_id: result.txn_id, correlation_id: result.correlation_id}
    catch send_error or NHCX refusal:
        UPDATE claim_query[query_id] SET status = error, error_message = its message,
            reply_text = text or null, reply_documents = document_ids
            (+ reply_txn_id, reply_correlation_id when it named them)
        raise it
    UPDATE claim_query[query_id] SET status = answered, error_message = null,
        reply_text = text or null, reply_documents = document_ids,
        reply_txn_id = ack.txn_id, reply_correlation_id = ack.correlation_id,
        answered_at = now, reply_json = bundle
    recompute case stage

// ---- acknowledgement of a notification (called when C9 records one, or by hand)
function acknowledge_notification(query_id):
    asked = claim_query[query_id]          or refuse "Query not found."
    case  = claim[asked.claim_id]
    try:
        if asked.kind != notification:
            refuse "Only a notification is acknowledged; a query is answered from the communication tab."
        org = default organization; if HFR ID or participant code empty:
            refuse "Set the facility's HFR ID and NHCX participant code under Settings first."
        bundle = the stored request bundle (asked.request_json) sent back: the payer's
                 F10 Task set completed (built when missing), F17 Organizations together
                 with the facility's first, other entries in place
        result = gateway.send("v1/communication/on_request",           // G7 Send
                     {jwe_headers: reply_headers(asked, case, org), fhir: bundle})
        if not result.ok: fail with NHCX's refusal
        ack = {txn_id: result.txn_id, correlation_id: result.correlation_id}
    catch refusal, send_error or NHCX refusal:
        UPDATE claim_query[query_id] SET status = error, error_message = message
            (+ reply_txn_id, reply_correlation_id when a G7 error or NHCX refusal named them)
        raise                                        // the automatic caller swallows it
    UPDATE claim_query[query_id] SET status = acknowledged, error_message = null,
        reply_txn_id = ack.txn_id, reply_correlation_id = ack.correlation_id,
        acknowledged_at = now, reply_json = bundle
```

#### A7U. USED BY
- Screens: [S10. Communication](../screens/S10-communication.md)
- Callbacks: [C1. Callback Door](../callbacks/C1-callback-door.md), [C9. Payer Communication](../callbacks/C9-communication-request.md)
- FHIR: [F11. CommunicationRequest](../fhir/F11-communicationrequest.md), [F12. Communication](../fhir/F12-communication.md), [F15. Patient](../fhir/F15-patient.md), [F18. Coverage](../fhir/F18-coverage.md)
- Database: [D23. claim_query](../database/D23-claim-query.md)
- Gateway: [G7. Send](../gateway/G7-send.md)
- Tests: [T7. IRDAI Query Answered](../tests/T7-irdai-query-answered.md)
