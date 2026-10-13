# C1. Callback Door

#### C1E. ENDPOINT
`C1.receive(envelope, delivery) -> outcome`, called in-process by [G8. Receive](../gateway/G8-receive.md) for every message NHCX delivers to this payer; G8 is its only caller. There is no HTTP route of its own: NHCX posts `{"payload": "<JWE>"}` to the application's public inbound route (`POST /in/<path>` or `POST /v1/<path>`, whichever the payer's registered `endpoint_url` points at), and G8 opens it and calls `receive`.

`envelope` is the decrypted message: `jwe_headers` and `fhir` (see C1Q). `delivery` describes how it arrived:

| `delivery` field | Value |
|---|---|
| `path` | the NHCX API path the message arrived on, for example `v1/preauth/submit`. Bookkeeping only: it never routes (C1D) |
| `type` | the entity G8 derives from the path (`coverage`, `insurance`, `preauth`, `claim`, `task`, `status`, `communication`, `payment`). Logged beside the classification when a message is ignored, never used to route |
| `flow` | `request` for an `on_` path, `on_request` otherwise. Recorded in the archive only |
| `payload_kind` | `fhir` (a decrypted JWE), `protocol` (a plain `ProtocolResponse` or error notice) or `json`. Anything but `fhir` is ignored, except a status enquiry carried in headers alone (C8) |
| `correlation_id` | `x-hcx-correlation_id` of the message |
| `api_call_id` | `x-hcx-api_call_id`, kept by NHCX across its redeliveries: the identity of the message |
| `redelivery` | true when [G9. Ledger](../gateway/G9-ledger.md) already holds this `api_call_id`. A hint only; [D28. nhcx_delivery](../database/D28-nhcx-delivery.md) decides |
| `participant` | the payer participant code the message was addressed to |

It carries every message a hospital starts (C2 to C8, C10) and the hospital's replies to what this payer started (C9 answers [A5. Query Request](../apis/A5-query-request.md), C11 answers [A6. Payment Notice](../apis/A6-payment-notice.md)). Routing is in C1P.

#### C1D. DESCRIPTION
G8 decrypts every message NHCX delivers for one of this payer's participant codes, resolves the code it was addressed to, calls `C1.receive`, then records the message and the outcome in G9. A message G8 cannot open (not JSON, an unreadable JWE, addressed to a code no key of the application opens) is refused by G8 itself and never reaches C1.

**The bundle decides what a message is.** The reference implementation received messages through a gateway whose type header spelled the same message differently for different exchanges and sometimes not at all, so it stopped trusting the path and the header and read the bundle instead [REF](../references/PAYERS.md#markers). This skill keeps that: the focal resource of [F1. Bundle](../fhir/F1-bundle.md) says what the message is, in this order, the first match winning:

| Classification | The bundle holds | Callback |
|---|---|---|
| `eligibility` | a `CoverageEligibilityRequest` ([F2. CoverageEligibilityRequest](../fhir/F2-coverage-eligibility-request.md)) | C2 |
| `communication` | a `Communication` ([F12. Communication](../fhir/F12-communication.md)), bare or behind a Task coded `poll` | C9 |
| `insuranceplan` | a `Task` coded `poll`, or with no code and intent `plan` or none ([F4. Task (InsurancePlan request)](../fhir/F4-task-insuranceplan.md)) | C3 |
| `paymentnotice` | a `PaymentNotice` ([F13. PaymentNotice](../fhir/F13-paymentnotice.md)); a `PaymentReconciliation` on its own is somebody's answer, not a question | C10 |
| `status` | a `Task` coded `status` that is not a payment acknowledgement, or no bundle at all with `x-hcx-status_filters` in the headers | C8 |
| `task` | any other `Task` ([F10. Task (claim actions and answers)](../fhir/F10-task-claim-actions.md)): `cancel`, `reprocess`, `release`, or a payment acknowledgement (output `paymentack`) | C7, or C11 for the acknowledgement |
| `preauth`, `claim`, `predetermination` | a `Claim` ([F8. Claim](../fhir/F8-claim.md)) by its `use` (`preauthorization` or the older `preauth`; `claim`; `predetermination`) | C4, C5, C6 |
| `communicationrequest` | a `CommunicationRequest` and nothing above | ignored, logged: a hospital does not query this payer [REF](../references/PAYERS.md#markers) |
| `reply` | a `ClaimResponse`, `CoverageEligibilityResponse`, `InsurancePlan` or `PaymentReconciliation` and nothing above | ignored, logged: an answer to somebody else's question |
| unknown | anything else, or no resources | ignored, logged with every `resourceType` seen |

The eligibility enquiry is the narrowest question, so it wins; a Claim is the heaviest, so it comes last among the questions; a reply never wins over a question.

**Three headers are required.** `x-hcx-sender_code`, `x-hcx-recipient_code` and `x-hcx-correlation_id` must all be present, because an answer with no addressee or no thread to hang on can never be delivered. A message without them is `rejected` ("The envelope needs sender and recipient codes and a correlation id"); redelivering the same envelope changes nothing.

**One message, once.** Before anything is applied, the delivery is recorded in [D28. nhcx_delivery](../database/D28-nhcx-delivery.md) under its `x-hcx-api_call_id` (the ledger id when the header is missing). A second delivery of the same id answers `ignored` (the reference answered "duplicate") and nothing is filed again: without this every redelivery turned a claim's four attachments into eight [REF](../references/PAYERS.md#markers). The `redelivery` flag from G8 is not used for this; D28 decides. Each handler is also idempotent in its own right (C1P, shared rules), so a message that slipped past D28 (a second application instance, a cleared table) still does no harm.

**Which desk.** `delivery.participant` is the payer code the message was addressed to. The application may serve more than one payer code (its own and a scheme's, or one per client in the sandbox); the case is filed under the addressed code and only desks that work that code see it [SANDBOX](../references/PAYERS.md#markers). A single-payer deployment has one code and ignores the distinction.

**Answered now or later.** C2, C3, C6, C8 and C10 answer inside the same delivery; when the gateway is not configured the delivery fails with `error` ("No gateway is configured, so the enquiry cannot be answered"), so NHCX keeps retrying until somebody wires the gateway in. C4 and C5 file first and acknowledge best-effort: a gateway that is down at that moment does not stop the case being opened.

**No session.** `C1.receive` runs inside the application with no user session. Its only way in from outside is G8's inbound route, which takes only what decrypts with one of the application's participant keys. The reference implementation also gated its door with a shared token in the callback URL, which an embedded gateway does not need [REF](../references/PAYERS.md#markers).

#### C1Q. REQUEST
`envelope` is the message as G8 decrypted it. `jwe_headers` holds the NHCX protocol headers; the ones read are `x-hcx-sender_code` (the hospital, the recipient of every answer), `x-hcx-recipient_code` (this payer's code), `x-hcx-correlation_id` (the thread every answer travels on), `x-hcx-api_call_id` (the dedupe key), `x-hcx-workflow_id` (echoed on an answer, C8 matches on it too) and `x-hcx-status_filters` (C8). `fhir` is an [F1. Bundle](../fhir/F1-bundle.md) Bundle, or empty for a header-only status enquiry, or a plain `ProtocolResponse` when NHCX refused something this payer sent (kind `protocol`, ignored here; a refused send is handled where it was sent, A1 to A10).

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
    if delivery.payload_kind not in {fhir} and not status_filters(envelope):
        return "ignored"                                    # protocol, json: not a message for this door
    message = classify(envelope)                            # table in C1D; kind, resource types, parsed ask
    if message.kind in {communicationrequest, reply, unknown}:
        log "nhcx delivery ignored", kind, delivery.type, delivery.flow, delivery.path, message.resource_types
        return "ignored"
    if message.kind in {eligibility, insuranceplan, paymentnotice, predetermination, status}
            and gateway not configured:
        return error("No gateway is configured, so the enquiry cannot be answered")   # NHCX retries

    sender    = header(envelope, "x-hcx-sender_code")
    recipient = header(envelope, "x-hcx-recipient_code")
    corr      = header(envelope, "x-hcx-correlation_id")
    if sender == "" or recipient == "" or corr == "":
        raise Rejected("The envelope needs sender and recipient codes and a correlation id")

    key = header(envelope, "x-hcx-api_call_id") or delivery ledger id
    if not D28.mark_delivery(key, message.kind, ledger id):      # INSERT; a duplicate key means seen before
        return "ignored"                                    # the reference answered "duplicate"

    in = {envelope, payer: D1 row, ledger_id, sender, recipient, corr,
          workflow_id: header(envelope, "x-hcx-workflow_id")}
    archived = archive_inbound(envelope, message.kind, corr, delivery.participant)
    outcome = route(message, in)
    archive_note(archived, outcome)                         # skipped when route raised
    return outcome

route(message, in):
    if message.kind == eligibility:       return C2(in, message.ask)
    if message.kind == insuranceplan:     return C3(in, message.plan)
    if message.kind == preauth:           return C4(in, message.claim)
    if message.kind == claim:             return C5(in, message.claim)
    if message.kind == predetermination:  return C6(in, message.claim)
    if message.kind == status:            return C8(in, message.task)
    if message.kind == paymentnotice:     return C10(in, message.payment)
    if message.kind == communication:     return C9(in, message.communication)
    if message.kind == task:
        if message.task.output_status == "paymentack": return C11(in, message.task)
        return C7(in, message.task)

classify(envelope):
    types = resourceType of every entry in envelope.fhir
    if types empty:
        if status_filters(envelope): return {kind: status, task: {code: "status"}}
        return {kind: unknown, resource_types: []}
    if a CoverageEligibilityRequest: return {kind: eligibility, ask: F2 parse}
    if a Communication:              return {kind: communication, communication: F12 parse}
    if a Task that is a plan request (code "poll", or no code and intent "plan" or none):
                                     return {kind: insuranceplan, plan: F4 parse}
    if a PaymentNotice:              return {kind: paymentnotice, payment: F13 parse}
    if a Task that is not a plan request:
        task = F10 parse
        return {kind: status if task.code == "status" and task.output_status != "paymentack" else task, task}
    if a Claim with use in {preauthorization, preauth, claim, predetermination}:
        claim = F8 parse
        return {kind: claim if use == claim, predetermination if use == predetermination, else preauth, claim}
    if a CommunicationRequest: return {kind: communicationrequest}
    if a ClaimResponse, CoverageEligibilityResponse, InsurancePlan or PaymentReconciliation:
                                     return {kind: reply}
    return {kind: unknown, resource_types: types}

archive_inbound(envelope, kind, corr, participant):
    case = case_for_correlation(corr) or case_named_in(envelope)
    folder = case.claim_no if case else "unmatched"
    write <archive dir>/<folder>/<NNN>-<kind>-in.json          # whole envelope, unchanged
    append to <folder>/transactions.txt:
        time  NNN  IN  <kind>  workflow=<x-hcx-workflow_id>  correlation=<corr>
        api_call=<x-hcx-api_call_id>  participant=<participant>  file=<name>
    # a disk failure is logged and never breaks the receive; archiving can be switched off

archive_note(archived, outcome):
    append "    -> <file> outcome=<outcome>" to that folder's transactions.txt

case_for_correlation(corr):
    the D19 row whose nhcx_correlation_id, nhcx_claim_correlation_id,
    nhcx_query_correlation_id or nhcx_reprocess_correlation_id equals corr, else none

case_named_in(envelope):                                   # folder choice only; never raises
    every identifier value typed CLN, every "display" and "reference" string (last path segment)
    return the first that equals a D19 claim_no, id, nhcx_claim_ref or nhcx_claim_submission_ref, else none
```

G8 then answers NHCX from the result:

```
answer_nhcx(result):                                     # in G8, after C1.receive returns
    if result in {settled, unmatched, ignored, rejected}:
        accept: the acceptance body, protocol_status "request.queued"   # NHCX does not redeliver
    else:                                                  # error
        fail with an error status                          # NHCX redelivers
```

**Shared rules** used by C2 to C11:

```
payload(envelope):
    if envelope.fhir is not an object: raise Rejected("The callback carried no readable payload.")
    return envelope.fhir

answer(in, bundle, path, workflow, status, what):        # every answer on the hospital's thread
    headers = {x-hcx-sender_code: in.recipient, x-hcx-recipient_code: in.sender,
               x-hcx-correlation_id: in.corr,
               x-hcx-workflow_id: workflow (left off when empty), x-hcx-status: status}
    try: ack = gateway.send(path, {jwe_headers: headers, fhir: bundle})       # G7
    catch refused (the gateway looked at the envelope and would refuse it again):
        raise Rejected("The gateway refused the answer: " + message)
    catch unreachable or 5xx:
        raise Error("The gateway could not queue the answer")                # NHCX retries the delivery
    D31 audit {action: what + ".answered", entity: "nhcx_txn", id: in.ledger_id,
               detail: ... + ", answer txn " + ack.txn_id}
    return ack

find_enrolment(handles):                                  # C2, C4, C6
    D6 in force today (active, pstart <= today <= pend) matched by ABHA (member or enrolment),
    the last ten digits of the mobile, or the member id; else the most recently ended
    enrolment of the same person, whatever its status; else none

case_for_claim_ref(ref, sender):                          # C5, C7, C8, C9, C10
    the D19 row whose claim_no, id, nhcx_claim_ref or nhcx_claim_submission_ref equals ref,
    filed by sender (or by nobody), an open case (stage preauth or claim) before a closed one,
    the newest first; none when ref is blank

resolve_documents(documents):                             # C4, C5, C9
    for each: code = D3 code equal to the sent code, else the D3 code whose si_category equals it
    a code neither resolves is filed as ODN ("other document") and its original code is named
    on the case timeline: "N attachment(s) arrived under codes this payer does not know (...);
    they are filed as other documents rather than dropped"
    phase defaults to claim when not preauth or claim; doc_type to pdf when not pdf or image
    a document already on the case under the same code, title and size is not filed twice

exchange_message(case, direction, kind, corr, ledger_id, counterparty, summary, payload):
    one D27 row; a row with the same case, direction, kind and ledger id already there is not repeated
```

A handler never raises for a message it cannot use: it answers `rejected` (redelivery cannot help) or `ignored`. Only an unexpected fault (the database unavailable, the gateway down when an answer was due) is `error`.

#### C1S. RESPONSE
`C1.receive` returns one result to G8, and G8 turns it into NHCX's answer:

| Result | When | G8 answers NHCX |
|---|---|---|
| `settled` | filed on a case, answered on the spot, or recorded as the hospital's reply or acknowledgement | accept: no redelivery |
| `unmatched` | a Communication, a Task or a payment acknowledgement that names no case this payer holds (C7 still sends a refusal to the hospital, C10 an answer) | accept: no redelivery |
| `ignored` | a classification not handled, a `protocol` or `json` payload, or a delivery already recorded in D28 | accept: no redelivery |
| `rejected` (with the reason) | the envelope is not an object, lacks sender, recipient or correlation id, carries no readable payload, matches no enrolment (C4, C5), bills a closed case (C5), or the gateway refused the answer | accept: no redelivery |
| `error` (with the reason) | an unexpected failure, or an answer due now with no gateway to send it | fail, so NHCX redelivers |

State changes are per callback (C2 to C11). The door itself writes the delivery receipt ([D28. nhcx_delivery](../database/D28-nhcx-delivery.md), before anything else) and the archive: the envelope file and its `transactions.txt` line under the case's folder (or `unmatched`), then the outcome line. G8 keeps its own record of the message and the result in G9.

#### C1U. USED BY
- APIs: [A1. Eligibility Answer](../apis/A1-eligibility-answer.md), [A2. Insurance Plan Answer](../apis/A2-insurance-plan-answer.md), [A7. Payment Enquiry Answer](../apis/A7-payment-enquiry-answer.md), [A11. Transaction Related](../apis/A11-txn-related.md), [A12. Transaction FHIR](../apis/A12-txn-fhir.md)
- Callbacks: [C2. Coverage Eligibility Check](C2-coverage-eligibility-check.md), [C3. Insurance Plan Request](C3-insurance-plan-request.md), [C4. Pre-auth Submit](C4-preauth-submit.md), [C5. Claim Submit](C5-claim-submit.md), [C6. Predetermination](C6-predetermination.md), [C7. Task Submit](C7-task-submit.md), [C8. Status Enquiry](C8-status-enquiry.md), [C9. Communication](C9-communication.md), [C10. Payment Enquiry](C10-payment-enquiry.md), [C11. Payment Acknowledgement](C11-payment-acknowledgement.md)
- FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F8. Claim](../fhir/F8-claim.md), [F10. Task (claim actions and answers)](../fhir/F10-task-claim-actions.md), [F19. Other resources](../fhir/F19-other-resources.md)
- Database: [D28. nhcx_delivery](../database/D28-nhcx-delivery.md), [D31. audit_log](../database/D31-audit-log.md)
- Gateway: [G1. Embedding](../gateway/G1-embedding.md), [G2. Configuration and Participants](../gateway/G2-configuration.md), [G8. Receive](../gateway/G8-receive.md), [G9. Ledger](../gateway/G9-ledger.md)
- Tests: [T2. Test Runners](../tests/T2-test-runners.md), [T18. Redelivery and Duplicates](../tests/T18-redelivery-ignored.md)
