# F15. Patient

#### F15R. RESOURCE
`Patient`. **Received** in every hospital bundle that names a person: the eligibility request ([F2. CoverageEligibilityRequest](F2-coverage-eligibility-request.md)), the Claim bundles ([F8. Claim](F8-claim.md)), and read the same way in both. **Sent** in every answer this payer gives about a person: the eligibility answer ([F3. CoverageEligibilityResponse](F3-coverage-eligibility-response.md)), the verdicts ([F9. ClaimResponse](F9-claimresponse.md)), the Task answers ([F10. Task (claim actions and answers)](F10-task-claim-actions.md)), the query ([F11. CommunicationRequest](F11-communicationrequest.md)), the payment notice and reconciliation ([F13. PaymentNotice](F13-paymentnotice.md), [F14. PaymentReconciliation](F14-paymentreconciliation.md)). No profile is checked on the way in; on the way out every Patient is tagged `SUBSETTED` and carries no profile, as the scheme's does [PAYER](../references/PAYERS.md#markers).

#### F15D. DESCRIPTION
**Received.** The hospital's Patient is read for handles, never for facts. Identifiers are classified by their type coding first, then by their system when the type says nothing, because both conventions are in live use: `ABHA` or `JHN` (or an untyped identifier on a `healthid.` system) is the ABHA number, kept only when its digits make a whole 14-digit number, anything shorter being somebody's local id wearing the wrong type code; `MO` (or a `/mobile` system) is the mobile, digits only, at least 10; `MB`, `PI` or `PMJAY` is the member id, and the first untyped identifier is the member id when none was typed. The name (text, else given and family joined) is kept for the no-cover answer and as a fallback on the case; the first phone `telecom` is the mobile when no identifier gave one. On a Claim, `gender` (title-cased) and `birthDate` are read too. Nothing else is: not `address`, not `photo`, not `deceased`.

The person on a case is this payer's member ([D5. member](../database/D5-member.md)) found by those handles, not the name the hospital typed: the case's `patient_name` and `patient_gender` come from the member and fall back to the Claim's Patient, and the age is the member's age on the admission date.

**Sent, eligibility answer.** The member as this payer knows them, at `<base>/v1/coverageeligibility/on_check/patient/<member id>`: identified by the member id typed `MB` on this payer's member system, and by the ABHA typed `ABHA` when they have one; named, dated, gendered, reachable by phone, `deceasedBoolean` false. On a no-cover answer the Patient echoes the hospital's own name and handles back, because there is no member to describe.

**Sent, on a case.** The Patient beside a verdict carries the name, gender and date of birth; the one beside a Task answer carries the identifier alone, as the scheme's does. Its `id` and anchor are the member id (else the enrolment's member, else the case id), under the message's own base (`<base>/v1/preauth/on_submit/patient/<member id>` and so on). The name is the member's, else the case's snapshot; the date of birth is the member's and is left out when the member could not be read.

#### F15F. FIELDS

Received:

| Element read | Stored in | Notes |
|---|---|---|
| `identifier[]` typed `ABHA`, `JHN`, or on a `healthid.` system | handle `abha_no` (14 digits) | |
| `identifier[]` typed `MO`, or on a `/mobile` system | handle `mobile` | |
| `identifier[]` typed `MB`, `PI`, `PMJAY`, or the first untyped | handle `member_id` | |
| `name[0].text`, else `given[]` joined with `family` | `patient_name`; [D19. case](../database/D19-case.md) `patient_name` fallback; echoed on a no-cover [F3. CoverageEligibilityResponse](F3-coverage-eligibility-response.md) | |
| `telecom[]` system `phone` (or none) `.value` | handle `mobile` | when no identifier gave one |
| `gender` | [D19. case](../database/D19-case.md) `patient_gender` fallback | title-cased |
| `birthDate` | nothing on the case: the age comes from [D5. member](../database/D5-member.md) `dob` | |

Sent:

| Element written | From | Notes |
|---|---|---|
| `id` | the member id ([D5. member](../database/D5-member.md) `id`), else the enrolment's member ([D6. subscription](../database/D6-subscription.md) `member_id`), else the case id | same as the anchor's last segment |
| `meta.versionId`, `meta.lastUpdated`, `meta.tag` | `1`, now, `SUBSETTED` | |
| `identifier[0]` | type `MB` "Member Number" on `http://terminology.hl7.org/CodeSystem/v2-0203`, system this payer's member system (`<base>/member`), value the member id | always |
| `identifier[1]` | type `ABHA` "Ayushman Bharat Health Account (ABHA) ID" on `https://nrces.in/ndhm/fhir/r4/CodeSystem/ndhm-identifier-type-code`, system `https://healthid.abdm.gov.in`, value [D5. member](../database/D5-member.md) `abha_no` formatted | eligibility answer only, when the member has one |
| `name[0]` | [D5. member](../database/D5-member.md) `name` (given and family split on the first space), else [D19. case](../database/D19-case.md) `patient_name` | verdicts and the eligibility answer; left off a Task answer |
| `gender` | [D5. member](../database/D5-member.md) `gender` lower-cased, else [D19. case](../database/D19-case.md) `patient_gender` | as above |
| `birthDate` | [D5. member](../database/D5-member.md) `dob` | left out when unknown |
| `telecom[0]` | phone, [D5. member](../database/D5-member.md) `mobile` | eligibility answer only |
| `deceasedBoolean` | `false` | eligibility answer only |
| no-cover answer: `name`, `identifier[]` | the hospital's own name, member id, ABHA and mobile echoed | nothing invented |

#### F15U. USED BY
- APIs: [A1. Eligibility Answer](../apis/A1-eligibility-answer.md), [A3. Pre-auth Answer](../apis/A3-preauth-answer.md), [A4. Claim Answer](../apis/A4-claim-answer.md), [A5. Query Request](../apis/A5-query-request.md), [A8. Status Answer](../apis/A8-status-answer.md), [A9. Task Answer](../apis/A9-task-answer.md), [A10. Predetermination Quote](../apis/A10-predetermination-quote.md)
- Callbacks: [C2. Coverage Eligibility Check](../callbacks/C2-coverage-eligibility-check.md), [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md), [C5. Claim Submit](../callbacks/C5-claim-submit.md)
- FHIR: [F1. Bundle](F1-bundle.md), [F3. CoverageEligibilityResponse](F3-coverage-eligibility-response.md), [F8. Claim](F8-claim.md), [F9. ClaimResponse](F9-claimresponse.md), [F10. Task (claim actions and answers)](F10-task-claim-actions.md), [F11. CommunicationRequest](F11-communicationrequest.md), [F18. Coverage](F18-coverage.md)
- Database: [D5. member](../database/D5-member.md)
