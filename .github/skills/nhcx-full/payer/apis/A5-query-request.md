# A5. Query Request

#### A5E. ENDPOINT
In-process: `gateway.send("v1/communication/request", envelope)`, [G7. Send](../gateway/G7-send.md), which encrypts it and posts it to NHCX for the hospital on a **new** thread: `POST {nhcx}/v1/communication/request`. No correlation id is passed; G7 mints one ([G5. Protocol Headers](../gateway/G5-protocol-headers.md)) and returns it, and the hospital's reply comes back under it.

On the hospital's side it arrives as a payer communication (its callback for `communication/request`), is filed on the case as a query, and is answered with a Communication on `communication/on_request`, which reaches this payer as [C9. Communication](../callbacks/C9-communication.md).

#### A5D. DESCRIPTION
Sent by [A13. Adjudicate](A13-adjudicate.md) when an adjudicator queries a case (action `query`, with remarks, and any line marked `queried` with its query remarks). The hospital is told what is wanted on a thread of its own; the submission's thread stays open, unanswered, until the reply has been read and a decision made, and the ClaimResponse then goes on it ([A3. Pre-auth Answer](A3-preauth-answer.md), [A4. Claim Answer](A4-claim-answer.md)). Sending a `queued` ClaimResponse first would have the hospital's desk settle on a non-answer and would mark the thread answered here before it was.

This is the `communication` query mode. A scheme that asks inside its ClaimResponse and takes the answer as a fresh submission (PMJAY, `resubmit` mode) sends no CommunicationRequest: the query is [A3. Pre-auth Answer](A3-preauth-answer.md) with `outcome` `partial` and reason `queried`, and the answer arrives as a resubmission on [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md) under workflow 19 or 131 [PAYER](../references/PAYERS.md#markers). Which mode this payer speaks is a scheme setting (see [PAYERS.md](../references/PAYERS.md)); the reference speaks `communication` [REF](../references/PAYERS.md#markers).

**What is asked** ([F11. CommunicationRequest](../fhir/F11-communicationrequest.md)): one payload per thing wanted, in order: the adjudicator's case remarks, then each queried line as "`<line description>`: `<query remarks>`". The request is `about` the Claim (the hospital's claim number: the claim's submission reference, else the pre-authorisation's), addressed from this payer to the hospital, with the case's Patient, both Organizations and the Coverage beside it.

**Resend.** `POST cases/:id/query/resend` sends the open query again, for when the gateway was down the first time. Refusals, in order: "Only an adjudicator can send a query" (role), "No case with that id", "This case is not under query", "This case did not come off the exchange, so there is nobody to ask", "No gateway is configured" [REF](../references/PAYERS.md#markers), and "The gateway could not queue the query" when the send still fails. A resend opens a fresh thread and replaces the old one on the case.

**Headers set by the application.**

| Header | Value |
|---|---|
| `x-hcx-sender_code` | This payer's participant code ([D1. payer](../database/D1-payer.md)) |
| `x-hcx-recipient_code` | The case's `nhcx_sender_code` |
| `x-hcx-correlation_id` | not set: G7 mints a fresh thread |
| `x-hcx-workflow_id` | From the table below |
| `x-hcx-status` | `request.initiated` |

Workflow ids, per scheme dialect (see [PAYERS.md](../references/PAYERS.md)) [PAYER](../references/PAYERS.md#markers):

| Case being queried | `pmjay` | `kyrocare` (Sandbox Payer) | `generic` | `x-hcx-status` |
|---|---|---|---|---|
| Claim (stage `claim`, or a claim thread on the case) | 27 | 27 | 27 | `request.initiated` |
| Pre-authorisation after an enhancement (`enhancement_count` > 0) | 241 | 241 | 241 | `request.initiated` |
| Pre-authorisation | 24 | 24 | 24 | `request.initiated` |

**Checks before sending.** The case must be `queried` and must have come off the exchange (a desk-raised case has nobody to ask); a gateway that is not configured is logged, "case `<id>` was queried but no gateway is configured, so `<hospital>` was not asked", and the query stands on the case for a resend. Nothing refuses the adjudication.

#### A5Q. REQUEST

The arguments passed to G7 Send:

| Field | Type | Notes |
|---|---|---|
| `jwe_headers` | object | Sender, recipient, workflow id, status; no correlation id |
| `fhir` | Bundle | The CommunicationRequest bundle |

FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F11. CommunicationRequest](../fhir/F11-communicationrequest.md), [F15. Patient](../fhir/F15-patient.md), [F17. Organization](../fhir/F17-organization.md), [F18. Coverage](../fhir/F18-coverage.md)

Envelope, a pre-authorisation queried on one line:

```json
{
  "jwe_headers": {"x-hcx-sender_code": "<payer code>",
                  "x-hcx-recipient_code": "<facility code>",
                  "x-hcx-workflow_id": "24",
                  "x-hcx-status": "request.initiated"},
  "fhir": <F1 Bundle: F11 CommunicationRequest (status active, about Claim/<claim number>, sender this payer, recipient the hospital, payload "Send the ICU chart" and "ICU bed, 3 days: attach the ICU chart for the stay"), F15 Patient, F17 Organizations, F18 Coverage>
}
```

#### A5S. RESPONSE

**Acknowledgement:** the G7 result. Its `correlation_id` is the thread the hospital's reply will carry; its `txn_id` the ledger row.

Recorded:
- [D19. case](../database/D19-case.md) `nhcx_query_correlation_id` = the result's `correlation_id` (the `txn_id` when the gateway gave none [REF](../references/PAYERS.md#markers)), `nhcx_query_txn_id` = `txn_id`. A new query replaces the old thread. [C9. Communication](../callbacks/C9-communication.md) clears the correlation id when the reply is filed.
- [D27. case_exchange_message](../database/D27-case-exchange-message.md) exchange message, direction `out`, kind `communicationrequest`, that correlation id and transaction, summary "Query sent: `<the asks joined with "; ">`".
- [D26. case_timeline](../database/D26-case-timeline.md) timeline event "Query Sent over NHCX", "`<hospital>` asked for: `<the asks>`", by `NHCX`, type `warning`.
- [D31. audit_log](../database/D31-audit-log.md) audit `case.query_sent`: "`<hospital>` asked, correlation `<id>`, txn `<id>`".

**Failed send.** Logged ("could not queue the query on case `<id>` for `<hospital>`: `<message>`"), nothing recorded, the case stays `queried` with no query thread, and the resend endpoint tries again. Nothing is shown as a 500: the adjudication has already answered the screen.

Data: [D19. case](../database/D19-case.md), [D25. case_line_item](../database/D25-case-line-item.md), [D26. case_timeline](../database/D26-case-timeline.md), [D27. case_exchange_message](../database/D27-case-exchange-message.md), [D31. audit_log](../database/D31-audit-log.md), [D1. payer](../database/D1-payer.md)

Reply: [C9. Communication](../callbacks/C9-communication.md). The hospital's Communication, matched on this correlation id first. When the reply has been filed the case is back with the adjudicator (`pending`, the queried lines `pending`), and the next decision sends the verdict ([A3. Pre-auth Answer](A3-preauth-answer.md), [A4. Claim Answer](A4-claim-answer.md)).

**Polling.** When the callback was missed, opening the case ([A15. Case Exchange Log](A15-case-exchange.md)) polls the query thread: [A11. Transaction Related](A11-txn-related.md) with `nhcx_query_txn_id`, the newest inbound row carrying a Communication read through [A12. Transaction FHIR](A12-txn-fhir.md) and applied as C9 would.

#### A5P. PSEUDOCODE

```
function query_workflow(case):                      // [PAYER](../references/PAYERS.md#markers): the pmjay column
    if case.stage == claim or (case.stage != preauth and case.nhcx_claim_correlation_id set): return "27"
    if case.enhancement_count > 0: return "241"
    return "24"

// called by A13 answer_verdict when the decision was "query"
function send_query(case):
    if case.nhcx_sender_code empty: return case        // not from the exchange
    if case.adjudication_status != queried: return case
    if gateway not configured:
        log "case <id> was queried but no gateway is configured, so <hospital> was not asked"; return case
    payer = D1 payer row
    claim_ref = case.nhcx_claim_submission_ref or case.nhcx_claim_ref
    asked = [case.adjudication_remarks] if set
          + for each D25 line with status queried and query_remarks: line.description + ": " + line.query_remarks
    bundle = F11 bundle(payer, payer code, case, claim_ref, recipient = case.nhcx_sender_code, payloads = asked)
    headers = {x-hcx-sender_code: payer code, x-hcx-recipient_code: case.nhcx_sender_code,
               x-hcx-workflow_id: query_workflow(case), x-hcx-status: "request.initiated"}
    ack = SEND("v1/communication/request", {jwe_headers: headers, fhir: bundle}, case)   // A1: SEND
        on any failure f: log "could not queue the query on case <id> for <hospital>: <f>"; return case
    thread = ack.correlation_id or ack.txn_id          // [REF](../references/PAYERS.md#markers)
    UPDATE D19[case.id] SET nhcx_query_correlation_id = thread, nhcx_query_txn_id = ack.txn_id
    INSERT D27 {case_id, direction: out, kind: communicationrequest, correlation_id: thread,
                txn_id: ack.txn_id, counterparty: case.nhcx_sender_code,
                summary: "Query sent: " + join(asked, "; "), payload: bundle}
    INSERT D26 {case_id, title: "Query Sent over NHCX",
                description: "<hospital> asked for: " + join(asked, "; "), actor: "NHCX", type: warning}
    INSERT D31 audit {action: "case.query_sent", entity_type: case, entity_id: case.id,
                      detail: "<hospital> asked, correlation <thread>, txn " + ack.txn_id}
    return case with the query thread set

// POST cases/:id/query/resend
function resend_query(case_id, user):
    if user cannot adjudicate: refuse 403 "Only an adjudicator can send a query"
    case = visible case(case_id)            or refuse 404 "No case with that id"
    if case.adjudication_status != queried:  refuse 409 "This case is not under query"
    if case.nhcx_sender_code empty:          refuse 409 "This case did not come off the exchange, so there is nobody to ask"
    if gateway not configured:               refuse 409 "No gateway is configured"
    before = case.nhcx_query_txn_id
    case = send_query(case)
    if case.nhcx_query_txn_id empty or == before: refuse 502 "The gateway could not queue the query"
    return case
```

#### A5U. USED BY
- Screens: [S3. Case Desk](../screens/S3-case-desk.md), [S11. FHIR Preview](../screens/S11-fhir-preview.md)
- APIs: [A3. Pre-auth Answer](A3-preauth-answer.md), [A4. Claim Answer](A4-claim-answer.md), [A11. Transaction Related](A11-txn-related.md), [A13. Adjudicate](A13-adjudicate.md)
- Callbacks: [C1. Callback Door](../callbacks/C1-callback-door.md), [C9. Communication](../callbacks/C9-communication.md)
- FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F9. ClaimResponse](../fhir/F9-claimresponse.md), [F11. CommunicationRequest](../fhir/F11-communicationrequest.md)
- Database: [D19. case](../database/D19-case.md), [D27. case_exchange_message](../database/D27-case-exchange-message.md), [D31. audit_log](../database/D31-audit-log.md)
- Gateway: [G5. Protocol Headers](../gateway/G5-protocol-headers.md), [G7. Send](../gateway/G7-send.md)
- Tests: [T8. Pre-auth Queried and Answered](../tests/T8-preauth-queried.md)
