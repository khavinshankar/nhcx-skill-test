# D2. staff

#### D2T. TABLE
One row is the desk's half of one account: the payer it works for and its avatar; primary key `user_id`, which is the account's id in the target's own account table. Parent tables: the account table (the target's own) and [D1. payer](D1-payer.md). The reference implementation names it `payer_staff` and keeps the account itself (handles, password, sessions) and the role on this desk in tables shared with other desks [REF](../references/PAYERS.md#markers); those are not specified here.

#### D2D. DESCRIPTION
The target payer system already has accounts. What NHCX needs from them is three things, and this table plus the target's own role model hold them:

- **Which payer the account works for** (`payer_id`), so a deployment that hosts more than one insurer can tell them apart. Most deployments have one row in [D1. payer](D1-payer.md) and every staff row points at it.
- **The role**, which decides what an account may do on the desk. Three roles, exact strings [REF](../references/PAYERS.md#markers):

| Role | May |
|---|---|
| `adjudicator` | decide line items and cases ([A13. Adjudicate](../apis/A13-adjudicate.md)) |
| `finance` | raise and complete payments ([A14. Disburse](../apis/A14-disburse.md)) |
| `admin` | both |

  Deciding a case is refused to `finance`; the reference lets every role release a payment, because a sandbox is worked by one person wearing every hat, and records who released what in [D31. audit_log](D31-audit-log.md) [REF](../references/PAYERS.md#markers). A production target keeps the two apart: an adjudicator cannot move money and finance cannot decide a claim.
- **Which participant codes the account works** [SANDBOX](../references/PAYERS.md#markers): the reference lets a sign-up account list the NHCX participant codes it fronts, and shows it only the cases ([D19. case](D19-case.md) `nhcx_recipient_code`) and payments addressed to them; an account listing none sees everything. A single-payer target does not need this.

Create:
- When an account is given a role on the desk. The reference opens the desk on an existing account (`POST auth/desk`) with the `admin` role [REF](../references/PAYERS.md#markers).

Update:
- `avatar_url` from the account's own profile; `payer_id` never changes in practice.

Delete:
- Cascades from the account.

Every write to member, policy and case data records the acting account in [D31. audit_log](D31-audit-log.md) `user_id`, and a decision records it in [D19. case](D19-case.md) `adjudicated_by`, a payment in [D30. payment](D30-payment.md) `initiated_by`, a wallet movement in [D8. wallet_entry](D8-wallet-entry.md) `user_id`.

#### D2C. COLUMNS
| column | type | null/default | meaning (and allowed values) |
|---|---|---|---|
| user_id | VARCHAR(36) | primary key | the account's id in the target's account table |
| payer_id | VARCHAR(32) | NOT NULL | the payer worked for ([D1. payer](D1-payer.md)) |
| avatar_url | VARCHAR(500) | null | profile picture |
| created_at | TIMESTAMPTZ | NOT NULL, default now | when the desk was opened on the account |
| updated_at | TIMESTAMPTZ | NOT NULL, default now | bumped by trigger on a real change |

The role itself lives on the target's account-to-desk table with the values above; a target with a single role column keeps it there.

#### D2K. KEYS AND INDEXES
- Primary key `user_id`.
- Foreign key `user_id` references the account table (`ON DELETE CASCADE`).
- Foreign key `payer_id` references [D1. payer](D1-payer.md) `id` (`ON DELETE RESTRICT`).
- Index `idx_payer_staff_payer` on `payer_id`.

#### D2U. USED BY
- Database: [D1. payer](D1-payer.md), [D8. wallet_entry](D8-wallet-entry.md), [D9. abha_link_event](D9-abha-link-event.md), [D19. case](D19-case.md), [D30. payment](D30-payment.md), [D31. audit_log](D31-audit-log.md)
