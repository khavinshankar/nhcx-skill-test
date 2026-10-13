# D17. policy_exclusion

#### D17T. TABLE
One row is one thing a policy ([D12. policy](D12-policy.md)) does not pay for, in the shape the Claim-Exclusion extension carries: an IRDAI exclusion code, its wording, and optionally the one concept it names; primary key `id`. The reference implementation names it `payer_policy_exclusions` [REF](../references/PAYERS.md#markers).

#### D17D. DESCRIPTION
The standard IRDAI exclusions (`Excl01` and so on), coded from the ndhm-claim-exclusion value set in [D4. terminology_code](D4-terminology-code.md) with the display it publishes. The InsurancePlan ([F5. InsurancePlan](../fhir/F5-insuranceplan.md)) carries each as a claim-exclusion extension with the code, the statement and, when set, the excluded item as a SNOMED concept.

One clause per exclusion code per policy (`uq_policy_exclusions_code`): stating an exclusion twice can only produce two different answers at adjudication. An item is a code and a display together or neither (`ck_policy_exclusions_item`).

Create, update, delete:
- Written with the policy ([S7. Policy Configurator](../screens/S7-policy-configurator.md)): deleted and rewritten in the policy's transaction; a short random `EXC-` id unless one is given [REF](../references/PAYERS.md#markers). Cascades with the policy.

#### D17C. COLUMNS
| column | type | null/default | meaning (and allowed values) |
|---|---|---|---|
| id | VARCHAR(24) | primary key | `EXC-<random>` [REF](../references/PAYERS.md#markers) |
| policy_id | CITEXT | NOT NULL | the product ([D12. policy](D12-policy.md)) |
| code | VARCHAR(64) | NOT NULL | the exclusion code ([D4. terminology_code](D4-terminology-code.md), ndhm-claim-exclusion) |
| statement | VARCHAR(2000) | null | the wording |
| item_snomed_code | VARCHAR(32) | null | the one concept the wording names |
| item_display | VARCHAR(300) | null | its display |
| position | INTEGER | NOT NULL, default 0 | order on the plan |

#### D17K. KEYS AND INDEXES
- Primary key `id`.
- Unique `uq_policy_exclusions_code` on `(policy_id, code)`.
- Foreign key `policy_id` references [D12. policy](D12-policy.md) `id` (`ON DELETE CASCADE`).
- Check `ck_policy_exclusions_item` (both item columns null, or both set).
- Index `idx_policy_exclusions_order` on `(policy_id, position)`.

#### D17U. USED BY
- Screens: [S7. Policy Configurator](../screens/S7-policy-configurator.md)
- APIs: [A2. Insurance Plan Answer](../apis/A2-insurance-plan-answer.md), [A10. Predetermination Quote](../apis/A10-predetermination-quote.md)
- FHIR: [F5. InsurancePlan](../fhir/F5-insuranceplan.md)
- Database: [D4. terminology_code](D4-terminology-code.md), [D12. policy](D12-policy.md)
