# F4. Task (InsurancePlan request)

#### F4R. RESOURCE
`Task`, received on `v1/insuranceplan/request` as the only entry of a hospital's Task bundle ([F1. Bundle](F1-bundle.md)). No profile is checked. It is read by [C3. Insurance Plan Request](../callbacks/C3-insurance-plan-request.md) and answered at once by [A2. Insurance Plan Answer](../apis/A2-insurance-plan-answer.md) with an InsurancePlan bundle ([F5. InsurancePlan](F5-insuranceplan.md) with [F6. Questionnaire](F6-questionnaire.md)), or an empty plan when nothing matches.

#### F4D. DESCRIPTION
The request is a Task rather than a resource of the thing being asked about: "send me the plan", not "here is a plan". It carries what it wants in `Task.input`, each entry typed by a code from the NDHM task-input system.

**What makes a Task a plan request.** The Task is coded `poll` on `http://terminology.hl7.org/CodeSystem/financialtaskcode` (the reference hospital's spelling, intent `order`), or it carries no code and its `intent` is empty or `plan` (the older IG spelling). A Task coded anything else (`cancel`, `status`, `reprocess`, `release`) is somebody else's errand and is read as [F10. Task (claim actions and answers)](F10-task-claim-actions.md) instead. The bundle's `Organization`, when it carries one, names the requester for the audit line; the payer's own Organization is not in a request, so there is nothing to tell apart.

**A Task with no inputs is still a request.** The scheme reads an empty policy number as "everything this provider is empanelled for", and refusing to parse it would turn a legitimate question into a dead letter [PAYER](../references/PAYERS.md#markers). This payer answers it with the empty plan, because it has no product to name.

**Which product.** The `policyNumber` input is looked up, in order: a product by id, UIN or alias ([D12. policy](../database/D12-policy.md), [D16. policy_alias](../database/D16-policy-alias.md)); an enrolment by its id ([D6. subscription](../database/D6-subscription.md)), because this payer's own eligibility answer hands the enrolment id out as the Coverage id and a handle it taught the hospital has to resolve here too; a retired product by its code, which is answered with the default product everyone was moved onto [REF](../references/PAYERS.md#markers) [SANDBOX](../references/PAYERS.md#markers). Nothing found is answered with the empty plan, not refused: the IG says an empty plan is a legitimate outcome, and silence would leave the asking hospital's poll running until it timed out.

**What is not read.** `status`, `intent` beyond the check above, `authoredOn`, `requester`, `owner`, `description`, and any input display. The workflow id the request travels under ([REF](../references/PAYERS.md#markers): the reference hospital sends its case number) is echoed on the answer's `x-hcx-workflow_id` and never routed on.

#### F4F. FIELDS

| Element read | Stored in | Notes |
|---|---|---|
| `Task.code.coding[]` code on `http://terminology.hl7.org/CodeSystem/financialtaskcode` (else the first coding of any system) | decides the kind: `poll` is a plan request | a code from another system is taken when no coding names the system [REF](../references/PAYERS.md#markers) |
| `Task.intent` | decides the kind when there is no code: empty or `plan` is a plan request | |
| `Task.input[]` with `type.coding[]` code `policyNumber` on `https://nrces.in/ndhm/fhir/r4/CodeSystem/ndhm-task-input-type-code`, `valueString` | the ask's `policy_number`; the audit detail on [D31. audit_log](../database/D31-audit-log.md) | the product, as the hospital spells it: an id, a UIN, an alias, or an enrolment id |
| `Task.input[]` with code `providerId`, `valueString` | the ask's `provider_id`; the audit detail | the facility asking; a live payer would filter the plan to what the network agreement covers with it [REF](../references/PAYERS.md#markers) |
| `Organization.name` (any Organization in the bundle) | the ask's `provider_name`; the audit line | for a person reading the trail |
| the whole bundle | nothing on a case | a plan request opens no case; the delivery outcome names the policy served or `no_plan` |

Inputs are matched on their code with the system as a preference, not a requirement: a builder that left the system off `policyNumber` still gets its plan.

#### F4U. USED BY
- APIs: [A2. Insurance Plan Answer](../apis/A2-insurance-plan-answer.md)
- Callbacks: [C1. Callback Door](../callbacks/C1-callback-door.md), [C3. Insurance Plan Request](../callbacks/C3-insurance-plan-request.md)
- FHIR: [F1. Bundle](F1-bundle.md), [F10. Task (claim actions and answers)](F10-task-claim-actions.md), [F18. Coverage](F18-coverage.md)
- Database: [D16. policy_alias](../database/D16-policy-alias.md)
