# D16. claim_line

#### D16T. TABLE
One row is one line the pre-authorisation quotes from the payer's package master: a procedure, an implant or a ward / ICU stratification tier. Primary key `id`. Parent table: `claim` (D9).

#### D16D. DESCRIPTION
The lines are the procedure set of the case. They are chosen on Line Items (S8) only once the payer's insurance plan (D10) is `ready`; the price always comes from the plan (D11), never from the form.

**Created.** "Add" on S8 inserts one row:

- `Procedure` or `Implant`: the code must be a D11 benefit of that `kind` in the claim's plan. `display`, `category_code`, `category_display` and `unit_price` (the benefit's `rate`, 0 when it has none) are copied from it.
- `Stratification`: the tier is resolved through the procedure it is quoted with (`parent_code`), because different procedures price the same ward differently [PAYER](../references/PAYERS.md#markers). The tier must appear in that procedure's `extras` with type `Stratification`; its `label` becomes `display` and its `rate` becomes `unit_price`. The category is the parent procedure's.
- `seq` is the claim's highest `seq` plus 1, `quantity` is 1 and `amount` is `unit_price` rounded to 2 places.
- Adding a code already on the claim under the same kind is refused ("<code> is already on this preauth.").

**Updated.** "Save quantities" on S8 rewrites every line in one transaction:

- `quantity` must be a whole number above 0.
- `unit_price` may be changed only where the plan prices the line at nothing (a rate of 0 or none); anywhere else the plan's rate stands. A negative price is refused.
- `amount` is always recomputed as `unit_price * quantity`, rounded to 2 places.

**Deleted.** "Remove" on S8 deletes one row. Rows also go when the claim is deleted (cascade) or when the whole transactional store is cleared.

**How the lines are read.**

- `lines_total` (the sum of `amount`) is the pre-authorisation's requested amount (D18 `requested_amount`, D19 `requested_amount`) and the claim's `preauth_total` for a package case.
- The first `Procedure` line names the claim's `package_code` and `package_name` when the pre-auth draft (S4) is saved for a package case.
- On the wire a `Stratification` line is not an item of its own: it rides as a `modifier` on its parent procedure's `Claim.item`, and its rate is inside that item's `net`. A tier with no `parent_code` (quoted before the column existed) falls back to the first procedure whose plan costs offer it, then to the first procedure.
- Enhancement: lines whose code is not in the last pre-authorisation bundle sent (D18 `request_json`) are the enhancement lines, once D18 is `approved` or `partial`.
- The claim leg quotes these same lines, except that a LAMA or DAMA discharge before or during surgery (D20) replaces them all with the single procedure `LM100` [PAYER](../references/PAYERS.md#markers). That substitution is computed at send time and is not stored here.
- The auth-requirements ruling (D13) is stale when the set of non-`Stratification` codes here differs from the codes ruled on (D14).

There is no status column.

#### D16C. COLUMNS
| Column | Type | Null / default | Meaning |
|---|---|---|---|
| id | INTEGER | primary key | Row id |
| claim_id | INTEGER | NOT NULL | The claim (D9) the line is quoted on |
| seq | INTEGER | NOT NULL, default 1 | Order of addition within the claim |
| kind | TEXT | NOT NULL | `Procedure`, `Implant` or `Stratification` (shown as "Ward / ICU tier") |
| code | TEXT | NOT NULL | Package, implant or tier code from the payer's plan |
| display | TEXT | null | Name from the plan (tier: its label) |
| category_code | TEXT | null | Speciality code, sent as `Claim.item.category` |
| category_display | TEXT | null | Speciality name |
| unit_price | REAL | NOT NULL, default 0 | The plan's rate; hospital price only where the plan prices it at nothing |
| quantity | REAL | NOT NULL, default 1 | Whole number of times done or implants used |
| amount | REAL | NOT NULL, default 0 | `unit_price * quantity`, recomputed on every save |
| parent_code | TEXT | null | For `Stratification` only: the procedure code the tier was quoted through. Null for the other kinds. Added by migration |

#### D16K. KEYS AND INDEXES
- Primary key `id` (integer).
- Foreign key `claim_id` references `claim (id)` (D9), `ON DELETE CASCADE`.
- Unique index `ux_claim_line` on `(claim_id, kind, code)`: a code appears once per kind on a claim.

#### D16U. USED BY
- Screens: [S4. Claim Creation Form](../screens/S4-claim-creation-form.md), [S8. Line Items](../screens/S8-line-items.md), [S9. Pre-authorisation](../screens/S9-preauthorisation.md), [S11. Claim Submission](../screens/S11-claim-submission.md)
- APIs: [A17. Claim State](../apis/A17-claim-state.md)
- FHIR: [F2. CoverageEligibilityRequest](../fhir/F2-coverage-eligibility-request.md), [F5. InsurancePlan](../fhir/F5-insuranceplan.md), [F8. Claim](../fhir/F8-claim.md), [F19. Other bundle resources](../fhir/F19-other-resources.md)
- Database: [D9. claim](D9-claim.md), [D10. claim_plan](D10-claim-plan.md), [D11. claim_plan_benefit](D11-claim-plan-benefit.md), [D14. claim_auth_item](D14-claim-auth-item.md), [D15. claim_auth_requirement](D15-claim-auth-requirement.md), [D18. claim_preauth](D18-claim-preauth.md), [D19. claim_predetermination](D19-claim-predetermination.md), [D27. claim_item](D27-claim-item.md)
