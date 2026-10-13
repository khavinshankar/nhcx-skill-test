# D14. policy_coverage_clause

#### D14T. TABLE
One row is one coverage clause of one policy: a SNOMED CT concept the policy says it pays for, in the vocabulary the FHIR InsurancePlan uses; primary key `id`. Parent table [D12. policy](D12-policy.md). The reference implementation names it `payer_policy_coverage_clauses` [REF](../references/PAYERS.md#markers).

#### D14D. DESCRIPTION
What the policy covers, stated as concepts rather than prose, so the InsurancePlan ([F5. InsurancePlan](../fhir/F5-insuranceplan.md)) can carry them as `coverage[].type` with the benefits ([D15. policy_clause_benefit](D15-policy-clause-benefit.md)) beneath. The concept and its display come from the SNOMED slice in [D4. terminology_code](D4-terminology-code.md); the claim condition is the wording the plan carries as the clause's requirement.

One clause per concept per policy: saying the same thing twice can only produce two different answers later, and `uq_clauses_policy_code` forbids it.

Create, update, delete:
- Written with the policy ([S7. Policy Configurator](../screens/S7-policy-configurator.md)): the clauses and their benefits are deleted and rewritten in the policy's transaction, in the order given. An id may be given to keep a clause's identity across edits; otherwise a short random `COV-` id is minted [REF](../references/PAYERS.md#markers). Cascades with the policy.

#### D14C. COLUMNS
| column | type | null/default | meaning (and allowed values) |
|---|---|---|---|
| id | VARCHAR(24) | primary key | `COV-<random>` [REF](../references/PAYERS.md#markers) |
| policy_id | CITEXT | NOT NULL | the product ([D12. policy](D12-policy.md)) |
| snomed_code | VARCHAR(32) | NOT NULL | the SNOMED CT concept |
| display | VARCHAR(300) | NOT NULL | the concept's display, resolved through [D4. terminology_code](D4-terminology-code.md) |
| claim_condition | VARCHAR(1000) | null | the wording of the condition the clause carries |
| position | INTEGER | NOT NULL, default 0 | order on the plan |

#### D14K. KEYS AND INDEXES
- Primary key `id`.
- Unique `uq_clauses_policy_code` on `(policy_id, snomed_code)`.
- Foreign key `policy_id` references [D12. policy](D12-policy.md) `id` (`ON DELETE CASCADE`).
- Index `idx_clauses_order` on `(policy_id, position)`.
- Referenced by [D15. policy_clause_benefit](D15-policy-clause-benefit.md) `clause_id` (`ON DELETE CASCADE`).

#### D14U. USED BY
- Screens: [S7. Policy Configurator](../screens/S7-policy-configurator.md)
- APIs: [A2. Insurance Plan Answer](../apis/A2-insurance-plan-answer.md)
- FHIR: [F5. InsurancePlan](../fhir/F5-insuranceplan.md)
- Database: [D4. terminology_code](D4-terminology-code.md), [D12. policy](D12-policy.md), [D15. policy_clause_benefit](D15-policy-clause-benefit.md)
