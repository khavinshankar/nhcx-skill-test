# D12. claim_plan_form

#### D12T. TABLE
One row is one payer questionnaire (dynamic form) shipped with a claim's package master; primary key `id`; parent table [D10. claim_plan](D10-claim-plan.md).

#### D12D. DESCRIPTION
The payer's InsurancePlan bundle carries Questionnaire resources: policy forms and standard-treatment-guideline (STG) checklists that a document requirement points at through its `documentationUrl`. The payer sends the same form once for every benefit that needs it, so forms are collected by `url` and stored once per plan. Answers are stored per claim in [D17. claim_form_answer](D17-claim-form-answer.md), keyed by the same url (`form_url`).

Which forms a leg must carry (the one rule; F6, F7, A4, A5, S9 and S11 all follow it):
- With a `ready` auth-requirements ruling ([D13](D13-claim-auth.md)): the forms named by its `form` requirements ([D15](D15-claim-auth-requirement.md) `form_url`) for that stage (`at_preauth = 1` for the pre-authorisation, `0` for the claim).
- On both legs, ruling or not: the quoted packages' own forms, named in `supporting_info[].form` of the quoted packages ([D11](D11-claim-plan-benefit.md)), their standard treatment guideline (STG) checklists. PMJAY lists an STG requirement per stage on every benefit, and its ruling (C3) never names the STG, so a claim that offered only the ruling's forms never carried the STG [PAYER](../references/PAYERS.md#markers). The ruling adds to this list; it does not replace it.
- On both legs, always: the policy-wide forms named in the plan's `policy_documents[].form` ([D10](D10-claim-plan.md)). A form answered earlier is offered again with the earlier answers filled in.
- Without a biometric token for the stage, the scheme's consent form for the stage, whether or not anything lists it ([A18. Biometric Authentication](../apis/A18-biometric-authentication.md): Authentication Consent at pre-authorisation, Discharge Consent at the claim) [PAYER](../references/PAYERS.md#markers).
- Nothing is required unless the plan is `ready`.

Each question in `items` is a flattened Questionnaire item:
- `linkId` (this spelling, the FHIR name, never `link_id`: a parser that stores `link_id` leaves every screen reading `linkId` blank), `type`, `text` (the item's `prefix`, else its `text`), `required`.
- `depth`: nesting level, `0` for top-level items.
- `options`: `answerOption` `valueString`, else the valueCoding's display or code.
- `initial`: the first option marked `initialSelected`, the payer's default answer.

Lifecycle:
- Inserted when a plan reply is applied, after all the plan's earlier forms are deleted in the same transaction.
- Copied from another claim's `ready` plan when a master is reused.
- A refetch request does not delete forms. They are replaced when the reply is applied.
- Deleted with the plan (`ON DELETE CASCADE`).
- Never updated in place.

#### D12C. COLUMNS
| column | type | null/default | meaning (and allowed values) |
|---|---|---|---|
| id | INTEGER | primary key | row id |
| plan_id | INTEGER | NOT NULL | the package master ([D10](D10-claim-plan.md)) |
| url | TEXT | NOT NULL | Questionnaire.url; how requirements and answers name the form |
| form_id | TEXT | null | Questionnaire.id |
| title | TEXT | null | Questionnaire.title, else name, else url |
| kind | TEXT | null | the url path segment before the last one: `questionnaire` (policy form) or `stgquestionnaire` (STG checklist) [PAYER](../references/PAYERS.md#markers) |
| items | TEXT | NOT NULL | JSON list of questions `{linkId, type, text, required, depth, options, initial}` |

#### D12K. KEYS AND INDEXES
- Primary key `id` (integer).
- `plan_id` references [D10. claim_plan](D10-claim-plan.md) `id`, `ON DELETE CASCADE`.
- Unique index: `ux_claim_plan_form (plan_id, url)`.
- `url` is matched without a foreign key by [D15. claim_auth_requirement](D15-claim-auth-requirement.md) `form_url`, [D11](D11-claim-plan-benefit.md) `supporting_info[].form`, [D10](D10-claim-plan.md) `policy_documents[].form` and [D17. claim_form_answer](D17-claim-form-answer.md) `form_url`.

#### D12U. USED BY
- Screens: [S7. Insurance Plan](../screens/S7-insurance-plan.md), [S9. Pre-authorisation](../screens/S9-preauthorisation.md), [S11. Claim Submission](../screens/S11-claim-submission.md)
- APIs: [A3. Insurance Plan Request](../apis/A3-insurance-plan-request.md), [A4. Pre-auth Submit](../apis/A4-preauth-submit.md), [A5. Claim Submit](../apis/A5-claim-submit.md), [A17. Claim State](../apis/A17-claim-state.md)
- Callbacks: [C4. Insurance Plan Reply](../callbacks/C4-insuranceplan-on-request.md)
- FHIR: [F5. InsurancePlan](../fhir/F5-insuranceplan.md), [F6. Questionnaire](../fhir/F6-questionnaire.md), [F7. QuestionnaireResponse](../fhir/F7-questionnaireresponse.md)
- Database: [D10. claim_plan](D10-claim-plan.md), [D11. claim_plan_benefit](D11-claim-plan-benefit.md), [D15. claim_auth_requirement](D15-claim-auth-requirement.md), [D17. claim_form_answer](D17-claim-form-answer.md)
- Tests: [T13. PMJAY Eligibility, Package Master and Ruling](../tests/T13-pmjay-eligibility-and-package-master.md)
