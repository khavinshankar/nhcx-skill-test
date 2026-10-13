# D14. claim_auth_item

#### D14T. TABLE
One row is the payer's ruling on one line of the procedure set; primary key `id`; parent table [D13. claim_auth](D13-claim-auth.md).

#### D14D. DESCRIPTION
One row per `insurance[0].item[]` of the payer's CoverageEligibilityResponse to the `auth-requirements` check. The item codes are compared with the quoted lines ([D16](D16-claim-line.md), Stratification excluded) to tell whether the ruling still describes the set being sent. When the codes differ the ruling is stale.

Values:
- `code` / `display`: `productOrService`.
- `category_code`: `category`.
- `auth_required`: `authorizationRequired` (`1` / `0`, null when absent).
- `excluded`: `excluded` (`1` / `0`, null when absent).
- `benefit_type`: the code of `benefit[0].type`.
- `allowed_amount`: `benefit[0].allowedMoney.value`.

Lifecycle:
- Inserted when a ruling is applied, numbered `seq` 1, 2, ... in reply order, after the ruling's earlier items are deleted in the same transaction.
- Deleted when a new check is requested for the claim, and with the ruling (`ON DELETE CASCADE`).
- Never updated in place.

#### D14C. COLUMNS
| column | type | null/default | meaning (and allowed values) |
|---|---|---|---|
| id | INTEGER | primary key | row id |
| auth_id | INTEGER | NOT NULL | the ruling ([D13](D13-claim-auth.md)) |
| seq | INTEGER | NOT NULL, default `1` | order in the reply |
| code | TEXT | NOT NULL | line code (package, implant or item code); empty string when the payer sent none |
| display | TEXT | null | its display |
| category_code | TEXT | null | item category code |
| auth_required | INTEGER | null | `1` authorisation required, `0` not |
| excluded | INTEGER | null | `1` excluded from cover, `0` not |
| benefit_type | TEXT | null | benefit type code, for example `Procedure` or `Implant` |
| allowed_amount | REAL | null | amount the payer allows for the line |

#### D14K. KEYS AND INDEXES
- Primary key `id` (integer).
- `auth_id` references [D13. claim_auth](D13-claim-auth.md) `id`, `ON DELETE CASCADE`.
- No unique constraint.
- Index: `ix_claim_auth_item (auth_id, seq)`.
- `code` corresponds to [D16. claim_line](D16-claim-line.md) `code` (no foreign key).

#### D14U. USED BY
- Screens: [S8. Line Items](../screens/S8-line-items.md)
- APIs: [A2. Coverage Eligibility Check](../apis/A2-coverage-eligibility-check.md)
- Callbacks: [C3. Authorisation Requirements Ruling](../callbacks/C3-auth-requirements-on-check.md)
- FHIR: [F3. CoverageEligibilityResponse](../fhir/F3-coverage-eligibility-response.md)
- Database: [D13. claim_auth](D13-claim-auth.md), [D16. claim_line](D16-claim-line.md)
