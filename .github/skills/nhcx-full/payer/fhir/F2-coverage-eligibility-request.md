# F2. CoverageEligibilityRequest

#### F2R. RESOURCE
`CoverageEligibilityRequest`, received on `v1/coverageeligibility/check` inside a bundle a hospital built ([F1. Bundle](F1-bundle.md)). No profile is required or checked: a discovery request in the wild follows the scheme's reference bundle (patient identifiers typed `PMJAY`, `JHN`, `PI`) and a validation request the generic NRCeS profile (typed `ABHA`, `MO`, `MB`), and the exchange carries whatever the sender's builder made [PAYER](../references/PAYERS.md#markers). It is read by [C2. Coverage Eligibility Check](../callbacks/C2-coverage-eligibility-check.md) and answered at once by [A1. Eligibility Answer](../apis/A1-eligibility-answer.md) with an [F3. CoverageEligibilityResponse](F3-coverage-eligibility-response.md).

#### F2D. DESCRIPTION
The question "is this person covered", and for one purpose "what do you need with this procedure set". The parser walks the bundle as plain maps, takes every handle it recognises, and never fails on a shape it merely does not know: an odd bundle still deserves an answer, and "no cover found" is one. The only condition for the bundle to count as an eligibility question is that a `CoverageEligibilityRequest` resource is in it; nothing else in the bundle is required.

**Purposes.** `purpose[]` is read in full and every value is kept in order. What the answer does with them:

| `purpose` | The question | Answered with (F3) |
|---|---|---|
| `validation` | is the cover in force | the enrolment in force, lapsed, or no cover |
| `benefits` | what does the cover pay | the same, with the wallet as the benefit |
| `discovery` | which plan is this person on (the Coverage identifier is `NONE`) | the same, found by ABHA, mobile or member id |
| `auth-requirements` | what is needed for these packages | one item per asked item: the package rate, the documents per phase and the treatment-guideline form |

A request with no purpose at all is answered as a validation [REF](../references/PAYERS.md#markers).

**Handles.** Everything the person might be found by is collected, in this precedence, then reduced to three lookups (ABHA, mobile, member id) the enrolment store runs ([D6. subscription](../database/D6-subscription.md) joined to [D5. member](../database/D5-member.md)):

- `Patient.identifier[]`, classified by the type coding first, then by the system when the type says nothing: `ABHA` or `JHN` is the ABHA number (kept only when its digits are a whole 14-digit number); `MO` the mobile (digits only, at least 10); `MB`, `PI` or `PMJAY` the member id; an untyped identifier on a `healthid.` system is the ABHA, on a `/mobile` system the mobile, otherwise the first untyped value becomes the member id.
- `Patient.name[0]` (text, else given and family joined) as the patient name, echoed on a no-cover answer.
- `Patient.telecom[]` with system `phone` (or none) as the mobile, when no identifier gave one.
- `Coverage.subscriberId`, what the hospital's desk actually typed: folded into whichever slot is still empty by its shape, 14 digits is an ABHA, 10 to 12 digits with at most separators is a mobile, anything else a member id.
- `Coverage.identifier[0].value` as the policy code, unless it is `NONE` or `UNDEFINED` (a discovery).

**Provider.** The `Organization` typed `prov` is the asker: its first identifier is the facility registry id and its `name` the name. Both are echoed back as the requestor Organization of the answer ([F17. Organization](F17-organization.md)) and written on the audit trail. The payer Organization a request carries is not read.

**Items.** `item[]` is read only into the auth-requirements ruling. An item with no `productOrService` code is not a question anybody can answer and is dropped; the rest are kept in the order sent, because the answer is per item and the asking desk matches them up by position.

**What is not read.** `priority`, `created`, `enterer`, `facility`, `insurance[].focal`, the `Location`, the `PractitionerRole` and the Coverage's `relationship`. The request's whole bundle is kept: the answer echoes the request's entries before appending its own ([F3. CoverageEligibilityResponse](F3-coverage-eligibility-response.md)).

#### F2F. FIELDS

| Element read | Stored in | Notes |
|---|---|---|
| `CoverageEligibilityRequest.purpose[]` | the ask's `purposes`; the checklist step ticked per purpose [SANDBOX](../references/PAYERS.md#markers) | in order; `auth-requirements` switches the answer to the ruling |
| `CoverageEligibilityRequest.item[].productOrService.coding[0]` code, display, system | the ask's `items[]` (`code`, `display`, `system`) | items without a code are dropped |
| `item[].category.coding[0].code` | `items[].category` | |
| `item[].quantity.value`, `item[].unitPrice.value`, `item[].net.value` | `items[].quantity`, `.unit_price`, `.net` | as sent; the answer says what the payer allows |
| `Patient.identifier[]` typed `ABHA`, `JHN`, or on a `healthid.` system | handle `abha_no` | canonical 14 digits, else ignored |
| `Patient.identifier[]` typed `MO`, or on a `/mobile` system | handle `mobile` | digits only, at least 10 |
| `Patient.identifier[]` typed `MB`, `PI`, `PMJAY`, or the first untyped value | handle `member_id` | first one wins |
| `Patient.name[0].text`, else `given` joined with `family` | `patient_name` | echoed on the no-cover answer |
| `Patient.telecom[]` (system `phone` or none) `.value` | handle `mobile` | only when no identifier gave one |
| `Coverage.subscriberId` | whichever of `abha_no`, `mobile`, `member_id` is still empty, by shape | |
| `Coverage.identifier[0].value` | `policy_code` | ignored when `NONE` or `UNDEFINED` |
| `Organization` (type `prov`) `identifier[0].value`, `name` | `provider_id`, `provider_name` | echoed in F3 as the requestor |
| the whole bundle | the request half of the answer ([F3. CoverageEligibilityResponse](F3-coverage-eligibility-response.md)); the audit row on [D31. audit_log](../database/D31-audit-log.md) names the sender, correlation id and enrolment | nothing is written to a case: an eligibility question opens none |

The enrolment found becomes `subscription_id` in the delivery outcome and the audit line; the case tables ([D19. case](../database/D19-case.md)) are not touched by this resource.

#### F2U. USED BY
- Screens: [S4. Members](../screens/S4-members.md)
- APIs: [A1. Eligibility Answer](../apis/A1-eligibility-answer.md)
- Callbacks: [C1. Callback Door](../callbacks/C1-callback-door.md), [C2. Coverage Eligibility Check](../callbacks/C2-coverage-eligibility-check.md)
- FHIR: [F1. Bundle](F1-bundle.md), [F3. CoverageEligibilityResponse](F3-coverage-eligibility-response.md), [F8. Claim](F8-claim.md), [F15. Patient](F15-patient.md), [F18. Coverage](F18-coverage.md), [F19. Other resources](F19-other-resources.md)
