---
name: nhcx-payer-full
description: >-
  Build India's NHCX (National Health Claims Exchange) payer-side claims processing into an existing insurer, TPA or scheme system, end to end: answering coverage eligibility and insurance plan requests, filing pre-authorisations and claims as cases, adjudicating them on a desk, querying the hospital, cancellations, reprocess and status, payment notices and their acknowledgement, with the NHCX gateway (JWE, x-hcx headers, ABDM session tokens, registry, callbacks) embedded in the application. Use when adding NHCX cashless claims to a payer system as a whole, or when unsure which part of NHCX is needed.
metadata:
  version: "1.0.1"
---

**Version 1.0.1**, built 2026-10-09, checked against NHA's NHCX package 1.0.0.

# READ FIRST: CORE
Before anything else, read [references/CORE.md](references/CORE.md) and keep it in mind for the whole task. Its **Instructions** are binding: follow them strictly in every step and every file, and re-read them at the start of each step (L1 to L8). Its **Confusions** settle what easily mixed-up terms mean; when a word is ambiguous, CORE.md decides. It also holds the base URLs and, for every exchange, the route it arrives on, the bundle, the callback that takes it in, the answer and the workflow id the answer travels under.

# WHICH SIDE
This folder is the **payer side** of the skill above it: [../SKILL.md](../SKILL.md) is the provider side, for a hospital's HMIS. Use this folder when L1 discovery found the target is an insurer, TPA or scheme system, the participant that answers eligibility, files and decides pre-authorisations and claims, and pays. Every link below stays inside this folder; nothing at the root applies, and its ids are not these. If the target turns out to be a hospital system after all, log a `corrected` entry and go back to [../SKILL.md](../SKILL.md).
# GOAL
Add NHCX payer-side claims processing to the target payer system, from the eligibility answer to the payment notice, with the NHCX gateway running inside the application.

This skill holds only the specs this goal needs; the SCOPE section lists them. Specs it names but does not hold are marked with the skill that has them.

# REQUIREMENTS
- **The target payer system source**: an insurer's, TPA's or scheme's claims platform, with its build, test and migration commands working.
- **NHCX participant credentials** for the payer: participant code, ABDM client id and client secret, and the private key of the encryption certificate registered for that code. Where a separate participant processes the payer's claims, its code too.
- **A public URL** NHCX can reach, registered as the participant's `endpoint_url`, routed to the application's inbound path (`/in/<path>` or `/v1/<path>`). Every hospital's message arrives there.
- **A knowledge source**: the nhcx-docs MCP server, or network access to download the NHCX package (see KNOWLEDGE SOURCE).
- For end-to-end tests: sandbox credentials, the sandbox provider EMR that sends to this payer (signed in to by token login), and members seeded in this payer's registry for it to send about.

# KNOWLEDGE SOURCE
NHCX facts (API paths and headers, FHIR profiles and example bundles, codes, workflow ids, error codes, go-live rules) come from one knowledge source, chosen at the start of L1 and recorded in `nhcx-plan/knowledge.json`. Details: [references/KNOWLEDGE.md](references/KNOWLEDGE.md).

1. **nhcx-docs MCP.** If the `nhcx-docs` MCP server is connected (`catalogue_info` answers), use it: `search_docs`, `get_operation`, `get_fhir_profile`, `get_fhir_example`, `validate_fhir`, `validate_request`, `decode_error`.
2. **GitHub package.** Otherwise download the latest release zip from [github.com/nha-in/nhcx-package/releases](https://github.com/nha-in/nhcx-package/releases) (`nhcx-package-v<version>.zip`), keep it as `nhcx-plan/knowledge/nhcx-package-v<version>.zip`, extract it to `nhcx-plan/knowledge/nhcx-package/`, and check it against its `MANIFEST`.

On the protocol the knowledge source wins over these specs; on what the application does, the specs win. Statements that are not the protocol are marked [REF](references/PAYERS.md#markers) (a reference-implementation choice), [PAYER](references/PAYERS.md#markers) (depends on the scheme dialect this payer speaks) or [SANDBOX](references/PAYERS.md#markers) (seen only in the sandbox); every dialect-specific value is in [references/PAYERS.md](references/PAYERS.md). Its ids (NHA use cases such as `C5`) are not this skill's ids: write them as `nha:C5`.

# STEPS
Follow [steps/INDEX.md](steps/INDEX.md) in order. Each step writes one file under `nhcx-plan/` in the target repository, and every sub-step and file change is logged in `nhcx-plan/progress.json` and `nhcx-plan/progress.md` ([steps/LOG.md](steps/LOG.md)). At the end of every prompt, whatever it did, run the report builder to rebuild `nhcx-plan/report.html`: every plan file (progress, log, discovery, mapping, plan, code, validation, dry-run and end-to-end results) on its own tab of one self-contained page, errors first, with a refresh button; `nhcx-plan/make-report.sh` and `make-report.bat` rebuild it every 10 seconds ([steps/LOG.md](steps/LOG.md#logh-reporthtml)).

1. [L1 Discovery](steps/L1-discovery.md): the knowledge source, the target's technology, and every spec item in SCOPE found, partial or missing, with file and lines.
2. [L2 Mapping](steps/L2-mapping.md): target fields to database columns and FHIR elements.
3. [L3 Integration Planning](steps/L3-integration-planning.md): phases, steps and sub-steps for this target, in the build order of the [SCAFFOLDING](references/SCAFFOLDING.md), including the "Cases" and "Payments" entries on the payer system's home screen, sidebar or navbar.
4. [L4 Code Planning](steps/L4-code-planning.md): files, functions and order, laid out by mapping the [SCAFFOLDING](references/SCAFFOLDING.md) onto the target's conventions.
5. [L5 Write Code](steps/L5-write-code.md): file by file, recorded in `nhcx-plan/code.json`, keeping the scaffolding's dependency rules.
6. [L6 Validate Code](steps/L6-validate-code.md): each file against its specs.
7. [L7 Dry-run Tests](steps/L7-dry-run-tests.md): no network; fakes for NHCX and the registry; hospital messages fed straight to the door.
8. [L8 End-to-end Tests](steps/L8-e2e-tests.md): against the NHCX sandbox, the T tests in [references/TESTS.md](references/TESTS.md), each run through the screens (GUI) and from the command line (CLI), with the sandbox provider EMR sending the hospital's side.

# SCAFFOLDING
[references/SCAFFOLDING.md](references/SCAFFOLDING.md) is the shape the code takes in the target payer system. Read it before L3 and keep it open through L5.

- **One NHCX module** (`nhcx/`) holding `gateway/` (G, in-process), `fhir/` (F, pure builders and parsers), `services/` (A), `callbacks/` (C), `models/` and `migrations/` (D), `screens/` and `routes` (S), and the message `archive`.
- **Existing payer modules** change only for the fields NHCX needs: member ABHA number (D5), product UIN and plan type codes (D12), procedure package rate, treatment-guideline questions and document rules per phase (D10, D11), the payer's own participant and processing codes (D1), and the "Cases" and "Payments" navigation entries.
- **Dependency rules:** screens call services and read models; only services and callbacks write case tables; FHIR builders never touch the database or the gateway; the gateway knows nothing about cases; a reply found by polling is applied by the same callback handler.
- **Outside the repository:** the gateway config, client secret, private key, ledger and archive directories.
- **Tests** under `tests/nhcx/` (dry-run and end-to-end), and **plan files** under `nhcx-plan/`.
- **Build order** in phases, from the gateway foundation to the navigation entries; L3 plans in that order and leaves out phases whose specs are not in SCOPE.

L4 maps these placeholder names onto the target's own conventions (a Django app, a Spring module, a Node package); the split between parts and the dependency direction do not change.

# SCOPE
The specs this skill holds:

- **Screens** (12): [S1](screens/S1-overview.md), [S2](screens/S2-cases.md), [S3](screens/S3-case-desk.md), [S4](screens/S4-members.md), [S5](screens/S5-subscriptions.md), [S6](screens/S6-policies.md), [S7](screens/S7-policy-configurator.md), [S8](screens/S8-procedures.md), [S9](screens/S9-procedure-configurator.md), [S10](screens/S10-payments.md), [S11](screens/S11-fhir-preview.md), [S12](screens/S12-organisation.md)
- **APIs** (20): [A1](apis/A1-eligibility-answer.md), [A2](apis/A2-insurance-plan-answer.md), [A3](apis/A3-preauth-answer.md), [A4](apis/A4-claim-answer.md), [A5](apis/A5-query-request.md), [A6](apis/A6-payment-notice.md), [A7](apis/A7-payment-enquiry-answer.md), [A8](apis/A8-status-answer.md), [A9](apis/A9-task-answer.md), [A10](apis/A10-predetermination-quote.md), [A11](apis/A11-txn-related.md), [A12](apis/A12-txn-fhir.md), [A13](apis/A13-adjudicate.md), [A14](apis/A14-disburse.md), [A15](apis/A15-case-exchange.md), [A16](apis/A16-abha-policy-link.md), [A17](apis/A17-participant-lookup.md), [A18](apis/A18-provider-driver.md), [A19](apis/A19-sandbox-scenarios.md), [A20](apis/A20-abha-m1.md)
- **Callbacks** (11): [C1](callbacks/C1-callback-door.md), [C2](callbacks/C2-coverage-eligibility-check.md), [C3](callbacks/C3-insurance-plan-request.md), [C4](callbacks/C4-preauth-submit.md), [C5](callbacks/C5-claim-submit.md), [C6](callbacks/C6-predetermination.md), [C7](callbacks/C7-task-submit.md), [C8](callbacks/C8-status-enquiry.md), [C9](callbacks/C9-communication.md), [C10](callbacks/C10-payment-enquiry.md), [C11](callbacks/C11-payment-acknowledgement.md)
- **FHIR** (19): [F1](fhir/F1-bundle.md), [F2](fhir/F2-coverage-eligibility-request.md), [F3](fhir/F3-coverage-eligibility-response.md), [F4](fhir/F4-task-insuranceplan.md), [F5](fhir/F5-insuranceplan.md), [F6](fhir/F6-questionnaire.md), [F7](fhir/F7-questionnaireresponse.md), [F8](fhir/F8-claim.md), [F9](fhir/F9-claimresponse.md), [F10](fhir/F10-task-claim-actions.md), [F11](fhir/F11-communicationrequest.md), [F12](fhir/F12-communication.md), [F13](fhir/F13-paymentnotice.md), [F14](fhir/F14-paymentreconciliation.md), [F15](fhir/F15-patient.md), [F16](fhir/F16-practitioner.md), [F17](fhir/F17-organization.md), [F18](fhir/F18-coverage.md), [F19](fhir/F19-other-resources.md)
- **Database** (32): [D1](database/D1-payer.md), [D2](database/D2-staff.md), [D3](database/D3-document-type.md), [D4](database/D4-terminology-code.md), [D5](database/D5-member.md), [D6](database/D6-subscription.md), [D7](database/D7-subscription-family-member.md), [D8](database/D8-wallet-entry.md), [D9](database/D9-abha-link-event.md), [D10](database/D10-procedure-rule.md), [D11](database/D11-procedure-rule-doc.md), [D12](database/D12-policy.md), [D13](database/D13-policy-procedure.md), [D14](database/D14-policy-coverage-clause.md), [D15](database/D15-policy-clause-benefit.md), [D16](database/D16-policy-alias.md), [D17](database/D17-policy-exclusion.md), [D18](database/D18-policy-sub-limit.md), [D19](database/D19-case.md), [D20](database/D20-case-diagnosis.md), [D21](database/D21-case-procedure.md), [D22](database/D22-case-doctor.md), [D23](database/D23-case-document.md), [D24](database/D24-case-document-file.md), [D25](database/D25-case-line-item.md), [D26](database/D26-case-timeline.md), [D27](database/D27-case-exchange-message.md), [D28](database/D28-nhcx-delivery.md), [D29](database/D29-predetermination-quote.md), [D30](database/D30-payment.md), [D31](database/D31-audit-log.md), [D32](database/D32-id-sequence.md)
- **Gateway** (11): [G1](gateway/G1-embedding.md), [G2](gateway/G2-configuration.md), [G3](gateway/G3-session-token.md), [G4](gateway/G4-registry.md), [G5](gateway/G5-protocol-headers.md), [G6](gateway/G6-encryption.md), [G7](gateway/G7-send.md), [G8](gateway/G8-receive.md), [G9](gateway/G9-ledger.md), [G10](gateway/G10-beneficiary-registry.md), [G11](gateway/G11-startup-checks.md)
- **Tests** (18): [T1](tests/T1-test-configuration.md), [T2](tests/T2-test-runners.md), [T3](tests/T3-eligibility-answered.md), [T4](tests/T4-auth-requirements-ruled.md), [T5](tests/T5-insurance-plan-served.md), [T6](tests/T6-preauth-approved.md), [T7](tests/T7-preauth-rejected.md), [T8](tests/T8-preauth-queried.md), [T9](tests/T9-enhancement-approved.md), [T10](tests/T10-preauth-cancelled.md), [T11](tests/T11-predetermination-quoted.md), [T12](tests/T12-claim-approved.md), [T13](tests/T13-claim-lama-death.md), [T14](tests/T14-reprocess-and-release.md), [T15](tests/T15-payment-noticed.md), [T16](tests/T16-payment-enquiry-answered.md), [T17](tests/T17-status-answered.md), [T18](tests/T18-redelivery-ignored.md)

Other skills built from the same source:

- **nhcx-coverage/payer**: coverage eligibility answers, the authorisation-requirements ruling and the insurance plan.
- **nhcx-preauth/payer**: pre-authorisation: filing, adjudication, enhancement, cancel, predetermination and status.
- **nhcx-claim/payer**: claim filing, its verdict, reprocess and balance release.
- **nhcx-communication/payer**: queries to the hospital and the replies to them.
- **nhcx-payment/payer**: disbursement, payment notices, their acknowledgement and payment enquiries.

# VERSION
This is nhcx-payer-full version 1.0.1, built on 2026-10-09. Its protocol tables (workflow ids, statuses, base URLs) were checked against NHA's NHCX package 1.0.0 ([github.com/nha-in/nhcx-package](https://github.com/nha-in/nhcx-package)).

- Record it when the work starts: `nhcx-plan/knowledge.json` and the `target` of `nhcx-plan/progress.json` carry `skill` and `skill_version`, and the header of `nhcx-plan/report.html` shows them.
- If a later prompt runs with a different version of this skill than the one recorded, say so to the user before continuing, log it as a `corrected` entry naming both versions, and re-check the steps already done against the specs that changed.
- A knowledge source newer than 1.0.0 wins on the protocol, as KNOWLEDGE SOURCE says; note the difference in `knowledge.json`.

# REFERENCES
- [references/CORE.md](references/CORE.md): base URLs, and every exchange from the payer's side with its route, bundles, callback, answer and workflow id, on one page.
- [references/KNOWLEDGE.md](references/KNOWLEDGE.md): the NHCX knowledge source, MCP or GitHub package, and which lookup answers which question.
- [references/SCREENS.md](references/SCREENS.md): every screen in scope, its route and what it does.
- [references/API.md](references/API.md): every API call in scope and what it does.
- [references/CALLBACK.md](references/CALLBACK.md): every NHCX callback in scope and what it does.
- [references/GATEWAY.md](references/GATEWAY.md): every part of the in-process NHCX gateway and what it does.
- [references/FHIR.md](references/FHIR.md): every FHIR resource in scope, sent or read, and what it is.
- [references/DATABASE.md](references/DATABASE.md): every table in scope, what one row is, and which screens, APIs, callbacks and FHIR resources use it.
- [references/PAYERS.md](references/PAYERS.md): the scheme dialects this payer may speak, the workflow ids of its sends, and what the [REF](references/PAYERS.md#markers), [PAYER](references/PAYERS.md#markers) and [SANDBOX](references/PAYERS.md#markers) markers mean.
- [references/OPERATIONS.md](references/OPERATIONS.md): production cutover, and running the application as more than one instance.
- [references/TESTS.md](references/TESTS.md): every end-to-end test in scope, each run through the screens and from the command line, with the sandbox provider EMR on the hospital's side.
- [references/READSETS.md](references/READSETS.md): for each screen, API, callback and gateway part, the other specs to read before implementing it.
- [references/SCAFFOLDING.md](references/SCAFFOLDING.md): the module layout in the target, what each part holds and where each spec lands.

# OUTPUT
In the target repository:
- **Code** in the NHCX module and the changed payer modules, as laid out in SCAFFOLDING.
- **Tests** under `tests/nhcx/`: dry-run (L7) and end-to-end (L8), the end-to-end ones with a GUI runner and a CLI runner (`nhcx-payer-e2e`).
- **Plan files** under `nhcx-plan/`: `knowledge.json`, `discovery.json`, `mapping.json`, `plan.json`, `code-plan.json`, `code.json`, `validation.json`, `dry-run.json`, `e2e.json`, the log `progress.json` with `progress.md`, and `report.html`, rebuilt at the end of every prompt by the report builder (`report.py` or the target language's equivalent) with its `make-report.sh` and `make-report.bat` beside it.
