# F5. InsurancePlan

#### F5R. RESOURCE
`InsurancePlan`. Direction: received on `insuranceplan/on_request`, in a bundle the payer profiles as `https://nrces.in/ndhm/fhir/r4/StructureDefinition/InsurancePlanBundle` or not at all. No profile is checked. Extensions read: `https://nrces.in/ndhm/fhir/r4/StructureDefinition/Claim-Condition` and `https://nrces.in/ndhm/fhir/r4/StructureDefinition/Claim-SupportingInfoRequirement` (also spelled `claimCondition` / `claimSupportingInfoRequirement`).

#### F5D. DESCRIPTION
The payer's machine-readable package master for one policy and one facility, the answer to F4. It is flattened into one D10 `claim_plan` row, one D11 `claim_plan_benefit` row per package or implant, and one D12 `claim_plan_form` row per distinct Questionnaire (F6) in the same bundle. A new answer replaces the stored master wholesale.

Only the **first** InsurancePlan in the bundle is read. Two published shapes are read, because the payer chooses, and PMJAY sends both for the same packages [PAYER](../references/PAYERS.md#markers):

| Shape | Tree | Gives |
|---|---|---|
| Package master | `plan[] > specificCost[] > category, benefit[] > type, cost[]` | package code, name, speciality, rate, tiers, implants |
| Indemnity | `coverage[] > type, benefit[] > type, limit[]` | benefit code, name, category, limit |

The two are merged on the package code. `specificCost` is read first and wins, and `coverage` adds only codes `specificCost` did not carry. They are never concatenated, which would double every package.

**Costs (package master).** The cost whose `type.coding[0].code` is `Procedure` is the package rate (matched on the code, never on the display, which is a sentence). A rate of 0 is real: many packages are priced by their ward tiers alone [PAYER](../references/PAYERS.md#markers). Every other cost (`Stratification` for the ward, HDU and ICU tiers; `Implant`) is money over and above the rate. It is kept as an extra, named by its first `qualifiers[]` coding. A benefit is typed `Procedure` when it has a rate, else `Implant` when one of its extras is an Implant, else left untyped.

**Limits (indemnity).** The first limit whose `code` is absent or equals the benefit's own code is the rate. The others are extras of type `Limit`. A benefit found here is typed `Implant` when its code appears as the qualifier of an `Implant` cost anywhere under `specificCost`, else `Procedure`. `benefit.requirement` is kept as both the cost type and the requirement.

**Extensions.** A plan element (the InsurancePlan itself, a `plan`, a `coverage`, a benefit) can carry two families of complex extension, told apart by url with hyphens and underscores removed and case ignored:
- **Conditions** (`Claim-Condition`) constrain whether the package can be claimed. Where the extension has children, a child's url tail names the condition (`.../Claim-Condition/IsDayCare` gives `IsDayCare: "Y"`). A child named `code`, `type` or `condition` paired with one named `value` is read as that code and value. An extension with no children is keyed by its own url tail. The value is the child's `value[x]`: a CodeableConcept gives its display, else code.
- **Document requirements** (`Claim-SupportingInfoRequirement`) name a document that must ride with the claim, or a form to fill. Its children are a category and a code CodeableConcept (child urls `category` / `code`, or `SupportInfoCategory` / `SupportInfoCode`), plus an optional `documentationUrl` pointing at a Questionnaire (F6): `/policy/questionnaire/<id>` is a policy form, `/policy/stgquestionnaire/<id>` a standard treatment guideline checklist. The pointer's value is read from whichever child the payer uses: `valueUrl`, `valueUri`, `valueString`, `valueCanonical` **or `valueReference.reference`**. The IRDAI sandbox payer sends the Reference shape, `{"url": "documentationUrl", "valueReference": {"reference": "https://.../Questionnaire/<id>", "display": "<STG title>"}}` [PAYER](../references/PAYERS.md#markers); a reader that takes only the URL shapes loses every package's STG form (`form` null on each requirement), so read both. PMJAY nests one requirement per document instead (`.../Claim-SupportingInfoRequirement/MG0111A/100455/MAND0455`, each with its own category and code) [PAYER](../references/PAYERS.md#markers). When any child has children of its own, each such child is one requirement and flat children are ignored. A requirement with neither a code nor a form is dropped.

A benefit's conditions are its plan element's conditions overlaid with its own. Its document list is the plan element's list followed by its own. Requirements on the InsurancePlan resource itself are policy-wide (proof of identity, proof of address, forms every claim needs) and are stored once on D10.

**Empty answers.** A bundle with no InsurancePlan (only the payer Organization) is a valid answer, "no product under this policy for this facility": the plan settles as `empty` with the message "The payer reply carries no InsurancePlan. The payer has no package master filed under this policy." A plan with zero benefits also settles as `empty`. Otherwise `ready`. A ProtocolResponse sets the plan to `error`.

What the stored master drives later: the package picker and line rates (D16), each package's `ProcedureType` condition as `Claim.procedure[].type` (F8), the documents and forms asked for when no auth-requirements ruling exists (F3), the `LM100` rate on a LAMA/DAMA claim (F8) [PAYER](../references/PAYERS.md#markers).

#### F5F. FIELDS
Into D10 `claim_plan`:

| Element read | Stored in | Notes |
|---|---|---|
| `identifier[0].value`, else `id` | `plan_identifier` | |
| `name` | `plan_title` | |
| `type[0].coding[0].display`, else its `text`, else the first `plan[].type` display | `plan_type` | |
| first `plan[].generalCost[].cost.value` | `sum_insured` | the overall sum insured |
| `extension[]` of the requirement family on the InsurancePlan itself | `policy_documents` (JSON list of `{category, category_display, code, display, form}`) | |
| the whole bundle | `response_json` | also `status` `ready` / `empty`, `fetched_at` |

Into D11 `claim_plan_benefit`, from `plan[].specificCost[]`:

| Element read | Stored in | Notes |
|---|---|---|
| `specificCost[].category.coding[0]` code / display | `category_code` / `category_display` | the speciality |
| `benefit[].type.coding[0]` code / display (else `text`) | `code` / `display` | a benefit without a code is skipped; a code already seen is skipped |
| `benefit[].cost[]` with `type` code `Procedure`: `value.value`, `value.unit` (else `value.code`) | `rate`, `currency` | first such cost; `cost_type` = `Procedure` when present |
| other `cost[]`: `type` code, `qualifiers[0].coding[0]` code / display, `value.value`, `value.unit` | `extras` (JSON list of `{type, code, label, rate, currency}`) | `Stratification`, `Implant` |
| computed | `kind` | `Procedure` with a rate, else `Implant` with an Implant extra, else null |
| `Claim-Condition` on the `plan[]` element and on the benefit | `conditions` (JSON object) | benefit overrides plan |
| `Claim-SupportingInfoRequirement` on the `plan[]` element and on the benefit | `supporting_info` (JSON list of `{category, category_display, code, display, form}`) | plan first |
| none | `requirement` | null on this shape |

From `coverage[]` (only codes not already taken):

| Element read | Stored in | Notes |
|---|---|---|
| `coverage[].type.coding[0]` code / display | `category_code` / `category_display` | |
| `coverage[].benefit[].type.coding[0]` code / display | `code` / `display` | |
| first `limit[]` with no code or the benefit's own code: `value.value`, `value.unit` | `rate`, `currency` | |
| other `limit[]`: `code.coding[0]` code / display, `value` | `extras` (type `Limit`) | |
| `benefit[].requirement` | `requirement` and `cost_type` | |
| computed | `kind` | `Implant` when the code is an Implant qualifier elsewhere, else `Procedure` |
| extensions on the `coverage[]` element and the benefit | `conditions`, `supporting_info` | as above |

`seq` numbers the rows from 1 in reading order. Questionnaires go to D12 (F6).

#### F5U. USED BY
- Screens: [S7. Insurance Plan](../screens/S7-insurance-plan.md)
- Callbacks: [C4. Insurance Plan Reply](../callbacks/C4-insuranceplan-on-request.md)
- FHIR: [F1. Bundle](F1-bundle.md), [F3. CoverageEligibilityResponse](F3-coverage-eligibility-response.md), [F4. Task (InsurancePlan discovery)](F4-task-insuranceplan.md), [F6. Questionnaire](F6-questionnaire.md)
