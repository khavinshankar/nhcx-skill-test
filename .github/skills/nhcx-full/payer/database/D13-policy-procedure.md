# D13. policy_procedure

#### D13T. TABLE
One row is one procedure ([D10. procedure_rule](D10-procedure-rule.md)) covered by one policy ([D12. policy](D12-policy.md)); primary key `(policy_id, procedure_id)`. The reference implementation names it `payer_policy_procedures` [REF](../references/PAYERS.md#markers).

#### D13D. DESCRIPTION
The list of packages a product pays for. The document rules and the rate come from the registry ([D10. procedure_rule](D10-procedure-rule.md), [D11. procedure_rule_doc](D11-procedure-rule-doc.md)); this row only says the policy covers the procedure, and in what order the plan lists it.

What NHCX reads from the rows:
- Each covered procedure is rendered on the InsurancePlan ([F5. InsurancePlan](../fhir/F5-insuranceplan.md)) as a benefit in its own right, with its rate under `plan.specificCost`, its documents per phase and its treatment-guideline form ([F6. Questionnaire](../fhir/F6-questionnaire.md)).
- An auth-requirements ruling ([A1. Eligibility Answer](../apis/A1-eligibility-answer.md), [F3. CoverageEligibilityResponse](../fhir/F3-coverage-eligibility-response.md)) answers each quoted item as covered when the item's code is a procedure the member's product covers, with the package rate as the allowed amount; an item whose code is not covered is answered excluded [PAYER](../references/PAYERS.md#markers).

Create, update, delete:
- Written with the policy ([S7. Policy Configurator](../screens/S7-policy-configurator.md)): deleted and rewritten in the policy's transaction, in the order given. A `procedure_id` not in the registry is refused ("invalid reference"). Cascades with the policy; a procedure that policies point at cannot be removed (`RESTRICT`, see [D10. procedure_rule](D10-procedure-rule.md)).

#### D13C. COLUMNS
| column | type | null/default | meaning (and allowed values) |
|---|---|---|---|
| policy_id | CITEXT | primary key part | the product ([D12. policy](D12-policy.md)) |
| procedure_id | VARCHAR(32) | primary key part | the procedure ([D10. procedure_rule](D10-procedure-rule.md)) |
| position | INTEGER | NOT NULL, default 0 | the order the plan lists the packages in |

#### D13K. KEYS AND INDEXES
- Primary key `(policy_id, procedure_id)`.
- Foreign keys: `policy_id` references [D12. policy](D12-policy.md) `id` (`ON DELETE CASCADE`); `procedure_id` references [D10. procedure_rule](D10-procedure-rule.md) `id` (`ON DELETE RESTRICT`).
- Indexes: `idx_policy_procedures_order` on `(policy_id, position)`; `idx_policy_procedures_procedure` on `procedure_id`.

#### D13U. USED BY
- Screens: [S6. Policies](../screens/S6-policies.md), [S7. Policy Configurator](../screens/S7-policy-configurator.md), [S8. Procedures](../screens/S8-procedures.md)
- APIs: [A1. Eligibility Answer](../apis/A1-eligibility-answer.md), [A2. Insurance Plan Answer](../apis/A2-insurance-plan-answer.md)
- Callbacks: [C2. Coverage Eligibility Check](../callbacks/C2-coverage-eligibility-check.md)
- FHIR: [F3. CoverageEligibilityResponse](../fhir/F3-coverage-eligibility-response.md), [F5. InsurancePlan](../fhir/F5-insuranceplan.md)
- Database: [D10. procedure_rule](D10-procedure-rule.md), [D12. policy](D12-policy.md), [D21. case_procedure](D21-case-procedure.md)
