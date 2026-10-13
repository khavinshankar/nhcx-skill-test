# Scaffolding

This is the shape the NHCX work takes inside a target HMIS. It lists every module to add, every file in it, what each file holds, which specs it implements, how the modules may depend on each other, and where configuration, secrets, migrations, tests and plan files go.

Names and folders here are placeholders. [L4 Code Planning](../steps/L4-code-planning.md) maps them onto the target's own conventions, so a Django app, a Spring module, a Rails engine, a .NET project or a Node package each gets the same parts in its own idiom. What must not change is the split between the parts and the direction of the dependencies.

## 1. Principles

1. **One NHCX module.** Everything NHCX-specific lives in one module (`nhcx/`), so it can be reviewed, tested and switched off as a unit. The HMIS's own modules change only where NHCX needs a field they own (patient ABHA, practitioner HPR id, facility HFR id and participant code) and where the navigation gets its "Claims" entry.
2. **The gateway is internal.** The gateway (G1 to G11) runs in the application process. The application calls it as functions; it never calls a separate gateway service over HTTP. The only HTTP the gateway serves is the route NHCX posts to and the health checks.
3. **Specs are the source of truth.** Each file implements named spec ids. The pseudocode (P sections), field tables (FnF, DnC) and verbatim messages are copied into behaviour exactly; the file's header comment names the spec ids it implements, and `nhcx-plan/code.json` records them with line ranges.
4. **Builders are pure.** FHIR builders and parsers turn plain values into resources and back. They never read the database, call the gateway or know about screens.
5. **Two writers.** Only services (A) and callback handlers (C) write the claim tables. Screens read models and call services.
6. **Replies are applied one way.** A reply found by polling (A10 to A13) is applied by the same callback handler (C2 to C10) that would have applied it if it had come in through G8.
7. **No secrets in the repository.** Client secret, private key and any payer desk credentials come from configuration or the environment.

## 2. Layout

```
<target repo>/
  nhcx/
    __init__ / module file             registers routes, opens the gateway at startup
    settings                           the module's own settings (see section 6)
    gateway/                           G1 to G11
    fhir/                              F1 to F19
    services/                          A1 to A19
    callbacks/                         C1 to C10
    models/                            D9 to D31
    migrations/                        D1 to D31 changes
    screens/                           S1 to S12, S18
    routes                             application routes for S1 to S12, S18 and A17
    archive                            the per-case message archive C1 writes
  <existing patient module>            S13 to S15 changes (ABHA verify and create, A19)
  <existing practitioner module>       S16 changes
  <existing facility settings>         D1 changes (HFR id, participant code)
  <existing navigation>                the "Claims" entry
  tests/nhcx/
    dry_run/                           L7
    e2e/                               L8
    fixtures/
  nhcx-plan/                           L1 to L8 outputs and the progress log
```

## 3. The NHCX module, file by file

### 3.1 `nhcx/gateway/` (G1 to G11)

The gateway knows nothing about claims. It sends, receives, records and hands over. It depends on nothing else in `nhcx/` except the C1 entry it is given at startup.

| File | Spec | Holds | Public surface |
|---|---|---|---|
| `embedding` | G1 | Opens the gateway from its config path and the C1 receive function; mounts the NHCX-facing routes; starts the token refresher (every minute) and the ledger pruner (hourly); shuts both down with the application. | `open(config_path, receive, host, guests, version)`, `start()`, `stop()`, `routes()` |
| `config` | G2 | Loads and validates the config file, expands `${ENV}` and `@file`, picks sandbox or production URLs, builds the participant profiles (default, hosted codes, guests). | `load(path)`, `profile_for(code)`, `owns_key(public_key)` |
| `token` | G3 | The ABDM session token cache per client id, refresh before expiry, one retry on a 401; `post_with_token` used by every ABDM call. | `token(participant)`, `refresh_token(participant)`, `post_with_token(url, body)` |
| `registry` | G4 | Participant record lookup and encryption certificate fetch, with a certificate cache and the self-key guard. | `participant(code)`, `certificate(code)`, `forget_certificate(code)` |
| `headers` | G5 | Builds the protected `x-hcx-*` headers, mints ids, defaults the status by path, normalises participant codes, formats timestamps. | `build_protected_headers(given, path)`, `entity_type(path)` |
| `crypto` | G6 | Compact JWE: RSA-OAEP-256 and A256GCM out, the allow-listed algorithms in; key parsing (PEM, PKCS#8, PKCS#1, X.509). | `encrypt(payload, public_key, headers)`, `decrypt(jwe, private_key)`, `parse_header(jwe)` |
| `send` | G7 | One FHIR payload to one encrypted NHCX message, posted synchronously, recorded in the ledger. Returns the result with its ids, or a send error with code, message, retryable and the ids it went out under. | `send(path, envelope)` |
| `receive` | G8 | The inbound handler for `/in/<path>` and `/v1/<rest>`: decrypt, resolve participant, call C1, record the outcome, answer NHCX 202 (or 502 on `error`). | `handle(path, body)` (mounted by `embedding`) |
| `ledger` | G9 | One file per message under `<ledger dir>/<yyyy-mm-dd>/`, in-memory indexes, retention pruning, and the queries polling uses. | `related(txn_id)`, `fhir(txn_id)`, `dispatch(txn_id)`, `list()`, `get(id)` |
| `beneficiary` | G10 | Pass-through to the ABDM participant service for policy search and ABHA link or delink. | `policies_search(query)`, `abha_link(body)`, `abha_delink(body)` |
| `checks` | G11 | Startup checks (token, registry record, certificate match, endpoint probe) and the `/healthz` and `/readyz` answers. Reports only. | `check()`, `healthz()`, `readyz()` |

Mounted routes, and nothing else: `POST /in/<path>`, `POST /v1/<rest>`, `GET|POST /healthz`, `GET|POST /in/healthz`, `GET /readyz`.

### 3.2 `nhcx/fhir/` (F1 to F19)

Pure functions. Builders take a plain input object assembled by a service from the models (field sources come from `nhcx-plan/mapping.json`) and return a resource. Parsers take a received bundle and return plain values the callback handler writes.

| File | Spec | Holds |
|---|---|---|
| `bundle` | F1 | Bundle ids per message kind, profiles, the anchor-first entry order, absolute `https://nhcx.abdm.gov.in/...` references; wraps built resources into a Bundle and unwraps received ones. |
| `build/coverage_request` | F2 | The seven-entry eligibility bundle for all four purposes; items only for auth-requirements. |
| `build/plan_task` | F4 | The InsurancePlan discovery Task. |
| `build/questionnaire_response` | F7 | One QuestionnaireResponse per answered form for the leg being sent. |
| `build/claim` | F8 | The Claim for every leg: items (grouped lines, factors, tiers), diagnoses, care team, supportingInfo (documents, forms, discharge, query answers), insurance, total. |
| `build/task` | F10 | Cancel, status, reprocess and release Tasks with their reason codes. |
| `build/communication` | F12 | The query reply bundle and the notification acknowledgement bundle. |
| `build/payment_ack` | F14 | The payment acknowledgement Task. |
| `build/patient` | F15 | The Patient variants (claim bundle, communication reply, eligibility), with the policy fallbacks. |
| `build/practitioner` | F16 | Practitioner per care-team doctor (HPR id, degree coding) and the fixed PractitionerRole. |
| `build/organization` | F17 | Provider (HFR id) and payer (participant code). |
| `build/coverage` | F18 | Coverage with the policy code and member id, `NONE` for discovery. |
| `build/other` | F19 | Procedure per package and the Location. |
| `read/eligibility` | F3 | Verdict, wallet and pre-auth flag; the auth-requirements ruling per item with its documents and forms. |
| `read/plan` | F5, F6 | Packages, rates, tiers, conditions, documents; forms collected by url. |
| `read/claim_response` | F9 | Decision from the adjudication, totals, per-item results, pre-auth reference; the Task answer for cancel and enquiries (F10). |
| `read/communication` | F11 | Query or notification classification, the questions asked, the case it names. |
| `read/payment` | F13 | Amount, status, date, UTR, breakdown and the claim number, with the fallbacks. |
| `codes` | F8, F16, D8 | Code systems and lookups: ICD-10, SNOMED, document type codes, degree codes, gender and relationship. |

### 3.3 `nhcx/services/` (A1 to A19)

One file per API. Each follows its spec's pseudocode (AnP): pre-send checks with the verbatim refusal messages, gather data from models, build with `fhir/`, call `gateway.send` **outside any database transaction**, then record the ids and status on the leg's row in a transaction of its own, handle a failed send that names ids (section 8).

| File | Spec | Holds | Called from |
|---|---|---|---|
| `policy` | A1 | Search, normalise the registry's field spellings, open a case from a chosen policy. | S1, S2 |
| `eligibility` | A2 | Validation, benefits and discovery checks; the auth-requirements check on the chosen lines. | S3, S8.2 |
| `plan` | A3 | Request the package master, or reuse one already held for the same payer, policy and facility. | S7 |
| `preauth` | A4, A6 cancel and status | Send kinds (request, query answer, enhancement, enhancement resubmit), predetermination, cancel with reason, status enquiry. | S9 |
| `claim` | A5, A6 reprocess and release | Claim send kinds, the LAMA and DAMA rule, reprocess and release. | S11 |
| `communication` | A7 | Reply to a query with text and documents; acknowledge a notification. | S10, C9 |
| `payment` | A8 | Acknowledge a payment notice, automatically or by hand. | S12, C10 |
| `polling` | A10 to A13 | For each leg still waiting: find the reply in the ledger and apply it through its callback handler, or record a dispatch failure or protocol rejection. | S6 on open, A17 |
| `adjudicator` | A14 to A16 | Payer role lookup and decisions for sandbox testing. Off in production. | adjudicator console, L8 |
| `state` | A17 | The claim state JSON for drivers and tests. | A17 route |
| `biometric` | A18 | The beneficiary's fingerprint, iris or face authentication against ABDM's biometric service, for any payer; the current user token per stage, refreshed on the way out. Plain JSON with the session token, never through G7. | S18; A2, A4, A5 read it |
| `abha` | A19 | Create an ABHA from an Aadhaar OTP, or verify one by OTP, through ABDM's ABHA service (the calls from the MCP's M1 catalogue), **on the server**: the page seals the identifiers and holds only the `txn_id`; the session token, X-token and T-token stay server-side for the flow's few minutes. | S13, S14, S15 |
| `stage` | D9 | Recomputes a case's `stage` and `sub_stage` after any write. Every service and handler calls it. | services, callbacks |

### 3.4 `nhcx/callbacks/` (C1 to C10)

Called only by G8 (inbound) and by `services/polling` (a reply found in the ledger). Each handler answers `settled`, `unmatched`, `ignored`, `rejected` or `error`, and must be safe to receive the same message twice.

| File | Spec | Holds |
|---|---|---|
| `dispatch` | C1 | Rejects an unreadable envelope, archives the message beside its case, routes by type, applies the shared rules (refusals, reopening a failed send, redelivery). |
| `eligibility` | C2, C3 | Applies the eligibility verdict to the case, or the ruling to D13 to D15. |
| `plan` | C4 | Replaces the package master in D10 to D12; `empty` when no plan came. |
| `preauth` | C5, C7 | Applies pre-auth and predetermination replies; applies the cancel answer. |
| `claim` | C6 | Applies the claim verdict. |
| `enquiry` | C8 | Applies status, reprocess and release answers. |
| `communication` | C9 | Files a query, notification or note; triggers the notification acknowledgement (A7). |
| `payment` | C10 | Records the notice and its breakdown, updates a repeat, triggers the acknowledgement (A8). |

### 3.5 `nhcx/models/` and `nhcx/migrations/` (D1 to D30)

- Models for D9 to D30, one per table, with the status values from each DnD as named constants rather than bare strings.
- D1 to D8 are the HMIS's own tables. Add only the missing columns that `nhcx-plan/mapping.json` lists (for example `patient.abha_number`, `practitioner` HPR id, `organization.participant_code`), in their own modules' models.
- One migration per plan phase, created with the target's migration tool, never by editing a schema file by hand. Each migration creates the phase's tables with the keys and indexes in DnK.

### 3.6 `nhcx/screens/` and `nhcx/routes` (S1 to S12)

- One template or component per screen; the claim detail (S6) is a shell that renders its tabs (S3, S7, S8, S4 with S9, S10, S11, S12) in episode order.
- Screens read models and call services. They never build FHIR and never call the gateway.
- Field labels, options, chips, empty states and messages follow each S spec verbatim.
- Wherever a screen shows a payer, it shows the payer's registered name from the participant registry cache (D9 `payer_name`, G4); a payer whose lookup failed shows its participant code, never a guessed or configured name ([PAYERS.md](PAYERS.md)).
- Routes:

| Route | Screen or API |
|---|---|
| `claims/list` | S5 |
| `claims/search`, `claims/search/results` | S1, S2 |
| `claims/view/:caseid` | S6, with `tab` for S3, S7, S8, S9, S10, S11, S12 |
| `claims/view/:caseid/plan/...` | S7.1 to S7.3 |
| `claims/view/:caseid/lines/...` | S8.1 |
| `claims/view/:caseid/state` | A17 |
| one POST per screen action | the service call the S spec names |

### 3.7 `nhcx/archive`

C1 archives every inbound envelope, and services archive every outbound one, beside the case under `<archive dir>/<claim number or "unmatched">/`, with a `transactions.txt` line per message. The directory comes from settings and lives outside the repository.

## 4. Changes to existing HMIS modules

| Module | Spec | Change |
|---|---|---|
| Patient | S13, S14, S15, D3 | ABHA number and address fields on the form, the ABHA search in the list, the ABHA chip on the chart. The ABHA number is what links a claim to an admission. |
| Practitioner | S16, D2 | HPR id, registration number and qualification; retired practitioners drop out of pickers. The care team on the pre-auth comes from here. |
| Facility settings | D1 | HFR id and NHCX participant code. |
| Patient (ABHA) | D3, A19 | "Register with ABHA" on the list and "Verify or create an ABHA" on the form and the chart, filling the file from the ABHA service's profile. |
| Admission (encounter) | D4 | Nothing new if the HMIS already marks the current admission and its dates; S4 links a case to it. |
| Navigation | L3 | A "Claims" entry on the home screen, sidebar or navbar, opening S5. |

Two patterns are allowed where the HMIS's own tables should not change:
- **NHCX-owned one-to-one extension tables** for D1 (the facility's HFR id and participant code) and D2 (the practitioner's HPR id and `active` flag), keyed on the HMIS row, instead of altering the HMIS's own tables; the ABHA number goes through the HMIS's own identifier mechanism when it has one (an identifier table or a typed identifier list), else onto D3. Mapping.json records which was chosen.
- **Coexistence with an ABDM plug** that already owns the ABHA screens (M1, consent): NHCX's entry points sit beside the plug's, never inside them; the two keep separate identifier systems; and claims match a patient only on the NHCX-recorded ABHA number, read through the identifier mechanism above, never on the plug's internal ids.

## 5. Dependency direction

```
screens ──> services ──> fhir/build ──> (plain values only)
   │            │
   │            ├──> models
   │            └──> gateway.send ──> NHCX
   └──> models (read)

NHCX ──> gateway.receive ──> callbacks ──> fhir/read
                                  └──> models, services/stage, services/communication|payment (acks)

services/polling ──> gateway.ledger ──> callbacks (same handlers)
```

Forbidden: screens to gateway, screens to fhir, fhir to models, fhir to gateway, gateway to services or models.

## 6. Configuration and secrets

| Setting | Where | Used by |
|---|---|---|
| Gateway config file path | module settings | G1 |
| Environment (`sandbox` or `production`) | gateway config | G2 |
| Participant code, client id | gateway config | G2, G3 |
| Client secret | environment variable referenced as `${NAME}` | G3 |
| Private key of the registered certificate | file outside the repo, referenced as `@path` | G6 |
| Public URL registered as `endpoint_url` | gateway config | G2, G11 |
| Ledger directory and retention days | gateway config | G9 |
| Archive directory | module settings | C1 |
| Payer service token, IRDAI desk URL and account | module settings, sandbox only | A14 to A16 |
| Adjudicator console on or off | module settings, off in production | A14, A15 |
| Biometric hosts (`biometric_base_url`, `faceauth_base_url`, `faceauth_qr_url`) and the user-token header name (`biometric_token_header`); the face Aadhaar is sealed under the ABHA service's certificate (A19), no key of its own | module settings | A18, A2, A4, A5 |
| ABHA service base (`abha_base_url`) | module settings | A19 |

## 7. Background work

- Token refresh, every minute (G1, G3).
- Ledger pruning, hourly (G1, G9).
- No polling job: polling runs when a claim is opened (S6) or its state is read (A17). A target that wants background polling adds a job that calls `services/polling` per waiting case; it must use the same handlers.

## 8. Errors and logging

- Services return the spec's refusal messages to the screen as a flash, never a server error.
- A failed send that names ids keeps them on the leg and marks it failed, because the message may have reached NHCX.
- **`gateway.send` is never called inside a database transaction** (G7): the ledger row would roll back with the caller and the failed send's ids would be lost. Services send first, then write the leg in their own transaction. A framework with per-request transactions opts the sending routes and the inbound routes (G8) out; C2 to C8 may run in a savepoint, C9 and C10 (which send acknowledgements) may not.
- Callback handlers never raise for a message they cannot use; they answer `rejected` or `ignored`. Only an unexpected fault is `error`, which makes NHCX redeliver.
- Log with the target's logger, always with the case number, correlation id and ledger id, so any line can be traced to G9 and the archive.

## 9. Tests

```
tests/nhcx/
  fixtures/
    keys/                  a test key pair for G6
    registry/              participant records, certificates, policy search replies
    bundles/               received bundles from the knowledge source's examples, with their source noted
  dry_run/                 L7, no network
    gateway/               G5 to G9 and G11
    fhir/                  one test file per builder and parser
    services/              one per A, every refusal and the send failure cases
    callbacks/             one per C, with a redelivery and a ProtocolResponse each
    screens/               one per S
    flow                   S1 to S12 against the fake NHCX
  e2e/                     L8, NHCX sandbox
    setup                  G11 checks
    exchanges              E1 to E9, one test each
```

## 10. Plan files

```
nhcx-plan/
  discovery.json      L1: technology, every spec id found, partial or missing, with file and lines
  mapping.json        L2: target fields to D columns and F elements
  plan.json           L3: phases, steps, sub-steps, dependencies, risks
  code-plan.json      L4: conventions, files, functions, order, batches
  code.json           L5: written files, what each implements, line ranges
  validation.json     L6: per-file checks against the specs
  dry-run.json        L7: test results and coverage
  e2e.json            L8: sandbox exchanges and results
  knowledge.json      L1.0: the knowledge source chosen (MCP or package) and its version
  knowledge/          the GitHub package zip and its extracted folder, when the package is the source
  progress.json       every step: the log of sub-steps and file changes (steps/LOG.md)
  progress.md         generated from progress.json
```

All of them are committed with the code they describe.

## 11. Where each spec lands

| Spec | Lands in |
|---|---|
| G1 to G11 | `nhcx/gateway` |
| F1 to F19 | `nhcx/fhir` |
| A1 to A17 | `nhcx/services` (A17 also in `nhcx/routes`) |
| C1 to C10 | `nhcx/callbacks` |
| D1 to D8 | the HMIS's own models, extended by `nhcx/migrations` |
| D9 to D30 | `nhcx/models`, created by `nhcx/migrations` |
| S1 to S12 | `nhcx/screens`, `nhcx/routes` |
| S13 to S16 | the existing patient and practitioner modules |

## 12. Build order

Matches the plan phases in [L3](../steps/L3-integration-planning.md). Each phase adds its migrations, FHIR builders and parsers, services, callbacks, screens and dry-run tests together, so it can be exercised before the next starts.

| Phase | Adds |
|---|---|
| 1 Foundation | `gateway/`, settings, the inbound route wired to a stub receive that answers `unmatched` (202) |
| 2 Data | `models/` and migrations for D9, D30 and every leg table C1 matches on (D10, D13, D18, D19, D20, D21, D23, D24, D29); D1 to D3 field changes; then `callbacks/dispatch` (C1) and `archive`, which read those tables (`claim_for_correlation`, `claim_named_in`) and cannot be written before them |
| 3 Policy and eligibility | `services/policy`, `services/eligibility`, `callbacks/eligibility` (C2), F2, F3, F15 to F18, S1, S2, S3, S5, S6 shell |
| 4 Plan and line items | `services/plan`, auth-requirements, `callbacks/plan`, C3, F4 to F6, D10 to D16, S7, S8 |
| 5 Pre-authorisation | `services/preauth`, `callbacks/preauth`, `callbacks/enquiry`, F7 to F10, F19, D17 to D19, D25 to D29, S4, S9 |
| 6 Payer communication | `services/communication`, `callbacks/communication`, F11, F12, D23, S10 |
| 7 Claim | `services/claim`, `callbacks/claim`, D20, S11 |
| 8 Payment | `services/payment`, `callbacks/payment`, F13, F14, D21, D22, S12 |
| 9 Patient and practitioner | S13 to S16 field changes |
| 10 Navigation | the "Claims" entry |
