# D16. policy_alias

#### D16T. TABLE
One row is one alternate name a product ([D12. policy](D12-policy.md)) is marketed or filed under; primary key `(policy_id, alias)`. The reference implementation names it `payer_policy_aliases` [REF](../references/PAYERS.md#markers).

#### D16D. DESCRIPTION
A hospital's plan request ([C3. Insurance Plan Request](../callbacks/C3-insurance-plan-request.md), [F4. Task (InsurancePlan request)](../fhir/F4-task-insuranceplan.md)) names the product by whatever the registry or the beneficiary's card says, which is not always the product id or the UIN. The lookup in [A2. Insurance Plan Answer](../apis/A2-insurance-plan-answer.md) tries the id, the UIN and every alias, case-insensitively, before giving up; an alias is how a product filed as `POL7UMV001` answers to the name printed on a policy schedule. The InsurancePlan ([F5. InsurancePlan](../fhir/F5-insuranceplan.md)) carries the aliases as further identifiers.

Create, update, delete:
- Written with the policy ([S7. Policy Configurator](../screens/S7-policy-configurator.md)): deleted and rewritten in the policy's transaction, in the order given. Cascades with the policy.

#### D16C. COLUMNS
| column | type | null/default | meaning (and allowed values) |
|---|---|---|---|
| policy_id | CITEXT | primary key part | the product ([D12. policy](D12-policy.md)) |
| alias | CITEXT, at most 200 | primary key part | the alternate name, matched case-insensitively |
| position | INTEGER | NOT NULL, default 0 | order on the plan |

#### D16K. KEYS AND INDEXES
- Primary key `(policy_id, alias)`.
- Foreign key `policy_id` references [D12. policy](D12-policy.md) `id` (`ON DELETE CASCADE`).
- Check `ck_policy_aliases_len` (at most 200).
- Index `idx_policy_aliases_order` on `(policy_id, position)`.

#### D16U. USED BY
- Screens: [S6. Policies](../screens/S6-policies.md), [S7. Policy Configurator](../screens/S7-policy-configurator.md)
- APIs: [A2. Insurance Plan Answer](../apis/A2-insurance-plan-answer.md)
- Callbacks: [C3. Insurance Plan Request](../callbacks/C3-insurance-plan-request.md)
- FHIR: [F4. Task (InsurancePlan request)](../fhir/F4-task-insuranceplan.md), [F5. InsurancePlan](../fhir/F5-insuranceplan.md)
- Database: [D12. policy](D12-policy.md)
