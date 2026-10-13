# D15. policy_clause_benefit

#### D15T. TABLE
One row is one benefit under one coverage clause ([D14. policy_coverage_clause](D14-policy-coverage-clause.md)), optionally carrying its own limit ("up to 90 days after discharge", "at most 10 percent of the sum insured"); primary key `id`. Parent table [D14. policy_coverage_clause](D14-policy-coverage-clause.md). The reference implementation names it `payer_policy_clause_benefits` [REF](../references/PAYERS.md#markers).

#### D15D. DESCRIPTION
The benefits the InsurancePlan ([F5. InsurancePlan](../fhir/F5-insuranceplan.md)) lists under each `coverage[].benefit[]`, each a SNOMED concept with its display from [D4. terminology_code](D4-terminology-code.md), its claim condition as the requirement, and its limit as `benefit.limit` with the value, comparator and unit.

A limit is a number, a comparator and a unit together or none of them: a number without a comparator and a unit is not a limit anybody can apply, and `ck_benefits_limit` refuses it. Comparators are `<=`, `=`, `>=`.

One benefit per concept per clause (`uq_benefits_clause_code`).

Create, update, delete:
- Written with the clause, in the policy's transaction ([S7. Policy Configurator](../screens/S7-policy-configurator.md)); a short random `BEN-` id [REF](../references/PAYERS.md#markers). Cascades with the clause.

#### D15C. COLUMNS
| column | type | null/default | meaning (and allowed values) |
|---|---|---|---|
| id | VARCHAR(24) | primary key | `BEN-<random>` [REF](../references/PAYERS.md#markers) |
| clause_id | VARCHAR(24) | NOT NULL | the clause ([D14. policy_coverage_clause](D14-policy-coverage-clause.md)) |
| snomed_code | VARCHAR(32) | NOT NULL | the SNOMED CT concept |
| display | VARCHAR(300) | NOT NULL | its display |
| claim_condition | VARCHAR(1000) | null | the requirement wording |
| limit_value | NUMERIC(14,2) | null | the limit's number, never negative |
| limit_comparator | VARCHAR(2) | null | `<=`, `=`, `>=` |
| limit_unit | VARCHAR(32) | null | the limit's unit, for example `day`, `INR`, `percent` |
| position | INTEGER | NOT NULL, default 0 | order under the clause |

#### D15K. KEYS AND INDEXES
- Primary key `id`.
- Unique `uq_benefits_clause_code` on `(clause_id, snomed_code)`.
- Foreign key `clause_id` references [D14. policy_coverage_clause](D14-policy-coverage-clause.md) `id` (`ON DELETE CASCADE`).
- Checks: `ck_benefits_comparator`; `ck_benefits_limit` (all three limit columns null, or all three set); `ck_benefits_limit_sign` (`limit_value` null or `>= 0`).
- Index `idx_benefits_order` on `(clause_id, position)`.

#### D15U. USED BY
- Screens: [S7. Policy Configurator](../screens/S7-policy-configurator.md)
- APIs: [A2. Insurance Plan Answer](../apis/A2-insurance-plan-answer.md)
- FHIR: [F5. InsurancePlan](../fhir/F5-insuranceplan.md)
- Database: [D4. terminology_code](D4-terminology-code.md), [D12. policy](D12-policy.md), [D14. policy_coverage_clause](D14-policy-coverage-clause.md)
