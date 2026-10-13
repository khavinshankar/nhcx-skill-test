# D5. member

#### D5T. TABLE
One row is one beneficiary in the payer's directory; primary key `id`, the member id a hospital quotes. No parent table. The reference implementation names it `payer_members` [REF](../references/PAYERS.md#markers).

#### D5D. DESCRIPTION
The member is who a claim is about. The handles on this row (the id, the ABHA number, the mobile) are what an eligibility check ([C2. Coverage Eligibility Check](../callbacks/C2-coverage-eligibility-check.md)) and a pre-authorisation ([C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md)) are matched on, through the enrolment ([D6. subscription](D6-subscription.md)): a hospital sends whichever it has, and the enrolment found is the cover the answer describes. The member's own name, gender and date of birth are what an answer carries as the Patient ([F15. Patient](../fhir/F15-patient.md)), not the spelling the hospital typed.

Create:
- From the Members screen ([S4. Members](../screens/S4-members.md)) through `POST members`. The id may be given (the card the beneficiary carries) or is allocated: the first three letters of the name, the birth year and a serial from the `member` counter ([D32. id_sequence](D32-id-sequence.md)), for example `MRAJ1990001` [REF](../references/PAYERS.md#markers). Gender is spelled the way the check allows whatever case it arrived in. The ABHA number is stored as 14 bare digits and shown as `xx-xxxx-xxxx-xxxx`.
- Refusals: a second member with the same ABHA number ("That ABHA number is already registered", on `uq_members_abha_no`); an id already taken.

Update:
- `PATCH members/:id`: name, gender, date of birth, mobile, ABHA number. The same uniqueness applies.

Delete:
- Soft: `deleted_at` is set. Refused while the member holds a live enrolment ("still referenced"), because claims arriving against a policyholder the directory says does not exist would have nowhere to land. A deleted member keeps the enrolments and cases filed against them.

Ownership [SANDBOX](../references/PAYERS.md#markers): `owner_client_id` names the sign-up account that registered the member; empty is the shared set every account sees and no sign-up account may change. A single-payer target leaves it empty.

#### D5C. COLUMNS
| column | type | null/default | meaning (and allowed values) |
|---|---|---|---|
| id | CITEXT, at most 48 | primary key | the member id, upper case; `subscriberId` and `memberId` on the wire |
| name | VARCHAR(160) | NOT NULL | full name |
| gender | VARCHAR(32) | NOT NULL | `Male`, `Female`, `Other` |
| dob | DATE | NOT NULL | date of birth; the age on a case is the age on the admission date |
| mobile | VARCHAR(24) | NOT NULL | as entered; reduced to ten digits when sent to ABDM |
| abha_no | VARCHAR(14) | null, UNIQUE | 14 digits, no separators |
| owner_client_id | CITEXT, at most 64 | null | the sign-up account that owns the row; empty is shared [SANDBOX](../references/PAYERS.md#markers) |
| created_at | TIMESTAMPTZ | NOT NULL, default now | |
| updated_at | TIMESTAMPTZ | NOT NULL, default now | bumped by trigger on a real change |
| deleted_at | TIMESTAMPTZ | null | set when retired; a live row has null |

#### D5K. KEYS AND INDEXES
- Primary key `id`.
- Unique `uq_members_abha_no` on `abha_no` (many nulls allowed).
- Checks: `ck_members_gender` (the three values); `ck_members_abha_no` (null or exactly 14 digits); `ck_members_id_len` (at most 48); `ck_members_owner_len` (at most 64).
- Indexes: `idx_members_live_name` on `(deleted_at, name)`; `idx_members_mobile` on `mobile`; `idx_members_owner` on `owner_client_id`.
- Referenced by [D6. subscription](D6-subscription.md) `member_id` and [D19. case](D19-case.md) `member_id`, both `ON DELETE RESTRICT`.

#### D5U. USED BY
- Screens: [S1. Overview](../screens/S1-overview.md), [S4. Members](../screens/S4-members.md)
- APIs: [A1. Eligibility Answer](../apis/A1-eligibility-answer.md), [A3. Pre-auth Answer](../apis/A3-preauth-answer.md), [A4. Claim Answer](../apis/A4-claim-answer.md), [A10. Predetermination Quote](../apis/A10-predetermination-quote.md), [A16. ABHA Policy Link](../apis/A16-abha-policy-link.md), [A19. Sandbox Scenarios](../apis/A19-sandbox-scenarios.md), [A20. ABHA Create and Verify (ABDM M1)](../apis/A20-abha-m1.md)
- Callbacks: [C2. Coverage Eligibility Check](../callbacks/C2-coverage-eligibility-check.md), [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md), [C5. Claim Submit](../callbacks/C5-claim-submit.md), [C6. Predetermination](../callbacks/C6-predetermination.md)
- FHIR: [F2. CoverageEligibilityRequest](../fhir/F2-coverage-eligibility-request.md), [F3. CoverageEligibilityResponse](../fhir/F3-coverage-eligibility-response.md), [F8. Claim](../fhir/F8-claim.md), [F15. Patient](../fhir/F15-patient.md)
- Database: [D6. subscription](D6-subscription.md), [D19. case](D19-case.md), [D29. predetermination_quote](D29-predetermination-quote.md), [D32. id_sequence](D32-id-sequence.md)
