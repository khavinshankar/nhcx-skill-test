# G8. Receive

#### G8E. ENTRY
HTTP routes the gateway serves for NHCX (mounted by G1 on the application's listener, no API key):

| Route | NHCX path handed on |
|---|---|
| `POST /in/<path>` | `<path>`, for example `v1/preauth/submit` (registry `endpoint_url` ending `/in`) |
| `POST /v1/<path>` | `v1/<path>` (registry `endpoint_url` at the root) |

In-process, the gateway then calls the application's callback door once per accepted message:

- `C1.receive(envelope, delivery) -> outcome` (the application's function; G8 is its only caller)

Internal steps, exposed for tests: `gateway.receive(path, body, remote_addr) -> Inbound`, `gateway.record_inbound(inbound, result, error)`, `gateway.record_refused(path, remote_addr, peeked_headers, error)`.

#### G8D. DESCRIPTION
NHCX posts `{"payload": "<compact JWE>"}` for every message addressed to a participant whose registry `endpoint_url` points at this application. The gateway decrypts it, works out who it was addressed to, hands the decrypted envelope to C1 in-process and waits for C1's result. Only then does it answer NHCX: `202` with the acceptance body when C1 took the message, an error status otherwise. NHCX redelivers a message it did not see accepted, five attempts in all, then drops the correlation id. So C1 must be idempotent on `x-hcx-api_call_id` / `x-hcx-correlation_id`; the gateway marks a repeat with `redelivery = true`.

A body without `payload` is not encrypted: a `ProtocolResponse` or error notice carries its protocol headers as top-level `x-hcx-*` keys. It is handed to C1 as it is, kind `protocol` (or `json` when it has no `x-hcx-*` key and no `type`).

Recipient resolution, for an encrypted message:
1. Read `x-hcx-recipient_code` from the JWE protected header without decrypting.
2. A code the gateway hosts (the payer's own code as the default participant, a scheme code under `participants` or added with the host option, G2) is local. A non-empty code that is not local is a guest.
3. A guest with guests not enabled (G2) is refused `WRONG_RECIPIENT` before decryption.
4. Decrypt with the addressed participant's private key first, then every other hosted participant's key, each distinct key once. Hosted codes that share the default's certificate share its key, so this is one attempt in the common case.
5. No key opens it: a guest is refused `WRONG_RECIPIENT` (it was never meant for here); anything else is `DECRYPT_FAILED`.
6. `participant` for the delivery is the guest's own code for a guest, else the code of the profile whose key was addressed (or the first profile whose key opened it). For a protocol message it is its `x-hcx-recipient_code`, as sent.

Guests are how one deployment serves any participant code whose registry record carries this gateway's `endpoint_url` and one of its certificates. The application decides from `participant` (and the path) which desk the message belongs to: the insurer's own, or a PMJAY scheme desk hosted beside it [REF](../references/PAYERS.md#markers).

#### G8Q. INPUT
From NHCX (HTTP):

| Part | Value |
|---|---|
| body | `{"payload": "<compact JWE>"}` (JSON object), or a plain protocol JSON object. Limit `maxBodyBytes`, default 100 MiB |
| peer address | the TCP peer; `X-Forwarded-For` is not trusted |

To C1 (in-process). `envelope`:

```json
{"meta": {"type": "in", "payloadType": "fhir", "path": "v1/preauth/submit",
          "ip": "10.0.0.5", "time": "2026-09-21T12:01:05+05:30",
          "redelivery": false, "participant": "<payer code>"},
 "jwe_headers": {"alg": "RSA-OAEP-256", "enc": "A256GCM",
                 "x-hcx-sender_code": "<facility code>", "x-hcx-recipient_code": "<payer code>",
                 "x-hcx-correlation_id": "...", "x-hcx-api_call_id": "...", "...": "..."},
 "fhir": {"resourceType": "Bundle", "...": "..."}}
```

`jwe_headers` is the whole protected header (or, for a protocol message, its top-level `x-hcx-*` keys), with null values dropped and sender and recipient codes given the `@hcx` suffix. `fhir` is the decrypted payload (a non-JSON plaintext becomes a JSON string), or the whole plain body for a protocol message.

`delivery`, passed as an argument beside the envelope:

| Field | Value |
|---|---|
| `path` | the NHCX path, slashes trimmed |
| `type` | entity of the path: `coverage` (coverageeligibility), `insurance` (insuranceplan), `preauth`, `claim`, `task`, `communication`, `payment` (paymentnotice), `status` (`v1/on_status`), `error` (`v1/error`), otherwise the path's entity segment. These short names are [REF](../references/PAYERS.md#markers) |
| `flow` | `request` for a response path (`on_...`), `on_request` otherwise (naming kept as the reference implementation has it [REF](../references/PAYERS.md#markers)); most of what a payer receives is `on_request`, and C1 never routes on it |
| `payload_kind` | `fhir`, `protocol` or `json` |
| `correlation_id` | `x-hcx-correlation_id`, may be empty |
| `api_call_id` | `x-hcx-api_call_id`; stable across NHCX's redeliveries, so it is the dedupe key |
| `redelivery` | the ledger already holds an inbound row with this `api_call_id` |
| `participant` | the addressed code, resolved as in G8D |

#### G8S. OUTPUT
C1's result, and what NHCX is answered:

| C1 result | Ledger status | NHCX gets |
|---|---|---|
| returns an outcome (`settled`, `unmatched`, `ignored`) | `delivered` | `202` with the acceptance body |
| returns `rejected` (unreadable body; redelivery cannot help) | `delivered`, outcome `rejected` kept on `peer.outcome` | `202` with the acceptance body; no redelivery |
| returns `error`, or raises | `delivery_failed`, error `RECEIVE_FAILED`, retryable | `502` error body; NHCX redelivers |

A `rejected` message is accepted so NHCX does not redeliver a body that can never be read. The ledger entry is written after C1 returns, so it carries the outcome.

The gateway keeps C1's answer on the ledger row as `peer` (`url` = the in-process handler name, `status_code` = the equivalent status, `response` = the outcome body).

Acceptance body (`202`, and response header `X-Nhcx-Ledger-Id: <ledger id>` when recorded):

```json
{"timestamp": "21/09/2026 12:01:05:480",
 "api_call_id": "<x-hcx-api_call_id, or a fresh UUID when it is not one>",
 "correlation_id": "<x-hcx-correlation_id, or a fresh UUID when it is not one>",
 "result": {"sender_code": "<facility code>", "recipient_code": "<payer code>",
            "entity_type": "preauth", "protocol_status": "request.queued"},
 "error": null}
```

`entity_type` is the path's entity in protocol spelling (`coverageeligibility`, `insuranceplan`, `preauth`, `claim`, `task`, `communication`, `payment`, `status`). `timestamp` is local time as `DD/MM/YYYY hh:mm:ss:mmm`.

Error body to NHCX (any failure):

```json
{"ok": false, "error": {"code": "WRONG_RECIPIENT", "message": "...", "retryable": false},
 "request_id": "<X-Request-Id or a fresh UUID>", "upstream_status": 400, "upstream_body": {"...": "..."}}
```

`upstream_status` and `upstream_body` appear only for callback failures (C1's equivalent status and body).

| Code | NHCX gets | Ledger | When |
|---|---|---|---|
| `BODY_TOO_LARGE` | 413 | none | body over `maxBodyBytes` |
| `BODY_READ` | 400 | none | body could not be read |
| `INVALID_BODY` | 400 | `rejected`, kind `unknown` | body not a JSON object |
| `INVALID_JWE` | 400 | `rejected`, kind `unknown` | `payload` not a compact JWE string, or its protected header unreadable |
| `WRONG_RECIPIENT` | 400 | `rejected`, kind `unknown` | a code not hosted and guests off; or a guest no key opens |
| `DECRYPT_FAILED` | 422 | `rejected`, kind `unknown` | no hosted key opens a message for a hosted (or absent) code |
| `RECEIVE_FAILED` | 502 | `delivery_failed` | C1 answered `error` or raised, table above |
| `MARSHAL_ERROR` | 500 | `rejected` | the envelope could not be encoded |
| `INTERNAL` | 500 | none | a panic in the handler |

A refused message is recorded with the headers peeked from its JWE (no decryption), so its ids are visible in the ledger. An `api_call_id` recorded this way also counts for the next delivery's `redelivery` flag.

#### G8P. PSEUDOCODE

```text
on POST /in/<p>:  inbound(path = p)
on POST /v1/<p>:  inbound(path = "v1/" + p)

inbound(path):
    body = read request body (limit maxBodyBytes)
        too large -> answer 413 BODY_TOO_LARGE; other read error -> 400 BODY_READ
    try in = receive(path, body, peer_ip)
    on error e:
        record_refused(path, peer_ip, peek_headers(body), e)
        answer error(e)                                        // status per G8S
        return
    result, err = deliver(in)
    record_inbound(in, result, err)                            // sets in.ledger_id
    if err: answer error(err); return                           // 502 for RECEIVE_FAILED
    if in.ledger_id: set response header X-Nhcx-Ledger-Id
    answer 202 acceptance(in)

receive(path, body, ip):
    obj = parse body as JSON object, else raise INVALID_BODY "body must be a JSON object"
    in = {path: trim_slashes(path), received_at: now, remote_addr: ip}
    if "payload" in obj:
        jwe = obj.payload as string; if not a compact JWE: raise INVALID_JWE
        hdr = protected header of jwe (G6), else raise INVALID_JWE "unreadable JWE protected header"
        rc = hdr["x-hcx-recipient_code"]
        guest = rc != "" and rc is not a hosted code
        if guest and guests not enabled:
            raise WRONG_RECIPIENT "message is addressed to <rc>, this adapter holds <codes>"
        profile, plain = decrypt_for(rc, jwe)
            on DECRYPT_FAILED:
                if guest: raise WRONG_RECIPIENT "... none of its keys opens it; a guest is served
                                                 once its registry record carries this adapter's certificate"
                raise DECRYPT_FAILED
        in.profile = profile
        if guest: in.guest = with_hcx_suffix(rc)
        if plain is not valid JSON: plain = JSON string of plain
        in.kind = "fhir"; in.headers = normalise(hdr); in.payload = plain
    else:
        in.payload = body
        in.headers = every top-level key of obj starting "x-hcx-"
        in.kind = "protocol" if in.headers non-empty or obj has "type" else "json"
        in.headers = normalise(in.headers)
    in.redelivery = ledger on and ledger.seen("in", in.headers["x-hcx-api_call_id"])
    return in

decrypt_for(code, jwe):
    tried = {}
    for profile in [hosted profile for code] + all hosted profiles in order:
        if profile has no key or its key is in tried: continue
        add key to tried
        if decrypt(jwe, profile.key) succeeds: return profile, plaintext     // G6
    raise DECRYPT_FAILED "payload could not be decrypted with any configured participant's private key"

normalise(h):  drop null values; give sender_code and recipient_code the "@hcx" suffix

participant(in):  in.guest if set, else in.profile.code if set, else in.headers.recipient_code

deliver(in):
    envelope = {meta: {type: "in", payloadType: in.kind, path: in.path, ip: in.remote_addr,
                       time: in.received_at as RFC 3339, redelivery: in.redelivery,
                       participant: participant(in)},
                jwe_headers: in.headers, fhir: in.payload}
    delivery = {path: in.path, type: kit_type(in.path), flow: kit_flow(in.path),
                payload_kind: in.kind, correlation_id: in.headers.correlation_id,
                api_call_id: in.headers.api_call_id, redelivery: in.redelivery,
                participant: participant(in)}
    start = now
    try outcome = C1.receive(envelope, delivery)       // settled | unmatched | ignored | rejected | error
    on e:           return {outcome: "error", detail: e text, duration},
                           error RECEIVE_FAILED "C1 could not apply the message", retryable true
    if outcome == "error":
                    return {outcome, duration},
                           error RECEIVE_FAILED "C1 could not apply the message", retryable true
    return {outcome, duration: now - start}, no error   // rejected is accepted too
    // The result is internal: it goes on the ledger row as `peer`. NHCX never
    // sees it; the caller answers NHCX 202 (no error) or 502 (RECEIVE_FAILED).

kit_type(path):  e = entity_type(path)       // G5: segment before the action; "v1/on_status" -> status;
                                             // "paymentnotice" -> payment; leading "on_" dropped
                 "insuranceplan" -> "insurance"; "coverageeligibility" -> "coverage"; else e
kit_flow(path):  "request" if the last segment starts "on_" else "on_request"

record_inbound(in, result, err):              // no-op when the ledger is off
    entry = {direction: "in", created_at: in.received_at, path: in.path, format: in.kind,
             sender, recipient, correlation_id, api_call_id, request_id, workflow_id,
             hcx_status: from in.headers, headers: in.headers, fhir: in.payload,
             redelivery: in.redelivery, duration_ms: now - in.received_at}
    if result: entry.peer = {handler: "C1.receive", outcome: result.outcome}; entry.duration_ms = result.duration
    if no err:                             entry.status = "delivered"
    else if err.code == "RECEIVE_FAILED":  entry.status = "delivery_failed"; entry.error = {code, message}
    else:                                  entry.status = "rejected";        entry.error = {code, message}
    ledger.record(entry)                   // G9; a write failure is only logged
    in.ledger_id = entry.id

record_refused(path, ip, headers, err):
    record_inbound({path, kind: "unknown", headers: normalise(headers), received_at: now,
                    remote_addr: ip}, none, err)

acceptance(in):
    {timestamp: now as "DD/MM/YYYY hh:mm:ss:mmm",
     api_call_id: in.headers.api_call_id if a UUID else a fresh UUID,
     correlation_id: in.headers.correlation_id if a UUID else a fresh UUID,
     result: {sender_code, recipient_code: from in.headers,
              entity_type: entity_type(in.path), protocol_status: "request.queued"},
     error: null}
```

#### G8U. USED BY
- APIs: [A1. Eligibility Answer](../apis/A1-eligibility-answer.md), [A11. Transaction Related](../apis/A11-txn-related.md), [A12. Transaction FHIR](../apis/A12-txn-fhir.md)
- Callbacks: [C1. Callback Door](../callbacks/C1-callback-door.md), [C2. Coverage Eligibility Check](../callbacks/C2-coverage-eligibility-check.md), [C3. Insurance Plan Request](../callbacks/C3-insurance-plan-request.md), [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md), [C5. Claim Submit](../callbacks/C5-claim-submit.md), [C6. Predetermination](../callbacks/C6-predetermination.md), [C7. Task Submit](../callbacks/C7-task-submit.md), [C8. Status Enquiry](../callbacks/C8-status-enquiry.md), [C9. Communication](../callbacks/C9-communication.md), [C10. Payment Enquiry](../callbacks/C10-payment-enquiry.md), [C11. Payment Acknowledgement](../callbacks/C11-payment-acknowledgement.md)
- FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F17. Organization](../fhir/F17-organization.md)
- Database: [D28. nhcx_delivery](../database/D28-nhcx-delivery.md)
- Gateway: [G1. Embedding](G1-embedding.md), [G2. Configuration and Participants](G2-configuration.md), [G3. Session Token](G3-session-token.md), [G5. Protocol Headers](G5-protocol-headers.md), [G6. Encryption](G6-encryption.md), [G9. Ledger](G9-ledger.md)
- Tests: [T2. Test Runners](../tests/T2-test-runners.md), [T18. Redelivery and Duplicates](../tests/T18-redelivery-ignored.md)
