# F6. Questionnaire

#### F6R. RESOURCE
`Questionnaire`, `status: active`, inside the InsurancePlan bundle (F5), one per covered procedure that has anything to ask. Direction: sent by [A2. Insurance Plan Answer](../apis/A2-insurance-plan-answer.md). It is also pointed at from an `auth-requirements` ruling (F3) as `fullUrl: <url>`, so a hospital that never fetched the plan still learns which form to answer. No profile is declared [REF](../references/PAYERS.md#markers). The hospital's answers come back as F7.

#### F6D. DESCRIPTION
The standard treatment guideline (STG) as the questions a clinician answers at pre-authorisation. It belongs to the procedure ([D10. procedure_rule](../database/D10-procedure-rule.md)), not the policy, so one guideline serves every product that covers the procedure; that is why it is a resource of its own addressed by `url`, and the benefit in F5 points at it through a `Claim-SupportingInfoRequirement` (category `INF`, code `STG`, `documentationUrl`).

**Which items.** Two sources, the first that yields anything:
1. The procedure's own guideline questions (`D10.stg_questions`, a JSON list of strings): one item per non-blank question, `linkId` `<package code>/stg/<n>` counting from 1, `text` the question, `type` `string`, `required` `true`. Free text, because a grade, a finding or a fitness assessment is not a yes or a no.
2. Otherwise one item per **required** document wanted at pre-authorisation whose document type has an NDHM supporting-information category ([D11. procedure_rule_doc](../database/D11-procedure-rule-doc.md) phase `preauth`, [D3. document_type](../database/D3-document-type.md)): `linkId` `<package code>/preauth/<doc code>`, `prefix` the document name, `text` "Is the <document name> attached?", `type` `choice`, `required` `true`, `answerOption` `Yes` and `No`. Documents wanted at discharge or claim are never asked about: nobody has them at pre-authorisation.

A procedure with neither gets no Questionnaire, no STG requirement on its benefit, and no `fullUrl:` concept in a ruling.

**The url.** `<payer base>/Questionnaire/<package code>`; the resource `id` is a deterministic UUID v5 of `Questionnaire/<D10.id>` [REF](../references/PAYERS.md#markers). The hospital reads the kind of form from the path segment before the id: this payer's forms therefore count as policy forms on the provider side, not `stgquestionnaire` guidelines, which is a spelling difference and changes nothing about what is answered [PAYER](../references/PAYERS.md#markers).

`answerOption[].initialSelected` is written even when false, so an option nobody decided about reads differently from one deliberately left unselected.

#### F6F. FIELDS
| Element written | From | Notes |
|---|---|---|
| `id` | UUID v5 of `Questionnaire/<D10.id>` | |
| `meta.versionId` | `1` | |
| `url` | `<payer base>/Questionnaire/<D10.code>` | the key the answer (F7) and the ruling (F3) name |
| `name` | `STG Questionnaire` | constant [REF](../references/PAYERS.md#markers) |
| `title` | `<D10.name>` followed by "Standard Treatment Guidelines" | |
| `status` | `active` | |
| `item[].linkId` | `<D10.code>/stg/<n>` or `<D10.code>/preauth/<D11.doc_code>` | stable; answers come back under it |
| `item[].text` | the question, or "Is the <D3.name> attached?" | |
| `item[].prefix` | `D3.name` | document items only |
| `item[].type` | `string` or `choice` | |
| `item[].required` | `true` | |
| `item[].answerOption[]` | `Yes`, `No`, each with `initialSelected: false` | document items only |
| bundle entry `fullUrl` | the `url` | after the InsurancePlan and the Organization |

#### F6U. USED BY
- Screens: [S7. Policy Configurator](../screens/S7-policy-configurator.md), [S8. Procedures](../screens/S8-procedures.md), [S9. Procedure Configurator](../screens/S9-procedure-configurator.md)
- APIs: [A1. Eligibility Answer](../apis/A1-eligibility-answer.md), [A2. Insurance Plan Answer](../apis/A2-insurance-plan-answer.md)
- FHIR: [F1. Bundle](F1-bundle.md), [F3. CoverageEligibilityResponse](F3-coverage-eligibility-response.md), [F4. Task (InsurancePlan request)](F4-task-insuranceplan.md), [F5. InsurancePlan](F5-insuranceplan.md), [F7. QuestionnaireResponse](F7-questionnaireresponse.md)
- Database: [D10. procedure_rule](../database/D10-procedure-rule.md), [D11. procedure_rule_doc](../database/D11-procedure-rule-doc.md), [D13. policy_procedure](../database/D13-policy-procedure.md)
- Tests: [T4. Auth-requirements Ruling Answered](../tests/T4-auth-requirements-ruled.md), [T5. Insurance Plan Served](../tests/T5-insurance-plan-served.md)
