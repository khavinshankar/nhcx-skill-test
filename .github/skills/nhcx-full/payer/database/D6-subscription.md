# D6. subscription

#### D6T. TABLE
One row is one enrolment of one member ([D5. member](D5-member.md)) on one product ([D12. policy](D12-policy.md)) for one cover period; primary key `id`. Parent tables [D5. member](D5-member.md) and [D12. policy](D12-policy.md). The reference implementation names it `payer_subscriptions` [REF](../references/PAYERS.md#markers).

#### D6D. DESCRIPTION
The cover. An eligibility check ([C2. Coverage Eligibility Check](../callbacks/C2-coverage-eligibility-check.md)) is answered from this row: in force when `status` is `active` and today lies inside `pstart` to `pend`, lapsed when the newest enrolment the handles find is not, no cover when none is found ([A1. Eligibility Answer](../apis/A1-eligibility-answer.md)). The wallet is what the answer reports as the benefit left ([F3. CoverageEligibilityResponse](../fhir/F3-coverage-eligibility-response.md)), and what a claim approval draws down ([A13. Adjudicate](../apis/A13-adjudicate.md)). The enrolment id is a handle this payer hands out: an eligibility answer names it, and a plan request quoting it back ([C3. Insurance Plan Request](../callbacks/C3-insurance-plan-request.md)) resolves to this person's cover rather than the product alone.

Create:
- From the Subscriptions screen ([S5. Subscriptions](../screens/S5-subscriptions.md)) through `POST subscriptions`. `id` is `SUB-<serial>` from the `subscription` counter ([D32. id_sequence](D32-id-sequence.md)), five digits [REF](../references/PAYERS.md#markers). The period is validated (`pend` not before `pstart`); the opening wallet balance is honoured only here. Family members ([D7. subscription_family_member](D7-subscription-family-member.md)) are written with it when `sub_type` is `Family Floater`.
- Refused when the member is already enrolled on the same policy ("already enrolled on that policy", `uq_subscriptions_member_policy`), or the member or policy does not exist.

Update:
- `PATCH subscriptions/:id`: period, type, plan type and the family list (replaced whole). `POST subscriptions/:id/status` sets `active` or `paused`.
- The wallet moves only through a ledgered write ([D8. wallet_entry](D8-wallet-entry.md)): a manual adjustment from the screen (`POST subscriptions/:id/wallet`, credit or debit with a reason), the debit of the approved amount when a claim is approved ([A13. Adjudicate](../apis/A13-adjudicate.md)), and the credit of the same amount when a decided claim is reopened ([C7. Task Submit](../callbacks/C7-task-submit.md) reprocess). The row is locked, the balance and the ledger entry are written in one transaction, and a debit below zero is refused ("Insufficient wallet balance").
- ABHA link state moves only through [A16. ABHA Policy Link](../apis/A16-abha-policy-link.md): a link that took at ABDM sets `abha_linked`, `abha_no`, `abha_token`, `abha_link_status` `linked`, `abha_linked_at`; a delink clears them and sets `delinked`; a refusal sets `failed` and `abha_request_id` and nothing else; a link recorded with no gateway configured sets the number and leaves `abha_link_status` at `none`, because the exchange has been told nothing. Every attempt writes a row in [D9. abha_link_event](D9-abha-link-event.md).

Statuses (`status`): `active`, `paused`. `abha_link_status`: `none`, `linked`, `delinked`, `failed`.

Delete:
- Soft: `deleted_at` set. Cases filed against it stay (`RESTRICT` on [D19. case](D19-case.md)).

A product retired from under an enrolment is repointed to the default product at boot [SANDBOX](../references/PAYERS.md#markers).

#### D6C. COLUMNS
| column | type | null/default | meaning (and allowed values) |
|---|---|---|---|
| id | VARCHAR(24) | primary key | `SUB-<serial>` [REF](../references/PAYERS.md#markers); the enrolment handle in an eligibility answer |
| member_id | CITEXT | NOT NULL | the member ([D5. member](D5-member.md)) |
| policy_id | CITEXT | NOT NULL | the product ([D12. policy](D12-policy.md)) |
| pstart | DATE | NOT NULL | cover start; `Coverage.period.start` |
| pend | DATE | NOT NULL | cover end; `Coverage.period.end` |
| wallet_balance | NUMERIC(14,2) | NOT NULL, default 0 | what is left of the sum assured this cover year; never negative |
| status | VARCHAR(32) | NOT NULL, default `'active'` | `active`, `paused` |
| sub_type | VARCHAR(32) | NOT NULL | `Individual`, `Family Floater`: whether dependants are covered |
| plan_type_code | VARCHAR(64) | NOT NULL, default `'01'` | how the enrolment was sold, an ndhm-plan-type code ([D4. terminology_code](D4-terminology-code.md)) |
| owner_client_id | CITEXT, at most 64 | null | the sign-up account that sold it; empty is shared [SANDBOX](../references/PAYERS.md#markers) |
| abha_linked | BOOLEAN | NOT NULL, default false | an ABHA number is on file here |
| abha_no | VARCHAR(14) | null | 14 digits; required when `abha_linked` |
| abha_token | VARCHAR(120) | null | issued by ABDM on a link; held to replay consent, never returned to a screen |
| abha_link_status | VARCHAR(32) | NOT NULL, default `'none'` | what ABDM knows: `none`, `linked`, `delinked`, `failed` |
| abha_request_id | VARCHAR(64) | null | the request id of the last ABDM call, which its support desk asks for |
| abha_linked_at | TIMESTAMPTZ | null | when the link took at ABDM |
| abha_delinked_at | TIMESTAMPTZ | null | when the delink took at ABDM |
| created_at | TIMESTAMPTZ | NOT NULL, default now | |
| updated_at | TIMESTAMPTZ | NOT NULL, default now | bumped by trigger |
| deleted_at | TIMESTAMPTZ | null | set when retired |

#### D6K. KEYS AND INDEXES
- Primary key `id`.
- Unique `uq_subscriptions_member_policy` on `(member_id, policy_id)`: one wallet per member per product.
- Foreign keys: `member_id` references [D5. member](D5-member.md) `id`, `policy_id` references [D12. policy](D12-policy.md) `id`, both `ON DELETE RESTRICT`.
- Checks: `ck_subscriptions_status`; `ck_subscriptions_sub_type`; `ck_subscriptions_abha_link_status`; `ck_subscriptions_wallet` (`wallet_balance >= 0`); `ck_subscriptions_abha` (`abha_linked` implies `abha_no` set); `ck_subscriptions_abha_no` (null or 14 digits); `ck_subscriptions_period` (`pend >= pstart`); `ck_subscriptions_owner_len`.
- Indexes: `idx_subscriptions_live` on `(deleted_at, status)`; `idx_subscriptions_policy` on `policy_id`; `idx_subscriptions_period` on `(deleted_at, pend, pstart)`, for "whose cover is live today" and "whose lapses this month"; `idx_subscriptions_owner` on `owner_client_id`.
- Referenced by [D7. subscription_family_member](D7-subscription-family-member.md), [D8. wallet_entry](D8-wallet-entry.md) and [D9. abha_link_event](D9-abha-link-event.md) (`ON DELETE CASCADE`) and by [D19. case](D19-case.md) `subscription_id` (`ON DELETE RESTRICT`).

#### D6U. USED BY
- Screens: [S1. Overview](../screens/S1-overview.md), [S3. Case Desk](../screens/S3-case-desk.md), [S5. Subscriptions](../screens/S5-subscriptions.md)
- APIs: [A1. Eligibility Answer](../apis/A1-eligibility-answer.md), [A2. Insurance Plan Answer](../apis/A2-insurance-plan-answer.md), [A3. Pre-auth Answer](../apis/A3-preauth-answer.md), [A4. Claim Answer](../apis/A4-claim-answer.md), [A10. Predetermination Quote](../apis/A10-predetermination-quote.md), [A13. Adjudicate](../apis/A13-adjudicate.md), [A16. ABHA Policy Link](../apis/A16-abha-policy-link.md), [A19. Sandbox Scenarios](../apis/A19-sandbox-scenarios.md)
- Callbacks: [C1. Callback Door](../callbacks/C1-callback-door.md), [C3. Insurance Plan Request](../callbacks/C3-insurance-plan-request.md), [C5. Claim Submit](../callbacks/C5-claim-submit.md), [C7. Task Submit](../callbacks/C7-task-submit.md)
- FHIR: [F2. CoverageEligibilityRequest](../fhir/F2-coverage-eligibility-request.md), [F3. CoverageEligibilityResponse](../fhir/F3-coverage-eligibility-response.md), [F4. Task (InsurancePlan request)](../fhir/F4-task-insuranceplan.md), [F5. InsurancePlan](../fhir/F5-insuranceplan.md), [F10. Task (claim actions and answers)](../fhir/F10-task-claim-actions.md), [F11. CommunicationRequest](../fhir/F11-communicationrequest.md), [F15. Patient](../fhir/F15-patient.md), [F18. Coverage](../fhir/F18-coverage.md)
- Database: [D4. terminology_code](D4-terminology-code.md), [D5. member](D5-member.md), [D7. subscription_family_member](D7-subscription-family-member.md), [D8. wallet_entry](D8-wallet-entry.md), [D9. abha_link_event](D9-abha-link-event.md), [D12. policy](D12-policy.md), [D19. case](D19-case.md), [D29. predetermination_quote](D29-predetermination-quote.md), [D32. id_sequence](D32-id-sequence.md)
