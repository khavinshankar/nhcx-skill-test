# F1. Bundle

#### F1R. RESOURCE
`Bundle`, `type: collection`, in both directions.

Profiles the application puts in `meta.profile` (all under `https://nrces.in/ndhm/fhir/r4/StructureDefinition/`):

| Profile | Carries |
|---|---|
| `CoverageEligibilityRequestBundle` | F2 |
| `TaskBundle` | F4, F10, F12 and F14 |
| `ClaimBundle` | F8 |

Direction: sent as the `fhir` member of every outbound request (A2 to A8). Received as the `fhir` member of every envelope [G8. Receive](../gateway/G8-receive.md) passes to the callbacks (C1 to C10) or [G9. Ledger](../gateway/G9-ledger.md) returns (A12). The application never checks the profile of a received bundle.

#### F1D. DESCRIPTION
Every NHCX message is one Bundle wrapped in an envelope:

```json
{"jwe_headers": {"x-hcx-sender_code": "...", "x-hcx-recipient_code": "...", "x-hcx-workflow_id": "..."},
 "fhir": { "resourceType": "Bundle", ... }}
```

The application sets only the three headers shown. [G7. Send](../gateway/G7-send.md) adds the api call id, request id, correlation id, timestamp and status ([G5. Protocol Headers](../gateway/G5-protocol-headers.md)), then encrypts ([G6. Encryption](../gateway/G6-encryption.md)). The workflow id rules belong to each API (A2 to A8).

**Sent bundles.** The application builds each one itself. In the coverage, claim-side and Task bundles every intra-bundle reference is an absolute URL under `https://nhcx.abdm.gov.in`, never a `urn:uuid` (the communication bundles of F12 differ) [REF](../references/PAYERS.md#markers). `entry[0]` is always the focal resource (its "anchor"), and the other entries follow in a fixed order.

| Message | Bundle `id` | Profile | `entry[0].fullUrl` (anchor) | Entries after the anchor, in order |
|---|---|---|---|---|
| Coverage check (F2) | `coverage-<purpose without hyphens>-request-generic`, for example `coverage-authrequirements-request-generic` | CoverageEligibilityRequestBundle | `/coverage-eligibility/request` | `/patient`, `/provider`, `/payer`, `/location`, `/coverage`, `/practitioner-role` |
| Insurance plan request (F4) | `insurance-request-generic` | TaskBundle | `/insurance/request` | none |
| Pre-authorisation (F8) | `preauth-request-generic`, `preauth-enhancement-request-generic`, `preauth-queryupdate-request-generic` | ClaimBundle | `/preauth/request`, `/preauth/enhancement`, `/preauth/queryupdate` | `/patient`, `/provider`, `/payer`, `/coverage`, `/practitioner` (`/practitioner/2`, ...), `/procedure/1..n`, `/questionnaireresponse/1..n` |
| Predetermination (F8) | `predetermination-request-generic` | ClaimBundle | `/predetermination/request` | as pre-authorisation, with no QuestionnaireResponse |
| Claim (F8) | `claim-request-generic`, `claim-queryupdate-request-generic` | ClaimBundle | `/claim/request`, `/claim/queryupdate` | as pre-authorisation |
| Cancel (F10) | `preauth-cancel-request-generic` | TaskBundle | `/preauth/cancel` | `/provider`, `/payer` |
| Status (F10) | `preauth-status-request-generic` or `claim-status-request-generic` | TaskBundle | `/preauth/status` or `/claim/status` | `/provider`, `/payer` |
| Reprocess (F10) | `claim-reprocess-request-generic` | TaskBundle | `/claim/reprocess` | `/provider`, `/payer` |
| Release (F10) | `claim-release-request-generic` | TaskBundle | `/claim/release` | `/provider`, `/payer` |
| Payment acknowledgement (F14) | `payment-notice-ack-generic` | TaskBundle | `/payment/notice-ack` | `/provider`, `/payer` |
| Communication reply and acknowledgement (F12) | a fresh UUID | TaskBundle | `urn:uuid:<task id>` | see F12 |

Rules for sent bundles (these choices differ from some of the knowledge source's example atoms, which use `urn:uuid` fullUrls, a `Bundle.identifier` and `timestamp`, `facility.abdm.gov.in` as the NPI/NIIP identifier system, a package code in place of SNOMED `71388002` on the Procedure, and no `Claim.subType`; the sandbox accepted the bundles as specified here, pre-authorisation approved under workflow 21, so they are recorded as **confirmed** [SANDBOX](../references/PAYERS.md#markers) and kept):
- `id` is a fixed string per message kind [REF](../references/PAYERS.md#markers). It does not identify the case. The case number travels in the Claim's `id` and identifier (F8) or a Task's `claimNumber` input (F10), and sometimes in `x-hcx-workflow_id` [REF](../references/PAYERS.md#markers).
- No `identifier`, no `timestamp` and no `meta.lastUpdated` on the claim-side, coverage and task bundles. Only the communication bundles (F12) carry `identifier`, `timestamp` and `meta.lastUpdated`.
- Resource `id`s: in a Claim bundle every resource has one (F8). In a coverage bundle and a Task bundle no resource has one.
- A second resource of the same kind takes a serial on its anchor: `/practitioner`, then `/practitioner/2`. Procedures and answered forms are always numbered from 1.

**Received bundles.** The payer's bundle is read by resource type, never by position, and only `entry[].resource` (plus `entry[].fullUrl` when a Task points at another entry) is used. The payer's own `id`, `identifier`, `timestamp`, `meta.tag` and anchors are ignored.
- A coverage reply repeats the request's seven entries and then appends the payer's `CoverageEligibilityResponse`, `Patient`, `Coverage` and Organizations. Where a resource type repeats, the **last** one is the payer's copy (F3) [PAYER](../references/PAYERS.md#markers).
- A pre-authorisation or claim reply carries the ClaimResponse first (F9). A Task reply carries a Task whose `output[].valueReference` points at a ClaimResponse in the same bundle (F10).
- An InsurancePlan reply carries one InsurancePlan, the payer Organization and the Questionnaires (F5, F6). When it carries only the Organization, the payer has no plan for that policy and provider (F5).
- A refusal is not a Bundle. The `fhir` member is a plain `ProtocolResponse` object (`"type": "ProtocolResponse"`, `x-hcx-status: response.error`, `x-hcx-error_details {code, message}`) and it is shown as `<code>: <message>`.

When a thread is polled (A10, A12), the reply is the newest inbound envelope, not sent by this facility, whose bundle carries the resource the reply is made of: `CoverageEligibilityResponse` (F3), `InsurancePlan` (F5), `ClaimResponse` (F9) or `Task` (F10).

Every outbound bundle and every inbound envelope is archived beside its case, whole.

#### F1F. FIELDS
Sent:

| Element | Value or source | Notes |
|---|---|---|
| `resourceType` | `Bundle` | |
| `id` | constant per message kind (table above) | a UUID on F12 only |
| `meta.profile[0]` | constant per message kind (table above) | 1..1 |
| `type` | `collection` | |
| `entry[].fullUrl` | constant anchor under `https://nhcx.abdm.gov.in` | a Practitioner, Procedure or QuestionnaireResponse beyond the first takes a serial |
| `entry[].resource` | the resource (F2 to F19) | the anchor resource first |
| `identifier`, `timestamp` | not sent | sent on F12 only |

Received (read):

| Element | Read as | Notes |
|---|---|---|
| `type` = `ProtocolResponse` (top level, in place of a Bundle) | a refusal: `x-hcx-error_details.code` and `.message` | not FHIR |
| `entry[].resource.resourceType` | which resource the reply is | first match, except CoverageEligibilityResponse, Patient and Coverage in a coverage reply: last match |
| `entry[].fullUrl` | target of a Task `output[].valueReference` | also matched on the resource `id` after any `urn:uuid:` prefix |

#### F1U. USED BY
- APIs: [A2. Coverage Eligibility Check](../apis/A2-coverage-eligibility-check.md), [A3. Insurance Plan Request](../apis/A3-insurance-plan-request.md), [A4. Pre-auth Submit](../apis/A4-preauth-submit.md), [A5. Claim Submit](../apis/A5-claim-submit.md), [A6. Task Submit (cancel, status, reprocess, release)](../apis/A6-task-submit.md), [A7. Communication Reply](../apis/A7-communication-on-request.md), [A8. Payment Notice Acknowledgement](../apis/A8-paymentnotice-on-request.md), [A12. Transaction FHIR](../apis/A12-txn-fhir.md)
- Callbacks: [C1. Callback Door](../callbacks/C1-callback-door.md), [C2. Coverage Eligibility Verdict](../callbacks/C2-coverage-eligibility-on-check.md), [C3. Authorisation Requirements Ruling](../callbacks/C3-auth-requirements-on-check.md), [C4. Insurance Plan Reply](../callbacks/C4-insuranceplan-on-request.md), [C5. Pre-auth Reply](../callbacks/C5-preauth-on-submit.md), [C6. Claim Reply](../callbacks/C6-claim-on-submit.md), [C7. Cancel Reply](../callbacks/C7-cancel-on-submit.md), [C8. Enquiry Reply](../callbacks/C8-enquiry-on-submit.md), [C9. Payer Communication](../callbacks/C9-communication-request.md), [C10. Payment Notice](../callbacks/C10-paymentnotice-request.md)
- FHIR: [F2. CoverageEligibilityRequest](F2-coverage-eligibility-request.md), [F3. CoverageEligibilityResponse](F3-coverage-eligibility-response.md), [F4. Task (InsurancePlan discovery)](F4-task-insuranceplan.md), [F8. Claim](F8-claim.md), [F10. Task (claim actions)](F10-task-claim-actions.md)
