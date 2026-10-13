# F2. CoverageEligibilityRequest

#### F2R. RESOURCE
`CoverageEligibilityRequest`, profile `https://nrces.in/ndhm/fhir/r4/StructureDefinition/CoverageEligibilityRequest`, inside a bundle with profile `https://nrces.in/ndhm/fhir/r4/StructureDefinition/CoverageEligibilityRequestBundle` (F1). Direction: sent.

#### F2D. DESCRIPTION
One bundle shape serves all four purposes. The bundle has seven entries, always in this order:

| # | `fullUrl` | Resource | Spec |
|---|---|---|---|
| 1 | `https://nhcx.abdm.gov.in/coverage-eligibility/request` | CoverageEligibilityRequest | this file |
| 2 | `.../patient` | Patient: the member id only | F15 |
| 3 | `.../provider` | Organization, the facility | F17 |
| 4 | `.../payer` | Organization, the payer | F17 |
| 5 | `.../location` | Location | F19 |
| 6 | `.../coverage` | Coverage | F18 |
| 7 | `.../practitioner-role` | PractitionerRole, the enterer | F16 |

No resource carries an `id`. The bundle `id` is `coverage-<purpose without hyphens>-request-generic`.

Purposes:

| `purpose` | Sent when | Coverage identifier (F18) | `item[]` |
|---|---|---|---|
| `validation` | the eligibility check: is the policy in force | the policy code (required) | none |
| `benefits` | the eligibility check: what the policy covers for the quoted packages | the policy code (required) | the quoted lines, when there are any |
| `discovery` | the eligibility check, policy not yet known | the policy code if entered, else `NONE` | none |
| `auth-requirements` | the procedure-set ruling, by the operator or automatically before a pre-authorisation or enhancement | the case's policy code, else `NONE` | the quoted lines (at least one) |

Rules:
- Patient demographics are never sent. The payer returns them (F3).
- An `item` names a package and nothing else: no money, no diagnosis, no sequence.
- One `item` per procedure or implant line. A ward or ICU tier (stratification line) is not an item. It rides as a `modifier` on the procedure it was quoted through [PAYER](../references/PAYERS.md#markers): the procedure whose code is the tier's `parent_code`, else the first procedure whose plan costs offer that tier, else the first procedure. A tier with no procedure to ride on goes as an item of its own.
- `quantity` is sent as a whole number when it is whole (`1`, not `1.0`).
- The builder refuses a bundle without a member id ("A coverage check needs the member id to ask about."), without the facility registry id ("A coverage check needs the facility's registry id.") or without a payer code ("A coverage check needs the payer's participant code."), and any other purpose ("'<purpose>' is not a coverage eligibility purpose.").

#### F2F. FIELDS

| Element | Value or source | Card / notes |
|---|---|---|
| `meta.profile[0]` | `https://nrces.in/ndhm/fhir/r4/StructureDefinition/CoverageEligibilityRequest` | 1..1 |
| `identifier[0].system` | `https://nhcx.abdm.gov.in` | 1..1, no `value` |
| `status` | `active` | |
| `priority` | `http://terminology.hl7.org/CodeSystem/processpriority` `normal` "Normal" | |
| `purpose[0]` | the purpose; the eligibility check stores it in D9 `claim.purpose` | 1..1 |
| `patient.reference` | `https://nhcx.abdm.gov.in/patient` (F15) | |
| `created` | now, `YYYY-MM-DDThh:mm:ss+05:30` | |
| `enterer.reference` | `https://nhcx.abdm.gov.in/practitioner-role` (F16) | |
| `provider.reference` | `https://nhcx.abdm.gov.in/provider` (F17) | |
| `insurer.reference` | `https://nhcx.abdm.gov.in/payer` (F17) | |
| `facility.reference` | `https://nhcx.abdm.gov.in/location` (F19) | |
| `insurance[0].focal` | `true` | 1..1 |
| `insurance[0].coverage.reference` | `https://nhcx.abdm.gov.in/coverage` (F18) | |
| `item[]` | one per procedure or implant line in D16 `claim_line` | `benefits` and `auth-requirements` only; left out when empty |
| `item[].category` | system `https://nhcx.abdm.gov.in/category-code`, code D16 `claim_line.category_code`, display `.category_display` | only when the line has a category code |
| `item[].productOrService` | system `https://nhcx.abdm.gov.in/product-code`, code D16 `claim_line.code`, display `.display` | 1..1 |
| `item[].quantity.value` | D16 `claim_line.quantity`, else 1 | whole number when whole |
| `item[].modifier[]` | per tier riding on the line: code D16 `claim_line.code` of the tier, display `.display`, **no system** [REF](../references/PAYERS.md#markers) | only when tiers ride on it |

Inputs to the other six entries (details in F15 to F19): the member id (the check form's member id, stored in D9 `claim.member_id`; the ruling reads `claim.member_id`), the policy code (form, or D9 `claim.policy_code`), D1 `organization.identifier_value` and `.name` for the facility and location, D9 `claim.payer_id` (default the configured payer code) and `claim.payer_name` for the payer.

#### F2U. USED BY
- Screens: [S17. Beneficiary Discovery](../screens/S17-beneficiary-discovery.md)
- APIs: [A2. Coverage Eligibility Check](../apis/A2-coverage-eligibility-check.md)
- Callbacks: [C2. Coverage Eligibility Verdict](../callbacks/C2-coverage-eligibility-on-check.md), [C3. Authorisation Requirements Ruling](../callbacks/C3-auth-requirements-on-check.md)
- FHIR: [F1. Bundle](F1-bundle.md), [F3. CoverageEligibilityResponse](F3-coverage-eligibility-response.md), [F15. Patient](F15-patient.md), [F16. Practitioner and PractitionerRole](F16-practitioner.md), [F17. Organization](F17-organization.md), [F18. Coverage](F18-coverage.md), [F19. Other bundle resources](F19-other-resources.md)
