# F3. CoverageEligibilityResponse

#### F3R. RESOURCE
`CoverageEligibilityResponse`. Direction: sent on `v1/coverageeligibility/on_check` by [A1. Eligibility Answer](../apis/A1-eligibility-answer.md), answering [C2. Coverage Eligibility Check](../callbacks/C2-coverage-eligibility-check.md) on the request's correlation id. `meta.profile` is the base R4 profile `http://hl7.org/fhir/StructureDefinition/CoverageEligibilityResponse`, which is what the scheme payer declares [REF](../references/PAYERS.md#markers); the NRCeS profile is not claimed. Every resource carries the `SUBSETTED` tag (F1).

#### F3D. DESCRIPTION
The answer to F2, built at once from the enrolment the request's handles matched ([D6. subscription](../database/D6-subscription.md), [D5. member](../database/D5-member.md), [D12. policy](../database/D12-policy.md)). The bundle first echoes the hospital's request entries as they came, then appends this payer's own entries under one anchor, in this order: the CoverageEligibilityResponse, the Patient (F15), the Coverage (F18), the payer Organization and, when the request named a facility, the hospital Organization (F17). A hospital reads the **last** resource of each type as the payer's, so the order matters [PAYER](../references/PAYERS.md#markers).

**What the purpose decides.** The `purpose` list is echoed (`validation` when the request carried none):

| Purpose | `insurance[0].item[]` |
|---|---|
| `discovery` alone | none: the cover, and nothing else |
| `validation`, or `benefits` / `auth-requirements` with no items | one admission item (SNOMED `305056002` "Admission procedure") carrying the money |
| `benefits` with items | one item per package asked about, with the package rate |
| `auth-requirements` with items | one item per package, with the rate, every document due at any stage and the treatment-guideline form |

**In force, lapsed, exhausted.** `insurance[0].inforce` and the `disposition` come from the enrolment's standing on the day, in these words: not active gives `false`, "Cover is <status>. No benefit is payable while the subscription is not active."; before the period `false`, "Cover does not begin until <start>."; after it `false`, "Cover lapsed on <end>."; a zero wallet `true`, "Policy is in force until <end>. The sum insured is exhausted; no balance remains."; otherwise `true`, "Policy is in force until <end>. INR <balance> of cover remains." An enrolment found only among lapsed ones is still answered, so the hospital learns why rather than "no such person" ([A1. Eligibility Answer](../apis/A1-eligibility-answer.md)).

**The money on a validation.** Two benefits on the admission item, and the hospital reads the one typed `benefit` as the wallet [PAYER](../references/PAYERS.md#markers):
- typed `30` "Health Benefit Plan Coverage" (`http://terminology.hl7.org/CodeSystem/ex-benefitcategory`): `allowedMoney` the sum assured (`D12.total_assured`), `usedMoney` sum assured minus the wallet balance;
- typed `benefit` "Benefit" (`http://terminology.hl7.org/CodeSystem/benefit-type`): `allowedMoney` what is left (`D6.wallet_balance`), `usedMoney` the same used figure.
`authorizationRequired` is always `true`: this payer wants to see every case before money is committed [REF](../references/PAYERS.md#markers).

**Per package.** A package is found on the policy by this payer's own code first, then by its SNOMED or ICD-10-PCS coding ([D10. procedure_rule](../database/D10-procedure-rule.md), [D13. policy_procedure](../database/D13-policy-procedure.md)). Not on the policy: `excluded: true`, no benefit, no requirements. Covered: the registry's own code and name replace the hospital's spelling, the category is the registry's (the hospital's category code kept when it sent one), `authorizationRequired: true`, `excluded: false`, one benefit typed `Procedure` with `allowedMoney` the package rate when one is set (`D10.package_rate`; null is "not priced" and gives no benefit), and `authorizationSupporting[]`.

**`authorizationSupporting[]` text conventions** [PAYER](../references/PAYERS.md#markers). The profile gives no place to say when a document is due, so the stage rides on the concept's `text`, exactly as the scheme writes it and as hospital readers parse it: one concept per required document, `coding[0]` the document code and name ([D11. procedure_rule_doc](../database/D11-procedure-rule-doc.md), [D3. document_type](../database/D3-document-type.md)), `text` `Type: <stage>\n Procedure Code:<package code>`. The stage is `pre` for documents wanted at pre-authorisation and `post` for those wanted at discharge or claim. A `benefits` answer lists the `pre` documents only; an `auth-requirements` answer lists every stage and then the treatment-guideline form as one more concept, `coding[0]` the Questionnaire id and title, `text` `fullUrl: <questionnaire url>` (F6). Duplicates on one stage and code are written once. The disposition then adds a sentence: "All N requested items are covered; pre-authorisation is required and the documents listed must accompany it.", "None of the N requested items is covered by this policy.", or "K of N requested items are covered; the rest are not on this policy's schedule."

**No cover.** When no enrolment matches any handle, the answer is still sent: `outcome` `complete`, `disposition` "No active cover was found for the details provided.", no `insurance[]`, and a Patient built from what the request said (member id, ABHA, name, mobile) so the response has something to point at. Leaving the enquiry unanswered would keep the hospital polling ([A1. Eligibility Answer](../apis/A1-eligibility-answer.md)).

`outcome` is always `complete` on every answer; the verdict is in `inforce` and the disposition, never in `outcome`.

#### F3F. FIELDS
The response, at `<anchor>/<member id>`:

| Element written | From | Notes |
|---|---|---|
| `id`, `identifier[0].value` | `<member id>-<facility id>`, or the member id alone | `identifier[0].system` is `<payer base>/v1/coverageeligibility/check` |
| `meta.profile[0]` | `http://hl7.org/fhir/StructureDefinition/CoverageEligibilityResponse` | plus the `SUBSETTED` tag |
| `status` | `active` | |
| `purpose[]` | the request's, else `["validation"]` | |
| `patient.reference` | `<anchor>/patient/<member id>` | |
| `created` | now, IST | |
| `requestor.reference` | `<anchor>/organization/provider/<facility id>` | left out when the request named no facility |
| `request.reference` | `https://nhcx.abdm.gov.in/coverage-eligibility/request` | the request anchor [REF](../references/PAYERS.md#markers) |
| `outcome` | `complete` | |
| `disposition` | the standing sentence, plus the items sentence | |
| `insurer.reference` | `<anchor>/organization/payer/<payer code without @hcx>` | |
| `insurance[0].coverage.reference` | `<anchor>/coverage/<D6.id><member id>` | |
| `insurance[0].inforce` | the standing | |
| `insurance[0].item[]` | per purpose, above | none on discovery and on no cover |
| `item[].productOrService.coding[0]` | SNOMED admission concept, or `D10.code` / `D10.name` | |
| `item[].category.coding[0]` | `D10.category`, code overridden by the hospital's when sent | packages only |
| `item[].benefit[]` | `30` and `benefit` with `D12.total_assured`, `D6.wallet_balance` (admission); `Procedure` with `D10.package_rate` (package) | `currency` `INR` |
| `item[].authorizationRequired` | `true` | |
| `item[].excluded` | `false`, or `true` for a package not on the policy | packages only |
| `item[].authorizationSupporting[]` | `D11` rows joined to `D3`, `text` `Type: <pre or post>\n Procedure Code:<D10.code>`; the STG form as `fullUrl: <url>` | required documents only |

The Patient, Coverage and Organizations beside it are F15, F18 and F17. Nothing is written to the database by the render; the answer is recorded on the audit log ([D31. audit_log](../database/D31-audit-log.md)) and the checklist by [A1. Eligibility Answer](../apis/A1-eligibility-answer.md).

#### F3U. USED BY
- Screens: [S7. Policy Configurator](../screens/S7-policy-configurator.md), [S9. Procedure Configurator](../screens/S9-procedure-configurator.md)
- APIs: [A1. Eligibility Answer](../apis/A1-eligibility-answer.md)
- Callbacks: [C2. Coverage Eligibility Check](../callbacks/C2-coverage-eligibility-check.md)
- FHIR: [F1. Bundle](F1-bundle.md), [F2. CoverageEligibilityRequest](F2-coverage-eligibility-request.md), [F6. Questionnaire](F6-questionnaire.md), [F15. Patient](F15-patient.md), [F17. Organization](F17-organization.md), [F18. Coverage](F18-coverage.md)
- Database: [D4. terminology_code](../database/D4-terminology-code.md), [D6. subscription](../database/D6-subscription.md), [D10. procedure_rule](../database/D10-procedure-rule.md), [D11. procedure_rule_doc](../database/D11-procedure-rule-doc.md), [D13. policy_procedure](../database/D13-policy-procedure.md), [D18. policy_sub_limit](../database/D18-policy-sub-limit.md)
- Tests: [T3. Eligibility Validation and Discovery Answered](../tests/T3-eligibility-answered.md), [T4. Auth-requirements Ruling Answered](../tests/T4-auth-requirements-ruled.md)
