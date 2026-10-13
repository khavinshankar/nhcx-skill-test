# Scaffolding

This is the shape the NHCX work takes inside a target payer system. It lists every module to add, every file in it, what each file holds, which specs it implements, how the modules may depend on each other, and where configuration, secrets, migrations, tests and plan files go.

Names and folders here are placeholders. [L4 Code Planning](../steps/L4-code-planning.md) maps them onto the target's own conventions, so a Django app, a Spring module, a Rails engine, a .NET project or a Node package each gets the same parts in its own idiom. What must not change is the split between the parts and the direction of the dependencies.

## 1. Principles

1. **One NHCX module.** Everything NHCX-specific lives in one module (`nhcx/`), so it can be reviewed, tested and switched off as a unit. The payer system's own modules change only where NHCX needs a field they own (member ABHA number, product UIN and plan type codes, procedure package rate and document rules, the payer's participant codes) and where the navigation gets its "Cases" and "Payments" entries.
2. **The gateway is internal.** The gateway (G1 to G11) runs in the application process. The application calls it as functions; it never calls a separate gateway service over HTTP. The only HTTP the gateway serves is the route NHCX posts to and the health checks.
3. **Specs are the source of truth.** Each file implements named spec ids. The pseudocode (P sections), field tables (FnF, DnC) and verbatim messages are copied into behaviour exactly; the file's header comment names the spec ids it implements, and `nhcx-plan/code.json` records them with line ranges.
4. **Builders are pure.** FHIR builders and parsers turn plain values into resources and back. They never read the database, call the gateway or know about screens.
5. **Two writers.** Only services (A) and callback handlers (C) write the case tables. Screens read models and call services.
6. **Replies are applied one way.** A hospital's reply found by polling (A11, A12) is applied by the same callback handler (C9, C11) that would have applied it if it had come in through G8.
7. **A person decides.** A pre-authorisation or a claim is filed and acknowledged, never decided by code; only a predetermination is priced by rules. The verdict goes out once, when the decision exists, and a gateway that is down does not un-make it.
8. **No secrets in the repository.** Client secret, private key and the callback token come from configuration or the environment.

## 2. Layout

```
<target repo>/
  nhcx/
    __init__ / module file             registers routes, opens the gateway at startup
    settings                           the module's own settings (see section 6)
    gateway/                           G1 to G11
    fhir/                              F1 to F19
    services/                          A1 to A19
    callbacks/                         C1 to C11
    models/                            D19 to D32
    migrations/                        D1 to D32 changes
    screens/                           S1 to S3, S10, and the additions to S4 to S9, S11, S12
    routes                             application routes for S1 to S12 and A15
    archive                            the per-case message archive C1 writes
  <existing member module>             S4, S5 changes (D5 to D9)
  <existing product module>            S6 to S9 changes (D10 to D18)
  <existing payer settings>            S12, D1 changes (participant and processing codes)
  <existing navigation>                the "Cases" and "Payments" entries
  tests/nhcx/
    dry_run/                           L7
    e2e/                               L8
    fixtures/
  nhcx-plan/                           L1 to L8 outputs and the progress log
```

## 3. The NHCX module, file by file

### 3.1 `nhcx/gateway/` (G1 to G11)

The gateway knows nothing about cases. It sends, receives, records and hands over. It depends on nothing else in `nhcx/` except the C1 entry it is given at startup.

| File | Spec | Holds | Public surface |
|---|---|---|---|
| `embedding` | G1 | Opens the gateway from its config path and the C1 receive function; mounts the NHCX-facing routes; starts the token refresher (every minute) and the ledger pruner (hourly); shuts both down with the application. | `open(config_path, receive, host, guests, version)`, `start()`, `stop()`, `routes()` |
| `config` | G2 | Loads and validates the config file, expands `${ENV}` and `@file`, picks sandbox or production URLs, builds the participant profiles (the payer, a processing code it also answers for, guests). | `load(path)`, `profile_for(code)`, `owns_key(public_key)` |
| `token` | G3 | The ABDM session token cache per client id, refresh before expiry, one retry on a 401; `post_with_token` used by every ABDM call. | `token(participant)`, `refresh_token(participant)`, `post_with_token(url, body)` |
| `registry` | G4 | Participant record lookup and encryption certificate fetch, with a certificate cache and the self-key guard. | `participant(code)`, `certificate(code)`, `forget_certificate(code)` |
| `headers` | G5 | Builds the protected `x-hcx-*` headers, mints ids, defaults the status by path, normalises participant codes, formats timestamps. | `build_protected_headers(given, path)`, `entity_type(path)` |
| `crypto` | G6 | Compact JWE: RSA-OAEP-256 and A256GCM out, the allow-listed algorithms in; key parsing (PEM, PKCS#8, PKCS#1, X.509). | `encrypt(payload, public_key, headers)`, `decrypt(jwe, private_key)`, `parse_header(jwe)` |
| `send` | G7 | One FHIR payload to one encrypted NHCX message, posted synchronously, recorded in the ledger. Returns the result with its ids, or a send error with code, message, retryable and the ids it went out under. | `send(path, envelope)` |
| `receive` | G8 | The inbound handler for `/in/<path>` and `/v1/<rest>`: decrypt, resolve participant, call C1, record the outcome, answer NHCX 202 (or 502 on `error`). | `handle(path, body)` (mounted by `embedding`) |
| `ledger` | G9 | One file per message under `<ledger dir>/<yyyy-mm-dd>/`, in-memory indexes, retention pruning, and the queries polling uses. | `related(txn_id)`, `fhir(txn_id)`, `dispatch(txn_id)`, `list()`, `get(id)` |
| `beneficiary` | G10 | Pass-through to the ABDM participant service for ABHA link and delink (the policy search is a hospital's call and is not used here). | `abha_link(body)`, `abha_delink(body)` |
| `checks` | G11 | Startup checks (token, registry record, certificate match, endpoint probe) and the `/healthz` and `/readyz` answers. Reports only. | `check()`, `healthz()`, `readyz()` |

Mounted routes, and nothing else: `POST /in/<path>`, `POST /v1/<rest>`, `GET|POST /healthz`, `GET|POST /in/healthz`, `GET /readyz`.

### 3.2 `nhcx/fhir/` (F1 to F19)

Pure functions. Builders take a plain input object assembled by a service from the models (field sources come from `nhcx-plan/mapping.json`) and return a resource. Parsers take a hospital's bundle and return plain values the callback handler writes.

| File | Spec | Holds |
|---|---|---|
| `bundle` | F1 | Bundle ids per message kind, profiles, the anchor-first entry order, absolute references; wraps built answers into a Bundle and unwraps a hospital's bundle. |
| `build/eligibility_response` | F3 | In force with the wallet as benefit, lapsed with the reason, no cover; the per-item ruling for auth-requirements with rate, documents and forms. |
| `build/insurance_plan` | F5, F6 | The package master from the product and its procedures: plan, coverage clauses, benefits and limits, procedure costs, documents per phase, exclusions, sub-limits, aliases; the treatment-guideline Questionnaire per package; the empty plan. |
| `build/claim_response` | F9 | The acknowledgement (queued) and the verdict: outcome and adjudication from the case decision, per-item adjudication from the line decisions, totals, the case number as preAuthRef, process notes. |
| `build/task_answer` | F10 | The completed Task answering a cancel, reprocess, release or status, with the ClaimResponse or the status on its output. |
| `build/communication_request` | F11 | The query: one payload per thing wanted, about the Claim. |
| `build/payment_notice` | F13, F14 | The PaymentNotice with its PaymentReconciliation (one line per payment with amount, TDS, net, UTR and date); the OperationOutcome when nothing is owed. |
| `build/patient` | F15 | This payer's member as Patient in every answer. |
| `build/organization` | F17 | This payer as the insurer Organization (IRDAI registration, ROHINI id, participant code). |
| `build/coverage` | F18 | The enrolment as Coverage with the product, member id, period and class. |
| `read/eligibility_request` | F2 | Purposes, the handles (member id, subscriber id, ABHA, mobile, name), the provider, the items of an auth-requirements ask. |
| `read/plan_request` | F4 | The policy number and the asking provider. |
| `read/claim` | F8, F7, F16, F19 | The dossier: patient handles, hospital, admission, diagnoses, care team, items with modifiers and factors, documents, discharge block, query note, the prior it enhances; the answered forms; practitioners; Procedure, Condition, Encounter, Location. |
| `read/task` | F10 | Cancel, reprocess, release, status and payment acknowledgement Tasks; the status filters off the headers. |
| `read/communication` | F12 | Texts, attachments with their document codes, the references the reply hangs on. |
| `read/payment_notice` | F13 | A hospital's enquiry: the claim number, amount and status it names. |
| `codes` | F3, F5, D3, D4 | Code systems and lookups: document type codes, plan and insurance plan types, SNOMED clauses, categories, gender and relationship. |

### 3.3 `nhcx/services/` (A1 to A19)

One file per API. Each follows its spec's pseudocode (AnP): the refusals with their verbatim messages, gather data from models, build with `fhir/`, call `gateway.send` with the routing slip (sender, recipient, correlation id, workflow id and status word), record the transaction on the case, handle a failed send that names ids.

| File | Spec | Holds | Called from |
|---|---|---|---|
| `eligibility` | A1 | Find the enrolment by every handle; answer in force, lapsed or no cover; the auth-requirements ruling per item. | C2 |
| `plan` | A2 | Serve the package master by product id, UIN, alias or enrolment id; the empty plan. | C3 |
| `preauth` | A3, A10 | The queued acknowledgement at filing; the verdict on decision, with the enhancement's own workflow ids; the predetermination quote priced by rules. | C4, C6, A13 |
| `claim` | A4 | The claim acknowledgement and verdict on the claim's thread. | C5, A13 |
| `query` | A5 | The CommunicationRequest on a fresh thread, its correlation id kept on the case; resend. | A13, S3 |
| `payment_notice` | A6, A7 | The notice when a payment is raised and again with the UTR; the reconciliation answering a hospital's enquiry. | A14, C10 |
| `status` | A8 | The thread's state as the status header and a Task bundle, on the route the ask came in on. | C8 |
| `task` | A9 | Cancel accomplished; reprocess and release acknowledged, then decided on that thread. | C7, A13 |
| `polling` | A11, A12 | For each thread still waiting on the hospital (an open query, an unacknowledged notice): find the reply in the ledger and apply it through its callback handler. | S3 on open, A15 |
| `adjudicate` | A13 | Line decisions, the case decision, the wallet debit on a claim approval and its refusal when cover is short; triggers the answer. | S3 |
| `disburse` | A14 | Raise, complete (one step or later) and fail a payment; settle the case; triggers A6. | S10 |
| `exchange` | A15 | The exchange log, the forms and the FHIR preview of a case, for drivers and tests. | S3, S11, A15 route |
| `abha` | A16 | Link and delink through G10; every attempt recorded; local when no gateway. | S5 |
| `abha_m1` | A20 | Create a member's ABHA from an Aadhaar OTP, or verify one by OTP, through ABDM's ABHA service (the calls from the MCP's M1 catalogue); seals the identifiers and keeps the flow's tokens for its few minutes. | S4 |
| `participants` | A17 | Name participant codes through G4. | S12, S2 |
| `provider_driver` | A18 | The sandbox provider EMR driven by token login, for L8. Off in production. | L8 |
| `scenarios` | A19 | Member-id presets and fault injection, sandbox only. Off in production. | S3, L8 |
| `stage` | D19 | Recomputes a case's `stage`, totals and adjudication after any write. Every service and handler calls it. | services, callbacks |

### 3.4 `nhcx/callbacks/` (C1 to C11)

Called only by G8 (inbound) and by `services/polling` (a reply found in the ledger). Each handler answers `settled`, `unmatched`, `ignored`, `rejected` or `error`, and must be safe to receive the same message twice.

| File | Spec | Holds |
|---|---|---|
| `dispatch` | C1 | Classifies by the bundle, drops a redelivery by api call id (D28), requires sender, recipient and correlation id, archives the message beside its case, routes. |
| `eligibility` | C2 | Hands the question to A1 and answers at once. |
| `plan` | C3 | Hands the plan request to A2 and answers at once. |
| `preauth` | C4, C6 | Opens the case, or files an enhancement or a query resubmission on the case it comes back to; acknowledges through A3. Prices a predetermination through A10. |
| `claim` | C5 | Files the final bill, discharge and documents on the pre-authorised case; acknowledges through A4. |
| `task` | C7, C8 | Cancel, reprocess, release through A9; status through A8. |
| `communication` | C9 | Files the hospital's reply and its documents, puts the queried lines back with the adjudicator. |
| `payment` | C10, C11 | Answers a payment enquiry through A7; marks a notice acknowledged. |

### 3.5 `nhcx/models/` and `nhcx/migrations/` (D1 to D32)

- Models for D19 to D32, one per table, with the status values from each DnD as named constants rather than bare strings, and the rules the schema must hold (a line's decision and its money agree, one primary diagnosis, `net_payable = payment_amount - tds_amount`, a completed payment has a UTR) as constraints.
- D1 to D18 are the payer system's own tables. Add only the missing columns that `nhcx-plan/mapping.json` lists (for example `member.abha_no`, `payer.nhcx_participant_id`, `procedure.package_rate`, `policy.uin`), in their own modules' models.
- One migration per plan phase, created with the target's migration tool, never by editing a schema file by hand. Each migration creates the phase's tables with the keys and indexes in DnK.

### 3.6 `nhcx/screens/` and `nhcx/routes` (S1 to S12)

- One template or component per screen; the case desk (S3) is a shell that renders its parts (line items, decision, documents, exchange log, timeline) on one page.
- Screens read models and call services. They never build FHIR and never call the gateway.
- Field labels, options, chips, empty states and messages follow each S spec verbatim.
- Routes:

| Route | Screen or API |
|---|---|
| `/` | S1 |
| `/cases` | S2 |
| `/cases/:id` | S3, with its parts S3.1 to S3.6 |
| `/cases/:id/exchange`, `/cases/:id/fhir`, `/cases/:id/forms` | A15 |
| `/members`, `/subscriptions` | S4, S5 (additions to existing screens) |
| `/policies`, `/policies/new`, `/policies/edit/:id` | S6, S7 (additions) |
| `/procedures`, `/procedures/new`, `/procedures/edit/:id` | S8, S9 (additions) |
| `/payments` | S10 |
| `/fhir`, `/organisation` | S11, S12 |
| one POST per screen action | the service call the S spec names |

### 3.7 `nhcx/archive`

C1 archives every inbound envelope, and services archive every outbound one, beside the case under `<archive dir>/<case id or "unmatched">/`, with a `transactions.txt` line per message. The directory comes from settings and lives outside the repository. The exchange log table ([D27. case_exchange_message](../database/D27-case-exchange-message.md)) holds the same messages for the desk; the archive is the file copy.

## 4. Changes to existing payer modules

| Module | Spec | Change |
|---|---|---|
| Members | S4, D5 | The ABHA number, canonical 14 digits, unique; it is one of the handles a hospital's message is matched on. |
| Subscriptions | S5, D6 to D9 | Cover period, wallet balance with its ledger, ABHA link state and its events, dependants. |
| Products | S6, S7, D12 to D18 | UIN, plan and insurance plan type codes, covered procedures, SNOMED coverage clauses with benefits and limits, exclusions, sub-limits, aliases: what the InsurancePlan is rendered from. |
| Procedures | S8, S9, D10, D11 | Package rate, treatment-guideline questions, required documents per phase: what the ruling and the plan quote. |
| Payer settings | S12, D1 | NHCX participant code and processing code, IRDAI registration, ROHINI id. |
| Navigation | L3 | "Cases" and "Payments" entries on the home screen, sidebar or navbar, opening S2 and S10. |

## 5. Dependency direction

```
screens ──> services ──> fhir/build ──> (plain values only)
   │            │
   │            ├──> models
   │            └──> gateway.send ──> NHCX
   └──> models (read)

NHCX ──> gateway.receive ──> callbacks ──> fhir/read
                                  └──> models, services/stage, services (the answers sent at once)

services/polling ──> gateway.ledger ──> callbacks (same handlers)
```

Forbidden: screens to gateway, screens to fhir, fhir to models, fhir to gateway, gateway to services or models.

## 6. Configuration and secrets

| Setting | Where | Used by |
|---|---|---|
| Gateway config file path | module settings | G1 |
| Environment (`sandbox` or `production`) | gateway config | G2 |
| Participant code, processing code, client id | gateway config | G2, G3 |
| Client secret | environment variable referenced as `${NAME}` | G3 |
| Private key of the registered certificate | file outside the repo, referenced as `@path` | G6 |
| Public URL registered as `endpoint_url` | gateway config | G2, G11 |
| Ledger directory and retention days | gateway config | G9 |
| Archive directory | module settings | C1 |
| Rules file for predetermination pricing | module settings | A10 |
| Sandbox provider EMR URL and the scenario presets | module settings, sandbox only | A18, A19 |
| Whether to push payment notices | module settings | A6 |

## 7. Background work

- Token refresh, every minute (G1, G3).
- Ledger pruning, hourly (G1, G9).
- A delayed answer under a sandbox fault scenario runs off the request (A19) [SANDBOX](PAYERS.md#markers).
- No polling job: polling runs when a case is opened (S3) or its exchange log is read (A15). A target that wants background polling adds a job that calls `services/polling` per waiting case; it must use the same handlers.

## 8. Errors and logging

- Services return the spec's refusal messages to the screen as a flash, never a server error.
- A decision already recorded stands whatever the gateway does; the case keeps the correlation id so the answer can be sent again.
- Callback handlers never raise for a message they cannot use; they answer `rejected` or `ignored`. Only an unexpected fault is `error`, which makes NHCX redeliver. A message that can never be filed (no enrolment matches) is a permanent refusal, not an `error`.
- Log with the target's logger, always with the case id, the hospital's claim number, the correlation id and the ledger id, so any line can be traced to G9 and the archive.

## 9. Tests

```
tests/nhcx/
  fixtures/
    keys/                  a test key pair for G6
    registry/              participant records, certificates, an ABHA link reply
    bundles/               hospital bundles from the knowledge source's examples, with their source noted
    seed/                  a member, an enrolment in force, a lapsed one, a product with procedures
  dry_run/                 L7, no network
    gateway/               G5 to G9 and G11
    fhir/                  one test file per builder and parser
    services/              one per A, every refusal and the send failure cases
    callbacks/             one per C, with a redelivery each
    screens/               one per S
    flow                   the whole case against the fake NHCX
  e2e/                     L8, NHCX sandbox
    setup                  G11 checks
    scenarios/             T3 to T18, one each, driven by both runners
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
| A1 to A17 | `nhcx/services` (A15 also in `nhcx/routes`) |
| A18, A19 | `nhcx/services`, sandbox only, off in production |
| C1 to C11 | `nhcx/callbacks` |
| D1 to D18 | the payer system's own models, extended by `nhcx/migrations` |
| D19 to D32 | `nhcx/models`, created by `nhcx/migrations` |
| S1 to S3, S10 | `nhcx/screens`, `nhcx/routes` |
| S4 to S9, S11, S12 | the existing member, subscription, product, procedure and settings screens, extended |

## 12. Build order

Matches the plan phases in [L3](../steps/L3-integration-planning.md). Each phase adds its migrations, FHIR builders and parsers, services, callbacks, screens and dry-run tests together, so it can be exercised before the next starts.

| Phase | Adds |
|---|---|
| 1 Foundation | `gateway/`, `callbacks/dispatch`, `archive`, settings, the inbound route |
| 2 Data | `models/` and migrations for D19, D27, D28, D32; the column additions to D1, D5, D6, D10 to D12 |
| 3 Eligibility and plan | `services/eligibility`, `services/plan`, `services/abha`, `services/participants`, `callbacks/eligibility`, `callbacks/plan`, F2 to F6, F15 to F18, S4 to S9, S11, S12 |
| 4 Pre-authorisation | `services/preauth`, `services/status`, `services/task`, `services/adjudicate`, `callbacks/preauth`, `callbacks/task`, F7 to F10, F19, D20 to D26, D29, S1 to S3 |
| 5 Queries | `services/query`, `callbacks/communication`, F11, F12 |
| 6 Claim | `services/claim`, the claim branch of `callbacks/preauth` as `callbacks/claim`, the wallet debit in `services/adjudicate`, the reprocess leg of `services/task` |
| 7 Payment | `services/payment_notice`, `services/disburse`, `callbacks/payment`, F13, F14, D30, S10 |
| 8 Navigation | the "Cases" and "Payments" entries |
