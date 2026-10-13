# D18. policy_sub_limit

#### D18T. TABLE
One row is one sub-limit of a policy ([D12. policy](D12-policy.md)): a cap on one concept inside the sum insured, a room-rent ceiling, an ambulance allowance; primary key `id`. The reference implementation names it `payer_policy_sub_limits` [REF](../references/PAYERS.md#markers).

#### D18D. DESCRIPTION
The concept is carried as a code rather than implied by a column name, so a plan can cap anything the coding system can name. The picker offers the curated sub-limit category slice of SNOMED in [D4. terminology_code](D4-terminology-code.md). The InsurancePlan ([F5. InsurancePlan](../fhir/F5-insuranceplan.md)) carries each sub-limit as a `plan.specificCost` benefit with the concept and the amount, and the eligibility answer ([F3. CoverageEligibilityResponse](../fhir/F3-coverage-eligibility-response.md)) can report the standard sub-limits beside the sum insured [PAYER](../references/PAYERS.md#markers).

The predetermination rules ([A10. Predetermination Quote](../apis/A10-predetermination-quote.md)) read a sub-limit as a cap on the matching line: a line billed above it is reduced to it, with a finding naming the rule.

One sub-limit per concept per policy (`uq_policy_sub_limits_code`); the amount is positive.

Create, update, delete:
- Written with the policy ([S7. Policy Configurator](../screens/S7-policy-configurator.md)): deleted and rewritten in the policy's transaction; a short random `SLM-` id unless one is given [REF](../references/PAYERS.md#markers). Cascades with the policy.

#### D18C. COLUMNS
| column | type | null/default | meaning (and allowed values) |
|---|---|---|---|
| id | VARCHAR(24) | primary key | `SLM-<random>` [REF](../references/PAYERS.md#markers) |
| policy_id | CITEXT | NOT NULL | the product ([D12. policy](D12-policy.md)) |
| snomed_code | VARCHAR(32) | NOT NULL | the capped concept |
| display | VARCHAR(300) | NOT NULL | its display |
| amount | NUMERIC(14,2) | NOT NULL | the cap, positive |
| position | INTEGER | NOT NULL, default 0 | order on the plan |

#### D18K. KEYS AND INDEXES
- Primary key `id`.
- Unique `uq_policy_sub_limits_code` on `(policy_id, snomed_code)`.
- Foreign key `policy_id` references [D12. policy](D12-policy.md) `id` (`ON DELETE CASCADE`).
- Check `ck_policy_sub_limits_amount` (`amount > 0`).
- Index `idx_policy_sub_limits_order` on `(policy_id, position)`.

#### D18U. USED BY
- Screens: [S7. Policy Configurator](../screens/S7-policy-configurator.md)
- APIs: [A2. Insurance Plan Answer](../apis/A2-insurance-plan-answer.md), [A10. Predetermination Quote](../apis/A10-predetermination-quote.md)
- Callbacks: [C3. Insurance Plan Request](../callbacks/C3-insurance-plan-request.md)
- FHIR: [F5. InsurancePlan](../fhir/F5-insuranceplan.md)
- Database: [D4. terminology_code](D4-terminology-code.md), [D12. policy](D12-policy.md)
