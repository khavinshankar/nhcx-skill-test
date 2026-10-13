# G7. Send

#### G7E. ENTRY
In-process, called by A1 to A10:

- `gateway.send(path, envelope) -> SendResult` or raises `SendError`
- `gateway.parse_outbound(path, envelope) -> OutboundRequest` (called by `send`; exposed so a caller can validate an envelope without sending)

Calls out (all through the sending participant's ABDM client, G3 and G4):

| Call | URL | When |
|---|---|---|
| encryption certificate | `POST <urls.participant>/fetch/certs` | recipient certificate not in the cache (G4) |
| session token | `<urls.sessions>` | no cached token, or within a minute of expiry, or after a 401 (G3) |
| dispatch | `POST <urls.nhcx>/<path>` | every send that got this far |

`send` has no timeout of its own; the only timeouts are the ABDM ones (`outboundTimeoutSeconds`, default 30 s per call).

#### G7D. DESCRIPTION
Turns one FHIR payload into one encrypted NHCX message and posts it, synchronously. There is no queue and no worker: when `send` returns, NHCX has already answered (usually `202`), or the send has failed. Every attempt that got past the envelope checks is recorded in the ledger (G9), whether NHCX accepted it, NHCX refused it, or it never left.

Steps: complete the protocol headers (G5), pick the sending identity from `x-hcx-sender_code`, fetch the recipient's certificate (G4), encrypt (G6), dispatch with the session token (G3), record.

Which identity sends: the participant named in `x-hcx-sender_code`. When absent, the default participant's code is filled in. A code the gateway does not host is not refused: it goes out on the default participant's session and certificate cache, with the given code still in the protected header.

Threading a response: when the ledger is on, the path is a response path (last segment starts `on_`, for example `v1/communication/on_request`) and the caller gave no valid UUID correlation id, the gateway uses the correlation id (and, if the caller gave none, the workflow id) of the newest inbound request of the same entity from the recipient (and within the caller's workflow id, when given) [REF](../references/PAYERS.md#markers). With no match, a fresh correlation id is minted, which NHCX will refuse for a response. The answering APIs (A1 to A4, A7 to A10) always pass the correlation id of the request they answer, taken from the case or the delivery, so the fallback is never relied on; A5 and A6 start a thread and pass none.

Failure after the ids were minted still names them: a connection dropped after the request was written is reported as unreachable, yet NHCX may have taken the message. The caller keeps the correlation id so a late answer still matches.

NHCX refusing the message (a 4xx or 5xx from NHCX) is not an error of `send`: it returns a `SendResult` with `ok = false` and NHCX's status and body. The application treats `ok = false` as a failed send (see G7S).

#### G7Q. INPUT
`path`: the NHCX API path, for example `v1/preauth/submit`. Leading and trailing slashes are trimmed.

`envelope`: a JSON object of this shape.

```json
{"fhir": {"resourceType": "Bundle", "...": "..."},
 "jwe_headers": {"x-hcx-sender_code": "<payer code>", "x-hcx-recipient_code": "<facility code>",
                 "x-hcx-workflow_id": "<workflow id>"}}
```

The workflow id is the one the scheme dialect gives for the kind of send, or the request's own when an answer echoes it (see [PAYERS.md](../references/PAYERS.md)) [PAYER](../references/PAYERS.md#markers).

| Field | Type | Default | Meaning |
|---|---|---|---|
| `fhir` | JSON | none | the payload. Else `payload`. Else `INVALID_ENVELOPE` |
| `payload` | JSON | none | read when `fhir` is absent |
| `jwe_headers` | object | `{}` | protected header values, copied as given |
| `x-hcx-sender_code`, `x-hcx-recipient_code`, `x-hcx-correlation_id`, `x-hcx-request_id`, `x-hcx-api_call_id`, `x-hcx-workflow_id`, `x-hcx-status`, `x-hcx-timestamp` | string | none | top-level header keys; override `jwe_headers` |
| `sender`, `recipient`, `correlation_id`, `request_id`, `api_call_id`, `workflow_id`, `status` | string | none | short aliases of the keys above; override both |

Precedence, lowest first: `jwe_headers`, then top-level `x-hcx-*` keys, then the short aliases. Non-string top-level values are taken as their JSON text with quotes stripped.

Header completion (G5): sender and recipient get the `@hcx` suffix; `x-hcx-correlation_id`, `x-hcx-request_id` and `x-hcx-api_call_id` are kept only when they are UUIDs, otherwise minted; `x-hcx-status` defaults to `request.initiated` (`response.complete` on an `on_` path); `x-hcx-timestamp` defaults to now; an empty `x-hcx-workflow_id` is dropped. Only `recipient` is required.

#### G7S. OUTPUT
`SendResult` (the call reached NHCX and NHCX answered):

| Field | Type | Meaning |
|---|---|---|
| `ok` | bool | NHCX answered 2xx |
| `path` | string | the cleaned path |
| `url` | string | the NHCX URL posted to |
| `headers` | object | the complete protected header set that went out |
| `gateway_status` | int | NHCX's HTTP status (202 in practice) |
| `response` | JSON | NHCX's body; a non-JSON body as a JSON string; empty as `null` |
| `duration_ms` | int | time of the dispatch call |
| `ledger_id` | string | the ledger id (G9); `""` when the ledger is off |
| `txn_id` | string | same value as `ledger_id`; the id A11 and A12 take |
| `correlation_id` | string | `headers["x-hcx-correlation_id"]` |
| `api_call_id` | string | `headers["x-hcx-api_call_id"]` |
| `request_id` | string | `headers["x-hcx-request_id"]` |

```json
{"ok": true, "path": "v1/preauth/on_submit", "url": "https://.../v1/preauth/on_submit",
 "gateway_status": 202, "headers": {"x-hcx-correlation_id": "...", "x-hcx-api_call_id": "..."},
 "response": {"...": "NHCX body"}, "duration_ms": 412,
 "ledger_id": "7UMV0007", "txn_id": "7UMV0007", "correlation_id": "...", "request_id": "..."}
```

When `ok` is false the send failed at NHCX: the ids above are the ids it went out under, the ledger row is `rejected` with error `GATEWAY_HTTP_<status>` / "NHCX did not accept the message", and the application records the leg as failed under those ids (A-conventions). The message to show is NHCX's own `response.error.code` and `.message` when present, else `GATEWAY_HTTP_<status>: NHCX did not accept the message`.

`SendError`:

| Field | Meaning |
|---|---|
| `code` | stable code, table below |
| `message` | text for the operator |
| `retryable` | the same call may reasonably be repeated |
| `upstream_status`, `upstream_body` | the ABDM service's status and body (JSON when parseable), when there was one |
| `ledger_id`, `txn_id`, `headers`, `correlation_id`, `api_call_id`, `request_id` | present only when the failure came after the headers were built (from `NO_RECIPIENT` down in the table). `request_id` is left out when empty |

| Code | `retryable` | Ids named | When |
|---|---|---|---|
| `INVALID_ENVELOPE` | no | no | envelope not a JSON object, `jwe_headers` not an object, or no `fhir` / `payload` |
| `NO_PATH` | no | no | path empty after trimming |
| `INVALID_PAYLOAD` | no | no | payload empty or not valid JSON |
| `NO_RECIPIENT` | no | yes | no `x-hcx-recipient_code` |
| `CERT_NOT_FOUND` | no | yes | registry has no usable encryption certificate for the recipient |
| `SELF_ENCRYPTION_KEY` | no | yes | the registry returned one of the gateway's own keys for a code it does not host, and self-keys are refused (production default, G4) |
| `CERT_FETCH_HTTP_<n>` | when n >= 500 or 429 | yes | registry refused the certificate lookup |
| `CERT_FETCH_BAD_JSON` | yes | yes | registry answer not JSON |
| `CERT_FETCH_UNREACHABLE`, `CERT_FETCH_READ_ERROR` | yes | yes | registry transport failure |
| `CERT_FETCH_REQUEST` | no | yes | request could not be built |
| `TOKEN_UNREACHABLE`, `TOKEN_BAD_JSON` | yes | yes | session service transport or body failure (G3) |
| `TOKEN_HTTP_<n>` | when n >= 500 or 429 | yes | session service refused the credentials |
| `TOKEN_MISSING`, `TOKEN_REQUEST` | no | yes | no token in the answer; request not buildable |
| `ENCRYPT_ERROR` | no | yes | JWE encryption failed (G6) |
| `GATEWAY_UNREACHABLE`, `GATEWAY_READ_ERROR` | yes | yes | NHCX transport failure. The message may still have arrived |
| `GATEWAY_REQUEST` | no | yes | request not buildable |
| `MARSHAL_ERROR`, `INTERNAL` | no | yes | encoding failure; any untyped error |

A second 401 from NHCX after a token refresh is not an error: it comes back as a `SendResult` with `gateway_status` 401 and `ok` false.

Ledger statuses written (G9): `accepted` (NHCX 2xx), `rejected` (NHCX non-2xx, error `GATEWAY_HTTP_<n>`), `failed` (never reached NHCX, error = the `SendError` code and message). Nothing is written for `INVALID_ENVELOPE`, `NO_PATH` and `INVALID_PAYLOAD`. A ledger write failure is logged and never fails the send.

#### G7P. PSEUDOCODE

```text
parse_outbound(path, envelope):
    if envelope is not a JSON object: raise INVALID_ENVELOPE "body must be a JSON object"
    headers = {}
    if "jwe_headers" in envelope:
        if not an object: raise INVALID_ENVELOPE "jwe_headers must be an object"
        copy every key of it into headers
    for k in the eight x-hcx-* keys: if k in envelope: headers[k] = as_string(envelope[k])
    for alias, k in {sender, recipient, correlation_id, request_id, api_call_id, workflow_id, status}:
        if alias in envelope: headers[k] = as_string(envelope[alias])
    fhir = envelope.fhir if non-empty
           else envelope.payload if non-empty
           else raise INVALID_ENVELOPE 'body needs a "fhir" object or must itself be a FHIR resource'
    return {path, headers, fhir}

send(path, envelope):
    req = parse_outbound(path, envelope)
    path = trim_slashes(req.path)
    if path == "": raise NO_PATH
    if req.fhir is blank or not valid JSON: raise INVALID_PAYLOAD "fhir payload must be a JSON value"

    if ledger on and path is a response path and req.headers.correlation_id is not a UUID:
        prev = ledger.last_inbound_request(entity_type(path),
                                           from = req.headers.recipient,
                                           workflow = req.headers.workflow_id)   // G9
        if prev:
            req.headers.correlation_id = prev.correlation_id
            if prev.workflow_id and req.headers.workflow_id empty:
                req.headers.workflow_id = prev.workflow_id

    headers = build_protected_headers(req.headers, path)                          // G5
    if headers.sender_code empty: headers.sender_code = default participant code
    sender = identity for headers.sender_code, else the default identity          // G2
    recipient = headers.recipient_code
    start = now
    entry = {direction: "out", created_at: start, path, format: "fhir",
             sender, recipient, correlation_id, api_call_id, request_id, workflow_id,
             hcx_status: headers.status, headers, fhir: compact(req.fhir)}

    fail(err):
        entry.status = "failed"; entry.error = {err.code, err.message}
        entry.duration_ms = now - start
        ledger.record(entry)                     // assigns entry.id; failure only logged
        raise SendError(err) with ids {ledger_id: entry.id, txn_id: entry.id, headers,
                                       correlation_id, api_call_id, request_id if set}

    if recipient empty: fail(NO_RECIPIENT "x-hcx-recipient_code is required")
    pub = sender.certificate(recipient)          // G4; may fail CERT_*, TOKEN_*, SELF_ENCRYPTION_KEY
        on error: fail(error)
    jwe = encrypt(entry.fhir, pub, headers)      // G6; protected header = headers
        on error: fail(ENCRYPT_ERROR)
    res = sender.dispatch(path, jwe)             // below
        on error: fail(error)

    entry.duration_ms = res.duration
    entry.peer = {url: res.url, status_code: res.status, response: res.body}
    if 200 <= res.status < 300: entry.status = "accepted"
    else: entry.status = "rejected"
          entry.error = {code: "GATEWAY_HTTP_" + res.status, message: "NHCX did not accept the message"}
    ledger.record(entry)
    return SendResult{ok: 2xx, path, url: res.url, headers, gateway_status: res.status,
                      response: res.body, duration_ms: res.duration,
                      ledger_id: entry.id, txn_id: entry.id,
                      correlation_id, api_call_id, request_id from headers}

dispatch(path, jwe):                             // abdm client
    url = join(urls.nhcx, path)                  // a "/v1" suffix on the base and "v1/" on the path are not doubled
    body = {"payload": jwe}
    if path is a response path: body.type = "JWEPayload"
    start = now
    status, raw = post_with_token(url, body, label = "GATEWAY")
    body = raw if valid JSON, else JSON string of raw if non-empty, else null
    return {url, status, body, duration: now - start}

post_with_token(url, body, label):               // shared with G4 and G10 (label "CERT_FETCH")
    for attempt in 0, 1:
        token = session_token()                  // G3; errors propagate (TOKEN_*)
        POST url, JSON body, headers:
            Content-Type: application/json, Accept: application/json,
            bearer_auth: Bearer <token>  (lower case, written as is),
            Authorization: Bearer <token>
        on transport error: raise <label>_UNREACHABLE (retryable)
        read the whole answer; on read error raise <label>_READ_ERROR (retryable)
        if status == 401 and attempt == 0:
            refresh_token()                      // errors propagate
            continue
        return status, raw                       // any status, including a second 401
```

#### G7U. USED BY
- APIs: [A1. Eligibility Answer](../apis/A1-eligibility-answer.md), [A2. Insurance Plan Answer](../apis/A2-insurance-plan-answer.md), [A3. Pre-auth Answer](../apis/A3-preauth-answer.md), [A4. Claim Answer](../apis/A4-claim-answer.md), [A5. Query Request](../apis/A5-query-request.md), [A6. Payment Notice](../apis/A6-payment-notice.md), [A7. Payment Enquiry Answer](../apis/A7-payment-enquiry-answer.md), [A8. Status Answer](../apis/A8-status-answer.md), [A9. Task Answer](../apis/A9-task-answer.md), [A10. Predetermination Quote](../apis/A10-predetermination-quote.md), [A11. Transaction Related](../apis/A11-txn-related.md), [A12. Transaction FHIR](../apis/A12-txn-fhir.md), [A17. Participant Lookup](../apis/A17-participant-lookup.md), [A19. Sandbox Scenarios](../apis/A19-sandbox-scenarios.md)
- Callbacks: [C1. Callback Door](../callbacks/C1-callback-door.md)
- FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F11. CommunicationRequest](../fhir/F11-communicationrequest.md)
- Gateway: [G1. Embedding](G1-embedding.md), [G2. Configuration and Participants](G2-configuration.md), [G3. Session Token](G3-session-token.md), [G4. Registry and Certificates](G4-registry.md), [G5. Protocol Headers](G5-protocol-headers.md), [G6. Encryption](G6-encryption.md), [G9. Ledger](G9-ledger.md)
