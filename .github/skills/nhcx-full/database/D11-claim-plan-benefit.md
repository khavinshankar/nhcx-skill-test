# D11. claim_plan_benefit

#### D11T. TABLE
One row is one package (or covered benefit) in a claim's package master; primary key `id`; parent table [D10. claim_plan](D10-claim-plan.md).

#### D11D. DESCRIPTION
The InsurancePlan comes in one of two shapes, and both flatten to this table:
- Approach 1, package master: `plan -> specificCost -> category -> benefit -> cost`.
- Approach 2, indemnity: `coverage -> benefit -> limit`.

When a bundle carries both, they are merged on the package code. `specificCost` wins, and `coverage` adds only codes it did not carry. A code already seen is skipped, so each code appears at most once per plan.

Approach 1 row:
- `category_*` from `specificCost.category`; `code` / `display` from `benefit.type`.
- The cost typed `Procedure` is `rate` / `currency`, and `cost_type` is then `Procedure`.
- Every other cost (`Stratification`, `Implant` [PAYER](../references/PAYERS.md#markers)) goes into `extras` as `{type, code, label, rate, currency}`, `code` and `label` taken from its first qualifier.
- `kind` is `Procedure` when a rate was found. Otherwise it is `Procedure` or `Implant` from the first extra of that type, else null.
- `conditions` merges the plan-level and benefit-level claim conditions. `supporting_info` is the plan-level plus benefit-level document requirements.

Approach 2 row:
- `category_*` from `coverage.type`.
- The limit whose code is empty or equal to the benefit code is `rate` / `currency`; the other limits go into `extras` as `{type: "Limit", code, label, rate, currency}`.
- `kind` is `Implant` when the code was named as an implant qualifier under Approach 1, else `Procedure`.
- `cost_type` and `requirement` are `benefit.requirement`.
- `conditions` / `supporting_info` merge the coverage-level and benefit-level ones.

`rate = 0` means bundled, not free [PAYER](../references/PAYERS.md#markers). A null `rate` means the benefit has no package rate of its own.

Lifecycle:
- Inserted when a plan reply is applied, numbered `seq` 1, 2, ... in merge order. All earlier rows of the plan are deleted first, in the same transaction.
- Copied from another claim's `ready` plan when a master is reused.
- Deleted when the plan is refetched (the request deletes them at once) or when the plan row is deleted (`ON DELETE CASCADE`).
- Never updated in place.

Reads:
- The line picker filters by `category_code`, `kind`, and `code` or `display` LIKE the search text, ordered by `seq`.
- An implant tier in `extras` is joined back to the benefit with the same `code`. The packages that allow an implant are found by searching `extras` for its code.
- The price of a claim line ([D16](D16-claim-line.md)) is read from here, never from the form.
- Without a ruling, `supporting_info` of the quoted codes lists the documents (entries with a `code` other than `STG` [PAYER](../references/PAYERS.md#markers) and no `form`) and the forms (entries with a `form`) the pre-authorisation needs.

#### D11C. COLUMNS
| column | type | null/default | meaning (and allowed values) |
|---|---|---|---|
| id | INTEGER | primary key | row id |
| plan_id | INTEGER | NOT NULL | the package master ([D10](D10-claim-plan.md)) |
| seq | INTEGER | NOT NULL, default `1` | order in the plan |
| category_code | TEXT | null | speciality or coverage type code |
| category_display | TEXT | null | its display |
| code | TEXT | NOT NULL | package or benefit code |
| display | TEXT | null | package name |
| kind | TEXT | null | what the code names: `Procedure` or `Implant`. Added by migration |
| rate | REAL | null | package rate; `0` means bundled |
| currency | TEXT | null | currency or unit of the rate, for example `INR` |
| cost_type | TEXT | null | `Procedure` (Approach 1 with a rate) or Approach 2 `benefit.requirement` |
| requirement | TEXT | null | Approach 2 `benefit.requirement` |
| conditions | TEXT | null | JSON object: claim-condition name to value, for example `{"IsDayCare": "Y"}` |
| extras | TEXT | null | JSON list of tiers paid over the rate: `{type, code, label, rate, currency}`, `type` one of `Stratification`, `Implant`, `Limit`. Added by migration |
| supporting_info | TEXT | null | JSON list of document requirements: `{code, display, category, category_display, form}`, where `form` is the Questionnaire url when the requirement is a form. Added by migration |

#### D11K. KEYS AND INDEXES
- Primary key `id` (integer).
- `plan_id` references [D10. claim_plan](D10-claim-plan.md) `id`, `ON DELETE CASCADE`.
- No unique constraint. The parser keeps `code` unique per plan.
- Index: `ix_claim_plan_benefit (plan_id, seq)`.
- `supporting_info[].form` names a [D12. claim_plan_form](D12-claim-plan-form.md) `url` (no foreign key).

#### D11U. USED BY
- Screens: [S7. Insurance Plan](../screens/S7-insurance-plan.md), [S8. Line Items](../screens/S8-line-items.md), [S9. Pre-authorisation](../screens/S9-preauthorisation.md), [S11. Claim Submission](../screens/S11-claim-submission.md)
- APIs: [A3. Insurance Plan Request](../apis/A3-insurance-plan-request.md), [A17. Claim State](../apis/A17-claim-state.md)
- Callbacks: [C4. Insurance Plan Reply](../callbacks/C4-insuranceplan-on-request.md)
- FHIR: [F5. InsurancePlan](../fhir/F5-insuranceplan.md), [F8. Claim](../fhir/F8-claim.md)
- Database: [D10. claim_plan](D10-claim-plan.md), [D12. claim_plan_form](D12-claim-plan-form.md), [D16. claim_line](D16-claim-line.md), [D28. claim_document](D28-claim-document.md)
- Tests: [T13. PMJAY Eligibility, Package Master and Ruling](../tests/T13-pmjay-eligibility-and-package-master.md)
