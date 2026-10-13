# APIs

Every call the application makes for NHCX, in one list. Each row links to its full spec in [../apis/](../apis/INDEX.md). All of them run in-process: outbound messages go through [G7. Send](../gateway/G7-send.md), lookups through [G9. Ledger](../gateway/G9-ledger.md) or [G10. Beneficiary Registry](../gateway/G10-beneficiary-registry.md). Inbound messages are the callbacks in [CALLBACK.md](CALLBACK.md).

## Outbound to NHCX

| # | API | Call | What it does | Replies | Screens |
|---|---|---|---|---|---|
| [A1](../apis/A1-policy-search.md) | Policy Search | `registry.policies_search` (G10), registry `participant/get/policies` | Finds every policy linked to a member id, mobile number or ABHA number. Synchronous, the first call of every case; "No policies found" reads as an empty list. | none | [S1](../screens/S1-search-policy.md), [S2](../screens/S2-select-policy.md) |
| [A2](../apis/A2-coverage-eligibility-check.md) | Coverage Eligibility Check | `gateway.send("v1/coverageeligibility/check")` | Sends a CoverageEligibilityRequest for one of four purposes: validation (is the policy in force), benefits, discovery (find the policy) or auth-requirements (rule on the chosen procedure set). | [C1](../callbacks/C1-callback-door.md), [C2](../callbacks/C2-coverage-eligibility-on-check.md), [C3](../callbacks/C3-auth-requirements-on-check.md) | [S3](../screens/S3-policy-discovery.md), [S8](../screens/S8-line-items.md), [S9](../screens/S9-preauthorisation.md), [S17](../screens/S17-beneficiary-discovery.md), [S18](../screens/S18-beneficiary-verification.md) |
| [A3](../apis/A3-insurance-plan-request.md) | Insurance Plan Request | `gateway.send("v1/insuranceplan/request")` | Asks the payer for its package master for this policy and facility (specialities, packages, rates, tiers, conditions, documents, forms). Reuses a master already held for the same payer, policy and facility. | [C1](../callbacks/C1-callback-door.md), [C4](../callbacks/C4-insuranceplan-on-request.md) | [S7](../screens/S7-insurance-plan.md) |
| [A4](../apis/A4-preauth-submit.md) | Pre-auth Submit | `gateway.send("v1/preauth/submit")` | Sends the pre-authorisation Claim bundle: first request, query answer, enhancement or enhancement resubmit; also a predetermination quote that binds nobody. | [C1](../callbacks/C1-callback-door.md), [C5](../callbacks/C5-preauth-on-submit.md) | [S9](../screens/S9-preauthorisation.md), [S14](../screens/S14-patient-registration-form.md), [S15](../screens/S15-patient-detail.md), [S16](../screens/S16-practitioner-master.md), [S18](../screens/S18-beneficiary-verification.md) |
| [A5](../apis/A5-claim-submit.md) | Claim Submit | `gateway.send("v1/claim/submit")` | Files the claim after discharge: the pre-auth bundle with `use: claim`, the pre-auth reference, the completed procedure, discharge details and claim-stage documents; also answers a claim query. | [C1](../callbacks/C1-callback-door.md), [C6](../callbacks/C6-claim-on-submit.md) | [S11](../screens/S11-claim-submission.md), [S14](../screens/S14-patient-registration-form.md), [S15](../screens/S15-patient-detail.md), [S16](../screens/S16-practitioner-master.md), [S18](../screens/S18-beneficiary-verification.md) |
| [A6](../apis/A6-task-submit.md) | Task Submit (cancel, status, reprocess, release) | `gateway.send("v1/task/submit")` | Sends a Task for a follow-up: cancel the pre-authorisation, ask the status of a leg, ask for a decided claim to be reprocessed, or ask for the unpaid balance to be released. | [C1](../callbacks/C1-callback-door.md), [C7](../callbacks/C7-cancel-on-submit.md), [C8](../callbacks/C8-enquiry-on-submit.md) | [S9](../screens/S9-preauthorisation.md), [S11](../screens/S11-claim-submission.md) |
| [A7](../apis/A7-communication-on-request.md) | Communication Reply | `gateway.send("v1/communication/on_request")` | Answers a payer query with text and documents, or acknowledges a payer notification, on the payer's own thread. | [C5](../callbacks/C5-preauth-on-submit.md), [C6](../callbacks/C6-claim-on-submit.md), [C9](../callbacks/C9-communication-request.md) | [S10](../screens/S10-communication.md) |
| [A8](../apis/A8-paymentnotice-on-request.md) | Payment Notice Acknowledgement | `gateway.send("v1/paymentnotice/on_request")` | Tells the payer a payment notice was received. Sent automatically when a notice is recorded; re-sent by hand when that failed. | [C10](../callbacks/C10-paymentnotice-request.md) | [S12](../screens/S12-payments.md) |

## Ledger queries (polling)

Polling is the fallback when a callback is missed. Opening a claim runs these for every leg still waiting.

| # | API | Call | What it does | Replies | Screens |
|---|---|---|---|---|---|
| [A10](../apis/A10-txn-related.md) | Transaction Related | `ledger.related(txn_id)` | Lists every ledger row on the same thread as a send, newest first, to find the payer's reply and apply it as its callback would. | [C1](../callbacks/C1-callback-door.md), [C2](../callbacks/C2-coverage-eligibility-on-check.md), [C3](../callbacks/C3-auth-requirements-on-check.md), [C4](../callbacks/C4-insuranceplan-on-request.md), [C5](../callbacks/C5-preauth-on-submit.md), [C6](../callbacks/C6-claim-on-submit.md), [C7](../callbacks/C7-cancel-on-submit.md), [C8](../callbacks/C8-enquiry-on-submit.md) | [S3](../screens/S3-policy-discovery.md), [S7](../screens/S7-insurance-plan.md), [S8](../screens/S8-line-items.md), [S9](../screens/S9-preauthorisation.md), [S11](../screens/S11-claim-submission.md) |
| [A11](../apis/A11-txn-dispatch.md) | Transaction Dispatch | `ledger.dispatch(txn_id)` | Says what became of a send's dispatch to NHCX (`dispatched`, `dispatch_failed`); a refusal's text is read from the entry. | [C2](../callbacks/C2-coverage-eligibility-on-check.md), [C8](../callbacks/C8-enquiry-on-submit.md) | [S3](../screens/S3-policy-discovery.md), [S7](../screens/S7-insurance-plan.md), [S8](../screens/S8-line-items.md), [S9](../screens/S9-preauthorisation.md), [S11](../screens/S11-claim-submission.md) |
| [A12](../apis/A12-txn-fhir.md) | Transaction FHIR | `ledger.fhir(txn_id)` | Returns the stored, decrypted envelope of one ledger row, so a poll can read what a reply says. | [C1](../callbacks/C1-callback-door.md), [C2](../callbacks/C2-coverage-eligibility-on-check.md), [C3](../callbacks/C3-auth-requirements-on-check.md), [C4](../callbacks/C4-insuranceplan-on-request.md), [C5](../callbacks/C5-preauth-on-submit.md), [C6](../callbacks/C6-claim-on-submit.md), [C7](../callbacks/C7-cancel-on-submit.md), [C8](../callbacks/C8-enquiry-on-submit.md) | [S3](../screens/S3-policy-discovery.md) |
| [A13](../apis/A13-txn-list.md) | Transaction List | `ledger.list()` | Lists the ledger to find a ProtocolResponse rejection addressed to one of our sends (for example PAYR-1008). | [C1](../callbacks/C1-callback-door.md) | [S3](../screens/S3-policy-discovery.md) |

## Payer adjudication (sandbox testing)

| # | API | Call | What it does | Replies | Screens |
|---|---|---|---|---|---|
| [A14](../apis/A14-adjudicator-user-role.md) | Adjudicator User Role | payer service `get/user-role`, or the IRDAI desk | Reads which payer role holds a case now, and so which actions are legal. | none | none |
| [A15](../apis/A15-adjudicator-process-case.md) | Adjudicator Process Case | payer service `process/case`, or the IRDAI desk | Takes one decision on a pre-auth or claim, or walks a case through every role (at most 8 rounds) until it is decided. | [C10](../callbacks/C10-paymentnotice-request.md) | none |
| [A16](../apis/A16-gateway-token.md) | Gateway Token | `gateway.token(participant)` (G3) | Supplies the ABDM session token the payer service calls need, unless a payer service token is configured. | none | none |

## ABDM calls beside the exchange

Plain JSON to ABDM with the session token: the beneficiary's biometric authentication and their ABHA. No JWE, no protocol headers, no ledger row.

| # | API | Call | What it does | Replies | Screens |
|---|---|---|---|---|---|
| [A18](../apis/A18-biometric-authentication.md) | Biometric Authentication | `abdm.biometric.init / capture / verify / refresh` | Proves the beneficiary is at the hospital: a fingerprint, iris or face authentication against their ABHA through ABDM's biometric service, on the Verification tab, before the pre-authorisation while admitted and again once discharged. Optional for any payer, required by PMJAY. The user token it yields rides on the eligibility check, the pre-authorisation and the claim; PMJAY's consent questionnaire stands in only where no capture is possible. | none | [S4](../screens/S4-claim-creation-form.md), [S11](../screens/S11-claim-submission.md), [S14](../screens/S14-patient-registration-form.md), [S18](../screens/S18-beneficiary-verification.md) |
| [A19](../apis/A19-abha-m1.md) | ABHA Create and Verify (ABDM M1) | `abdm.abha.enrol / login` | Puts a verified ABHA on the patient file: an existing ABHA verified by the OTP sent to its mobile, or a new one created from an Aadhaar OTP with an address chosen. The calls are ABDM's M1 and come from the MCP; this spec says what the application does with them. | none | [S13](../screens/S13-patient-list.md), [S14](../screens/S14-patient-registration-form.md), [S18](../screens/S18-beneficiary-verification.md) |

## Application

| # | API | Call | What it does | Replies | Screens |
|---|---|---|---|---|---|
| [A17](../apis/A17-claim-state.md) | Claim State | `GET claims/view/:caseid/state` | Runs the same polls as opening the claim, then returns everything the claim's tabs show as one JSON document, for scripted drivers and tests. | [C2](../callbacks/C2-coverage-eligibility-on-check.md), [C3](../callbacks/C3-auth-requirements-on-check.md), [C4](../callbacks/C4-insuranceplan-on-request.md), [C5](../callbacks/C5-preauth-on-submit.md), [C6](../callbacks/C6-claim-on-submit.md), [C7](../callbacks/C7-cancel-on-submit.md), [C8](../callbacks/C8-enquiry-on-submit.md) | [S6](../screens/S6-claim-detail.md) |
