# G9. Ledger

#### G9E. ENTRY
In-process, the four reads the application polls with:

- `ledger.related(txn_id) -> [Row]` (A10)
- `ledger.fhir(txn_id) -> TxnEnvelope` (A12)
- `ledger.dispatch(txn_id) -> DispatchState` (A11)
- `ledger.list(limit = 200) -> [Row]` (A13)

And, for the gateway's own use and for diagnostics:

- `ledger.record(entry)` (G7, G8), `ledger.get(id)`, `ledger.thread(correlation_id)`, `ledger.seen(direction, api_call_id)`, `ledger.last_inbound_request(entity, from, workflow_id)`, `ledger.sweep(now)`

No network calls. Files only.

#### G9D. DESCRIPTION
The ledger is the gateway's record of every message it sent or received: headers, payload, and what became of it. It is plain files, no database [REF](../references/PAYERS.md#markers). The application never writes to it; it reads it to find a reply by polling (A10 to A13) when the callback (C1) has not delivered one.

**The contract.** What the rest of the application relies on is this, not the storage:

- `record(entry)` for every message sent or received, with its headers, payload and outcome;
- `related(txn_id)`: every entry on the same correlation thread, newest first;
- `fhir(txn_id)`, `get(id)`: one entry's envelope, or the whole entry;
- `dispatch(txn_id)`: what became of one send;
- `list(...)`: entries newest first, for the rejection scan (A13);
- `seen(direction, api_call_id)`: whether a message was already recorded (the redelivery flag of G8);
- pruning by a retention period.

The storage described below (one file per message under dated folders, with in-memory indexes) is the reference implementation's [REF](../references/PAYERS.md#markers). A target may keep the ledger in its own database instead, with the same contract; a ledger in the shared database can also be read by every instance ([OPERATIONS.md](../references/OPERATIONS.md)).

**The ledger in the application's database** (the recipe a multi-process host needs, [OPERATIONS.md](../references/OPERATIONS.md)): one table with the entry's fields as columns (`id` text primary key, `direction`, `created_at` as an aware timestamp, `day` the UTC date as text, `path`, `entity`, `action`, `kind`, `format`, `sender`, `recipient`, `correlation_id`, `api_call_id`, `request_id`, `workflow_id`, `hcx_status`, `status`, `error` JSON, `redelivery`, `duration_ms`, `peer` JSON, `headers` JSON, `fhir` JSON, `fhir_summary` JSON).
- **Id allocation across processes**: the id is still `<day><counter>` in the base32 above. Allocate under a per-day advisory lock (PostgreSQL `pg_advisory_xact_lock(hash(day))`; MySQL `GET_LOCK`), read `max(id)` for the day, add one, insert; on a unique violation (two processes racing without the lock, or SQLite with no advisory lock) retry with the next counter, at most 5 times. The ledger write commits in a transaction of its own, never inside the caller's (G7).
- **Indexes**: `(direction, api_call_id)` for `seen`; `(correlation_id, id)` for `related` and `thread`; `(direction, kind, entity, sender, workflow_id, id)` for `last_inbound_request`; `(day)` for pruning; `id` is the primary key, which also gives `list` its newest-first order.
- **Pruning**: `sweep` deletes `where day < cutoff` by the stored UTC day, in batches, and nothing is held in memory, so every instance sees every row and `seen` is the index lookup.
- `storeBodies` false leaves `fhir` and `peer.response` null as before; `get` reads the row. The contract above is unchanged and A10 to A13 cannot tell the two storages apart.

A transaction id is a ledger id. `send` (G7) returns it as both `ledger_id` and `txn_id`; the application stores it on the leg and polls with it.

Storage, under `ledger.dir` (default `data/ledger`, relative to the gateway config file):

```text
<dir>/<YYYY-MM-DD>/<id>.json     one entry, pretty-printed JSON, file mode 0640
<dir>/<YYYY-MM-DD>/index.jsonl   one summary line per entry, appended as written
```

The day folder is the entry's `created_at` in UTC. At startup only the `index.jsonl` files are read, into memory: summaries by id, ids in ascending order, ids by correlation id, and a `seen` set of `<direction>:<api_call_id>`. A full entry (with headers and payload) is read from its file on `get`.

Ids are eight characters over the alphabet `0123456789ABCDEFGHIJKLMNOPQRSTUV` (base 32 whose ASCII order is its numeric order, so ids sort by time as plain strings). The first four encode the UTC date as the number YYMMDD, the last four a counter that restarts each day at `0001` (up to 1,048,575 a day). `7UMV0001` is the first message of 2026-08-31. This id format is [REF](../references/PAYERS.md#markers). On the first message of a day, including the first after a restart, the counter continues from the highest id already on record for that date. Ids from older builds (24 or more characters starting `YYYYMMDD`) are still readable.

Retention: `ledger.retentionDays` (0 or unset keeps everything; the sample config sets 30 [REF](../references/PAYERS.md#markers)). Every hour, and once at start, day folders whose date is before `now - retentionDays` (UTC) are deleted with their entries, and dropped from the in-memory indexes (so their `api_call_id`s no longer count as seen). `ledger.storeBodies` (default true): when false, the payload and the peer's response body are not kept, so `fhir` reads back empty. `ledger.enabled` (default true): when false nothing is recorded, the reads below fail, redelivery is never flagged and responses are not threaded automatically (G7).

#### G9Q. INPUT
`Entry`, as written by G7 and G8 (missing `id`, `created_at`, `entity`, `action`, `kind` and `fhir_summary` are filled in by `record`):

| Field | Default | Meaning |
|---|---|---|
| `id` | next id | ledger id, format above |
| `direction` | none | `out` (application to NHCX) or `in` (NHCX to application) |
| `created_at` | now | send start, or receipt time |
| `path` | none | NHCX path, slashes trimmed |
| `entity` | from path | `preauth`, `claim`, `coverageeligibility`, `insuranceplan`, `task`, `communication`, `payment`, `status`, ... (G5 entity type) |
| `action` | last path segment | `submit`, `on_submit`, `check`, `on_check`, `request`, `on_request`, ... |
| `kind` | from path | `response` when `action` starts `on_`, else `request` |
| `format` | none | `fhir`; inbound also `protocol`, `json`, or `unknown` for a refused message |
| `sender`, `recipient` | none | participant codes |
| `correlation_id`, `api_call_id`, `request_id`, `workflow_id` | none | from the protected headers |
| `hcx_status` | none | `x-hcx-status` |
| `status` | none | outcome, table in G9S |
| `error` | none | `{code, message}` when not a success |
| `redelivery` | false | inbound: an earlier inbound row had the same `api_call_id` |
| `duration_ms` | 0 | dispatch time (out) or delivery time (in) |
| `peer` | none | `{url, status_code, response}`: NHCX's answer (out) or C1's (in) |
| `headers` | none | the full protected header set |
| `fhir` | none | the payload |
| `fhir_summary` | computed | `{resource_type, bundle_type, entries, resource_types, focus, identifier, patient, outcome}` of the payload |

Query input: `txn_id` is a ledger id. `limit` for `list` is 1 to 500, default 200; an out-of-range value is ignored and the default used.

#### G9S. OUTPUT
Statuses:

| Status | Direction | Meaning |
|---|---|---|
| `accepted` | out | NHCX answered 2xx |
| `rejected` | out | NHCX answered non-2xx (error `GATEWAY_HTTP_<n>`) |
| `rejected` | in | the gateway refused it: undecryptable, wrong recipient, unreadable |
| `failed` | out | never reached NHCX (no certificate, no token, unreachable) |
| `delivered` | in | C1 took it |
| `delivery_failed` | in | C1 refused or failed; NHCX will redeliver |

`Row` (one element of `related` and `list`), newest first:

| Field | From |
|---|---|
| `id` | ledger id |
| `direction` | `in` or `out` |
| `status` | table above |
| `sender`, `recipient` | codes |
| `correlation_id`, `api_call_id` | ids |
| `type` | `entity`, protocol spelling (`coverageeligibility`, `insuranceplan`, `preauth`, `claim`, `task`, `payment`, ...) |
| `flow` | `action` (`on_submit`, `request`, ...) |
| `created_at` | RFC 3339 timestamp with fractional seconds and zone |

`related(txn_id)`: every row with the same correlation id as that entry, both directions, newest first, at most 500. The entry itself is included.

`fhir(txn_id)` returns `TxnEnvelope`, the same shape C1 receives, from the stored entry:

```json
{"meta": {"type": "out", "payloadType": "fhir", "path": "v1/preauth/submit", "time": "2026-09-21T12:01:05.123+05:30"},
 "jwe_headers": {"x-hcx-correlation_id": "...", "x-hcx-api_call_id": "...", "...": "..."},
 "fhir": {"resourceType": "Bundle", "...": "..."}}
```

`meta.type` is `in` or `out`; `meta.payloadType` is the entry's `format`. `fhir` is `null` when bodies are not stored or the message was refused before decryption. There is no `payload` key.

`dispatch(txn_id)` returns `DispatchState`:

| Field | Value |
|---|---|
| `txnId` | the id |
| `status` | `dispatch_failed` for `failed` and `rejected`; `dispatched` for `accepted` and `delivered`; otherwise the ledger status as is (`delivery_failed`) |
| `errorCode` | `error.code` (for example `CERT_NOT_FOUND`, `GATEWAY_HTTP_400`), when set |
| `errorMessage` | `error.message`, when set |

There is no `dispatch` object and no `dead` or `errored` status: dispatch is synchronous (G7), so by the time a transaction has an id its fate is decided and there is nothing queued to retry. NHCX's own refusal body is on the full entry's `peer.response` (`ledger.get`), not in this answer.

`list(limit)`: the newest `limit` rows of the whole ledger, same `Row` shape. With the ledger off it returns `[]`.

Errors (`related`, `fhir`, `dispatch`):

| Code | When |
|---|---|
| `NO_TXN_ID` | `txn_id` empty |
| `TXN_NOT_FOUND` | no entry with that id (unknown, pruned, or the ledger folder was reset). Final: A10 treats it as "stop polling" |
| `LEDGER_DISABLED` | the ledger is off |

`thread(correlation_id)`, for diagnostics: `{correlation_id, entity, workflow_id, counterparty, role, state, started, updated, messages: [Summary, oldest first]}` or nothing when unseen. `role` is `initiator` when the first message went out, `responder` when it came in (reversed when the first message is a response). `state` is derived by walking the messages oldest first:
- a `failed` or `rejected` message, a `delivery_failed` response, a `protocol` payload, or an `hcx_status` containing `error`: `error`;
- otherwise a request out: `awaiting_response`; a request in: `awaiting_our_response`;
- a response with `hcx_status` `response.partial`: `partial`; any other response: `completed`;
- nothing matched: `unknown`. The last message that matched sets the state.

#### G9P. PSEUDOCODE

```text
record(e):
    if e.created_at unset: e.created_at = now
    if e.id unset: under lock: e.id = next_id(e.created_at)
    e.path = trim_slashes(e.path)
    e.entity = e.entity or entity_type(e.path)
    e.action = e.action or last segment of e.path
    e.kind   = e.kind or ("response" if e.path is a response path else "request")
    if e.fhir and no e.fhir_summary: e.fhir_summary = summarize(e.fhir)
    if not store_bodies: e.fhir = none; e.peer.response = none
    day = e.created_at in UTC as YYYY-MM-DD
    write <dir>/<day>/<e.id>.json (indented)
    under lock:
        append summary(e) as one JSON line to <dir>/<day>/index.jsonl
        index it: by id, ids ascending (re-sort if the clock stepped back),
                  by correlation id, seen["<direction>:<api_call_id>"] = true
    // any error is returned to the caller, which only logs it

next_id(t):
    day = base32(YY*10000 + MM*100 + DD of t in UTC, width 4)
    if day != current_day: current_day = day; seq = highest counter on record for day
    seq = seq + 1
    return day + base32(seq, width 4)

related(txn_id):
    e = get(txn_id) or raise TXN_NOT_FOUND
    return rows(list(correlation_id = e.correlation_id, limit = 500))
    // an entry with an empty correlation id matches every row (the filter is off) [REF](../references/PAYERS.md#markers)

fhir(txn_id):
    e = get(txn_id) or raise TXN_NOT_FOUND
    return {meta: {type: "in" if e.direction == "in" else "out", payloadType: e.format,
                   path: e.path, time: e.created_at},
            jwe_headers: e.headers, fhir: e.fhir}

dispatch(txn_id):
    e = get(txn_id) or raise TXN_NOT_FOUND
    out = {txnId: e.id, status: e.status}
    if e.status in (failed, rejected):    out.status = "dispatch_failed"
    if e.status in (accepted, delivered): out.status = "dispatched"
    if e.error: out.errorCode = e.error.code; out.errorMessage = e.error.message
    return out

list(limit = 200):
    if ledger off: return []
    if limit not in 1..500: limit = 200
    return rows(list_summaries(limit))

list_summaries(correlation_id = none, limit = 50):   // newest first
    ids = ids for correlation_id if given, else all ids
    walk ids from newest to oldest, keep up to limit

rows(summaries): each -> {id, direction, status, sender, recipient, correlation_id,
                          api_call_id, type: entity, flow: action, created_at}

get(id):
    if id is not a valid id (either scheme, no slash): not found
    read <dir>/<day of id>/<id>.json; missing file: not found; bad JSON: error "corrupt"

seen(direction, api_call_id):  api_call_id non-empty and "<direction>:<api_call_id>" in seen

last_inbound_request(entity, from, workflow_id):     // G7 response threading
    for ids newest first:
        s = summary; skip unless s.direction == "in" and s.kind == "request"
                         and s.entity == entity and s.correlation_id set
        skip if from set and s.sender is not the same code as from
        skip if workflow_id set and s.workflow_id != workflow_id
        return s
    return none

sweep(now):                                          // hourly and at start, G1
    if retention_days == 0: return 0
    cutoff = (now - retention_days) in UTC as YYYY-MM-DD
    for each folder named YYYY-MM-DD with name < cutoff:
        delete the folder; drop its ids from every index and from seen
```

#### G9U. USED BY
- Screens: [S6. Claim Detail](../screens/S6-claim-detail.md)
- APIs: [A1. Policy Search](../apis/A1-policy-search.md), [A2. Coverage Eligibility Check](../apis/A2-coverage-eligibility-check.md), [A3. Insurance Plan Request](../apis/A3-insurance-plan-request.md), [A4. Pre-auth Submit](../apis/A4-preauth-submit.md), [A5. Claim Submit](../apis/A5-claim-submit.md), [A6. Task Submit (cancel, status, reprocess, release)](../apis/A6-task-submit.md), [A7. Communication Reply](../apis/A7-communication-on-request.md), [A8. Payment Notice Acknowledgement](../apis/A8-paymentnotice-on-request.md), [A10. Transaction Related](../apis/A10-txn-related.md), [A11. Transaction Dispatch](../apis/A11-txn-dispatch.md), [A12. Transaction FHIR](../apis/A12-txn-fhir.md), [A13. Transaction List](../apis/A13-txn-list.md), [A17. Claim State](../apis/A17-claim-state.md)
- Callbacks: [C1. Callback Door](../callbacks/C1-callback-door.md), [C5. Pre-auth Reply](../callbacks/C5-preauth-on-submit.md), [C6. Claim Reply](../callbacks/C6-claim-on-submit.md)
- FHIR: [F1. Bundle](../fhir/F1-bundle.md)
- Database: [D9. claim](../database/D9-claim.md), [D10. claim_plan](../database/D10-claim-plan.md), [D13. claim_auth](../database/D13-claim-auth.md), [D18. claim_preauth](../database/D18-claim-preauth.md), [D19. claim_predetermination](../database/D19-claim-predetermination.md), [D20. claim_submission](../database/D20-claim-submission.md), [D29. claim_enquiry](../database/D29-claim-enquiry.md)
- Gateway: [G1. Embedding](G1-embedding.md), [G2. Configuration and Participants](G2-configuration.md), [G5. Protocol Headers](G5-protocol-headers.md), [G7. Send](G7-send.md), [G8. Receive](G8-receive.md)
- Tests: [T2. Test Runners](../tests/T2-test-runners.md)
