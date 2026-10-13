# F1. Bundle

#### F1R. RESOURCE
`Bundle`, `type: collection`, in both directions.

Direction: sent as the `fhir` member of every outbound envelope (A1 to A10), received as the `fhir` member of every envelope [G8. Receive](../gateway/G8-receive.md) hands to the callback door ([C1. Callback Door](../callbacks/C1-callback-door.md)) or [G9. Ledger](../gateway/G9-ledger.md) returns (A12). This payer never checks the profile of a received bundle.

Profiles this payer puts in `meta.profile` (all under `https://nrces.in/ndhm/fhir/r4/StructureDefinition/`):

| Profile | Carries |
|---|---|
| `InsurancePlanBundle` | F5 with F6 (A2) |
| `TaskBundle` | F11 (A5) |
| none, only the `SUBSETTED` tag | F3 (A1), F9 (A3, A4, A10), F10 answers (A8, A9), F13 with F14 (A6, A7) |

#### F1D. DESCRIPTION
Every NHCX message is one Bundle wrapped in an envelope:

```json
{"jwe_headers": {"x-hcx-sender_code": "<payer code>", "x-hcx-recipient_code": "<facility code>",
                 "x-hcx-correlation_id": "<the request's>", "x-hcx-workflow_id": "...", "x-hcx-status": "..."},
 "fhir": { "resourceType": "Bundle", ... }}
```

This payer sets the sender, recipient, correlation id, workflow id and status ([A3. Pre-auth Answer](../apis/A3-preauth-answer.md) explains the pairs; the workflow table is in [PAYERS.md](../references/PAYERS.md)). [G7. Send](../gateway/G7-send.md) adds the api call id, request id and timestamp ([G5. Protocol Headers](../gateway/G5-protocol-headers.md)) and encrypts ([G6. Encryption](../gateway/G6-encryption.md)). An answer keeps the correlation id of the message it answers; a query (F11) and a payment notice (F13) leave the correlation id out and G7 mints one, which the hospital's reply then carries.

**Sent bundles.** Two families, each a strict subset of what the PMJAY scheme payer sends, so a hospital integrated against the scheme reads this payer with no code change [REF](../references/PAYERS.md#markers):

| Family | Bundles | `id` | `identifier` | `meta` | fullUrls |
|---|---|---|---|---|---|
| Case answers (the "wire" shape) | F3, F9, F10 answers, F13 with F14 | F3: the constant `request`; F9: `PreauthorizationResponseDocument-<claim number>` or `ClaimResponseDocument-<claim number>`; F10 and F13: the hospital's claim number | `system` the payer's base URL, `value` the hospital's claim number (F3: the request anchor `https://nhcx.abdm.gov.in/coverage-eligibility/request`) | `lastUpdated` now in IST with milliseconds, `tag` `SUBSETTED` (`http://terminology.hl7.org/CodeSystem/v3-ObservationValue`, "Resource encoded in summary mode") | resolvable `https` addresses under the payer's base, each entry's `id` equal to its `fullUrl` |
| Plan and query | F5 with F6, F11 | a deterministic UUID v5 from the payer's base and the resource key, so a re-render gives the same ids [REF](../references/PAYERS.md#markers) | `value` the bundle id | `profile` set, `security` `V` "very restricted" (`http://terminology.hl7.org/CodeSystem/v3-Confidentiality`) | `urn:uuid:<id>`; a Questionnaire sits at its own canonical `url` |

Rules for sent bundles:
- `timestamp` is now, in IST (`+05:30`), with milliseconds.
- The focal resource is `entry[0]` in every case answer (the ClaimResponse, the Task, the CoverageEligibilityResponse after the echoed request). The four resources beside it come in the scheme's order: Patient (F15), payer Organization, hospital Organization (F17), Coverage (F18).
- Every resource in the case-answer family carries the `SUBSETTED` tag on its `meta`.
- The eligibility answer (F3) first echoes the hospital's request entries exactly as they came, then appends its own under the anchor `https://payer.nha.gov.in/coverageeligibility/v1/coverageeligibility/on_check/coverageeligibilityresponse` [REF](../references/PAYERS.md#markers); the hospital reads the last resource of each type as the payer's.
- Anchors of the other case answers hang off the payer's own base URL (configuration, [D1. payer](../database/D1-payer.md) does not hold it): `<base>/preauthorization/v1/preauth/on_submit/claimresponse/...`, `<base>/claim/v1/claim/on_submit/claimresponse/...`, `<base>/v1/task/on_submit/...`, `<base>/v1/paymentnotice/request/...`.

**Received bundles.** A hospital's bundle is read by resource type, never by position or by the path it arrived on: the callback door classifies it by its focal resource, and for a Claim by `use` ([C1. Callback Door](../callbacks/C1-callback-door.md)). Only `entry[].resource` and, where a Task points at another entry, `entry[].fullUrl` are read. The hospital's own bundle `id`, `identifier`, `timestamp` and profiles are kept in the archive ([D27. case_exchange_message](../database/D27-case-exchange-message.md)) and not read.

| Focal resource | Read as | Callback |
|---|---|---|
| `CoverageEligibilityRequest` | F2 | [C2. Coverage Eligibility Check](../callbacks/C2-coverage-eligibility-check.md) |
| `Communication` (bare, or inside a Task coded `poll` or `deliver`) | F12 | [C9. Communication](../callbacks/C9-communication.md) |
| `Task` coded `poll` naming a policy number | F4 | [C3. Insurance Plan Request](../callbacks/C3-insurance-plan-request.md) |
| `PaymentNotice` | F13 | [C10. Payment Enquiry](../callbacks/C10-payment-enquiry.md) |
| `Task` coded `cancel`, `reprocess`, `release`, `status`, or with output `paymentack` | F10 | [C7. Task Submit](../callbacks/C7-task-submit.md), [C8. Status Enquiry](../callbacks/C8-status-enquiry.md), [C11. Payment Acknowledgement](../callbacks/C11-payment-acknowledgement.md) |
| `Claim` by `use` | F8 | [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md), [C5. Claim Submit](../callbacks/C5-claim-submit.md), [C6. Predetermination](../callbacks/C6-predetermination.md) |
| `CommunicationRequest` | logged, ignored | [C9. Communication](../callbacks/C9-communication.md) |
| `ClaimResponse`, `CoverageEligibilityResponse`, `InsurancePlan`, `PaymentReconciliation` | somebody else's answer: ignored | [C1. Callback Door](../callbacks/C1-callback-door.md) |

A message with no bundle is still classified: an envelope carrying `x-hcx-status_filters` and nothing else is a status enquiry ([C8. Status Enquiry](../callbacks/C8-status-enquiry.md)). A `ProtocolResponse` in place of a bundle is the exchange refusing one of this payer's own sends and is recorded on the exchange log, never answered.

Every outbound bundle and every inbound envelope is kept whole beside its case in [D27. case_exchange_message](../database/D27-case-exchange-message.md).

#### F1F. FIELDS
Sent:

| Element written | From | Notes |
|---|---|---|
| `resourceType` | `Bundle` | |
| `id` | per family, table above | F9: the document name and the hospital's claim number (`D19.nhcx_claim_ref`, else `D19.claim_no`) |
| `identifier.system`, `.value` | the payer's base URL; the hospital's claim number | plan and query family: the bundle id, no system |
| `meta.lastUpdated` | now, IST, milliseconds | case-answer family |
| `meta.tag[0]` | `SUBSETTED` | case-answer family |
| `meta.profile[0]` | `InsurancePlanBundle` or `TaskBundle` | plan and query family |
| `meta.security[0]` | `V` "very restricted" | plan and query family |
| `meta.versionId` | `1` | F5 only |
| `type` | `collection` | |
| `timestamp` | now, IST, milliseconds | |
| `entry[].id` | equal to `fullUrl` | case-answer family |
| `entry[].fullUrl` | anchor per family | |
| `entry[].resource` | F3, F5, F6, F9, F10, F11, F13, F14, F15, F17, F18 | focal resource first |

Received (read):

| Element read | Stored in | Notes |
|---|---|---|
| `entry[].resource.resourceType`, in order | the classification ([C1. Callback Door](../callbacks/C1-callback-door.md)) and `D27.kind` | every type seen is logged when nothing here handles the bundle |
| `entry[].resource` of the focal type | F2, F4, F8, F10, F12, F13 | the first of its type, except that a Task coded `poll` yields to a Communication beside it |
| `entry[].fullUrl` | matching a Task `input[].valueReference` or `output[].valueReference` | after any `urn:uuid:` prefix |
| the whole `fhir` member | `D27.payload` | |
| top-level `type` = `ProtocolResponse` | `D27.summary` as `<code>: <message>` from `x-hcx-error_details` | a refusal of this payer's own send, matched by correlation id |

#### F1U. USED BY
- APIs: [A1. Eligibility Answer](../apis/A1-eligibility-answer.md), [A2. Insurance Plan Answer](../apis/A2-insurance-plan-answer.md), [A3. Pre-auth Answer](../apis/A3-preauth-answer.md), [A4. Claim Answer](../apis/A4-claim-answer.md), [A5. Query Request](../apis/A5-query-request.md), [A6. Payment Notice](../apis/A6-payment-notice.md), [A7. Payment Enquiry Answer](../apis/A7-payment-enquiry-answer.md), [A8. Status Answer](../apis/A8-status-answer.md), [A9. Task Answer](../apis/A9-task-answer.md), [A10. Predetermination Quote](../apis/A10-predetermination-quote.md), [A12. Transaction FHIR](../apis/A12-txn-fhir.md), [A15. Case Exchange Log](../apis/A15-case-exchange.md)
- Callbacks: [C1. Callback Door](../callbacks/C1-callback-door.md), [C2. Coverage Eligibility Check](../callbacks/C2-coverage-eligibility-check.md), [C3. Insurance Plan Request](../callbacks/C3-insurance-plan-request.md), [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md), [C5. Claim Submit](../callbacks/C5-claim-submit.md), [C6. Predetermination](../callbacks/C6-predetermination.md), [C7. Task Submit](../callbacks/C7-task-submit.md), [C8. Status Enquiry](../callbacks/C8-status-enquiry.md), [C9. Communication](../callbacks/C9-communication.md), [C10. Payment Enquiry](../callbacks/C10-payment-enquiry.md), [C11. Payment Acknowledgement](../callbacks/C11-payment-acknowledgement.md)
- FHIR: [F2. CoverageEligibilityRequest](F2-coverage-eligibility-request.md), [F3. CoverageEligibilityResponse](F3-coverage-eligibility-response.md), [F4. Task (InsurancePlan request)](F4-task-insuranceplan.md), [F5. InsurancePlan](F5-insuranceplan.md), [F8. Claim](F8-claim.md), [F9. ClaimResponse](F9-claimresponse.md), [F10. Task (claim actions and answers)](F10-task-claim-actions.md), [F11. CommunicationRequest](F11-communicationrequest.md), [F13. PaymentNotice](F13-paymentnotice.md), [F14. PaymentReconciliation](F14-paymentreconciliation.md), [F17. Organization](F17-organization.md)
