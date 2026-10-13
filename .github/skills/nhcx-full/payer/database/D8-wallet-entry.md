# D8. wallet_entry

#### D8T. TABLE
One row is one movement of one enrolment's wallet, with the balance it produced; primary key `id`, an identity column. Parent table [D6. subscription](D6-subscription.md). The reference implementation names it `payer_wallet_entries` [REF](../references/PAYERS.md#markers).

#### D8D. DESCRIPTION
The ledger that explains [D6. subscription](D6-subscription.md) `wallet_balance`. An adjudicator asked "why is this member short of cover" needs the history, not the number, and the Subscriptions screen ([S5. Subscriptions](../screens/S5-subscriptions.md)) shows it newest first (`GET subscriptions/:id/wallet`).

Every entry is written in the same transaction as the balance it records, with the enrolment row locked first, so the running total and the ledger never disagree and two concurrent debits cannot both read the same balance. Three writers:

| Writer | Direction | Reason recorded |
|---|---|---|
| a manual adjustment from [S5. Subscriptions](../screens/S5-subscriptions.md) (`POST subscriptions/:id/wallet`) | `credit` or `debit` | the operator's reason |
| the claim approval in [A13. Adjudicate](../apis/A13-adjudicate.md): cover is drawn down when the final claim is approved, not at pre-authorisation, because a pre-authorisation is a promise and the money leaves when the bill behind it is settled | `debit` of the approved amount | "Claim `<case id>` approved" |
| a decided claim reopened by a reprocess or a balance release ([C7. Task Submit](../callbacks/C7-task-submit.md), or the desk's own reprocess on [S3. Case Desk](../screens/S3-case-desk.md)) | `credit` of the amount that had been debited | "Claim `<case id>` reopened for reprocessing" |

A debit that would take the balance below zero is refused before anything is written: on approval, with "Insufficient wallet balance", so an approval larger than the remaining cover is refused at adjudication rather than discovered at settlement. A rejected claim never drew on the wallet, so reopening it credits nothing.

Delete:
- Never; cascades with the enrolment.

#### D8C. COLUMNS
| column | type | null/default | meaning (and allowed values) |
|---|---|---|---|
| id | BIGINT | primary key, identity | row id |
| subscription_id | VARCHAR(24) | NOT NULL | the enrolment ([D6. subscription](D6-subscription.md)) |
| direction | VARCHAR(32) | NOT NULL | `credit`, `debit` |
| amount | NUMERIC(14,2) | NOT NULL | the movement, always positive |
| balance_after | NUMERIC(14,2) | NOT NULL | the wallet after this entry, never negative |
| reason | VARCHAR(300) | null | why |
| user_id | VARCHAR(36) | null | the acting account ([D2. staff](D2-staff.md)), null for a system write |
| at | TIMESTAMPTZ | NOT NULL, default now | when |

#### D8K. KEYS AND INDEXES
- Primary key `id`.
- Foreign key `subscription_id` references [D6. subscription](D6-subscription.md) `id` (`ON DELETE CASCADE`); `user_id` references the account table (`ON DELETE SET NULL`).
- Checks: `ck_wallet_direction`; `ck_wallet_amount` (`amount > 0`); `ck_wallet_balance` (`balance_after >= 0`).
- Index `idx_wallet_subscription` on `(subscription_id, at)`.

#### D8U. USED BY
- Screens: [S3. Case Desk](../screens/S3-case-desk.md), [S5. Subscriptions](../screens/S5-subscriptions.md)
- APIs: [A4. Claim Answer](../apis/A4-claim-answer.md), [A13. Adjudicate](../apis/A13-adjudicate.md)
- Callbacks: [C7. Task Submit](../callbacks/C7-task-submit.md)
- Database: [D2. staff](D2-staff.md), [D6. subscription](D6-subscription.md), [D19. case](D19-case.md)
- Tests: [T12. Claim Received and Approved](../tests/T12-claim-approved.md), [T14. Reprocess and Balance Release](../tests/T14-reprocess-and-release.md)
