# G11. Startup Checks and Health

#### G11E. ENTRY
In-process:

- `gateway.check()`: runs the setup checks and the endpoint probe, logs each outcome, returns nothing. Called once by the host after its listener is up (G1), in the background.
- `gateway.healthz(probe_nonce = none) -> Health`
- `gateway.readyz() -> Ready`

HTTP routes the gateway serves on the application's listener (no API key):

| Route | Answer |
|---|---|
| `GET /healthz`, `GET /in/healthz` | liveness |
| `POST /healthz`, `POST /in/healthz` | liveness plus the probe acknowledgement |
| `GET /readyz` | readiness |

`/in/healthz` exists so the probe reaches the gateway under a registry `endpoint_url` ending `/in`.

Calls out: `<urls.sessions>` (token, G3), `POST <urls.participant>/participant/search` (participant record, G4), `POST <urls.participant>/fetch/certs` (certificate, G4), `POST <endpoint_url>/healthz` (the probe, over the public internet back to this listener).

#### G11D. DESCRIPTION
The checks answer: can this gateway actually work as its participant? The session credentials mint a token, the participant is on the registry, the registry's encryption certificate is the one the gateway's private key opens (otherwise nothing addressed to it can be decrypted), each extra hosted participant is equally sound, and the registry's `endpoint_url` leads back to this gateway.

Embedded, `check` only reports. It never stops the host (the host is already serving, and NHCX redelivers whatever fails meanwhile) and never changes the registry: uploading a certificate or re-registering an endpoint is done with the standalone tool, not from the application. A failed session token ends the checks early (nothing else can be asked without it), but the host keeps running and the token loop (G3) keeps trying.

Order and outcomes:

| # | Check | Pass | Fail (logged as a warning) |
|---|---|---|---|
| 1 | session token | a fresh token (forced refresh) for the default participant: "issued by `<urls.sessions>`" | `<code>: <message> (<body>)` plus "check participant.clientId / clientSecret, auth.mode and urls.sessions". The remaining checks are skipped |
| 2 | participant record | registry search for the default code: "`<code>` · `<name>` · `<status>` · endpoint `<endpoint_url>`" (or "no endpoint_url registered") | the error. Not fatal; step 3 still runs, step 5 does not |
| 3 | encryption certificate | registry certificate equals the default participant's public key: `match` | `mismatch` ("does NOT match participant.privateKey, inbound messages could not be decrypted"), `missing` (`CERT_NOT_FOUND`, or unreadable PEM), or `unknown` (any other error) |
| 4 | participant `<code>`, once per extra hosted participant, only when more than one is hosted | its own token, its registry certificate matches its own key: "certificate matches · callback `<delivery target>`" | token error ("check its clientId / clientSecret"), no certificate, unreadable, or does not match its key |
| 5 | registered endpoint, only when step 2 returned an `endpoint_url` | the probe below is acknowledged: "`<endpoint_url>`/healthz reaches this adapter (probe acknowledged)" | see the probe outcomes |

Time limits in the embedded check: two minutes for steps 1 to 4 together (each ABDM call also has `outboundTimeoutSeconds`), 30 seconds for step 5 (the probe's own client times out at 15 seconds) [REF](../references/PAYERS.md#markers).

Endpoint probe. A plain `200` from `<endpoint_url>/healthz` proves only that something answers there. The probe proves it is this gateway, with this configuration:

- key = SHA-256 of `"nhcx-adapter probe v1\0" + participantId + "\0" + clientSecret + "\0" + apiKey` (default participant's code and secret, the gateway API key, empty when unset). Two gateways share it exactly when they run as the same participant with the same credentials. The probe scheme is [REF](../references/PAYERS.md#markers).
- nonce = 16 random bytes, hex.
- ack = hex HMAC-SHA256(key, nonce), compared in constant time.

Nothing secret travels, and a captured exchange cannot be replayed.

Probe outcomes (step 5 fails with the first that applies):
1. no `endpoint_url`: "NHCX has nowhere to deliver callbacks" (not reached embedded, since step 5 is skipped then);
2. unreachable: "`<url>` unreachable from here: `<error>`";
3. an answer without `probe_ack`: "answered `<status>` (Server: ...) without a probe acknowledgement ... the proxy at that URL is not forwarding to this adapter's listen address", with the first 120 characters of the body;
4. an ack that does not verify: "is an nhcx-adapter, but not one running with this configuration (different participant or credentials)";
5. a verified ack with a status other than 200: "reaches this adapter but answered `<status>`".

A failed probe logs the hint "NHCX cannot deliver callbacks until endpoint_url reaches this gateway".

#### G11Q. INPUT
`check()`: none. Uses the gateway configuration (G2): default participant code, client id and secret, private key, hosted participants, `urls.*`, `apiKey`.

`healthz(probe_nonce)`, from the HTTP body on a POST: `{"probe": "<nonce>"}`. The body is read up to 4096 bytes; a malformed body is ignored. A nonce that is empty or longer than 128 characters gets no acknowledgement.

`readyz()`: none.

#### G11S. OUTPUT
`check()`: nothing returned. Log lines `setup check` (info) or `setup check failed` (warning) with the check name and detail, then `registered endpoint verified` or `registered endpoint check failed`.

`Health`, always HTTP 200:

```json
{"status": "ok", "service": "nhcx-adapter", "version": "embedded",
 "env": "sandbox", "participant": "<payer code>", "probe_ack": "<hex, POST with a nonce only>"}
```

`version` is the host's version string when given at open (G1), else `embedded`. The `service` name is [REF](../references/PAYERS.md#markers). `participant` is the default participant's code.

`Ready`:

| Condition | HTTP | Body |
|---|---|---|
| the default participant holds an unexpired session token | 200 | `{"status": "ready"}` |
| otherwise | 503 | `{"status": "no session token"}` |

Only the default participant's token counts; an extra hosted participant without a token does not make the gateway unready.

#### G11P. PSEUDOCODE

```text
check():                                              // background, after the listener is up
    report = run_checks(timeout 2 min)
    for c in report.checks: log info or warning (c.name, c.detail)
    if report.participant is none or report.participant.endpoint_url empty: return
    c = test_endpoint(report.participant.endpoint_url, probe_key(), timeout 30 s)
    log "registered endpoint verified" or warning "registered endpoint check failed"
    // never raises, never stops the host, never writes to the registry

run_checks():
    r = {checks: [], cert: "unknown"}
    client = default participant's ABDM client
    try client.refresh_token()                                         // G3
    on error e: add("session token", fail, explain(e) + " - check participant.clientId /
                    clientSecret, auth.mode and urls.sessions"); return r
    add("session token", ok, "issued by " + urls.sessions)

    try p = client.fetch_participant(default code)                     // G4
        add("participant record", ok, code · name · status · endpoint or "no endpoint_url registered")
        r.participant = p
    on error e: add("participant record", fail, explain(e))

    try pem = client.fetch_certificate(default code)                   // G4, bypasses the cache
        pub = parse(pem)
        unreadable:                   r.cert = "missing";  add fail "registry certificate is unreadable"
        pub == own public key:        r.cert = "match";    add ok
        else:                         r.cert = "mismatch"; add fail
    on error e:
        if e.code == "CERT_NOT_FOUND": r.cert = "missing"; add fail "registry has no encryption certificate"
        else:                          add fail explain(e)

    if more than one participant hosted:
        for each non-default profile:
            name = "participant " + code
            token for it; on error add(name, fail, explain + " - check its clientId / clientSecret"); next
            fetch its certificate; on error add(name, fail, ...); next
            add(name, ok if it equals its own public key else fail)
    return r

test_endpoint(endpoint_url, key):
    url = trim_right(endpoint_url, "/") + "/healthz"
    nonce = hex(16 random bytes)
    POST url {"probe": nonce}, Content-Type and Accept application/json,
         Accept-Encoding: identity, User-Agent: nhcx-adapter-check, timeout 15 s, no compression
    on transport error: fail "unreachable from here"
    ans = parse body (up to 64 KiB) as {"probe_ack": ...}
    if ans.probe_ack empty:          fail "without a probe acknowledgement" (+ status, Server, body excerpt)
    if not verify(key, nonce, ack):  fail "not one running with this configuration"
    if status != 200:                fail "reaches this adapter but answered <status>"
    ok "reaches this adapter (probe acknowledged)"

probe_key():  sha256("nhcx-adapter probe v1\0" + participant_id + "\0" + client_secret + "\0" + api_key)
ack(key, n):  hex(hmac_sha256(key, n))
verify(key, n, a): constant_time_equal(ack(key, n), a)

healthz(method, body):
    out = {status: "ok", service: "nhcx-adapter", version, env, participant: default code}
    if method == POST:
        req = parse up to 4096 bytes of body as {"probe": ...}, errors ignored
        if req.probe non-empty and len(req.probe) <= 128: out.probe_ack = ack(probe_key(), req.probe)
    answer 200 out

readyz():
    if default participant's cached token is set and not expired: answer 200 {"status": "ready"}
    else: answer 503 {"status": "no session token"}
```

#### G11U. USED BY
- Gateway: [G1. Embedding](G1-embedding.md), [G3. Session Token](G3-session-token.md), [G4. Registry and Certificates](G4-registry.md)
- Tests: [T2. Test Runners](../tests/T2-test-runners.md)
