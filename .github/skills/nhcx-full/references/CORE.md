# Core

The NHCX facts every task needs, on one page: the addresses per environment, the calls that are not exchanges, and for each exchange the route, the bundle sent, the workflow id it travels under, the callback that answers it and the bundle that comes back. The knowledge source ([KNOWLEDGE.md](KNOWLEDGE.md)) is the authority behind every value here (`baseurl.yaml`, `workflow.yaml` and `usecases.yaml` in the package; `search_docs` and `get_operation` on the MCP). Check a value there before relying on it, and when they differ, the knowledge source wins.

NHA use-case codes are written `nha:B3`; bare ids (A4, C5, F8) are this skill's specs.

## Instructions

Follow these strictly, in every step and every file. When a spec seems to say otherwise, stop and resolve it against this list and the knowledge source; record the resolution under `corrections` in the current plan file.

1. **The gateway is inside the application.** Call it as functions ([G7. Send](../gateway/G7-send.md) `gateway.send`, [G9. Ledger](../gateway/G9-ledger.md) `ledger.*`, [G10. Beneficiary Registry](../gateway/G10-beneficiary-registry.md), [G3. Session Token](../gateway/G3-session-token.md)). Never call a separate gateway service over HTTP, and never mount any gateway route except the inbound route and the health checks ([G1. Embedding](../gateway/G1-embedding.md)).
2. **NHCX facts come from the knowledge source, never from memory.** Paths, headers, profiles, codes and workflow ids are checked there ([KNOWLEDGE.md](KNOWLEDGE.md)). On the protocol it wins over every spec; on what the application does, the specs win.
3. **Nothing payer- or environment-specific is hard-coded.** Participant codes, base URLs, workflow ids and scheme rules come from configuration or the payer adapter ([PAYERS.md](PAYERS.md)). Production URLs are set explicitly.
4. **One way out, one way in.** Every message leaves through `gateway.send`. Every message arrives through [G8. Receive](../gateway/G8-receive.md) and `C1.receive(envelope, delivery)`, which routes it to one callback. A reply found by polling (A10 to A13) is applied by that same callback handler, never by separate code.
5. **Replies are matched by `x-hcx-correlation_id`** (a payment notice by the claim number it carries), never by workflow id, route or timing.
6. **Every callback is safe to receive twice.** It answers `settled`, `unmatched`, `ignored` or `rejected` (NHCX gets 202, no redelivery) or `error` (NHCX gets 502 and redelivers). Only an unexpected fault is `error`.
7. **A failed send that names its ids keeps them.** Store the ids from the send result on the leg and mark it failed; the message may still have reached NHCX.
8. **Keep the layers.** Screens call services and read models. Only services (A) and callbacks (C) write claim tables. FHIR builders and parsers never touch the database or the gateway ([SCAFFOLDING.md](SCAFFOLDING.md)).
9. **No secrets in the repository.** Client secret, private key and payer desk credentials come from configuration or the environment.
10. **Treat markers as defined.** [REF](PAYERS.md#markers) may be chosen differently (record it); [PAYER](PAYERS.md#markers) values come from the payer adapter; [SANDBOX](PAYERS.md#markers) behaviour is not relied on in production.
11. **Work the steps in order and log them.** L1 to L8, one plan file each, every sub-step and file change in `nhcx-plan/progress.json` ([LOG.md](../steps/LOG.md)). Re-read this page at the start of each step.
12. **End every prompt by rebuilding the report.** The last action of every prompt, whatever it did, is to run the report builder (`nhcx-plan/report.py` or the target language's equivalent), which rewrites `nhcx-plan/report.html` from the plan files: every plan file on its own tab, errors first, with a refresh button; `make-report.sh` and `make-report.bat` rebuild it every 10 seconds for anyone watching ([LOG.md](../steps/LOG.md#logh-reporthtml)).

## Confusions

Terms and behaviours that are easy to mix up, with the reading this skill uses.

| Easily confused | Correct reading |
|---|---|
| This skill's ids and NHA's use-case codes | `A1` is our policy search; `nha:A1` is NHA's participant list. `C5` is our pre-auth reply callback; `nha:C5` is NHA's "respond to pre-authorisation" (a payer use case). Always prefix NHA codes with `nha:`. |
| "Gateway" | Here, the in-process module G. NHA's documents also call the NHCX exchange itself "the gateway", and ABDM has its own session gateway. Write "the exchange" for NHCX and "sessions" for ABDM. |
| Workflow id, correlation id, api call id, request id, ledger id | Workflow id (`x-hcx-workflow_id`): which step of the claim flow this is. Correlation id: the thread, kept by every reply. API call id: one message, kept across NHCX's redeliveries (the dedupe key). Request id: one request. Ledger id (`txn_id`): our own record in [G9. Ledger](../gateway/G9-ledger.md), never sent to NHCX. |
| Payer id and processing id | The policy search returns both. The **processing id** is the participant that handles the policy on NHCX (for PMJAY, the state health agency) and is the recipient of every message; the **payer id** only chooses the payer adapter. They are often equal in the sandbox, which hides the mistake. |
| `x-hcx-status` on a query answer | A query answer goes on a request route (`.../submit`) but is a response: `response.complete`, not `request.initiated`. |
| Our workflow ids and the payer's | The table in section 4 is what we send. The payer's replies carry their own (PMJAY: 20, 21, 25, 26 and others [PAYER](PAYERS.md#markers)); nothing routes on them. |
| An id we pass and the id that goes out | Correlation, request and api call ids that are not plain UUIDs are silently replaced when sending ([G5. Protocol Headers](../gateway/G5-protocol-headers.md)). Store the ids from the send result, never the ones passed in. |
| NHCX's 202 on a send | The exchange accepted the message for delivery. It says nothing about the payer's decision, which arrives later on the callback. |
| `outcome: complete` in a ClaimResponse | Not an approval: it comes back for a rejection too [PAYER](PAYERS.md#markers). The decision is read from the adjudication ([F9. ClaimResponse](../fhir/F9-claimresponse.md)). |
| Request and `on_` routes for payer-started exchanges | For payment notices and payer communications the payer calls `.../request` and we answer on `.../on_request`, the opposite way round from every exchange we start. |
| Two coverage replies on one route | The eligibility verdict ([C2. Coverage Eligibility Verdict](../callbacks/C2-coverage-eligibility-on-check.md)) and the authorisation-requirements ruling ([C3. Authorisation Requirements Ruling](../callbacks/C3-auth-requirements-on-check.md)) both arrive on `v1/coverageeligibility/on_check`; the correlation id decides which. Likewise `v1/task/on_submit` carries the cancel answer ([C7. Cancel Reply](../callbacks/C7-cancel-on-submit.md)) and enquiry answers ([C8. Enquiry Reply](../callbacks/C8-enquiry-on-submit.md)). |
| A `ProtocolResponse` | A refusal of our message by NHCX or the payer, not an answer to it. It arrives in place of a bundle, on the same thread. |
| The redelivery flag | A hint, not a reason to skip: a first delivery that failed is also on the ledger. Handlers dedupe by the api call id stored on the leg. |
| Query mode | PMJAY asks inside its ClaimResponse and takes the answer as a fresh submit ([A4. Pre-auth Submit](../apis/A4-preauth-submit.md), [A5. Claim Submit](../apis/A5-claim-submit.md)); other payers ask with a CommunicationRequest and take a Communication ([C9. Payer Communication](../callbacks/C9-communication-request.md), [A7. Communication Reply](../apis/A7-communication-on-request.md)) [PAYER](PAYERS.md#markers). A CommunicationRequest from PMJAY is a notification. |
| Claim number, claim reference, pre-auth reference | The claim number is our case number, sent as `Claim.identifier` (`claim_ref` keeps the one a leg went under). The pre-auth reference (`preAuthRef`) is the payer's number for its approval. |
| Member id, policy code, product id | The member id identifies the beneficiary on the policy. The policy code identifies the policy or plan; some registries return only a product id, used as the policy code then [REF](PAYERS.md#markers). |
| ABHA number and ABHA address | The 14-digit number (what links a claim to an admission) and the `name@abdm` style address; they are different fields ([D3. patient](../database/D3-patient.md)). |
| HFR id and participant code | The HFR id identifies the facility in the health facility registry (the provider Organization's identifier, [F17. Organization](../fhir/F17-organization.md)); the participant code (`...@hcx`) is its address on NHCX. |
| Sandbox participant codes | Examples only ([PAYERS.md](PAYERS.md)). Every code comes from configuration. |
| Predetermination and status routes | NHA lists `v1/predetermination/submit` and `v1/status`; the reference implementation sends predetermination on the pre-auth route and status as a Task [REF](PAYERS.md#markers). Check which the payer accepts. |
| Step ids, section letters, log ids | `L1` to `L8` are steps; `S1L` is the LAYOUT section of S1; `LOG-0042` is a progress log entry; `X1` to `X10` are the end-to-end exchanges of L8. |
| A9 | There is no A9: the inbound door it once described became the callbacks, C1 to C10. |
| Session token, user token, X-token, T-token | The **session token** is the application's own, minted from its client id ([G3. Session Token](../gateway/G3-session-token.md)) and sent as `Authorization: Bearer` on every ABDM call and as `bearer_auth` on the exchange. The **user token** is the beneficiary's, from a biometric verification ([A18. Biometric Authentication](../apis/A18-biometric-authentication.md)), thirty minutes, carried on the request headers under PMJAY. The **X-token** and **T-token** are ABHA M1's ([A19. ABHA Create and Verify (ABDM M1)](../apis/A19-abha-m1.md)): the X-token opens the person's ABHA profile, the T-token only chooses the account after a mobile login. None of the three is ever sent in another's place. |
| Biometric authentication and the consent questionnaire | A live capture ([A18. Biometric Authentication](../apis/A18-biometric-authentication.md), on the Verification tab [S18. Beneficiary Verification](../screens/S18-beneficiary-verification.md)) is optional for any payer and its token rides on the sends whenever the desk holds one. Under PMJAY it is required, and where none is possible the scheme's Authentication Consent and Discharge Consent forms are answered in the bundle instead ([F7. QuestionnaireResponse](../fhir/F7-questionnaireresponse.md)): one or the other goes, never both, and a cyclic case takes only the capture. The stage is the stay's: Preauth while admitted, Discharge once discharged. |

## 1. Environments and base URLs

| Service | Used for | Sandbox | Production |
|---|---|---|---|
| ABDM sessions | the session token every call carries ([G3](../gateway/G3-session-token.md)), `POST /api/hiecm/gateway/v3/sessions` | `https://dev.abdm.gov.in` | `https://apis.abdm.gov.in` (published by ABDM; confirm in the onboarding letter) |
| NHCX exchange | every exchange, under `/v1` ([G7](../gateway/G7-send.md)) | `https://apisbx.abdm.gov.in/hcx` | shared by NHA after sandbox exit |
| Participant service (registry) | participant records, certificates, policies ([G4](../gateway/G4-registry.md), [G10](../gateway/G10-beneficiary-registry.md)) | `https://apisbx.abdm.gov.in/pmjay/sbxhcx/participanthcxservice` | `https://apisprod.nha.gov.in/pmjay/hcx/participanthcxservice` |
| PMJAY payer service, role lookup | sandbox adjudication ([A14](../apis/A14-adjudicator-user-role.md)) [PAYER](PAYERS.md#markers) | `https://apisbx.abdm.gov.in` + `/pmjay/sbxhcx/nhcxpayerservice/v1/get/user-role` | not published |
| PMJAY payer service, act on a case | sandbox adjudication ([A15](../apis/A15-adjudicator-process-case.md)) [PAYER](PAYERS.md#markers) | `https://apisbeta.nha.gov.in` + `/pmjay/hcx/nhcxpayerservice/wrapper/process/case` | not published |
| NHCX portal | the portal and its published API specifications | `https://hcxsbx.abdm.gov.in` | not published |

| Setting | Sandbox | Production |
|---|---|---|
| `X-CM-ID` on the session call | `sbx` | `abdm` |
| This application's inbound route | the public URL registered as the participant's `endpoint_url`, routed to `/in/<path>` or `/v1/<path>` ([G8](../gateway/G8-receive.md)) | the same, on HTTPS (TLS 1.2 or newer), a domain name hosted in India, no IP address and no port; NHCX's source addresses allowed in ([OPERATIONS.md](OPERATIONS.md)) |

The gateway's production table ([G2. Configuration and Participants](../gateway/G2-configuration.md)) is this table. A host swap of the sandbox names (`apisbx` to `apis`, `sbxhcx` to `hcx`, `dev` to `live`) is wrong and must not be used. Set every production URL explicitly in configuration from the onboarding letter; the NHCX exchange base has no published production address.

## 2. Calls that are not exchanges

Plain JSON with the session token: no JWE, no protocol headers, no ledger row.

| NHA use case | Call | Does | This skill |
|---|---|---|---|
| nha:A4 | sessions (above) | trade client id and secret for the session token | [G3](../gateway/G3-session-token.md) |
| nha:A3 | registry `/fetch/certs` | a participant's encryption certificate | [G4](../gateway/G4-registry.md) |
| nha:A1 | registry `/fetch/participants/list`, `/participant/search` | participant records | [G4](../gateway/G4-registry.md) |
| nha:A2 | registry `/participant/get/policies` | a beneficiary's policies by member id, mobile or ABHA number | [A1](../apis/A1-policy-search.md), [G10](../gateway/G10-beneficiary-registry.md) |
| nha:C1, nha:C2 | registry `/participant/link/abha/policy`, `/participant/delink/abha/policy` | link or unlink an ABHA number and a policy | [G10](../gateway/G10-beneficiary-registry.md) |
| nha:D2 | ABDM biometric service: `auth/init`, `auth/verify`, `auth/refresh/token` on one host, `faceauth/init`, `capture/pid`, `v2/auth/verify` on another | the beneficiary's fingerprint, iris or face authentication against their ABHA; the user token that rides on the eligibility check, pre-authorisation and claim, optional for any payer and required by PMJAY | [A18](../apis/A18-biometric-authentication.md), defined in full; the tab is [S18](../screens/S18-beneficiary-verification.md) |
| ABDM M1 | ABHA service `/abha/api/v3/...` | create an ABHA from an Aadhaar OTP, or verify an existing one by OTP, and fill the patient file from the profile | [A19](../apis/A19-abha-m1.md); the calls themselves are read from the MCP's M1 catalogue |

## 3. Protocol defaults

- Every exchange is one FHIR Bundle ([F1. Bundle](../fhir/F1-bundle.md)) encrypted as a compact JWE to the recipient's certificate ([G6. Encryption](../gateway/G6-encryption.md)), with the `x-hcx-*` headers in the protected header ([G5. Protocol Headers](../gateway/G5-protocol-headers.md)).
- `x-hcx-status`: `request.initiated` on a request we start, `response.complete` on an `on_` path **and on a query answer** (workflow 19, 131, 151, 161), even though a query answer goes on `v1/preauth/submit` or `v1/claim/submit`. The sending API sets it; the gateway's path default is only a fallback ([G5. Protocol Headers](../gateway/G5-protocol-headers.md), [PAYERS.md](PAYERS.md)).
- `x-hcx-recipient_code`: the policy's **processing id** from the policy search, not its payer id (NHCX-1003 otherwise); the payer id only picks the payer adapter ([A1. Policy Search](../apis/A1-policy-search.md), [D9. claim](../database/D9-claim.md)).
- A reply keeps the request's `x-hcx-correlation_id`; callbacks match on it ([C1. Callback Door](../callbacks/C1-callback-door.md)).
- A refusal comes back as a plain `ProtocolResponse` instead of a bundle, on the same thread ([C1. Callback Door](../callbacks/C1-callback-door.md), [A13. Transaction List](../apis/A13-txn-list.md)).
- Workflow ids below are the provider's sends. The payer's replies carry their own; callbacks never route on them.

## 4. Exchanges

"Workflow id" gives the `pmjay` value first and the `generic` value when it differs; [PAYERS.md](PAYERS.md) has every adapter. Every send is made through `gateway.send` ([G7. Send](../gateway/G7-send.md)); every reply is taken in by [G8. Receive](../gateway/G8-receive.md) and routed by [C1. Callback Door](../callbacks/C1-callback-door.md).

### Eligibility and plan

| Exchange | NHA | Our API | Send route | Bundle sent | Workflow id | Reply route | Bundle back | Callback |
|---|---|---|---|---|---|---|---|---|
| Coverage eligibility (validation, benefits, discovery) | nha:B1, nha:D3 | [A2](../apis/A2-coverage-eligibility-check.md) | `v1/coverageeligibility/check` | [F2](../fhir/F2-coverage-eligibility-request.md) with [F15](../fhir/F15-patient.md) to [F18](../fhir/F18-coverage.md) | 11 (NHA's sample) by default; a setting sends the case number instead [REF](PAYERS.md#markers) | `v1/coverageeligibility/on_check` | [F3](../fhir/F3-coverage-eligibility-response.md) | [C2](../callbacks/C2-coverage-eligibility-on-check.md) |
| Authorisation requirements on the chosen lines | nha:B1 | [A2](../apis/A2-coverage-eligibility-check.md) (purpose `auth-requirements`) | `v1/coverageeligibility/check` | [F2](../fhir/F2-coverage-eligibility-request.md) with items | as eligibility: 11 by default, the case number under the setting [REF](PAYERS.md#markers) | `v1/coverageeligibility/on_check` | [F3](../fhir/F3-coverage-eligibility-response.md) | [C3](../callbacks/C3-auth-requirements-on-check.md) |
| Insurance plan (package master) | nha:B2, nha:D1 | [A3](../apis/A3-insurance-plan-request.md) | `v1/insuranceplan/request` | [F4](../fhir/F4-task-insuranceplan.md) (Task only) | the case number [REF](PAYERS.md#markers) | `v1/insuranceplan/on_request` | [F5](../fhir/F5-insuranceplan.md) with [F6](../fhir/F6-questionnaire.md) | [C4](../callbacks/C4-insuranceplan-on-request.md) |

### Pre-authorisation

| Exchange | NHA | Our API | Send route | Bundle sent | Workflow id | Reply route | Bundle back | Callback |
|---|---|---|---|---|---|---|---|---|
| Pre-authorisation | nha:B3, nha:D4 | [A4](../apis/A4-preauth-submit.md) | `v1/preauth/submit` | [F8](../fhir/F8-claim.md) (`use: preauthorization`) with [F7](../fhir/F7-questionnaireresponse.md), [F15](../fhir/F15-patient.md) to [F19](../fhir/F19-other-resources.md) | 12 | `v1/preauth/on_submit` | [F9](../fhir/F9-claimresponse.md) | [C5](../callbacks/C5-preauth-on-submit.md) |
| Pre-auth resubmitted after a rejection | nha:D5 | [A4](../apis/A4-preauth-submit.md) | `v1/preauth/submit` | [F8](../fhir/F8-claim.md) | 121 (defined; the reference never sends it [REF](PAYERS.md#markers)) | `v1/preauth/on_submit` | [F9](../fhir/F9-claimresponse.md) | [C5](../callbacks/C5-preauth-on-submit.md) |
| Pre-auth query answer | nha:D7 | [A4](../apis/A4-preauth-submit.md) (resubmit query mode) [PAYER](PAYERS.md#markers) | `v1/preauth/submit` | [F8](../fhir/F8-claim.md) with the answer | 19, status `response.complete` | `v1/preauth/on_submit` | [F9](../fhir/F9-claimresponse.md) | [C5](../callbacks/C5-preauth-on-submit.md) |
| Enhancement | nha:D6 | [A4](../apis/A4-preauth-submit.md) | `v1/preauth/submit` | [F8](../fhir/F8-claim.md) with the added lines | 13 | `v1/preauth/on_submit` | [F9](../fhir/F9-claimresponse.md) | [C5](../callbacks/C5-preauth-on-submit.md) |
| Enhancement query answer | nha:D6 | [A4](../apis/A4-preauth-submit.md) | `v1/preauth/submit` | [F8](../fhir/F8-claim.md) | 131, status `response.complete` | `v1/preauth/on_submit` | [F9](../fhir/F9-claimresponse.md) | [C5](../callbacks/C5-preauth-on-submit.md) |
| Predetermination (quote) | nha:B9 | [A4](../apis/A4-preauth-submit.md) | `v1/preauth/submit` with `use: predetermination` [REF](PAYERS.md#markers); NHA lists `v1/predetermination/submit` | [F8](../fhir/F8-claim.md) (`use: predetermination`) | 12 | `v1/preauth/on_submit` (NHA: `v1/predetermination/on_submit`) | [F9](../fhir/F9-claimresponse.md) | [C5](../callbacks/C5-preauth-on-submit.md) |
| Cancel the pre-authorisation | nha:D8 | [A6](../apis/A6-task-submit.md) (cancel) | `v1/task/submit` | [F10](../fhir/F10-task-claim-actions.md) (Task `cancel`) | PC01 | `v1/task/on_submit` | [F10](../fhir/F10-task-claim-actions.md) pointing at [F9](../fhir/F9-claimresponse.md) | [C7](../callbacks/C7-cancel-on-submit.md) |

Payer workflow ids on pre-auth replies [PAYER](PAYERS.md#markers): 20 received, 21 approved, 22 enhancement approved, 23 rejected, 24 queried; PC02 cancellation accomplished.

### Claim and after

| Exchange | NHA | Our API | Send route | Bundle sent | Workflow id | Reply route | Bundle back | Callback |
|---|---|---|---|---|---|---|---|---|
| Claim | nha:B5, nha:D9 | [A5](../apis/A5-claim-submit.md) | `v1/claim/submit` | [F8](../fhir/F8-claim.md) (`use: claim`) with [F7](../fhir/F7-questionnaireresponse.md), [F15](../fhir/F15-patient.md) to [F19](../fhir/F19-other-resources.md) | 15 | `v1/claim/on_submit` | [F9](../fhir/F9-claimresponse.md) | [C6](../callbacks/C6-claim-on-submit.md) |
| Claim query answer | nha:D10 | [A5](../apis/A5-claim-submit.md) | `v1/claim/submit` | [F8](../fhir/F8-claim.md) with the answer | 151 (published) for every adapter; the SHA sandbox takes only 161, set as a configuration override [SANDBOX](PAYERS.md#markers); status `response.complete` | `v1/claim/on_submit` | [F9](../fhir/F9-claimresponse.md) | [C6](../callbacks/C6-claim-on-submit.md) |
| Claim resubmitted | | [A5](../apis/A5-claim-submit.md) | `v1/claim/submit` | [F8](../fhir/F8-claim.md) | not offered for PMJAY [PAYER](PAYERS.md#markers); generic 16, which NHA's workflow list does not publish [REF](PAYERS.md#markers) | `v1/claim/on_submit` | [F9](../fhir/F9-claimresponse.md) | [C6](../callbacks/C6-claim-on-submit.md) |
| Reprocess a decided claim | nha:D11 | [A6](../apis/A6-task-submit.md) (reprocess) | `v1/task/submit` | [F10](../fhir/F10-task-claim-actions.md) (Task) | 36 | `v1/task/on_submit` | [F10](../fhir/F10-task-claim-actions.md) | [C8](../callbacks/C8-enquiry-on-submit.md) |
| Release the unpaid balance | nha:D12 | [A6](../apis/A6-task-submit.md) (release) | `v1/task/submit` | [F10](../fhir/F10-task-claim-actions.md) (Task) | 36 | `v1/task/on_submit` | [F10](../fhir/F10-task-claim-actions.md) | [C8](../callbacks/C8-enquiry-on-submit.md) |
| Status of a leg | nha:A5 | [A6](../apis/A6-task-submit.md) (status) | `v1/task/submit` with a status Task [REF](PAYERS.md#markers); NHA lists `v1/status` | [F10](../fhir/F10-task-claim-actions.md) (Task) | the leg's correlation id, else 13 [REF](PAYERS.md#markers) | `v1/task/on_submit` or `v1/on_status` | [F10](../fhir/F10-task-claim-actions.md) | [C8](../callbacks/C8-enquiry-on-submit.md) |

Payer workflow ids on claim replies [PAYER](PAYERS.md#markers): 25 received, 26 approved. PMJAY does not answer a status enquiry ([PAYERS.md](PAYERS.md)).

### Payer-started exchanges

| Exchange | NHA | Arrives on | Bundle in | Callback | Our answer | Answer route | Bundle out | Workflow id |
|---|---|---|---|---|---|---|---|---|
| Payer query, notification or note | nha:C6 (payer), nha:B4 (provider) | `v1/communication/request` | [F11](../fhir/F11-communicationrequest.md) (a note: a bare [F12](../fhir/F12-communication.md)) | [C9](../callbacks/C9-communication-request.md) | [A7](../apis/A7-communication-on-request.md): reply to a query, acknowledge a notification | `v1/communication/on_request` | [F12](../fhir/F12-communication.md) | the request's own, on the request's correlation id |
| Payment notice | nha:C9 (payer), nha:B7, nha:D13 (provider) | `v1/paymentnotice/request` | [F13](../fhir/F13-paymentnotice.md) | [C10](../callbacks/C10-paymentnotice-request.md) | [A8](../apis/A8-paymentnotice-on-request.md): acknowledge | `v1/paymentnotice/on_request` | [F14](../fhir/F14-payment-acknowledgement.md) | 17; generic: the notice's own |

### Not built by this skill

| NHA | Route | Note |
|---|---|---|
| nha:A6 | `v1/error` (inbound) | delivered by [G8](../gateway/G8-receive.md) with type `error`, which [C1](../callbacks/C1-callback-door.md) ignores [REF](PAYERS.md#markers) |
| nha:B6 | `v1/search/submit`, `v1/search/on_submit` | claim search: not specified here |
| nha:E1 | `v1/notification/subscribe`, `v1/notification/on_subscribe` | notification subscription: not specified here |
| nha:D2 | ABHA biometric authentication | not an NHCX exchange, but built: [A18](../apis/A18-biometric-authentication.md), section 2 |

## 5. Where the details are

| For | Read |
|---|---|
| What each API does, step by step | the A spec, and [READSETS.md](READSETS.md) for what to read with it |
| What each reply does to the case | the C spec |
| Every element of a bundle | the F spec, and the knowledge source's example bundles |
| Payer differences | [PAYERS.md](PAYERS.md) |
| Going live, addresses that change, inbound IPs | [OPERATIONS.md](OPERATIONS.md) |
