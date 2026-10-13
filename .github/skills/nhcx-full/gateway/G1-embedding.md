# G1. Embedding

#### G1E. ENTRY

In-process calls the application makes to run the gateway, in this order:

| Call | Returns | When |
|---|---|---|
| `gateway.open(options)` | a gateway, or an error | once at startup, before the listener opens |
| `gateway.log_startup()` | nothing (log lines) | right after `open` |
| `gateway.handler()` | an HTTP handler for the NHCX-facing routes | once, mounted on the application's own listener |
| `gateway.start(ctx)` | nothing (starts two background loops) | once, before or as the listener starts serving |
| `gateway.check()` | nothing (log lines) | once, in the background, after the listener is serving; skippable (G11) |

Stopping is cancelling `ctx`: both loops return, and the application shuts its own HTTP server down (the reference host waits up to 30 s for in-flight requests [REF](../references/PAYERS.md#markers)).

In-process calls the application makes to use the gateway once it is open. None of them is an HTTP hop:

| Call | Spec | Used by |
|---|---|---|
| `gateway.send(path, envelope)` | G7 | A2 to A8 |
| `registry.policies_search(query)` | G10 | A1 |
| `registry.abha_link(body)`, `registry.abha_delink(body)` | G10 | available to the application; no API in this skill uses it (ABHA linking is the payer's or beneficiary's step) |
| `ledger.related`, `ledger.dispatch`, `ledger.fhir`, `ledger.list` | G9 | A10 to A13 |
| `gateway.token(participant)`, `gateway.refresh_token(participant)` | G3 | A16 |
| `gateway.check()` | G11 | startup, in the background |

The one call the gateway makes into the application: `C1.receive(envelope, delivery)`, once per accepted inbound message (G8).

HTTP routes the handler serves. These are the only routes the application mounts, because NHCX and probes are the only outside callers:

| Method and path | Caller | Purpose |
|---|---|---|
| `POST /in/<nhcx path>` | NHCX | inbound message for a registered `endpoint_url` of `https://<host>/in`, for example `/in/v1/preauth/on_submit` (G8) |
| `POST /v1/<rest>` | NHCX | the same, for an `endpoint_url` registered as the bare host; the path handed on is `v1/<rest>` (G8) |
| `GET /healthz`, `GET /in/healthz` | probes | liveness (G11). `/in/healthz` is reachable under an `endpoint_url` ending in `/in` |
| `POST /healthz`, `POST /in/healthz` | the endpoint probe of `gateway.check` | liveness plus the probe acknowledgement (G11) |
| `GET /readyz` | probes | 200 when the default participant holds a session token (G3, G11) |

Outbound URLs the gateway calls (NHCX gateway, participant registry, session endpoint) are set per environment in G2.

#### G1D. DESCRIPTION

The gateway is a library inside the application process, not a separate service. The application opens it with the path of its configuration file (G2) and the function that receives inbound messages (C1), mounts one HTTP handler for NHCX on its own listener beside its own routes, and calls the gateway's functions directly to send (G7), search policies and link or delink ABHA (G10), poll the ledger (G9), read a session token (G3) and run the startup checks (G11).

**What the application passes to `open`.**
- `config_path`. Keys and the ledger directory resolve relative to that file's directory.
- `receive`: the application's C1 function. G8 calls it with the decrypted envelope and the delivery values, waits for its outcome, and only then answers NHCX (202 when C1 took the message, an error status otherwise, so NHCX redelivers). The `callback` section of the config file is not used (G2). Every profile, hosted code and guest delivers to this one function; C1 tells them apart by `delivery.participant` and `delivery.path`.
- `host`: extra participant codes to answer for, as code to display name. Each shares the default participant's client id, secret and private key. A code the file already lists keeps the file's entry. The application reads these codes and names from its own configuration, never from code; the reference host lists its PMJAY desk's code there [REF](../references/PAYERS.md#markers).
- `guests`: whether to take in messages for participant codes the gateway does not list (G2 guests, G8). Unset leaves the file's `guests` setting. The reference host turns guests on so the application serves any participant code whose registry record carries this gateway's `endpoint_url` and certificate.
- `version`: reported by `/healthz`. Default `embedded`.

**Opening and starting inside a web framework.** Frameworks with auto-reloaders, several worker processes and background task workers need the two calls placed with care:
- `open` runs at application start, in every process, with no network and no database (it only reads the file and parses keys), so the handler can be mounted everywhere requests are served.
- `start` (the token and pruning loops) runs **only in a process that serves HTTP**: not in migration, test, shell or any other command-line entry point of the framework; not in a development reloader's parent process (a reloader runs the application twice; start in the child it actually serves from, which every reloader marks with a variable of its own); not in background task workers; under a pre-forking server that loads the application once in a master, start in the master once, else once per worker. How the target tells these processes apart is recorded in `code-plan.json` conventions (L4.1). The test process never starts the loops and never opens the real configuration ([L7](../steps/L7-dry-run-tests.md)).
- A bad or missing configuration **must not stop the application**: `open` failing is logged, `/readyz` reports it ("gateway not configured: <cause>"), the inbound routes answer 202 `unmatched` ([OPERATIONS.md](../references/OPERATIONS.md)) and every `gateway.send` is refused with a clear message ("The NHCX gateway is not configured: <cause>") until the configuration is fixed; the rest of the HMIS keeps working.

**Order inside `open`.** Load the file (G2: parse, `${ENV}` expansion, env var overrides, defaults, `@file` keys, validation), add the hosted codes, apply the guests setting, then run the serve-time validation (G2). Only then are the profiles and keys built (G2), the token and certificate caches created (G3, G4) and the ledger opened (G9). `open` makes no network call.

**Mounting.** Mount the handler so that NHCX reaches `/in/...` (or `/v1/...`) and the health routes, and nothing else of the gateway faces the internet. Behind a front proxy that forwards only `/api/...`, the same NHCX-facing routes can also be mounted under `/api/gateway/...` (so `/api/gateway/in/...`, `/api/gateway/v1/...`, `/api/gateway/healthz`, `/api/gateway/in/healthz`, `/api/gateway/readyz`), with the registry's `endpoint_url` set to `https://<host>/api/gateway` [REF](../references/PAYERS.md#markers). The host's HTTP server needs a long write timeout (reference: 90 s [REF](../references/PAYERS.md#markers)), because an inbound request is held open while C1 runs.

**Middleware on the mounted routes**, outermost first: panic recovery (answers 500 `{"ok": false, "error": {"code": "INTERNAL", "message": "internal error"}}`), a request id (the caller's `X-Request-Id` when present and at most 128 characters, else a fresh UUID; echoed as `X-Request-Id`), and a body cap of `maxBodyBytes` (G2; over the cap is `BODY_TOO_LARGE`, HTTP 413, "request body exceeds <n> bytes").

**Background loops started by `start`.**
- Token refresher: at once, then every minute, for every profile (default first) ask G3 for a token under a 30 s deadline. G3 returns the cached token unless it is missing or within one minute of expiry, so profiles that share a client id cost one fetch. A failure is logged ("session token refresh failed") and the next tick or the next send tries again. This keeps the first send from paying for the token.
- Ledger pruning: only when the ledger is enabled. At once, then every hour, `ledger.sweep(now)` deletes day folders older than `ledger.retentionDays` (0 keeps everything) and drops them from the in-memory indexes (G9). Logs "ledger pruned" with the count when anything went.

**`check`** runs the startup checks of G11 against the registry and logs each result. It never stops the process and never writes to the registry: the application is already serving, and NHCX redelivers anything that fails meanwhile. It takes up to 2 minutes for the checks plus 30 s for the endpoint probe, so run it in the background.

**`log_startup`** logs one line naming the NHCX URL and how many participants are held, one line per profile (code, name, whether it is the default), and one line when guests are on.

#### G1Q. INPUT

`gateway.open` options:

| Field | Type | Default | Notes |
|---|---|---|---|
| `config_path` | string | required | the gateway config file (G2) |
| `receive` | function `(envelope, delivery) -> outcome` | required | C1.receive; the only delivery target (G8) |
| `host` | map code to name | none | codes (with or without `@hcx`) added as hosted profiles sharing the default's credentials and key |
| `guests` | boolean or unset | unset | true takes in unlisted recipient codes that one of the gateway's keys opens; false refuses them; unset keeps the file's `guests` section |
| `version` | string | `embedded` | shown by `/healthz` |

`start` takes a cancellable context; cancelling it stops the loops. `check` takes the same context.

#### G1S. OUTPUT

`open` returns the gateway or an error. Errors, verbatim shapes:
- config read or parse: `read config: <cause>`, or `<config path>: <cause>` for parse, key file and validation failures (G2 lists the causes; several validation failures are joined, one per line).
- serve-time validation: `<config path>: <cause>` (G2).
- a private key that does not parse: `participant.privateKey: <cause>` or `participants[<i>].privateKey: <cause>` (G2).
- the ledger directory cannot be opened: the file system error.

`handler` returns the handler. `start`, `check` and `log_startup` return nothing; their outcome is in the logs. What the mounted routes answer is in G8 (inbound) and G11 (health).

#### G1P. PSEUDOCODE

```text
open(options):
    cfg = load_config(options.config_path)                  // G2; error returned as is
    for code, name in options.host:
        code = trim(code); add "@hcx" unless present
        if code == "@hcx" or cfg already holds code (default or participants, case-insensitive): continue
        append {participantId: code, name: name} to cfg.participants
    if options.guests is true:  cfg.guests = {}              // on
    if options.guests is false: cfg.guests = none            // off
    validate_serve(cfg) or fail "<config_path>: <errors>"   // G2
    profiles = build_profiles(cfg)                           // G2; key errors returned
    caches   = empty token cache (G3), empty certificate cache (G4)
    ledger   = open ledger at cfg.ledger.dir when cfg.ledger.enabled   // G9
    return gateway{cfg, profiles, caches, ledger, receive: options.receive,
                   version: options.version or "embedded"}

handler():
    routes:
        POST /in/{path...}   -> inbound(path)            // G8
        POST /v1/{path...}   -> inbound("v1/" + path)    // G8
        GET  /healthz, GET /in/healthz, POST /healthz, POST /in/healthz -> healthz   // G11
        GET  /readyz         -> readyz                   // G11
    wrap with recover(request_id(limit_body(routes, cfg.maxBodyBytes)))

start(ctx):
    run in background token_loop(ctx)
    if ledger on: run in background sweep_loop(ctx)

token_loop(ctx):
    refresh_all(); every 1 minute until ctx cancelled: refresh_all()
refresh_all():
    deadline 30 s
    for profile in profiles (default first):
        identity_for(profile.code).client.token() or log error "session token refresh failed"   // G3

sweep_loop(ctx):
    sweep(); every 1 hour until ctx cancelled: sweep()
sweep():
    n = ledger.sweep(now)                                    // G9; 0 when retentionDays == 0
    if n > 0: log "ledger pruned", n

log_startup():
    log "nhcx gateway embedded", nhcx: cfg.urls.nhcx, participants: count(profiles)
    for profile in profiles: log "hosting participant", code, name, default
    if cfg.guests: log "hosting guests"

application startup (reference host):
    hosted = configured hosted participants, code -> name   // from configuration; the reference host lists its PMJAY desk [REF](../references/PAYERS.md#markers)
    gw = gateway.open({config_path, receive: C1.receive, host: hosted, guests: true, version})
    gw.log_startup()
    mount gw.handler() at "/"   // NHCX-facing routes only; optionally also under "/api/gateway"
    // the application's own code calls gw.send, ledger.*, registry.*, gw.token directly
    gw.start(ctx)
    serve the listener
    unless checks are skipped: run in background gw.check()                   // G11
    on signal: cancel ctx; shut the HTTP server down, waiting up to 30 s
```

#### G1U. USED BY
- Gateway: [G2. Configuration and Participants](G2-configuration.md), [G3. Session Token](G3-session-token.md), [G8. Receive](G8-receive.md), [G9. Ledger](G9-ledger.md), [G11. Startup Checks and Health](G11-startup-checks.md)
