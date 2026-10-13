# APIs

Every call the application makes into the embedded NHCX gateway (G), the NHCX or ABDM route that call puts on the wire, the payer-side calls made outside the exchange, and the application's own JSON endpoint. Screens refer to these by A number. Each file has ENDPOINT (E), DESCRIPTION (D), REQUEST (Q), RESPONSE (S), PSEUDOCODE (P) and USED BY (U) sections, and refers to FHIR resources by F number ([../fhir/](../fhir/INDEX.md)), tables by D number ([../database/](../database/INDEX.md)), replies by C number ([../callbacks/](../callbacks/INDEX.md)) and gateway parts by G number ([../gateway/](../gateway/INDEX.md)).

## Conventions

- The application calls G in-process, as function calls, never over HTTP. There is no gateway base URL, no gateway API key and no gateway HTTP timeout.
- Every outbound bundle goes through `gateway.send(path, envelope)`, [G7. Send](../gateway/G7-send.md), which completes the protocol headers ([G5. Protocol Headers](../gateway/G5-protocol-headers.md)), encrypts for the recipient ([G6. Encryption](../gateway/G6-encryption.md)) and posts to NHCX synchronously: when it returns, NHCX has answered. The arguments are the NHCX path (for example `v1/preauth/submit`) and the envelope `{jwe_headers, fhir}`: the `x-hcx-*` headers the application sets and the FHIR bundle. The result (`SendResult`) carries `ok` (NHCX answered 2xx), `txn_id` (the ledger id, also as `ledger_id`), `correlation_id`, `request_id`, `api_call_id`, the full `headers` the message went out under, NHCX's HTTP status (`gateway_status`, 202 when NHCX took it) and NHCX's reply (`response`).
- A failure comes back as a G7 `SendError`: `code`, `message`, `retryable`. A result with `ok` false (NHCX did not accept it) is a failed send too. Either is shown on the screen as a red message, never a 500: the error's `message`, or for `ok` false, NHCX's own `response.error.code: response.error.message`, else `GATEWAY_HTTP_<status>: NHCX did not accept the message`.
- A failed send may still name the ids it went out under: a `SendError` raised after the headers were built carries `txn_id`, `correlation_id` and the minted `headers`, and a result with `ok` false always carries them. When it does, the leg is kept under those ids and marked failed, because the message may have reached NHCX anyway (a connection dropped after the request was written is reported as unreachable). When it names none (a path or payload G7 refused before minting ids), nothing went out.
- Every message G sends or receives, accepted, refused or failed, is recorded in the [G9. Ledger](../gateway/G9-ledger.md). Polling reads it in-process (A10 to A13).
- Every outbound FHIR payload and its acknowledgement is also archived beside the claim, so a bundle can be read back later.
- A18 and A19 are ABDM calls beside the exchange, plain JSON with the session token and no ledger row: the beneficiary's biometric authentication, defined in full in A18, and the ABHA service (M1), whose calls A19 names on the MCP.
- There is no A9: the inbound door it once described became the callbacks, C1 to C10. Inbound messages are the callbacks in [../callbacks/](../callbacks/INDEX.md), taken in by [G8. Receive](../gateway/G8-receive.md).

## Outbound to NHCX

| # | API | Call | File |
|---|---|---|---|
| [A1](A1-policy-search.md) | Policy Search | `registry.policies_search` (G10), registry `participant/get/policies` | [A1-policy-search.md](A1-policy-search.md) |
| [A2](A2-coverage-eligibility-check.md) | Coverage Eligibility Check | `gateway.send("v1/coverageeligibility/check")` | [A2-coverage-eligibility-check.md](A2-coverage-eligibility-check.md) |
| [A3](A3-insurance-plan-request.md) | Insurance Plan Request | `gateway.send("v1/insuranceplan/request")` | [A3-insurance-plan-request.md](A3-insurance-plan-request.md) |
| [A4](A4-preauth-submit.md) | Pre-auth Submit | `gateway.send("v1/preauth/submit")` | [A4-preauth-submit.md](A4-preauth-submit.md) |
| [A5](A5-claim-submit.md) | Claim Submit | `gateway.send("v1/claim/submit")` | [A5-claim-submit.md](A5-claim-submit.md) |
| [A6](A6-task-submit.md) | Task Submit (cancel, status, reprocess, release) | `gateway.send("v1/task/submit")` | [A6-task-submit.md](A6-task-submit.md) |
| [A7](A7-communication-on-request.md) | Communication Reply | `gateway.send("v1/communication/on_request")` | [A7-communication-on-request.md](A7-communication-on-request.md) |
| [A8](A8-paymentnotice-on-request.md) | Payment Notice Acknowledgement | `gateway.send("v1/paymentnotice/on_request")` | [A8-paymentnotice-on-request.md](A8-paymentnotice-on-request.md) |

## Ledger queries (polling)

Polling is the fallback when a callback is missed. Opening a claim runs these for every leg still waiting.

| # | API | Call | File |
|---|---|---|---|
| [A10](A10-txn-related.md) | Transaction Related | `ledger.related(txn_id)` | [A10-txn-related.md](A10-txn-related.md) |
| [A11](A11-txn-dispatch.md) | Transaction Dispatch | `ledger.dispatch(txn_id)` | [A11-txn-dispatch.md](A11-txn-dispatch.md) |
| [A12](A12-txn-fhir.md) | Transaction FHIR | `ledger.fhir(txn_id)` | [A12-txn-fhir.md](A12-txn-fhir.md) |
| [A13](A13-txn-list.md) | Transaction List | `ledger.list()` | [A13-txn-list.md](A13-txn-list.md) |

## Payer adjudication (sandbox testing)

| # | API | Call | File |
|---|---|---|---|
| [A14](A14-adjudicator-user-role.md) | Adjudicator User Role | payer service `get/user-role`, or the IRDAI desk | [A14-adjudicator-user-role.md](A14-adjudicator-user-role.md) |
| [A15](A15-adjudicator-process-case.md) | Adjudicator Process Case | payer service `process/case`, or the IRDAI desk | [A15-adjudicator-process-case.md](A15-adjudicator-process-case.md) |
| [A16](A16-gateway-token.md) | Gateway Token | `gateway.token(participant)` (G3) | [A16-gateway-token.md](A16-gateway-token.md) |

## ABDM calls beside the exchange

Plain JSON to ABDM with the session token: the beneficiary's biometric authentication and their ABHA. No JWE, no protocol headers, no ledger row.

| # | API | Call | File |
|---|---|---|---|
| [A18](A18-biometric-authentication.md) | Biometric Authentication | `abdm.biometric.init / capture / verify / refresh` | [A18-biometric-authentication.md](A18-biometric-authentication.md) |
| [A19](A19-abha-m1.md) | ABHA Create and Verify (ABDM M1) | `abdm.abha.enrol / login` | [A19-abha-m1.md](A19-abha-m1.md) |

## Application

| # | API | Call | File |
|---|---|---|---|
| [A17](A17-claim-state.md) | Claim State | `GET claims/view/:caseid/state` | [A17-claim-state.md](A17-claim-state.md) |
