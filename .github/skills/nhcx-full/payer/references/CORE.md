# Core

The NHCX facts every task needs, on one page: the addresses per environment, the calls that are not exchanges, and for each exchange the route it arrives on, the bundle in, the callback that takes it, the answer this payer sends, its route, bundle, workflow id and status. The knowledge source ([KNOWLEDGE.md](KNOWLEDGE.md)) is the authority behind every value here (`baseurl.yaml`, `workflow.yaml` and `usecases.yaml` in the package; `search_docs` and `get_operation` on the MCP). Check a value there before relying on it, and when they differ, the knowledge source wins.

NHA use-case codes are written `nha:C5`; bare ids (A3, C4, F9) are this skill's specs.

## Instructions

Follow these strictly, in every step and every file. When a spec seems to say otherwise, stop and resolve it against this list and the knowledge source; record the resolution under `corrections` in the current plan file.

1. **The gateway is inside the application.** Call it as functions ([G7. Send](../gateway/G7-send.md) `gateway.send`, [G9. Ledger](../gateway/G9-ledger.md) `ledger.*`, [G4. Registry and Certificates](../gateway/G4-registry.md) and [G10. Beneficiary Registry](../gateway/G10-beneficiary-registry.md) `registry.*`, [G3. Session Token](../gateway/G3-session-token.md)). Never call a separate gateway service over HTTP, and never mount any gateway route except the inbound route and the health checks ([G1. Embedding](../gateway/G1-embedding.md)). The reference desk reached its gateway over HTTP [REF](PAYERS.md#markers); this skill embeds it.
2. **NHCX facts come from the knowledge source, never from memory.** Paths, headers, profiles, codes and workflow ids are checked there ([KNOWLEDGE.md](KNOWLEDGE.md)). On the protocol it wins over every spec; on what the application does, the specs win.
3. **Nothing scheme- or environment-specific is hard-coded.** Participant codes, base URLs, workflow ids and scheme rules come from configuration or the scheme profile ([PAYERS.md](PAYERS.md)). Production URLs are set explicitly.
4. **One way in, one way out.** Every message arrives through [G8. Receive](../gateway/G8-receive.md) and `C1.receive(envelope, delivery)`, which classifies it by its bundle and routes it to one callback. Every message leaves through `gateway.send`. A hospital's reply found by polling ([A11. Transaction Related](../apis/A11-txn-related.md), [A12. Transaction FHIR](../apis/A12-txn-fhir.md)) is applied by the same callback handler, never by separate code.
5. **An answer keeps the request's `x-hcx-correlation_id`.** Eligibility, plan, verdict, status, task and payment-enquiry answers travel on the thread the question opened. Only a query ([A5. Query Request](../apis/A5-query-request.md)) and a payment notice ([A6. Payment Notice](../apis/A6-payment-notice.md)) open a thread of their own, and the id the gateway mints is kept on the case or the payment so the hospital's reply can be matched.
6. **A submission is acknowledged at once and decided by a person.** A pre-authorisation or a claim is filed as a case and acknowledged with a queued ClaimResponse ([A3. Pre-auth Answer](../apis/A3-preauth-answer.md), [A4. Claim Answer](../apis/A4-claim-answer.md)) so NHCX keeps the thread open; the verdict goes out once, when an adjudicator decides ([A13. Adjudicate](../apis/A13-adjudicate.md)). Nothing but a predetermination ([A10. Predetermination Quote](../apis/A10-predetermination-quote.md)) is priced by rules.
7. **Every callback is safe to receive twice.** A delivery already taken in by `x-hcx-api_call_id` ([D28. nhcx_delivery](../database/D28-nhcx-delivery.md)) is `ignored`; a pre-authorisation delivered twice opens one case; documents are filed once. Handlers answer `settled`, `unmatched`, `ignored` or `rejected` (NHCX gets 202, no redelivery) or `error` (NHCX gets 502 and redelivers). Only an unexpected fault is `error`.
8. **A failed answer keeps the case's thread.** When the gateway refuses or cannot take an answer, the decision stands, the thread's correlation id stays on the case, and the answer can be sent again; the exchange log ([D27. case_exchange_message](../database/D27-case-exchange-message.md)) records what did not go.
9. **Keep the layers.** Screens call services and read models. Only services (A) and callbacks (C) write the case tables. FHIR builders and parsers never touch the database or the gateway ([SCAFFOLDING.md](SCAFFOLDING.md)).
10. **No secrets in the repository.** Client secret, private key and any sandbox desk credentials come from configuration or the environment.
11. **Treat markers as defined.** [REF](PAYERS.md#markers) may be chosen differently (record it); [PAYER](PAYERS.md#markers) values come from the scheme profile; [SANDBOX](PAYERS.md#markers) behaviour is not relied on in production ([PAYERS.md](PAYERS.md)).
12. **Work the steps in order, log them, and end every prompt by rebuilding the report.** L1 to L8, one plan file each, every sub-step and file change in `nhcx-plan/progress.json` ([LOG.md](../steps/LOG.md)); the last action of every prompt runs the report builder that rewrites `nhcx-plan/report.html` ([LOG.md](../steps/LOG.md#logh-reporthtml)). Re-read this page at the start of each step.

## Confusions

Terms and behaviours that are easy to mix up, with the reading this skill uses.

| Easily confused | Correct reading |
|---|---|
| This skill's ids and NHA's use-case codes | `A1` is our eligibility answer; `nha:A1` is NHA's participant list. `C5` is our claim-submit callback; `nha:C5` is NHA's "respond to pre-authorisation". Always prefix NHA codes with `nha:`. |
| "Gateway" | Here, the in-process module G. NHA's documents also call the NHCX exchange itself "the gateway", and ABDM has its own session gateway. Write "the exchange" for NHCX and "sessions" for ABDM. |
| Workflow id, correlation id, api call id, request id, ledger id | Workflow id (`x-hcx-workflow_id`): which step of the claim flow a message is. Correlation id: the thread, kept by every answer. API call id: one message, kept across NHCX's redeliveries (the dedupe key, [D28. nhcx_delivery](../database/D28-nhcx-delivery.md)). Request id: one request. Ledger id (`txn_id`): our own record in [G9. Ledger](../gateway/G9-ledger.md), never sent to NHCX. |
| The hospital's workflow ids and ours | A pre-authorisation arrives under 12, a query answer under 19, an enhancement under 13, a claim under 15; nothing routes on them ([C1. Callback Door](../callbacks/C1-callback-door.md) routes on the bundle). Our sends carry our own: 20 and 25 to acknowledge, 21, 22, 23, 231, 26, 291 to decide, 24, 241, 27 to query, PC02, 37, 252, 253 on Tasks, 30 on a payment notice ([PAYERS.md](PAYERS.md)). |
| `x-hcx-status` on an acknowledgement and on a verdict | An acknowledgement is `response.partial` (received, not decided); a verdict is `response.complete`; a query on `v1/communication/request` and a payment notice are `request.initiated`, because this payer starts them. |
| Participant code and processing code | The payer's participant code is who it is on NHCX; the processing code is who handles its claims (a TPA, or the payer itself). A hospital addresses the processing code; the answer goes out as the code the request was addressed to ([D1. payer](../database/D1-payer.md)). |
| The hospital's claim number, our case id and `preAuthRef` | The hospital's `Claim.identifier` is kept as the case's `nhcx_claim_ref` and is what its later messages name. Our case id is the desk's number and goes back as `preAuthRef` on every ClaimResponse ([F9. ClaimResponse](../fhir/F9-claimresponse.md)), so the hospital's claim leg quotes it. |
| `outcome` on a ClaimResponse | The hospital reads the pair of `outcome` and the claim-level `adjudication` reason: `queued` is the acknowledgement; `complete` with reason `approved` an approval; `complete` or `error` with reason `rejected` a rejection ([F9. ClaimResponse](../fhir/F9-claimresponse.md)). Never send `complete` for a rejection without the reason. |
| A query and a verdict | A query is not a verdict: it goes out as a CommunicationRequest on its own thread ([A5. Query Request](../apis/A5-query-request.md)) under the PMJAY dialect's `communication` mode, and the submission's thread stays open until the reply is read and a person decides. Some schemes ask inside a ClaimResponse and take the answer as a resubmission [PAYER](PAYERS.md#markers). |
| An enhancement and a fresh pre-authorisation | An enhancement comes back under the same claim number (or names the prior on `Claim.related`) with lines the case does not hold, and joins the case for a fresh decision; a number whose case is closed opens a new case ([C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md)). |
| A reprocess and the claim's thread | A verdict completes the claim's thread; the exchange refuses a second ClaimResponse on it. A reprocess arrives as a Task on a thread of its own, and the new decision goes back on that thread as a completed Task carrying the ClaimResponse ([A9. Task Answer](../apis/A9-task-answer.md)). |
| A payment notice and a payment enquiry | Both are a PaymentNotice on `v1/paymentnotice/request`: ours tells the hospital money moved ([A6. Payment Notice](../apis/A6-payment-notice.md)) and is acknowledged by a Task on `v1/paymentnotice/on_request` ([C11. Payment Acknowledgement](../callbacks/C11-payment-acknowledgement.md)); a hospital's asks where the money is ([C10. Payment Enquiry](../callbacks/C10-payment-enquiry.md)) and is answered with a PaymentReconciliation on `v1/paymentnotice/on_request` ([A7. Payment Enquiry Answer](../apis/A7-payment-enquiry-answer.md)). |
| A status enquiry's shape | It may arrive as a Task coded `status` on `v1/task/submit`, or on `v1/status` with only the `x-hcx-status_filters` header and no bundle; it is answered on the route it came in on ([C8. Status Enquiry](../callbacks/C8-status-enquiry.md), [A8. Status Answer](../apis/A8-status-answer.md)). |
| Predetermination | A Claim with `use: predetermination` on the pre-auth route; priced by the rules and answered at once, opening no case ([C6. Predetermination](../callbacks/C6-predetermination.md), [A10. Predetermination Quote](../apis/A10-predetermination-quote.md)). NHA also lists `v1/predetermination/submit`; take both. |
| Wallet, sum assured and the approved amount | The wallet is what is left of an enrolment's sum assured this year ([D6. subscription](../database/D6-subscription.md)). Approving a claim debits it; a reprocess credits it back; an approval larger than the wallet is refused ([A13. Adjudicate](../apis/A13-adjudicate.md)). |
| ABHA number and ABHA address | The 14-digit number (what an eligibility discovery matches on, [D5. member](../database/D5-member.md)) and the `name@abdm` style address; they are different fields. |
| HFR id and the facility's participant code | The HFR id identifies the hospital in the facility registry (its Organization, [F17. Organization](../fhir/F17-organization.md)); the participant code (`...@hcx`) is its address on NHCX and the recipient of every answer. |
| Sandbox participant codes | Examples only ([PAYERS.md](PAYERS.md)). Every code comes from configuration. |
| Step ids, section letters, log ids | `L1` to `L8` are steps; `S3L` is the LAYOUT section of S3; `LOG-0042` is a progress log entry. |

## 1. Environments and base URLs

| Service | Used for | Sandbox | Production |
|---|---|---|---|
| ABDM sessions | the session token every call carries ([G3](../gateway/G3-session-token.md)), `POST /api/hiecm/gateway/v3/sessions` | `https://dev.abdm.gov.in` | `https://apis.abdm.gov.in` (published by ABDM; confirm in the onboarding letter) |
| NHCX exchange | every answer and every payer-started send, under `/v1` ([G7](../gateway/G7-send.md)) | `https://apisbx.abdm.gov.in/hcx` | shared by NHA after sandbox exit |
| Participant service (registry) | participant records, certificates, ABHA policy link ([G4](../gateway/G4-registry.md), [G10](../gateway/G10-beneficiary-registry.md)) | `https://apisbx.abdm.gov.in/pmjay/sbxhcx/participanthcxservice` | `https://apisprod.nha.gov.in/pmjay/hcx/participanthcxservice` |
| NHCX portal | the portal and its published API specifications | `https://hcxsbx.abdm.gov.in` | not published |

| Setting | Sandbox | Production |
|---|---|---|
| `X-CM-ID` on the session call | `sbx` | `abdm` |
| This application's inbound route | the public URL registered as the participant's `endpoint_url`, routed to `/in/<path>` or `/v1/<path>` ([G8](../gateway/G8-receive.md)) | the same, on HTTPS (TLS 1.2 or newer), a domain name hosted in India, no IP address and no port; NHCX's source addresses allowed in ([OPERATIONS.md](OPERATIONS.md)) |

The gateway's built-in production defaults ([G2. Configuration and Participants](../gateway/G2-configuration.md)) follow a host-swap guess that does not match the published production participant service or sessions host above. Set every production URL explicitly in configuration.

## 2. Calls that are not exchanges

Plain JSON with the session token: no JWE, no protocol headers, no ledger row.

| NHA use case | Call | Does | This skill |
|---|---|---|---|
| nha:A4 | sessions (above) | trade client id and secret for the session token | [G3](../gateway/G3-session-token.md) |
| nha:A3 | registry `/fetch/certs` | a participant's encryption certificate, the hospital's before every answer | [G4](../gateway/G4-registry.md) |
| nha:A1 | registry `/fetch/participants/list`, `/participant/search` | participant records; naming a code on the desk | [G4](../gateway/G4-registry.md), [A17](../apis/A17-participant-lookup.md) |
| nha:C1, nha:C2 | registry `/participant/link/abha/policy`, `/participant/delink/abha/policy` | link or unlink a member's ABHA number and enrolment | [A16](../apis/A16-abha-policy-link.md), [G10](../gateway/G10-beneficiary-registry.md) |
| ABDM M1 | ABHA service `/abha/api/v3/...` | create a member's ABHA from an Aadhaar OTP, or verify an existing one by OTP, and fill the member from the profile | [A20](../apis/A20-abha-m1.md); the calls themselves are read from the MCP's M1 catalogue |

## 3. Protocol defaults

- Every exchange is one FHIR Bundle ([F1. Bundle](../fhir/F1-bundle.md)) encrypted as a compact JWE to the recipient's certificate ([G6. Encryption](../gateway/G6-encryption.md)), with the `x-hcx-*` headers in the protected header ([G5. Protocol Headers](../gateway/G5-protocol-headers.md)).
- An answer swaps sender and recipient of the request, keeps its `x-hcx-correlation_id` and echoes its `x-hcx-workflow_id` unless the scheme gives the answer a code of its own ([PAYERS.md](PAYERS.md)); the sending API sets `x-hcx-status` (`response.complete` for an answer, `response.partial` for an acknowledgement, `request.initiated` for a send this payer starts). The gateway's path default is only a fallback ([G5. Protocol Headers](../gateway/G5-protocol-headers.md)).
- `x-hcx-sender_code` is the participant code the request was addressed to ([D1. payer](../database/D1-payer.md) participant or processing code, or a hosted scheme code); `x-hcx-recipient_code` is the hospital's code from the case's routing slip ([D19. case](../database/D19-case.md)).
- A message is classified by its bundle's focal resource, never by the path or the gateway's type label ([C1. Callback Door](../callbacks/C1-callback-door.md)).
- A refusal of a hospital's message goes back as a delivery outcome to the gateway, not as a bundle: `rejected` for a body that can never be read, `error` only for a fault a redelivery may cure ([G8. Receive](../gateway/G8-receive.md)).

## 4. Exchanges

"Workflow id" gives the `pmjay` value; [PAYERS.md](PAYERS.md) has every dialect and the status paired with each. Every message is taken in by [G8. Receive](../gateway/G8-receive.md) and routed by [C1. Callback Door](../callbacks/C1-callback-door.md); every answer is made through `gateway.send` ([G7. Send](../gateway/G7-send.md)).

### Eligibility and plan, answered on the spot

| Exchange | NHA | Arrives on | Bundle in | Callback | Answer | Answer route | Bundle out | Workflow id | `x-hcx-status` |
|---|---|---|---|---|---|---|---|---|---|
| Coverage eligibility (validation, benefits, discovery) | nha:B1, nha:C3 | `v1/coverageeligibility/check` | [F2](../fhir/F2-coverage-eligibility-request.md) | [C2](../callbacks/C2-coverage-eligibility-check.md) | [A1](../apis/A1-eligibility-answer.md) | `v1/coverageeligibility/on_check` | [F3](../fhir/F3-coverage-eligibility-response.md) with [F15](../fhir/F15-patient.md), [F17](../fhir/F17-organization.md), [F18](../fhir/F18-coverage.md) | the request's own | `response.complete` |
| Authorisation requirements on the quoted packages | nha:B1 | `v1/coverageeligibility/check` (purpose `auth-requirements`) | [F2](../fhir/F2-coverage-eligibility-request.md) with items | [C2](../callbacks/C2-coverage-eligibility-check.md) | [A1](../apis/A1-eligibility-answer.md) | `v1/coverageeligibility/on_check` | [F3](../fhir/F3-coverage-eligibility-response.md) per item | the request's own | `response.complete` |
| Insurance plan (package master) | nha:B2, nha:C4 | `v1/insuranceplan/request` | [F4](../fhir/F4-task-insuranceplan.md) | [C3](../callbacks/C3-insurance-plan-request.md) | [A2](../apis/A2-insurance-plan-answer.md) | `v1/insuranceplan/on_request` | [F5](../fhir/F5-insuranceplan.md) with [F6](../fhir/F6-questionnaire.md), or an empty plan | the request's own | `response.complete` |
| Predetermination (quote) | nha:B9 | `v1/preauth/submit` with `use: predetermination` (NHA also lists `v1/predetermination/submit`) | [F8](../fhir/F8-claim.md) | [C6](../callbacks/C6-predetermination.md) | [A10](../apis/A10-predetermination-quote.md) | `v1/preauth/on_submit` | [F9](../fhir/F9-claimresponse.md) | the request's own | `response.complete` |

### Pre-authorisation, filed and decided by a person

| Exchange | NHA | Arrives on | Bundle in | Callback | Answer | Answer route | Bundle out | Workflow id | `x-hcx-status` |
|---|---|---|---|---|---|---|---|---|---|
| Pre-authorisation | nha:B3, nha:C5 | `v1/preauth/submit` | [F8](../fhir/F8-claim.md) (`use: preauthorization`) with [F7](../fhir/F7-questionnaireresponse.md), [F15](../fhir/F15-patient.md) to [F19](../fhir/F19-other-resources.md) | [C4](../callbacks/C4-preauth-submit.md) | [A3](../apis/A3-preauth-answer.md) acknowledgement at filing | `v1/preauth/on_submit` | [F9](../fhir/F9-claimresponse.md) (`outcome: queued`) | 20 | `response.partial` |
| Pre-authorisation verdict | nha:C5 | | | | [A3](../apis/A3-preauth-answer.md) when decided | `v1/preauth/on_submit` | [F9](../fhir/F9-claimresponse.md) | 21 approved, 23 rejected | `response.complete` |
| Enhancement (more lines under the same number, or `Claim.related` prior) | nha:D6 | `v1/preauth/submit` | [F8](../fhir/F8-claim.md) | [C4](../callbacks/C4-preauth-submit.md) | [A3](../apis/A3-preauth-answer.md) | `v1/preauth/on_submit` | [F9](../fhir/F9-claimresponse.md) | 22 approved, 231 denied | `response.complete` |
| Query answered by resubmission (schemes in `resubmit` mode) [PAYER](PAYERS.md#markers) | nha:D7 | `v1/preauth/submit` (the hospital's 19 or 131) | [F8](../fhir/F8-claim.md) with the answer | [C4](../callbacks/C4-preauth-submit.md) | [A3](../apis/A3-preauth-answer.md) | `v1/preauth/on_submit` | [F9](../fhir/F9-claimresponse.md) | 21 or 22 | `response.complete` |
| Cancel the pre-authorisation | nha:D8 | `v1/task/submit` (Task `cancel`) | [F10](../fhir/F10-task-claim-actions.md) | [C7](../callbacks/C7-task-submit.md) | [A9](../apis/A9-task-answer.md) | `v1/task/on_submit` | [F10](../fhir/F10-task-claim-actions.md) completed | PC02 | `response.complete` |

### Claim and after

| Exchange | NHA | Arrives on | Bundle in | Callback | Answer | Answer route | Bundle out | Workflow id | `x-hcx-status` |
|---|---|---|---|---|---|---|---|---|---|
| Claim | nha:B5, nha:C7 | `v1/claim/submit` | [F8](../fhir/F8-claim.md) (`use: claim`) with the discharge block, documents and forms | [C5](../callbacks/C5-claim-submit.md) | [A4](../apis/A4-claim-answer.md) acknowledgement at filing | `v1/claim/on_submit` | [F9](../fhir/F9-claimresponse.md) (`outcome: queued`) | 25 | `response.partial` |
| Claim verdict | nha:C7 | | | | [A4](../apis/A4-claim-answer.md) when decided | `v1/claim/on_submit` | [F9](../fhir/F9-claimresponse.md) | 26 approved, 291 rejected | `response.complete` |
| Reprocess a decided claim, release the unpaid balance | nha:D11, nha:D12 | `v1/task/submit` (Task `reprocess` or `release`) | [F10](../fhir/F10-task-claim-actions.md) | [C7](../callbacks/C7-task-submit.md) | [A9](../apis/A9-task-answer.md) acknowledgement, then the decision on the same thread | `v1/task/on_submit` | [F10](../fhir/F10-task-claim-actions.md) with [F9](../fhir/F9-claimresponse.md) on its output | 37 acknowledged; 252 approved, 253 rejected | `response.complete` |
| Status of a thread | nha:A5 | `v1/status` (headers only) or `v1/task/submit` (Task `status`) | [F10](../fhir/F10-task-claim-actions.md), or `x-hcx-status_filters` alone | [C8](../callbacks/C8-status-enquiry.md) | [A8](../apis/A8-status-answer.md) | `v1/on_status` or `v1/task/on_submit` | [F10](../fhir/F10-task-claim-actions.md) and the `x-hcx-status_response` header | the request's own | `response.complete` |

### Queries and payment, started by this payer

| Exchange | NHA | Our API | Send route | Bundle sent | Workflow id | `x-hcx-status` | Reply arrives on | Bundle back | Callback |
|---|---|---|---|---|---|---|---|---|---|
| Query the hospital | nha:C6 | [A5](../apis/A5-query-request.md) | `v1/communication/request` | [F11](../fhir/F11-communicationrequest.md) | 24 pre-authorisation, 241 enhancement, 27 claim | `request.initiated` | `v1/communication/on_request` | [F12](../fhir/F12-communication.md) | [C9](../callbacks/C9-communication.md) |
| Payment notice (raised, then completed with the UTR) | nha:C9 | [A6](../apis/A6-payment-notice.md) | `v1/paymentnotice/request` | [F13](../fhir/F13-paymentnotice.md) with [F14](../fhir/F14-paymentreconciliation.md) | 30 | `request.initiated` | `v1/paymentnotice/on_request` | [F10](../fhir/F10-task-claim-actions.md) (`paymentack`) | [C11](../callbacks/C11-payment-acknowledgement.md) |

### Payment enquiry, started by the hospital

| Exchange | NHA | Arrives on | Bundle in | Callback | Answer | Answer route | Bundle out | Workflow id | `x-hcx-status` |
|---|---|---|---|---|---|---|---|---|---|
| Where is the money | nha:B7 | `v1/paymentnotice/request` | [F13](../fhir/F13-paymentnotice.md) | [C10](../callbacks/C10-payment-enquiry.md) | [A7](../apis/A7-payment-enquiry-answer.md) | `v1/paymentnotice/on_request` | [F14](../fhir/F14-paymentreconciliation.md), or an OperationOutcome | the request's own | `response.complete` |

### Not built by this skill

| NHA | Route | Note |
|---|---|---|
| nha:A6 | `v1/error` (inbound) | delivered by [G8](../gateway/G8-receive.md) with type `error`, which [C1](../callbacks/C1-callback-door.md) ignores [REF](PAYERS.md#markers) |
| nha:B6 | `v1/search/submit`, `v1/search/on_submit` | claim search: not specified here |
| nha:E1 | `v1/notification/subscribe`, `v1/notification/on_subscribe` | notification subscription: not specified here |
| nha:D2 | ABHA biometric authentication | not an NHCX exchange; the hospital does it against ABDM and the user token arrives on the headers of its sends ([C2](../callbacks/C2-coverage-eligibility-check.md), [C4](../callbacks/C4-preauth-submit.md), [C5](../callbacks/C5-claim-submit.md)), optional for this payer, required by the live PMJAY scheme |
| a CommunicationRequest from a hospital | `v1/communication/request` | logged and ignored by [C9](../callbacks/C9-communication.md) [REF](PAYERS.md#markers) |

## 5. Where the details are

| For | Read |
|---|---|
| What each answer does, step by step | the A spec, and [READSETS.md](READSETS.md) for what to read with it |
| What each inbound message does to the case | the C spec |
| Every element of a bundle | the F spec, and the knowledge source's example bundles |
| Scheme differences | [PAYERS.md](PAYERS.md) |
| Going live, addresses that change, inbound IPs | [OPERATIONS.md](OPERATIONS.md) |
