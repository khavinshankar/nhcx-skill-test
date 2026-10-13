# G2. Configuration and Participants

#### G2E. ENTRY

In-process:

| Call | Purpose |
|---|---|
| `load_config(path)` | read, expand, default, resolve key files, validate. Called by `gateway.open` (G1) |
| `validate_serve(cfg)` | the checks a serving gateway needs, run by `gateway.open` after the host and guests options |
| `build_profiles(cfg)` | one profile per identity, keys parsed |
| `profiles.by_code(code)` | the profile holding that code, or none |
| `profiles.resolve(code)` | `by_code`, falling back to the default profile |
| `profiles.is_local(code)` | whether the code is one of the gateway's own |
| `profiles.owns_key(public_key)` | whether a public key is one of the gateway's own |
| `identity_for(code)` | the profile plus the ABDM client (G3, G4) acting as it, falling back to the default |

Environment URLs (`env`), each overridable under `urls`:

| | `sandbox` (default) | `production` |
|---|---|---|
| `urls.nhcx` (NHCX gateway base) | `https://apisbx.abdm.gov.in/hcx/v1` | `https://apis.abdm.gov.in/hcx/v1` |
| `urls.participant` (participant registry base) | `https://apisbx.abdm.gov.in/pmjay/sbxhcx/participanthcxservice` | `https://apis.abdm.gov.in/pmjay/hcx/participanthcxservice` |
| `urls.sessions` (session token endpoint) | `https://dev.abdm.gov.in/api/hiecm/gateway/v3/sessions` | `https://live.abdm.gov.in/api/hiecm/gateway/v3/sessions` |
| `cmId` (`X-CM-ID` on the session call) | `sbx` | `abdm` |

The sandbox values are the verified ones [SANDBOX](../references/PAYERS.md#markers). The production values follow the documented host swap (`apisbx` to `apis`, `sbxhcx` to `hcx`, `dev` to `live`); confirm them against the onboarding letter and override under `urls` when they differ. With `auth.mode` `get-session` and no `urls.sessions`, the session URL is `<urls.participant>/get/session`.

#### G2D. DESCRIPTION

The configuration is one JSON file. Unknown keys are rejected. Two conveniences keep secrets out of it:
- `${NAME}` anywhere in the file is replaced by environment variable `NAME` (JSON-escaped) before parsing. An unset variable is an error, never an empty string.
- a private key written as `@path` is read from that file; a relative path is relative to the config file's directory.

**Environment variable overrides.** After parsing and before defaults, these variables replace the file's value when they are set (even to empty; the value is trimmed): `NHCX_ENV` (env), `NHCX_URL` (urls.nhcx), `NHCX_PARTICIPANT_URL` (urls.participant), `NHCX_SESSIONS_URL` (urls.sessions), `NHCX_PUBLIC_URL` (publicUrl), `NHCX_CM_ID` (cmId). Precedence: variable, then file, then the environment's default. Setting `NHCX_ENV=production` therefore moves all three URLs at once.

**Participants.** `participant` is the default identity. `participants` lists hosted identities served by the same process, and `gateway.open` (G1) can add more through its `host` option. A hosted entry needs only `participantId`: when both `clientId` and `clientSecret` are blank it uses the default's pair, and when `privateKey` is blank it uses the default's key, the usual arrangement when one registration fronts several codes (an insurer and the scheme desk it also works as [REF](../references/PAYERS.md#markers)). Every `participantId` is stored with the `@hcx` suffix added when missing.

Hosted profiles that share a client id share one session token (G3). All profiles share one certificate cache (G4). Keys are parsed once per distinct key text at startup; a key that does not parse stops startup rather than failing on the first live message.

**Resolution.** Codes are compared after `normalize_code` (G5) and case-insensitively.
- Outbound, `x-hcx-sender_code` picks the identity: its credentials mint the token and its code is the sender. An unknown or missing sender falls back to the default profile, never an error (G7).
- Inbound, `x-hcx-recipient_code` picks the profile whose key is tried first, and the code handed to `C1.receive` as `delivery.participant` (G8). A code the gateway does not hold is refused as `WRONG_RECIPIENT` unless guests are on.

**Guests.** A participant whose registry record names this gateway's `endpoint_url` and one of its certificates is delivered here by NHCX whether or not its code is configured. With guests on, such a message is taken in when one of the gateway's own keys opens it, and refused as `WRONG_RECIPIENT` when none does (G8). It goes to the same `C1.receive` as every other message, with the guest's own code as `delivery.participant`; C1 decides from that code and the path which part of the application it belongs to. In the file, guests are on when a `guests` object is present (`"guests": {}` is enough) and off when it is absent; `gateway.open`'s `guests` option overrides the file. Sending as a guest needs nothing: an unlisted sender code goes out on the default's session.

**Keys ignored when embedded.** `callback` (`url`, `appendPath`, `timeoutSeconds`, `apiKey`, `routes`, `also`), `participant.callback`, `participant.callbackUrl`, `participants[].callback`, `guests.callback`, `apiKey`, `requireApiKey`, `listen`, `tls`, `panel`, `certificate` and `log.format` belong to the standalone gateway. The file may carry them, but the embedded gateway ignores them and does not validate them: delivery is the in-process call to `C1.receive` (G1, G8) and the application owns the listener.

**Validation** runs twice. `load_config` checks what every use needs; `validate_serve` runs after `gateway.open` has applied its options. All failures are collected and returned together, one per line.

#### G2Q. INPUT

Keys that matter to sending and receiving:

| Key | Default | Notes |
|---|---|---|
| `env` | `sandbox` | `sandbox` or `production`, lowercased. Picks the URL table above |
| `publicUrl` | none | how NHCX reaches this application from outside, for example `https://hcx.example.com/in`; the value that belongs in the registry's `endpoint_url`. Only validated when set; nothing in sending or receiving reads it |
| `participant.participantId` | required | registry code, with or without `@hcx` |
| `participant.name` | none | log label |
| `participant.clientId`, `participant.clientSecret` | required | ABDM credentials from onboarding. Usually `${NHCX_CLIENT_ID}`, `${NHCX_CLIENT_SECRET}` |
| `participant.privateKey` | required | RSA private key matching the registered encryption certificate: PEM, base64 of PEM, or `@file` (G6 key parsing) |
| `participants[]` | `[]` | hosted identities; same fields as `participant`. `clientId` and `clientSecret` both set or both blank; blank key or credentials inherit the default's |
| `guests` | absent (off) | present turns guests on; `gateway.open`'s `guests` option overrides |
| `ledger.enabled` | `true` | record every message (G9) |
| `ledger.dir` | `data/ledger` [REF](../references/PAYERS.md#markers) | relative to the config file |
| `ledger.retentionDays` | `0` | day folders older than this are pruned hourly (G1); 0 keeps all, negative becomes 0 |
| `ledger.storeBodies` | `true` | keep FHIR bundles and peer responses, not only headers |
| `certs.cacheHours` | `24` | recipient certificate cache lifetime (G4) |
| `certs.refuseSelfKey` | production: true, sandbox: false [REF](../references/PAYERS.md#markers) | refuse a registry certificate that is one of our own keys for another participant (G4) |
| `outboundTimeoutSeconds` | `30` | each call to ABDM: token, registry, NHCX gateway |
| `maxBodyBytes` | `104857600` (100 MiB) [REF](../references/PAYERS.md#markers) | body cap on the NHCX-facing routes (G1); claim dossiers carry documents inline as base64 |
| `auth.mode` | `sessions` | `sessions` (JSON to the HIECM sessions endpoint) or `get-session` (form post to the registry's `/get/session`) (G3) |
| `auth.tokenTtlSeconds` | `1200` | assumed token lifetime when the session answer carries none |
| `cmId` | env default | `X-CM-ID` header on the `sessions` call |
| `urls.nhcx`, `urls.participant`, `urls.sessions` | env defaults | absolute http(s) URLs |
| `log.level` | `info` | `debug`, `info`, `warn`/`warning`, `error` |

#### G2S. OUTPUT

A loaded configuration, or the joined errors. Messages, verbatim:

Parsing:
- `read config: <cause>`
- `environment variable(s) not set: <NAME>, <NAME>`
- `parse config: <cause>` (bad JSON or an unknown key)
- `participant.privateKey: <cause>`, `participants[<i>].privateKey: <cause>` (an `@file` that cannot be read)

`load_config` validation:
- `env must be "sandbox" or "production", got "<env>"`
- `participant.participantId is required`
- `participant.clientId and participant.clientSecret are required`
- `participant.privateKey is required (PEM, base64 PEM, or @file)` followed by a hint to generate one
- `participant.privateKey is not a valid RSA private key: <cause>` (G6)
- `participants[<i>].participantId is required`
- `participants[<i>].participantId <code> duplicates participant.participantId`
- `participants[<i>].participantId <code> duplicates participants[<j>]`
- `participants[<i>].privateKey is not a valid RSA private key: <cause>`
- `participants[<i>]: clientId and clientSecret must be set together (or both left blank to inherit)`
- `auth.mode must be "sessions" or "get-session", got "<mode>"`
- `urls.nhcx: <url error>`, `urls.participant: <url error>`, `urls.sessions: <url error>`
- `log.level must be debug, info, warn or error, got "<level>"`

`validate_serve`, embedded:
- `publicUrl: <url error>`

A URL error is `is required` (blank) or `"<url>" is not an absolute http(s) URL`.

`build_profiles` fails with `participant.privateKey: <cause>` or `participants[<i>].privateKey: <cause>` (index into `participants`). Resolution calls never fail: `by_code` returns none for an unknown or empty code, `resolve` and `identity_for` return the default.

A profile carries: the participant entry (with inherited credentials and key), the parsed private key, and whether it is the default.

#### G2P. PSEUDOCODE

```text
load_config(path):
    raw = read file or fail "read config: <cause>"
    missing = []
    text = replace every ${NAME} in raw with json_escape(env[NAME]); collect NAME when unset
    if missing: fail "<path>: environment variable(s) not set: " + join(missing, ", ")
    cfg = strict JSON decode (unknown keys rejected) or fail "<path>: parse config: <cause>"
    for var, field in [NHCX_ENV env, NHCX_URL urls.nhcx, NHCX_PARTICIPANT_URL urls.participant,
                       NHCX_SESSIONS_URL urls.sessions, NHCX_PUBLIC_URL publicUrl, NHCX_CM_ID cmId]:
        if var is set: field = trim(env[var])
    apply_defaults(cfg)
    for key in [participant.privateKey, participants[i].privateKey]:
        if trim(key) starts with "@": key = contents of that file (relative to dirname(path)) or fail
    validate(cfg) or fail "<path>: <errors joined by newline>"
    return cfg

apply_defaults(cfg):
    env = lower(trim(env)) or "sandbox"
    maxBodyBytes <= 0 -> 100 MiB;  outboundTimeoutSeconds <= 0 -> 30
    auth.mode "" -> "sessions";  auth.tokenTtlSeconds <= 0 -> 1200;  certs.cacheHours <= 0 -> 24
    ledger.enabled unset -> true;  ledger.storeBodies unset -> true;  ledger.dir "" -> "data/ledger"
    ledger.retentionDays < 0 -> 0;  log.level "" -> "info"
    defaults, cm = env_table(env)             // production table for "production", sandbox otherwise
    urls.nhcx "" -> defaults.nhcx;  urls.participant "" -> defaults.participant
    if urls.sessions == "":
        urls.sessions = auth.mode == "get-session" ? trim_right(urls.participant, "/") + "/get/session"
                                                   : defaults.sessions
    cmId "" -> cm
    for p in [participant] + participants:
        p.participantId = trim(p.participantId); append "@hcx" when non-empty and missing

validate_serve(cfg):                         // embedded
    if cfg.publicUrl != "": check it is an absolute http(s) URL, else error "publicUrl: <url error>"

all_participants(cfg):
    out = [cfg.participant]
    for p in cfg.participants:
        if p.clientId == "" and p.clientSecret == "": p.clientId, p.clientSecret = default's
        if trim(p.privateKey) == "": p.privateKey = default's
        append p
    return out

build_profiles(cfg):
    parsed = {}                               // key text -> parsed key
    for i, entry in all_participants(cfg):
        key = parsed[entry.privateKey] or parse_private_key(entry.privateKey)        // G6
              or fail "<participant | participants[i-1]>.privateKey: <cause>"
        profile = {participant: entry, key, default: i == 0}
        add profile in order; by_code_index[lower(entry.participantId)] = profile when code non-empty

by_code(code):
    code = normalize_code(code)               // G5
    return code == "" ? none : by_code_index[lower(code)]
resolve(code):  return by_code(code) or default profile
is_local(code): return by_code(code) is not none
owns_key(pub):  return pub is not none and some profile's public key equals pub

identity_for(code):                           // profile plus its ABDM client
    c = normalize_code(code)
    if c != "" and identities[lower(c)] exists: return it
    return default identity
```

#### G2U. USED BY
- Screens: [S12. Organisation](../screens/S12-organisation.md)
- APIs: [A11. Transaction Related](../apis/A11-txn-related.md), [A12. Transaction FHIR](../apis/A12-txn-fhir.md), [A16. ABHA Policy Link](../apis/A16-abha-policy-link.md), [A17. Participant Lookup](../apis/A17-participant-lookup.md)
- Database: [D1. payer](../database/D1-payer.md)
- Gateway: [G1. Embedding](G1-embedding.md), [G3. Session Token](G3-session-token.md), [G4. Registry and Certificates](G4-registry.md), [G5. Protocol Headers](G5-protocol-headers.md), [G6. Encryption](G6-encryption.md), [G7. Send](G7-send.md), [G8. Receive](G8-receive.md), [G11. Startup Checks and Health](G11-startup-checks.md)
