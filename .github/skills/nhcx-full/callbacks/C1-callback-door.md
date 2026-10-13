# C1. Callback Door

#### C1E. ENDPOINT
`C1.receive(envelope, delivery) -> outcome`, called in-process by [G8. Receive](../gateway/G8-receive.md) for every message NHCX delivers; G8 is its only caller. There is no HTTP route of its own: NHCX posts `{"payload": "<JWE>"}` to the application's public inbound route (`POST /in/<path>` or `POST /v1/<path>`, whichever the participant's registered `endpoint_url` points at), and G8 opens it and calls `receive`.

`envelope` is the decrypted message: `jwe_headers` and `fhir` (see C1Q). `delivery` describes how it arrived:

| `delivery` field | Value |
|---|---|
| `path` | the NHCX API path the message arrived on, for example `v1/preauth/on_submit` |
| `type` | the exchange, and the only thing that routes: `coverage`, `insurance`, `preauth`, `claim`, `task`, `status`, `communication`, `payment`. Derived by G8 from the path, see C1D |
| `flow` | the direction label: `request` for a reply to one of our sends (an `on_` path), `on_request` for a message the payer starts. Recorded in the archive, never used to route |
| `payload_kind` | `fhir` (a decrypted JWE), `protocol` (a plain `ProtocolResponse` or error notice) or `json` (anything else). `json` means the message is ignored |
| `correlation_id` | `x-hcx-correlation_id` of the message |
| `api_call_id` | `x-hcx-api_call_id` of the message, kept by NHCX across its redeliveries |
| `redelivery` | true when the [G9. Ledger](../gateway/G9-ledger.md) already holds this `api_call_id` |
| `participant` | the participant code the message was addressed to |

It answers every outbound API whose reply is asynchronous (A2 to A6), and it carries the two messages the payer starts itself (answered by A7 and A8). Routing to C2 to C10 is in C1P.

#### C1D. DESCRIPTION
G8 decrypts every message NHCX delivers for the facility, resolves the participant it was addressed to, calls `C1.receive`, then records the message and the outcome in G9. A message G8 cannot open (not JSON, an unreadable JWE, addressed to a code no key of the application opens) is refused by G8 itself and never reaches C1.

The type comes from the path's entity segment, with two shorter names:

| NHCX path | `type` | Callback |
|---|---|---|
| `v1/coverageeligibility/on_check` | `coverage` | C2 eligibility verdict, else C3 auth-requirements ruling |
| `v1/insuranceplan/on_request` | `insurance` | C4 |
| `v1/preauth/on_submit` | `preauth` | C5 |
| `v1/claim/on_submit` | `claim` | C6 |
| `v1/task/on_submit` | `task` | C8 when an enquiry waits on the thread, else C7 |
| `v1/on_status` (or another status path) | `status` | C8 |
| `v1/communication/request` | `communication` | C9 |
| `v1/paymentnotice/request` | `payment` | C10 |

The path itself is bookkeeping; `type` is what routes. The flow label is not a filter either: coverage, insurance, pre-auth, claim and task replies are labelled `request`, and payment notices and communications `on_request`.

**Matching.** A reply to one of our sends is matched by `correlation_id` against the leg that went out on it (C2 to C8). The payer's own messages (C9, C10) open a thread of their own, so they are matched by the claim number they carry instead, and the correlation id only dedupes redeliveries. `claim_named_in` matches the **claim number only** (a `CLN` identifier, or a display or reference ending in a claim number this desk holds); it never matches on a patient, a payer or a workflow id.

**A message this desk does not own.** Several desks may share one participant code behind a fan-out proxy ([OPERATIONS.md](../references/OPERATIONS.md)), so every message not owned here must end `unmatched` fast: no row written, nothing sent (C9 does not acknowledge a notification for a claim number it does not hold, C10 does not acknowledge such a payment notice), only the `unmatched` archive entry; and `unmatched` is answered 202 by G8. A failure to read the ledger or the archive is logged and never turns into a refusal.

**Polling applies through the same door.** A reply found by polling (A10 to A13) is handed to `route(type, envelope, corr)` with the **leg's** correlation id (for a cancel, the cancel's `cancel_correlation_id`), never to a handler function directly, so the matching, dedupe and revive rules are the same on both paths.

**Redelivery.** NHCX redelivers any message G8 did not accept (five attempts on one `api_call_id`), and a payer may send the same message more than once, so every handler is safe to receive twice. The `redelivery` flag is not a reason to skip: G9 also holds a first delivery that ended in `error`, so its redelivery must still be applied. Each handler dedupes by its own rule. A leg that has moved on answers `ignored`; a reply already applied answers `ignored`. The one exception is a leg on record as a failed send: the payer answering is proof the message went, so the leg is reopened and the reply applied (see "Shared rules" in C1P).

**Callbacks are the fast path.** Every leg is also polled when the case is opened (A10 to A13), and both paths apply a reply the same way, so a missed callback costs only speed. Exceptions are called out in each callback's USED BY.

**No session.** `C1.receive` runs inside the application, with no user session. Its only way in from outside is G8's inbound route, which takes only what decrypts with one of the application's participant keys.

#### C1Q. REQUEST
`envelope` is the message as G8 decrypted it. `jwe_headers` holds the NHCX protocol headers; the ones read are `x-hcx-correlation_id` (matching and dedupe), `x-hcx-api_call_id` (redelivery test on C5 and C6), `x-hcx-sender_code` and `x-hcx-workflow_id` (C9, C10), and `x-hcx-status_response` (C8). `fhir` is an F1 Bundle, or a plain `ProtocolResponse` when NHCX or the payer refused the request.

#### C1P. PSEUDOCODE

```
receive(envelope, delivery):                              # called by G8; G8 records the outcome in G9 afterwards
    try:
        if envelope is not an object: raise Rejected("Expected a JSON object.")
        return accept(envelope, delivery)
    except Rejected as why:                                 # any unreadable-payload error below
        return rejected(why)
    except any other failure as why:                        # database down, a bug
        return error(why)

accept(envelope, delivery):
    type, flow, payload_kind = delivery.type, delivery.flow, delivery.payload_kind
    participant, redelivery = delivery.participant, delivery.redelivery
    if payload_kind == "json" or type not in
            {coverage, insurance, preauth, task, claim, payment, communication, status}:
        return "ignored"                                    # not archived
    corr = envelope.jwe_headers["x-hcx-correlation_id"] if jwe_headers is an object else none
    archived = archive_inbound(envelope, type, flow, corr, participant, redelivery)  # before anything is applied
    outcome = route(type, envelope, corr)
    archive_note(archived, outcome)                         # skipped when route raised
    return outcome

route(type, envelope, corr):
    if type == "payment":       return C10(envelope, corr)
    if type == "communication": return C9(envelope, corr)
    if corr is empty:           return "unmatched"
    if type in {status, task} and a D29 row has correlation_id == corr:
                                return C8(envelope, corr)
    if type == "status":        return "unmatched"
    if type == "insurance":     return C4(envelope, corr)
    if type == "preauth":       return C5(envelope, corr)
    if type == "task":          return C7(envelope, corr)
    if type == "claim":         return C6(envelope, corr)
    # coverage
    if a D9 row has correlation_id == corr: return C2(envelope, corr)
    return C3(envelope, corr)

archive_inbound(envelope, type, flow, corr, participant, redelivery):
    claim = claim_for_correlation(corr) or claim_named_in(envelope)
    folder = claim.claim_no if claim else "unmatched"
    write <archive dir>/<folder>/<NNN>-<type or "exchange">-in.json   # whole envelope, unchanged
    append to <folder>/transactions.txt:
        time  NNN  IN  <type>  <flow or type>  workflow=<x-hcx-workflow_id>
        correlation=<corr>  api_call=<x-hcx-api_call_id>  txn=<x-hcx-txn_id>
        participant=<participant>  redelivery=<redelivery>  file=<name>
    # a disk failure is logged and never breaks the receive; archiving can be switched off

archive_note(archived, outcome):
    append "    ↳ <file> outcome=<outcome>" to that folder's transactions.txt

claim_for_correlation(corr):
    newest D9 row with correlation_id == corr, else the claim of the newest row matching, in order:
    D18.correlation_id, D18.cancel_correlation_id, D20.correlation_id, D10.correlation_id,
    D13.correlation_id, D23.correlation_id, D23.reply_correlation_id, D29.correlation_id,
    D21.correlation_id, D21.ack_correlation_id, D19.correlation_id, D24.correlation_id

claim_named_in(envelope):                                  # folder choice only; never raises
    walk every node of envelope.fhir, collecting: the value of any identifier whose
    type.coding[0].code is "CLN"; every "display" and "reference" string (last path segment)
    return the first collected value that equals a D9 claim_no, else none
```

G8 then answers NHCX from the result:

```
answer_nhcx(result):                                     # in G8, after C1.receive returns
    if result in {settled, unmatched, ignored, rejected}:
        accept: the acceptance body, protocol_status "request.queued"   # NHCX does not redeliver
    else:                                                  # error
        fail with an error status                          # NHCX redelivers
```

**Shared rules** used by C2 to C10:

```
payload(envelope):
    if envelope.fhir is not an object: raise Rejected("The callback carried no readable payload.")
    return envelope.fhir

rejection(body):                                         # a ProtocolResponse, as text
    code = body["x-hcx-error_details"].code or "NHCX"
    message = body["x-hcx-error_details"].message or "The gateway rejected the request."
    return "<code>: <message>"

failed_send(row):                                        # the leg's last send is on record as failed
    return row.status == "error"
        or (row.error_message is set
            and row.error_message != "The payer did not accept the cancellation."
            and row.status in {approved, partial, queried})

revive(table, row, waiting_status):                      # the payer answered a send reported failed
    if failed_send(row):
        write table row: status = waiting_status, error_message = null; restamp the case stage

leg_write(table, id, values):                            # D18, D20, D21 writes
    write values; restamp the case stage (D9.stage, D9.sub_stage)

already_applied(row, api_call_id, parsed):               # C5 and C6
    if api_call_id: return row.api_call_id == api_call_id
    if row.status == "submitting": return false
    return row.outcome == parsed.outcome and row.adjudication == parsed.adjudication
```

A `ProtocolResponse` is always settled before `revive`: it is the exchange refusing the message, not an answer to it. A leg whose refusal left it in `error` stays open to the same refusal, so a redelivered `ProtocolResponse` settles again.

#### C1S. RESPONSE
`C1.receive` returns one result to G8, and G8 turns it into NHCX's answer:

| Result | When | G8 answers NHCX |
|---|---|---|
| `settled` | applied to a leg, or recorded as a new payer message | accept: no redelivery |
| `unmatched` | nothing here is waiting on it or answers to what it names. Redelivery cannot help | accept: no redelivery |
| `ignored` | a type or payload kind not handled, a message already applied, or a reply to a leg that has moved on | accept: no redelivery |
| `rejected` (with the reason) | the envelope is not an object (`Expected a JSON object.`), has no object `fhir` (`The callback carried no readable payload.`), or cannot be read as what its type says (for example `The payer reply carries no ClaimResponse.`, `That is not a payment notice.`). Redelivery cannot help. The envelope is already archived, with no outcome line | accept: no redelivery |
| `error` (with the reason) | any unexpected failure, for example the database unavailable | fail, so NHCX redelivers |

State changes are per callback (C2 to C10). The door itself writes only the archive: the envelope file and its `transactions.txt` line under the claim's folder (or `unmatched`), then the outcome line. G8 keeps its own record of the message and the result in G9.

#### C1U. USED BY
- Screens: [S6. Claim Detail](../screens/S6-claim-detail.md)
- APIs: [A2. Coverage Eligibility Check](../apis/A2-coverage-eligibility-check.md), [A3. Insurance Plan Request](../apis/A3-insurance-plan-request.md), [A4. Pre-auth Submit](../apis/A4-preauth-submit.md), [A5. Claim Submit](../apis/A5-claim-submit.md), [A6. Task Submit (cancel, status, reprocess, release)](../apis/A6-task-submit.md), [A10. Transaction Related](../apis/A10-txn-related.md), [A12. Transaction FHIR](../apis/A12-txn-fhir.md), [A13. Transaction List](../apis/A13-txn-list.md)
- Callbacks: [C2. Coverage Eligibility Verdict](C2-coverage-eligibility-on-check.md), [C3. Authorisation Requirements Ruling](C3-auth-requirements-on-check.md), [C4. Insurance Plan Reply](C4-insuranceplan-on-request.md), [C5. Pre-auth Reply](C5-preauth-on-submit.md), [C6. Claim Reply](C6-claim-on-submit.md), [C7. Cancel Reply](C7-cancel-on-submit.md), [C8. Enquiry Reply](C8-enquiry-on-submit.md), [C9. Payer Communication](C9-communication-request.md), [C10. Payment Notice](C10-paymentnotice-request.md)
- FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F11. CommunicationRequest](../fhir/F11-communicationrequest.md)
- Gateway: [G1. Embedding](../gateway/G1-embedding.md), [G2. Configuration and Participants](../gateway/G2-configuration.md), [G8. Receive](../gateway/G8-receive.md), [G9. Ledger](../gateway/G9-ledger.md)
