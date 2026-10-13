# F18. Coverage

#### F18R. RESOURCE
`Coverage`. **Received** in the eligibility request ([F2. CoverageEligibilityRequest](F2-coverage-eligibility-request.md)) and the Claim bundles ([F8. Claim](F8-claim.md)), where it names the policy the hospital thinks the person is on. **Sent** in the eligibility answer ([F3. CoverageEligibilityResponse](F3-coverage-eligibility-response.md)) and beside every answer about a case ([F9. ClaimResponse](F9-claimresponse.md), [F10. Task (claim actions and answers)](F10-task-claim-actions.md), [F11. CommunicationRequest](F11-communicationrequest.md), [F13. PaymentNotice](F13-paymentnotice.md), [F14. PaymentReconciliation](F14-paymentreconciliation.md)), where it is the enrolment ([D6. subscription](../database/D6-subscription.md)) the case is filed under. No profile is checked on the way in; on the way out it carries no profile and is tagged `SUBSETTED` [PAYER](../references/PAYERS.md#markers).

#### F18D. DESCRIPTION
**Received.** Two things are read and both are hints, never keys: the first identifier's value as the policy code the hospital quotes, ignored when it is `NONE` (the discovery value, "which plan is the question") or the older `UNDEFINED`; and `subscriberId`, what the hospital's desk actually typed, folded into whichever handle is still empty by its shape ([F2. CoverageEligibilityRequest](F2-coverage-eligibility-request.md)). On a Claim the `period` gives the admission and expected discharge until the Claim's own dates override it, because the period is the cover, which a hospital may send as the policy year. `relationship`, `status`, `type`, `payor` and `class` are not read. The policy code is not used to find the enrolment: the enrolment is found by the person, and a hospital quoting the wrong plan still gets the cover the person actually has.

**Sent, eligibility answer.** The enrolment as the exchange sees it, at `.../coverage/<enrolment id>` with `id` the enrolment id: identified by the plan code (the product's UIN, else its id) typed `NH`; `status` `active` for an active enrolment and `cancelled` otherwise (a paused enrolment is not entered in error and is not a draft; `cancelled` is the one FHIR status that says it does not answer); typed `HIP` "health insurance plan policy"; subscriber and beneficiary the Patient, relationship `self` (the enrolled member is the subscriber; a dependant on a floater is answered under the policyholder's cover [REF](../references/PAYERS.md#markers)); the cover period; the payer as payor; and one `class` naming the product, typed `XV`. The enrolment id becomes the handle the hospital may later quote on a plan request ([F4. Task (InsurancePlan request)](F4-task-insuranceplan.md)).

**Sent, on a case.** The same Coverage beside a verdict or a Task answer, under the message's base, with `id` the case's enrolment (else the case id). What the payer has not looked up is left out: no `period` when the enrolment could not be read, no `identifier` or `class` when the product could not.

#### F18F. FIELDS

Received:

| Element read | Stored in | Notes |
|---|---|---|
| `identifier[0].value` | the policy code the hospital quotes (the ask's `policy_code`; the subscriber fallback handle on a Claim) | `NONE`, `UNDEFINED` ignored |
| `subscriberId` | whichever handle is still empty: ABHA (14 digits), mobile (10 to 12 digits), else member id | |
| `period.start`, `period.end` (Claim bundles) | [D19. case](../database/D19-case.md) `admitted_on`, `expected_discharge`, until the Claim's dates override them | dates trimmed to the calendar day |

Sent:

| Element written | From | Notes |
|---|---|---|
| `id` | [D6. subscription](../database/D6-subscription.md) `id` (the enrolment), else the case id | same as the anchor's last segment |
| `meta.tag` | `SUBSETTED` | |
| `identifier[0]` | type `NH` "National Health Plan Identifier" on `http://terminology.hl7.org/CodeSystem/v2-0203`, system this payer's base url, value [D12. policy](../database/D12-policy.md) `uin` else `id` | left out on a case when the product is unknown |
| `status` | `active` when [D6. subscription](../database/D6-subscription.md) `status` is `active`, else `cancelled` | `active` on a case when the enrolment is unknown |
| `type.coding[0]` | `HIP` "health insurance plan policy" on `http://terminology.hl7.org/CodeSystem/v3-ActCode` | |
| `subscriber`, `beneficiary` | the Patient's fullUrl ([F15. Patient](F15-patient.md)) | `subscriber` on the eligibility answer only |
| `relationship.coding[0]` | `self` "Self" on `http://terminology.hl7.org/CodeSystem/subscriber-relationship` | eligibility answer only |
| `period.start`, `period.end` | [D6. subscription](../database/D6-subscription.md) `pstart`, `pend` as instants | left out on a case when the enrolment is unknown |
| `payor[0]` | the payer Organization's fullUrl ([F17. Organization](F17-organization.md)) | |
| `class[0]` | `id` [D12. policy](../database/D12-policy.md) `id`, `name` [D12. policy](../database/D12-policy.md) `name` (eligibility answer only), type `XV` "Health Plan Identifier", `value` the plan code | left out on a case when the product is unknown |

#### F18U. USED BY
- APIs: [A1. Eligibility Answer](../apis/A1-eligibility-answer.md), [A3. Pre-auth Answer](../apis/A3-preauth-answer.md), [A4. Claim Answer](../apis/A4-claim-answer.md), [A5. Query Request](../apis/A5-query-request.md), [A8. Status Answer](../apis/A8-status-answer.md), [A9. Task Answer](../apis/A9-task-answer.md), [A10. Predetermination Quote](../apis/A10-predetermination-quote.md)
- Callbacks: [C2. Coverage Eligibility Check](../callbacks/C2-coverage-eligibility-check.md), [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md), [C5. Claim Submit](../callbacks/C5-claim-submit.md)
- FHIR: [F1. Bundle](F1-bundle.md), [F3. CoverageEligibilityResponse](F3-coverage-eligibility-response.md), [F8. Claim](F8-claim.md), [F9. ClaimResponse](F9-claimresponse.md), [F10. Task (claim actions and answers)](F10-task-claim-actions.md), [F11. CommunicationRequest](F11-communicationrequest.md)
