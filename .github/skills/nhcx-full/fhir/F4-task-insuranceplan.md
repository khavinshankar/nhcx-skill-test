# F4. Task (InsurancePlan discovery)

#### F4R. RESOURCE
`Task`, profile `https://nrces.in/ndhm/fhir/r4/StructureDefinition/Task`, the only entry of a bundle with profile `https://nrces.in/ndhm/fhir/r4/StructureDefinition/TaskBundle` (F1). Direction: sent.

#### F4D. DESCRIPTION
Asks the payer for its package master for one policy and this facility. The payer answers with an InsurancePlan bundle (F5).

- The bundle `id` is `insurance-request-generic`. It holds one entry, the Task at `https://nhcx.abdm.gov.in/insurance/request`, and nothing else: no Organization, no Patient.
- The Task carries no `id`, no `authoredOn`, no `requester`, no `owner` and no `description`. The facility is named only by the `providerId` input.
- Inputs carry no display.
- At least one input is required. Both go when both are known, which is the more precise lookup. With neither the send is refused: "A plan request needs a policy code or the facility's HFR ID."
- The case number is not in the bundle. It travels as `x-hcx-workflow_id` (A3) [REF](../references/PAYERS.md#markers).
- A master already held by this facility for the same payer and policy is copied onto the case instead of asking again. Only "Fetch again" always sends this Task.

#### F4F. FIELDS

| Element | Value or source | Card / notes |
|---|---|---|
| `meta.profile[0]` | `https://nrces.in/ndhm/fhir/r4/StructureDefinition/Task` | 1..1 |
| `status` | `requested` | |
| `intent` | `order` | |
| `code.coding[0]` | system `http://terminology.hl7.org/CodeSystem/financialtaskcode`, code `poll`, no display | 1..1 |
| `input[]` (policy) | `type.coding[0]` system `https://nrces.in/ndhm/fhir/r4/CodeSystem/ndhm-task-input-type-code`, code `policyNumber`; `valueString` D9 `claim.policy_code` | 0..1, when the case has a policy code; also stored in D10 `claim_plan.policy_code` |
| `input[]` (provider) | same system, code `providerId`; `valueString` D1 `organization.identifier_value` (the facility HFR ID) | 0..1, when set; also stored in D10 `claim_plan.provider_id` |

#### F4U. USED BY
- APIs: [A3. Insurance Plan Request](../apis/A3-insurance-plan-request.md)
- FHIR: [F1. Bundle](F1-bundle.md), [F5. InsurancePlan](F5-insuranceplan.md), [F17. Organization](F17-organization.md)
