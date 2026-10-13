# S7. Policy Configurator Screen

#### S7R. ROUTE
`/policies/new`, `/policies/edit/:id`

| Endpoint | Purpose |
|---|---|
| `GET policies/:id` | The product being edited |
| `POST policies` | Create |
| `PATCH policies/:id` | Save changes |
| `GET terminology` | The value sets every code is picked from |
| `GET procedures` | The registry to attach procedures from |

Breadcrumb: Policies (S6) > `<product name>` or "Create New Policy Product"

#### S7D. DESCRIPTION
Everything on this page ends up in the InsurancePlan this payer serves to a hospital ([F5. InsurancePlan](../fhir/F5-insuranceplan.md), [A2. Insurance Plan Answer](../apis/A2-insurance-plan-answer.md)) and in the eligibility answer's benefits ([F3. CoverageEligibilityResponse](../fhir/F3-coverage-eligibility-response.md)). Nothing here types a code or its display by hand: every code is picked from a published value set ([D4. terminology_code](../database/D4-terminology-code.md)), so the display shown to an underwriter and the display written into a bundle cannot drift apart. The page saves as a whole with "Publish Policy" (new) or "Save Policy Changes"; "Cancel" returns to S6.

**1. Policy Overview & Coverage Term**

| Field | Control | Rule |
|---|---|---|
| Policy Product Name | text | "Enter the policy name" |
| Other Names, comma separated, as filed or marketed | text; split on commas, trimmed, duplicates dropped | aliases ([D16. policy_alias](../database/D16-policy-alias.md)) a hospital may quote on a plan request |
| IRDAI UIN | text; "The number the product is filed under. Blank until it is filed." | |
| Status | select: Draft, Active, Retired, Unknown | "A product is draft, active, retired or unknown" |
| Base Sum Insured (₹) | number | "Enter the sum assured" (must be above zero) |
| Product Type | select from `ndhm-insuranceplan-type`, "`<code>`, `<display>`" | "Choose the product type" |
| Plan Type | select from `ndhm-plan-type`; "An enrolment can be sold on a different one." | "Choose the plan type" |

A product carries no dates: the period a member is covered for is on their enrolment (S5).

**2. Policy Monetary Sub-Limits & Specific Cost Caps.** One row per capped concept ([D18. policy_sub_limit](../database/D18-policy-sub-limit.md)): Capped Concept (SNOMED CT) as a select from the sub-limit value set, "`<display>` (`<code>`)", and Cap (₹). "Add Sub-Limit" offers the first concept nothing has capped yet; "Every concept in the value set is already capped" when none is left. A new product opens with four concepts at zero (the reference's defaults: room rent, ICU, ambulance, and a fourth [REF](../references/PAYERS.md#markers)), and a zero cap is dropped on save: "A cap of zero is no cap, remove the row instead." Server rules: "Every sub-limit needs a SNOMED concept", "Each concept can only be capped once", "A sub-limit must be more than zero, remove it instead", "A sub-limit cannot exceed the sum assured". Empty: "No sub-limits. The plan pays up to the sum insured for everything it covers."

**3. Exclusions.** What the plan does not pay for, against the standardised IRDAI codes ([D17. policy_exclusion](../database/D17-policy-exclusion.md)): Exclusion as a select from `ndhm-claim-exclusion`, Wording (free text), and optionally Excluded Item Code and Excluded Item Name, the one concept the wording is about. "Add Exclusion" offers the next code not yet stated; "Every exclusion in the value set is already stated". Server rules: "Every exclusion needs a code", "Each exclusion can only be stated once", "An excluded item needs both a code and a display name". Empty: "No exclusions configured, the plan states none."

**4. Coverage Clauses & Pre/Post Hospitalization Terms.** Pre-Hospitalization Limit (Days), default 60, and Post-Hospitalization Limit (Days), default 90. They are written back into the two benefits that carry them, as a limit of `<=` that many `day` with the wording "Medical Expenses incurred up to N days prior to admission to the hospital" and "... after discharge from the hospital". The clause set itself ([D14. policy_coverage_clause](../database/D14-policy-coverage-clause.md), [D15. policy_clause_benefit](../database/D15-policy-clause-benefit.md)) is edited from the product's own clauses; a new product opens with the standard IRDAI set (inpatient care with ICU, blood and oxygen as benefits; post-hospital care; pre-hospital care; ambulance up to 10% of the sum insured; day care; organ donor) [REF](../references/PAYERS.md#markers). Server rules: "Every coverage clause needs a SNOMED code", "Each SNOMED concept can only be covered once", "Every coverage clause needs a display name", "Every benefit needs a SNOMED code and a display name", "Each benefit can only be listed once per clause", "A benefit limit needs a value, a comparator and a unit", "A benefit limit cannot be negative", "A limit comparator must be <=, = or >=".

**5. Attached Procedure Stage Document Rules (n).** Every procedure in the registry as a row: name, code, and "Pre-Auth (`<n>` docs) | Final Claim (`<n>` docs)"; clicking toggles "Attached to Policy" and "Click to Attach". Procedures are attached by reference ([D13. policy_procedure](../database/D13-policy-procedure.md)): the document rules and the treatment-guideline questions live on the registry entry (S9), so a rule corrected there applies to every product at once, and the InsurancePlan lists each covered procedure as a benefit with its rate, documents per phase and questionnaire ([F5. InsurancePlan](../fhir/F5-insuranceplan.md), [F6. Questionnaire](../fhir/F6-questionnaire.md)). A new product opens with every procedure attached.

Toasts: "Policy `<id>` created!", "Policy `<id>` updated successfully!". Screen refusal: "Policy name is required". The default sandbox product opens read-only with "Default policy. This is the sandbox's shared product: every account sees it, every enrolment is on it, and it cannot be edited or removed. What follows is read-only." [SANDBOX](../references/PAYERS.md#markers).

API: [A2. Insurance Plan Answer](../apis/A2-insurance-plan-answer.md)

Data: [D4. terminology_code](../database/D4-terminology-code.md)

Data: [D12. policy](../database/D12-policy.md)

Data: [D13. policy_procedure](../database/D13-policy-procedure.md)

Data: [D14. policy_coverage_clause](../database/D14-policy-coverage-clause.md)

Data: [D15. policy_clause_benefit](../database/D15-policy-clause-benefit.md)

Data: [D16. policy_alias](../database/D16-policy-alias.md)

Data: [D17. policy_exclusion](../database/D17-policy-exclusion.md)

Data: [D18. policy_sub_limit](../database/D18-policy-sub-limit.md)

#### S7L. LAYOUT
The arrangement below is the reference desk's [REF](../references/PAYERS.md#markers): follow the target payer system's own screen conventions. What is required is in DESCRIPTION and ACTIONS: the fields, the value sets, the rules and the messages.

```
|------------------------------------------------------------------|
| Create New Policy Product        [< Cancel] [(save) Publish Policy]|
|------------------------------------------------------------------|
| [Card] 1. Policy Overview & Coverage Term                        |
|  Policy Product Name [__________________________]                |
|  Other Names [__________________________]                        |
|  IRDAI UIN [_______]  Status [Active v]  Base Sum Insured [700000]|
|  Product Type [01, ... v]     Plan Type [01, ... v]              |
|------------------------------------------------------------------|
| [Card] 2. Policy Monetary Sub-Limits & Specific Cost Caps        |
|  Capped Concept (SNOMED CT)             Cap (₹)                  |
|  [Room rent (224663004) v]              [50000]     [x]          |
|  [+ Add Sub-Limit]                                               |
|------------------------------------------------------------------|
| [Card] 3. Exclusions                                             |
|  Exclusion [Excl01, ... v]  [x]                                  |
|  Wording [_____________________]                                 |
|  Excluded Item Code [____]  Excluded Item Name [________]        |
|  [+ Add Exclusion]                                               |
|------------------------------------------------------------------|
| [Card] 4. Coverage Clauses & Pre/Post Hospitalization Terms      |
|  Pre-Hospitalization Limit (Days) [60]  Post-... (Days) [90]     |
|------------------------------------------------------------------|
| [Card] 5. Attached Procedure Stage Document Rules (5)            |
|  [x] Total Knee Replacement  PROC-KNEE-01   Attached to Policy   |
|      Pre-Auth (3 docs) | Final Claim (3 docs)                    |
|  [ ] Appendicectomy          PROC-APP-02    Click to Attach      |
|------------------------------------------------------------------|
```

- One long form of numbered cards; the save and cancel actions are in the header and repeated at the foot.
- Sub-limits and exclusions are repeating rows with a remove button and an add button under them.
- The procedure rows are whole-row toggles with a badge at the right.

#### S7A. ACTIONS
1. Publish Policy / Save Policy Changes: validate, save the whole product, return to S6.
2. Cancel: return to S6 without saving.
3. Add Sub-Limit / remove: manage the capped concepts.
4. Add Exclusion / remove: manage the exclusions.
5. Change the pre- and post-hospitalisation days: rewrites the two benefits' limits on save.
6. Attach / detach a procedure: toggle its row.
