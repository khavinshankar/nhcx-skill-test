# A15. Case Exchange Log

#### A15E. ENDPOINT

Inbound to the application (the desk's own JSON endpoints), behind a signed-in session with a payer desk role. `:id` is the case id ([D19. case](../database/D19-case.md)).

| Call | Does |
|---|---|
| `GET /cases/:id/exchange` | every message about the case, in order, without bundles |
| `GET /cases/:id/exchange/:msgId` | one message with its bundle as it went over the wire |
| `GET /cases/:id/fhir?kind=` | what this payer would put on the exchange about the case right now |
| `GET /cases/:id/forms` | the questionnaires the hospital answered, per submission |
| `GET /cases/:id` | the case itself, which every test reads for `stage`, `adjudication` and `exchange` |

#### A15D. DESCRIPTION

The trail of a case on the exchange. The timeline ([D26. case_timeline](../database/D26-case-timeline.md)) says what happened in words; the exchange log ([D27. case_exchange_message](../database/D27-case-exchange-message.md)) is the evidence: one row per message, in or out, with the correlation id, the ledger transaction, the other participant, a one-line summary and the bundle. Every callback (C2 to C11) and every send (A1 to A10) writes a row.

**The polls run first.** Before the log is listed, the threads this payer is waiting on are polled once ([A11. Transaction Related](A11-txn-related.md)): the open query and every unacknowledged payment notice on the case. A reply found is applied and its row appears in the list. A poll failure does not fail the call; its message goes into `poll_notes`.

**Bundles.** The list leaves `payload` out; the single read carries it. A row recorded without its bundle (an answer sent after a deliberate delay [SANDBOX](../references/PAYERS.md#markers), or written before the trail kept payloads) is read back from the ledger by `txn_id` ([A12. Transaction FHIR](A12-txn-fhir.md)).

**Kinds** (`kind`): `preauth`, `claimresponse`, `claim`, `communicationrequest`, `communication`, `paymentnotice`, `paymentreconciliation`, `task`, `status`, `predetermination`.

**What this payer would send now** (`/fhir`): renders the bundle the desk previews ([S11. FHIR Preview](../screens/S11-fhir-preview.md)) and the tests compare against, without sending it. `kind` is `claimresponse` (the ClaimResponse of the leg the case stands at, `use` `preauthorization` while the stage is `preauth`, else `claim`; `?use=` overrides it), `preauth` (the pre-auth ClaimResponse), `communicationrequest` (the open query), `paymentreconciliation` or `paymentnotice` (the reconciliation of everything paid). Rendered as the case stands, addressed to the hospital the case came from.

**Forms** (`/forms`): the QuestionnaireResponses the hospital carried on each submission ([F7. QuestionnaireResponse](../fhir/F7-questionnaireresponse.md)), read back out of the bundles the log keeps, so a case filed before the desk showed forms shows its answers too. One group per inbound submission that carried any.

**Visibility.** An account that works particular participant codes sees only cases addressed to them: a case addressed elsewhere is `404` "No case with that id", the same as a case that does not exist [SANDBOX](../references/PAYERS.md#markers). An account listing no participants sees everything.

Data: [D27. case_exchange_message](../database/D27-case-exchange-message.md), [D19. case](../database/D19-case.md), [D30. payment](../database/D30-payment.md).

#### A15Q. REQUEST

No body. Query parameters:

| Call | Parameter | Values |
|---|---|---|
| `/fhir` | `kind` | `claimresponse` (default), `preauth`, `communicationrequest`, `paymentreconciliation`, `paymentnotice` |
| `/fhir` | `use` | `preauthorization` or `claim`, overriding the stage's choice |

```
GET /cases/CASE-1017/exchange
GET /cases/CASE-1017/exchange/XM-7UQ2P0AB
GET /cases/CASE-1017/fhir?kind=claimresponse&use=claim
GET /cases/CASE-1017/forms
```

#### A15S. RESPONSE

**The log**, `200` `{"items": [...], "total": n, "poll_notes": [...]}`, oldest first:

| Key | Content |
|---|---|
| `id` | the row id, for the single read |
| `direction` | `in` or `out` |
| `kind` | as above |
| `correlation_id` | the thread; a payer-started message carries the id the gateway minted |
| `txn_id` | the ledger id ([G9. Ledger](../gateway/G9-ledger.md)) the message was taken in or sent under; blank when it never left |
| `counterparty` | the other participant, `<facility code>` |
| `summary` | one line, for example "Pre-auth NM-26-0SE000001 for INR 69000: 1 line(s)", "Pre-auth verdict: approved, INR 69000 approved of INR 69000", "Query: 2 item(s) asked for", "Payment notice: INR 67620 paid, UTR UTR2026..." |
| `at` | when |
| `poll_notes` | the error text of each poll that failed; empty when all ran cleanly |

```json
{"items": [
  {"id": "XM-7UQ2P0AA", "direction": "in", "kind": "preauth", "correlation_id": "5b1f0c1e-...", "txn_id": "7UPG002K", "counterparty": "<facility code>", "summary": "Pre-auth NM-26-0SE000001 for INR 69000: 1 line(s)", "at": "2026-09-30T10:02:11.000Z"},
  {"id": "XM-7UQ2P0AB", "direction": "out", "kind": "claimresponse", "correlation_id": "5b1f0c1e-...", "txn_id": "7UPG002M", "counterparty": "<facility code>", "summary": "Pre-auth verdict: acknowledged, with an adjudicator", "at": "2026-09-30T10:02:12.000Z"}
 ], "total": 2, "poll_notes": []}
```

**One message**, `200`: the row with `payload`, the bundle ([F1. Bundle](../fhir/F1-bundle.md)) as sent or received, or `null` with the note "The gateway no longer holds this message." when neither the log nor the ledger has it. `404` "No such message on this case".

**The preview**, `200`: `{"bundle": <F1 Bundle>, "issues": [{"severity", "path", "message"}]}`, the renderer's result with anything it could not fill (a procedure without a rate, a payer record without an IRDAI registration) listed as issues rather than invented. `422` `{"fields": {"kind": "Choose claimresponse, communicationrequest or paymentreconciliation"}}` for another kind.

**The forms**, `200` `{"items": [{"stage": "preauth | claim", "message_id", "received_at", "forms": [{"url", "title", "answers": [{"link_id", "text", "answer"}]}]}], "total": n}`.

**The case**, `200`: the [D19. case](../database/D19-case.md) row as A13 returns it. `404` "No case with that id".

#### A15P. PSEUDOCODE

When: the case desk's Exchange tab and FHIR preview ([S3. Case Desk](../screens/S3-case-desk.md), [S11. FHIR Preview](../screens/S11-fhir-preview.md)), and every scripted driver and test ([T2. Test Runners](../tests/T2-test-runners.md)) reading where a case stands.

```text
VISIBLE(case_id, user):
    case = D19 by case_id                              or refuse 404 "No case with that id"
    if user works participants and case.nhcx_recipient_code not among them: refuse 404 "No case with that id"
    return case

EXCHANGE(case_id, user):
    case = VISIBLE(case_id, user)
    poll_notes = []
    polls (each is the A11P loop for its thread):
        query thread of the case                         reply applied as C9
        every D30 payment of the case with nhcx_notice_txn_id set and nhcx_acknowledged_at null   C11
    for each poll: try run it; on error append its text to poll_notes and go on
    rows = D27 where case_id, ordered by seq
    respond 200 {items: rows without payload, total: count, poll_notes}

MESSAGE(case_id, msg_id, user):
    VISIBLE(case_id, user)
    row = D27 by id and case_id                        or refuse 404 "No such message on this case"
    if row.payload is null and row.txn_id set:
        row.payload, note = TRAIL_BUNDLE(row)          # A12
    respond 200 row (with payload; the note beside it when the ledger no longer holds it)

PREVIEW(case_id, kind, use, user):
    case = VISIBLE(case_id, user); payer = D1
    recipient = case.nhcx_sender_code; claim_ref = case.nhcx_claim_submission_ref or case.nhcx_claim_ref
    switch lower(kind or "claimresponse"):
        claimresponse, preauth:
            use = use or ("preauthorization" if kind == "preauth" or case.stage == preauth else "claim")
            result = F9 ClaimResponse bundle for the case as it stands (verdict from adjudication_status and the lines)
        communicationrequest:
            result = F11 CommunicationRequest bundle from the queried lines and the remarks
        paymentreconciliation, paymentnotice:
            result = F14 PaymentReconciliation bundle over every D30 payment of the case
        else: refuse 422 fields {kind: "Choose claimresponse, communicationrequest or paymentreconciliation"}
    respond 200 result as written (no HTML escaping of <, > and &: a "<=" comparator is part of the document)

FORMS(case_id, user):
    case = VISIBLE(case_id, user)
    items = []
    for row in D27 where case_id and direction == "in" and kind in (preauth, claim), by seq:
        forms = F7 answers read from row.payload           # every QuestionnaireResponse, linkId, text, answer
        if forms empty: continue
        append {stage: row.kind, message_id: row.id, received_at: row.at, forms}
    respond 200 {items, total: count}
```

#### A15U. USED BY
- Screens: [S3. Case Desk](../screens/S3-case-desk.md), [S11. FHIR Preview](../screens/S11-fhir-preview.md)
- APIs: [A5. Query Request](A5-query-request.md), [A6. Payment Notice](A6-payment-notice.md), [A11. Transaction Related](A11-txn-related.md), [A12. Transaction FHIR](A12-txn-fhir.md), [A18. Provider Driver](A18-provider-driver.md)
- Callbacks: [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md), [C5. Claim Submit](../callbacks/C5-claim-submit.md)
- FHIR: [F7. QuestionnaireResponse](../fhir/F7-questionnaireresponse.md)
- Database: [D27. case_exchange_message](../database/D27-case-exchange-message.md)
- Tests: [T2. Test Runners](../tests/T2-test-runners.md), [T3. Eligibility Validation and Discovery Answered](../tests/T3-eligibility-answered.md), [T4. Auth-requirements Ruling Answered](../tests/T4-auth-requirements-ruled.md), [T5. Insurance Plan Served](../tests/T5-insurance-plan-served.md), [T6. Pre-auth Received and Approved](../tests/T6-preauth-approved.md), [T7. Pre-auth Rejected](../tests/T7-preauth-rejected.md), [T8. Pre-auth Queried and Answered](../tests/T8-preauth-queried.md), [T9. Enhancement Received and Approved](../tests/T9-enhancement-approved.md), [T10. Pre-auth Cancelled](../tests/T10-preauth-cancelled.md), [T12. Claim Received and Approved](../tests/T12-claim-approved.md), [T13. LAMA and Death Claims](../tests/T13-claim-lama-death.md), [T14. Reprocess and Balance Release](../tests/T14-reprocess-and-release.md), [T15. Payment Notices and Acknowledgement](../tests/T15-payment-noticed.md), [T16. Payment Enquiry Answered](../tests/T16-payment-enquiry-answered.md), [T17. Status Enquiry Answered](../tests/T17-status-answered.md), [T18. Redelivery and Duplicates](../tests/T18-redelivery-ignored.md)
