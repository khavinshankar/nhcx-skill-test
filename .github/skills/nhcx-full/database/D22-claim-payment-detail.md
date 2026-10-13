# D22. claim_payment_detail

#### D22T. TABLE
One row is one line of a payment notice's reconciliation breakdown: an amount paid or withheld. Primary key `id`. Parent table: `claim_payment` (D21).

#### D22D. DESCRIPTION
**Created.** With its payment notice (C10), in the same transaction as the D21 row: one row per `PaymentReconciliation.detail[]` entry that is an object, numbered in order from 1 in `seq`.

**Replaced.** When a later notice with the same `notice_id` updates its D21 row, every detail row of that payment is deleted and the new notice's lines are inserted.

**Deleted.** With the parent payment (cascade), or when the transactional store is cleared.

Rows are never edited. There is no status column.

#### D22C. COLUMNS
| Column | Type | Null / default | Meaning |
|---|---|---|---|
| id | INTEGER | primary key | Row id |
| payment_id | INTEGER | NOT NULL | The payment notice (D21) |
| seq | INTEGER | NOT NULL, default 1 | Position of the line in `detail[]`, from 1 |
| reference | TEXT | null | `detail.id`, else `detail.identifier.value` |
| type_code | TEXT | null | `detail.type` code, for example `Payment`, `RF` |
| type_display | TEXT | null | `detail.type` display (or text) |
| date | TEXT | null | `detail.date` |
| amount | REAL | null | `detail.amount.value` |

#### D22K. KEYS AND INDEXES
- Primary key `id` (integer).
- Foreign key `payment_id` references `claim_payment (id)` (D21), `ON DELETE CASCADE`.
- Index `ix_claim_payment_detail` on `(payment_id, seq)`; lines are read in `seq` order.

#### D22U. USED BY
- Screens: [S12. Payments](../screens/S12-payments.md)
- Callbacks: [C10. Payment Notice](../callbacks/C10-paymentnotice-request.md)
- FHIR: [F13. PaymentNotice](../fhir/F13-paymentnotice.md)
- Database: [D21. claim_payment](D21-claim-payment.md)
