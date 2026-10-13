# D21. claim_payment

#### D21T. TABLE
One row is one payment the payer notified on a claim (a PaymentNotice), with the acknowledgement sent back for it. Primary key `id`. Parent table: `claim` (D9), many rows per claim; children in `claim_payment_detail` (D22).

#### D21D. DESCRIPTION
This is the one leg the payer starts. It posts a payment notice when money moves and expects an acknowledgement straight back. There is no correlation id of ours to match on, so the claim is found by the claim number inside the bundle.

**Created.** By the payment notice callback (C10):

1. The bundle is flattened from its `PaymentNotice`, `PaymentReconciliation` and `Task`. A bundle with neither of the first two is refused ("That is not a payment notice.").
2. A notice whose correlation id is already on a row is a redelivery and is ignored.
3. The claim number is read from the `CLN`-typed identifier on the PaymentNotice, else the PaymentReconciliation, else the Task, else the first entry's untyped identifier. It is matched against `claim.claim_no`, then against the `claim_ref` of D20 and D18 (a cancellation retires numbers). No match: the notice is `unmatched` and nothing is stored.
4. If a row on the same claim has the same `notice_id` (the payer sends one notice when the transfer is initiated and one when it clears [PAYER](../references/PAYERS.md#markers)), that row is updated with the new notice, its acknowledgement is reset (`ack_status` `pending`, `ack_txn_id`, `ack_correlation_id`, `acknowledged_at`, `ack_error` cleared) and its D22 rows are replaced. Otherwise a new row is inserted.
5. The acknowledgement is sent at once (below). A failed acknowledgement does not fail the callback.

**Acknowledgement statuses** (`ack_status`, exact strings): `pending`, `sent`, `error`.

- `pending` to `sent`: the acknowledgement Task went (A8). Writes `ack_txn_id`, `ack_correlation_id`, `acknowledged_at`, clears `ack_error`. It goes to `sender_code` (else the claim's payer), carries this notice's `correlation_id`, and its workflow id is the adapter's `payment_ack` (see [PAYERS.md](../references/PAYERS.md)) [PAYER](../references/PAYERS.md#markers), else this row's `workflow_id`, else `claim_ref`, else the claim number.
- `pending` to `error`: the send failed. Writes `ack_error` and, when [G7. Send](../gateway/G7-send.md) named them, `ack_txn_id` and `ack_correlation_id`.
- `error` to `sent`: re-sent by hand from Payments (S12).

**Reading the money.** `paid_total` counts rows whose `payment_status` is `paid` or `cleared` (any case), skips a row whose `utr` is empty and whose `disposition` contains "initiat" (money on its way) [REF](../references/PAYERS.md#markers), and counts each UTR once (newest row wins; a row without a UTR counts by its id). The claim stage becomes `payment` as soon as one notice exists: `paid` when that total is above 0, else `noticed`.

**Deleted.** Never by the application; by cascade with the claim or when the transactional store is cleared.

#### D21C. COLUMNS
| Column | Type | Null / default | Meaning |
|---|---|---|---|
| id | INTEGER | primary key | Row id |
| claim_id | INTEGER | NOT NULL | The claim (D9) the notice names |
| claim_ref | TEXT | null | The claim number the notice named |
| correlation_id | TEXT | null, unique | The payer's correlation id; dedupes redeliveries |
| sender_code | TEXT | null | `x-hcx-sender_code` of the notice; the acknowledgement goes back to it |
| workflow_id | TEXT | null | `x-hcx-workflow_id` of the notice |
| received_at | TEXT | NOT NULL | When the notice was stored |
| disposition | TEXT | null | `PaymentReconciliation.disposition`, else `Task.description`, else the payment status display, else the reconciliation outcome, else "Payment notice" |
| payment_status | TEXT | null | `PaymentNotice.paymentStatus` code, for example `paid`, `cleared` |
| payment_date | TEXT | null | `PaymentReconciliation.paymentDate`, else the date part of `PaymentNotice.created` |
| amount | REAL | null | `PaymentNotice.amount.value`, else `PaymentReconciliation.paymentAmount.value` |
| currency | TEXT | null | Currency of that amount |
| utr | TEXT | null | Unique Transaction Reference: `PaymentReconciliation.paymentIdentifier.value` |
| notice_json | TEXT | null | The notice bundle as received |
| ack_status | TEXT | NOT NULL, default `pending` | `pending`, `sent`, `error` |
| ack_txn_id | TEXT | null | Ledger id of the acknowledgement |
| ack_correlation_id | TEXT | null | Correlation id the acknowledgement went out under |
| acknowledged_at | TEXT | null | When the acknowledgement went |
| ack_error | TEXT | null | Why the acknowledgement failed |
| notice_id | TEXT | null | `PaymentNotice.id`; a later notice with the same id updates this row. Migration only |

#### D21K. KEYS AND INDEXES
- Primary key `id` (integer).
- Foreign key `claim_id` references `claim (id)` (D9), `ON DELETE CASCADE`. D22 rows reference this table.
- Index `ix_claim_payment` on `(claim_id, id DESC)`; notices are listed newest first.
- Unique index `ux_claim_payment_corr` on `(correlation_id)`. SQLite allows several nulls.

#### D21U. USED BY
- Screens: [S5. Claim Master](../screens/S5-claim-master.md), [S6. Claim Detail](../screens/S6-claim-detail.md), [S11. Claim Submission](../screens/S11-claim-submission.md), [S12. Payments](../screens/S12-payments.md)
- APIs: [A8. Payment Notice Acknowledgement](../apis/A8-paymentnotice-on-request.md), [A17. Claim State](../apis/A17-claim-state.md)
- Callbacks: [C1. Callback Door](../callbacks/C1-callback-door.md), [C10. Payment Notice](../callbacks/C10-paymentnotice-request.md)
- FHIR: [F13. PaymentNotice](../fhir/F13-paymentnotice.md), [F14. Payment acknowledgement](../fhir/F14-payment-acknowledgement.md)
- Database: [D9. claim](D9-claim.md), [D22. claim_payment_detail](D22-claim-payment-detail.md), [D29. claim_enquiry](D29-claim-enquiry.md)
