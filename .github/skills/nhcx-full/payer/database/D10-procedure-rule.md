# D10. procedure_rule

#### D10T. TABLE
One row is one procedure (package) in the payer's registry: what it is, what it pays, and the clinical questions asked before it is authorised; primary key `id`, which is the procedure code itself. No parent table. The reference implementation names it `payer_procedure_rules` [REF](../references/PAYERS.md#markers).

#### D10D. DESCRIPTION
The procedure master the plan and the rulings are built from. A policy names the procedures it covers ([D13. policy_procedure](D13-policy-procedure.md)) and inherits the rules from here rather than copying them, so a document requirement is stated once.

What NHCX reads from the row:
- `package_rate` is the `Procedure` cost the InsurancePlan quotes under `plan.specificCost` ([F5. InsurancePlan](../fhir/F5-insuranceplan.md)) and the allowed amount an auth-requirements ruling answers per item ([F3. CoverageEligibilityResponse](../fhir/F3-coverage-eligibility-response.md), [A1. Eligibility Answer](../apis/A1-eligibility-answer.md)). Null is "not priced", which is not the same as free: the procedure is listed on the plan without a rate, and the plan preview ([S11. FHIR Preview](../screens/S11-fhir-preview.md)) reports it.
- `stg_questions` become the treatment-guideline Questionnaire the plan hangs off the package ([F6. Questionnaire](../fhir/F6-questionnaire.md)), one required free-text item per question with `linkId` `<code>/stg/<n>`, which the ruling points the hospital at. A procedure with none falls back to one yes/no question per document wanted at pre-authorisation ([D11. procedure_rule_doc](D11-procedure-rule-doc.md)), never the discharge summary or the final bill, which nobody has at that stage.
- `snomed_code` and `pcs10_code` identify the procedure to whoever reads the plan; `category` groups it.

Create:
- From the Procedure Configurator ([S9. Procedure Configurator](../screens/S9-procedure-configurator.md)) through `POST procedures`. The code is the identifier: underwriters quote it on the policy schedule and hospitals send it on the claim, so `id` and `code` are the same upper-cased value and no second id is invented [REF](../references/PAYERS.md#markers). The document rules ([D11. procedure_rule_doc](D11-procedure-rule-doc.md)) are written in the same transaction.
- Refused when the code is taken ("A procedure with that code is already in the registry") or a document code named in the rules is not in [D3. document_type](D3-document-type.md).

Update:
- `PATCH procedures/:id`: every column but the id; the document rules are deleted and rewritten.

Delete:
- Soft: `deleted_at` set. Refused while a live policy still covers it ("still referenced"), because a policy that lost a procedure quietly would start declining claims it was sold to pay.

#### D10C. COLUMNS
| column | type | null/default | meaning (and allowed values) |
|---|---|---|---|
| id | VARCHAR(32) | primary key | the procedure code, upper case (same as `code`) [REF](../references/PAYERS.md#markers) |
| name | VARCHAR(200) | NOT NULL | the procedure's name; the display in a bundle |
| code | VARCHAR(32) | NOT NULL, UNIQUE | the code a hospital sends as `productOrService` |
| snomed_code | VARCHAR(32) | null | SNOMED CT concept |
| pcs10_code | VARCHAR(32) | null | ICD-10-PCS code |
| category | VARCHAR(32) | NOT NULL | `Surgical`, `Medical`, `Emergency`, `Day Care`, `Diagnostic`, `Critical Care` |
| package_rate | NUMERIC(14,2) | null | what the policy pays for the package; null is not priced |
| description | VARCHAR(500) | null | free text |
| stg_questions | JSONB | null | a list of strings: the treatment-guideline questions asked at pre-authorisation |
| created_at | TIMESTAMPTZ | NOT NULL, default now | |
| updated_at | TIMESTAMPTZ | NOT NULL, default now | bumped by trigger |
| deleted_at | TIMESTAMPTZ | null | set when retired |

#### D10K. KEYS AND INDEXES
- Primary key `id`.
- Unique `uq_procedure_rules_code` on `code`.
- Checks: `ck_procedure_rules_category`; `ck_procedure_rules_rate` (null or `>= 0`).
- Index `idx_procedure_rules_live` on `(deleted_at, category, name)`.
- Referenced by [D11. procedure_rule_doc](D11-procedure-rule-doc.md) `procedure_id` (`ON DELETE CASCADE`) and [D13. policy_procedure](D13-policy-procedure.md) `procedure_id` (`ON DELETE RESTRICT`).

#### D10U. USED BY
- Screens: [S8. Procedures](../screens/S8-procedures.md), [S9. Procedure Configurator](../screens/S9-procedure-configurator.md)
- APIs: [A1. Eligibility Answer](../apis/A1-eligibility-answer.md), [A2. Insurance Plan Answer](../apis/A2-insurance-plan-answer.md), [A10. Predetermination Quote](../apis/A10-predetermination-quote.md), [A19. Sandbox Scenarios](../apis/A19-sandbox-scenarios.md)
- Callbacks: [C2. Coverage Eligibility Check](../callbacks/C2-coverage-eligibility-check.md), [C3. Insurance Plan Request](../callbacks/C3-insurance-plan-request.md)
- FHIR: [F3. CoverageEligibilityResponse](../fhir/F3-coverage-eligibility-response.md), [F5. InsurancePlan](../fhir/F5-insuranceplan.md), [F6. Questionnaire](../fhir/F6-questionnaire.md), [F19. Other resources](../fhir/F19-other-resources.md)
- Database: [D11. procedure_rule_doc](D11-procedure-rule-doc.md), [D13. policy_procedure](D13-policy-procedure.md), [D21. case_procedure](D21-case-procedure.md)
