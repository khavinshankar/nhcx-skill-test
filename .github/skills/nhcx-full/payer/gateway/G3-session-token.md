# G3. Session Token

#### G3E. ENTRY

In-process, for the application (any call it makes to ABDM itself, for example the test driver A18):

| Call | Returns |
|---|---|
| `gateway.token(participant = default)` | `{token, token_type, expires_at, expires_in, participant}` for that profile, fetching when needed |
| `gateway.refresh_token(participant = default)` | the same, after discarding the cached token and fetching a new one |

In-process, on the ABDM client of one profile (`identity_for(code).client`, G2), for the gateway's own use:

| Call | Returns |
|---|---|
| `client.token()` | a valid token, fetched when missing or within a minute of expiry |
| `client.token_info()` | token and its expiry time |
| `client.refresh_token()` | a new token, discarding the cached one |
| `client.token_valid()` | whether a token is cached and unexpired (no network) |
| `post_with_token(client, url, body, label)` | status and raw body of an authenticated JSON POST, refreshing once on 401. The single definition; G4, G7 and G10 call it |

HTTP route the gateway calls:

| `auth.mode` | Method and URL | Body |
|---|---|---|
| `sessions` (default) | `POST <urls.sessions>`: sandbox `https://dev.abdm.gov.in/api/hiecm/gateway/v3/sessions`, production `https://live.abdm.gov.in/api/hiecm/gateway/v3/sessions` | JSON `{"clientId", "clientSecret", "grantType": "client_credentials"}` |
| `get-session` | `POST <urls.participant>/get/session` unless `urls.sessions` is set | form `client_id`, `client_secret`, `grant_type=client_credentials` |

#### G3D. DESCRIPTION

Every call to ABDM (registry, NHCX gateway) carries a session token minted from a participant's ABDM client id and secret.

**Cache.** One in-memory map, shared by every profile, keyed by client id. A hosted profile with blank credentials uses the default's client id and so shares the default's token: one session per distinct client id, never one per code. If no client id exists anywhere the key is a per-code sentinel so profiles do not collide. Nothing is persisted; a restart fetches again.

**Freshness.** `client.token()` returns the cached token while more than one minute of its lifetime remains; otherwise it fetches. The lifetime is `expiresIn` (or `expires_in`) seconds from the answer, else `auth.tokenTtlSeconds` (1200) [REF](../references/PAYERS.md#markers). The token loop of G1 calls `client.token()` for every profile every minute, so the token is normally renewed before a send needs it.

**Concurrency.** One lock guards the whole cache, and a fetch runs while holding it. Concurrent callers therefore wait for one fetch and then read its result; token fetches for different client ids are serialised too [REF](../references/PAYERS.md#markers).

**401 handling.** `post_with_token` is the one authenticated POST used for the registry (G4, G10) and the NHCX gateway (G7). It sends the token twice, as `bearer_auth: Bearer <token>` (header name written in lower case, exactly as NHCX documents it) and as `Authorization: Bearer <token>` [REF](../references/PAYERS.md#markers). When the answer is 401 on the first attempt it refreshes the token once and repeats the request. Any other status, including a second 401, is handed back to the caller as is.

**Timeouts.** Every call uses one HTTP client with a timeout of `outboundTimeoutSeconds` (30). Answers are read in full, with no size limit of their own: a large answer (a registry record, an insurance plan with thousands of packages) is never cut short or refused for its size.

**Token for the application.** `gateway.token(participant)` is how the application gets an ABDM bearer token for the calls it makes itself; no payer API in this skill needs one, the test driver A18 signs in to the sandbox provider EMR with it. With no participant it is the default profile's token. A participant code (either spelling) selects that hosted profile's token; an unknown code is refused with `UNKNOWN_PARTICIPANT` rather than falling back, since the wrong participant's token would fail confusingly later. `gateway.refresh_token(participant)` does the same after forcing a new fetch. The application should not keep the token beyond `expires_at`.

**Readiness.** `/readyz` is `client.token_valid()` of the default profile (G1, G11).

#### G3Q. INPUT

| Source | Field | Default | Notes |
|---|---|---|---|
| `gateway.token` | `participant` | the default participant | code with or without `@hcx` |
| profile | `clientId`, `clientSecret` | the default participant's | per profile (G2) |
| config | `auth.mode` | `sessions` | `sessions` or `get-session` |
| config | `urls.sessions` | env default (G2) | the session endpoint |
| config | `cmId` | `sbx` sandbox, `abdm` production | `X-CM-ID` header, `sessions` mode only |
| config | `auth.tokenTtlSeconds` | `1200` | used when the answer carries no expiry |
| config | `outboundTimeoutSeconds` | `30` | per call |
| `post_with_token` | `url` | required | absolute URL |
| `post_with_token` | `body` | required | any JSON value |
| `post_with_token` | `label` | `CERT_FETCH` | error prefix: `CERT_FETCH` for every registry call, `GATEWAY` for the NHCX dispatch |

Request headers on the session call, `sessions` mode: `Content-Type: application/json`, `Accept: application/json`, `REQUEST-ID: <fresh UUID>`, `TIMESTAMP: <now, UTC, RFC 3339, for example 2026-09-21T06:30:00Z>`, `X-CM-ID: <cmId>`. `get-session` mode: `Content-Type: application/x-www-form-urlencoded`, `Accept: application/json`.

Request headers on `post_with_token`: `Content-Type: application/json`, `Accept: application/json`, `bearer_auth: Bearer <token>`, `Authorization: Bearer <token>`.

#### G3S. OUTPUT

`gateway.token` and `gateway.refresh_token` return:

```json
{"token": "<token>", "token_type": "Bearer", "expires_at": "2026-09-21T06:50:00Z",
 "expires_in": 1199, "participant": "<payer code>"}
```

`client.token()` and `client.refresh_token()` return the token string; `client.token_info()` adds the expiry. `post_with_token` returns `(status, raw body)` for any HTTP answer.

**Gateway error shape**, raised by the in-process calls of G3, G4, G7 and G10: `{code, message, retryable, status (upstream HTTP status, when there was one), body (upstream body, clipped to 4096 characters plus "…"), cause}`. Its text form is `<code>: <message>` or `<code>: <message>: <cause>`. Any other error met on the way is reported as code `INTERNAL`. G8 turns the same shape into the HTTP answer NHCX sees on the inbound routes.

`UNKNOWN_PARTICIPANT`: `no participant <code> is configured; this adapter holds <code>, <code>`.

Session errors:

| Code | Message | Retryable |
|---|---|---|
| `TOKEN_REQUEST` | `build session request` | no |
| `TOKEN_UNREACHABLE` | `session endpoint unreachable` | yes |
| `TOKEN_HTTP_<status>` | `session endpoint rejected the credentials` (status and body attached) | when status >= 500 or 429 |
| `TOKEN_BAD_JSON` | `session response is not JSON` | yes |
| `TOKEN_MISSING` | `session response carried no access token` | no |

`post_with_token` errors (`<label>` is `CERT_FETCH` or `GATEWAY`):

| Code | Message | Retryable |
|---|---|---|
| `MARSHAL_ERROR` | `encode request body` | no |
| `<label>_REQUEST` | `build request` | no |
| `<label>_UNREACHABLE` | `<url> unreachable` | yes |
| `<label>_READ_ERROR` | `read response` | yes |
| any session error above | raised while getting or refreshing the token | as above |

#### G3P. PSEUDOCODE

```text
credentials(client):
    id, secret = client.profile.clientId, client.profile.clientSecret
    if id == "": id, secret = default participant's clientId, clientSecret
    key = id != "" ? id : "\0" + client.code
    return id, secret, key

client.token():
    lock token_lock
    _, _, key = credentials(client)
    e = tokens[key]
    if e and e.token != "" and e.expires - now > 1 minute: unlock; return e.token
    t = fetch_locked(client); unlock; return t

client.refresh_token():
    lock token_lock; t = fetch_locked(client); unlock; return t

client.token_info():
    client.token() or fail
    lock; e = tokens[key]; unlock; return e.token, e.expires

client.token_valid():
    lock; e = tokens[key]; unlock
    return e and e.token != "" and now < e.expires

fetch_locked(client):
    id, secret, key = credentials(client)
    if auth.mode == "get-session":
        request = POST urls.sessions, form {client_id: id, client_secret: secret, grant_type: "client_credentials"}
    else:
        request = POST urls.sessions, JSON {clientId: id, clientSecret: secret, grantType: "client_credentials"}
                  headers REQUEST-ID = new UUID, TIMESTAMP = now UTC RFC 3339, X-CM-ID = cmId
    if request cannot be built: fail TOKEN_REQUEST
    header Accept: application/json
    response = send (timeout outboundTimeoutSeconds) or fail TOKEN_UNREACHABLE (retryable)
    raw = read the whole answer
    if status not 2xx: fail TOKEN_HTTP_<status> (retryable when >= 500 or 429; status, clipped raw)
    out = parse JSON object or fail TOKEN_BAD_JSON (retryable)
    token = first non-blank trimmed string of out.accessToken, out.access_token
    if token == "": fail TOKEN_MISSING
    ttl = auth.tokenTtlSeconds
    n = first number of out.expiresIn, out.expires_in (a JSON number or a numeric string)
    if n > 0: ttl = n seconds
    tokens[key] = {token, expires: now + ttl}
    log "session token refreshed" (participant, mode, ttl, took)
    return token

gateway.token(participant = none, refresh = false):     // refresh_token(p) is token(p, refresh = true)
    client = default identity's client
    if participant given:
        if profiles.by_code(participant) is none:                                   // G2
            fail UNKNOWN_PARTICIPANT "no participant <participant> is configured; this adapter holds <codes>"
        client = identity_for(participant).client
    if refresh: client.refresh_token() or fail
    token, expires = client.token_info() or fail
    return {token, token_type: "Bearer", expires_at: expires as UTC RFC 3339,
            expires_in: whole seconds until expires, participant: client.code}

post_with_token(client, url, body, label):
    payload = json(body) or fail MARSHAL_ERROR
    for attempt in 0, 1:
        token = client.token() or fail with that error
        request = POST url, payload
                  headers Content-Type and Accept application/json,
                          "bearer_auth": "Bearer " + token   (exact lower-case name),
                          Authorization: "Bearer " + token
        if request cannot be built: fail <label>_REQUEST
        response = send or fail <label>_UNREACHABLE (retryable)
        raw = read the whole answer or fail <label>_READ_ERROR (retryable)
        if response.status == 401 and attempt == 0:
            log warning "upstream answered 401, refreshing session token"
            client.refresh_token() or fail with that error
            continue
        return response.status, raw          // a second 401 is returned here as a status
```

#### G3U. USED BY
- APIs: [A16. ABHA Policy Link](../apis/A16-abha-policy-link.md), [A17. Participant Lookup](../apis/A17-participant-lookup.md), [A18. Provider Driver](../apis/A18-provider-driver.md), [A20. ABHA Create and Verify (ABDM M1)](../apis/A20-abha-m1.md)
- Gateway: [G1. Embedding](G1-embedding.md), [G2. Configuration and Participants](G2-configuration.md), [G4. Registry and Certificates](G4-registry.md), [G5. Protocol Headers](G5-protocol-headers.md), [G6. Encryption](G6-encryption.md), [G7. Send](G7-send.md), [G10. Beneficiary Registry](G10-beneficiary-registry.md), [G11. Startup Checks and Health](G11-startup-checks.md)
- Tests: [T1. Test Configuration](../tests/T1-test-configuration.md)
