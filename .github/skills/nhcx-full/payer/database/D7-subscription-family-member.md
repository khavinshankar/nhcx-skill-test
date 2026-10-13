# D7. subscription_family_member

#### D7T. TABLE
One row is one dependant covered under a family floater enrolment; primary key `id`. Parent table [D6. subscription](D6-subscription.md). The reference implementation names it `payer_subscription_family_members` [REF](../references/PAYERS.md#markers).

#### D7D. DESCRIPTION
Dependants are held as rows on the enrolment rather than as members in their own right: they are covered by the policyholder's plan and have no wallet of their own. A case for a dependant ([D19. case](D19-case.md)) snapshots the patient and points here through `family_member_id`, so a claim keeps saying who it was for after the family list is edited.

A dependant's ABHA number is one more handle an eligibility check ([C2. Coverage Eligibility Check](../callbacks/C2-coverage-eligibility-check.md)) or a pre-authorisation ([C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md)) may arrive under: the enrolment lookup matches it beside the policyholder's own ([A1. Eligibility Answer](../apis/A1-eligibility-answer.md)).

Create and update:
- Written with the enrolment ([S5. Subscriptions](../screens/S5-subscriptions.md), `POST` and `PATCH subscriptions`): the whole list is deleted and rewritten in the enrolment's transaction, in the order given, and only when `sub_type` is `Family Floater`. An id may be given to keep a row's identity across edits; otherwise a short random `FAM-` id is minted [REF](../references/PAYERS.md#markers). Each date of birth is validated.
- Refused when two dependants, or a dependant and a member, share an ABHA number (`uq_family_abha`).

Delete:
- With the enrolment (cascade), or when the list is rewritten without the row.

#### D7C. COLUMNS
| column | type | null/default | meaning (and allowed values) |
|---|---|---|---|
| id | VARCHAR(24) | primary key | `FAM-<random>` [REF](../references/PAYERS.md#markers) |
| subscription_id | VARCHAR(24) | NOT NULL | the enrolment ([D6. subscription](D6-subscription.md)) |
| name | VARCHAR(160) | NOT NULL | full name |
| relation | VARCHAR(32) | NOT NULL | `Spouse`, `Child`, `Parent`, `Sibling` |
| gender | VARCHAR(32) | NOT NULL | `Male`, `Female`, `Other` |
| dob | DATE | NOT NULL | date of birth |
| abha_no | VARCHAR(14) | null, UNIQUE | 14 digits |
| position | INTEGER | NOT NULL, default 0 | order on the enrolment |

#### D7K. KEYS AND INDEXES
- Primary key `id`.
- Unique `uq_family_abha` on `abha_no`.
- Foreign key `subscription_id` references [D6. subscription](D6-subscription.md) `id` (`ON DELETE CASCADE`).
- Checks: `ck_family_relation`; `ck_family_gender`; `ck_family_abha_no` (null or 14 digits).
- Index `idx_family_subscription` on `(subscription_id, position)`.
- Referenced by [D19. case](D19-case.md) `family_member_id` (`ON DELETE RESTRICT`).

#### D7U. USED BY
- Screens: [S5. Subscriptions](../screens/S5-subscriptions.md)
- Database: [D6. subscription](D6-subscription.md), [D19. case](D19-case.md)
