# D30. payment

#### D30T. TABLE
One row is one disbursement against one approved case ([D19. case](D19-case.md)); primary key `id`. Several are allowed: a claim can be settled in instalments. The reference implementation names it `payer_payments` [REF](../references/PAYERS.md#markers).

#### D30D. DESCRIPTION
The money. Finance raises a payment against a case whose claim is approved, completes it with the bank's UTR, or records that the bank returned it; each movement is what the payment notice ([A6. Payment Notice](../apis/A6-payment-notice.md), [F13. PaymentNotice](../fhir/F13-paymentnotice.md), [F14. PaymentReconciliation](../fhir/F14-paymentreconciliation.md)) tells the hospital, and the hospital's acknowledgement ([C11. Payment Acknowledgement](../callbacks/C11-payment-acknowledgement.md)) is stamped here. A hospital asking where the money is ([C10. Payment Enquiry](../callbacks/C10-payment-enquiry.md)) is answered from these rows ([A7. Payment Enquiry Answer](../apis/A7-payment-enquiry-answer.md)).

**Numbering.** `id` is `PAY-<year>-<serial>` from the `payment` counter ([D32. id_sequence](D32-id-sequence.md)), four digits [REF](../references/PAYERS.md#markers); it is the `PaymentNotice.identifier` and the reconciliation's line identifier.

**Raised** by [A14. Disburse](../apis/A14-disburse.md) (`POST payments`), only by a role that may disburse ([D2. staff](D2-staff.md)):
- The case must be `approved` ("the case is not approved"); the case row is locked and every payment on it that is not `failed` is summed, so two terminals cannot each raise the last instalment; the new amount over what is left is refused ("over-payment"). The amount must be positive.
- TDS is computed once here (`tds_amount` = amount times percent, rounded to paise; `net_payable` = amount minus TDS), so the three numbers on the advice note always add up; the check enforces the arithmetic.
- With a `utr_no` given, the payment is raised and completed in one transaction (the one-step disbursement); without one it waits as `initiated`. Either way [A6. Payment Notice](../apis/A6-payment-notice.md) sends the notice and records the transaction in `nhcx_notice_txn_id`.

**Completed** by [A14. Disburse](../apis/A14-disburse.md) (`POST payments/:id/complete` with the UTR): the payment must be `initiated` ("the payment is closed"); the UTR goes on the row, `completed_at` now, the case's `total_paid` up by the amount, and the case becomes `settled` when the approved amount has gone out in full. [A6. Payment Notice](../apis/A6-payment-notice.md) sends the notice again with the UTR. A UTR is one movement of money and is unique across the table ("That UTR has already been recorded against another payment").

**Failed** by [A14. Disburse](../apis/A14-disburse.md) (`POST payments/:id/fail` with a note): from `initiated` only; the money never left, the case's paid total is untouched, and the amount becomes available to disburse again.

**Acknowledged** by [C11. Payment Acknowledgement](../callbacks/C11-payment-acknowledgement.md): every completed, unacknowledged payment on the case is stamped `nhcx_acknowledged_at` when the hospital's `paymentack` Task arrives.

Statuses (`status`): `initiated`, `completed`, `failed`. A completed transfer has a UTR and a completion time; nothing else may (`ck_payments_completion`). A bank transfer carries an account and an IFSC, UPI a handle, a cheque neither (`ck_payments_beneficiary`).

Delete: never; a case with payments cannot be removed (`RESTRICT`).

#### D30C. COLUMNS
| column | type | null/default | meaning (and allowed values) |
|---|---|---|---|
| id | VARCHAR(24) | primary key | `PAY-<year>-<serial>` [REF](../references/PAYERS.md#markers) |
| case_id | VARCHAR(24) | NOT NULL | the case ([D19. case](D19-case.md)) |
| payment_amount | NUMERIC(14,2) | NOT NULL | gross, positive |
| tds_percent | NUMERIC(5,2) | NOT NULL, default 2 | 0 to 100 |
| tds_amount | NUMERIC(14,2) | NOT NULL | withheld; 0 to `payment_amount` |
| net_payable | NUMERIC(14,2) | NOT NULL | `payment_amount - tds_amount` |
| mode | VARCHAR(32) | NOT NULL | `NEFT`, `RTGS`, `IMPS`, `UPI`, `Cheque` |
| beneficiary_name | VARCHAR(200) | NOT NULL | the payee, the hospital |
| beneficiary_account | VARCHAR(40) | null | required for a bank transfer |
| beneficiary_ifsc | VARCHAR(16) | null | required for a bank transfer, upper case |
| beneficiary_bank | VARCHAR(160) | null | |
| beneficiary_upi | VARCHAR(120) | null | required for UPI |
| utr_no | VARCHAR(40) | null, UNIQUE | the bank's reference; set exactly when `completed` |
| status | VARCHAR(32) | NOT NULL, default `'initiated'` | `initiated`, `completed`, `failed` |
| failure_note | VARCHAR(500) | null | why the bank returned it |
| initiated_by | VARCHAR(36) | null | the disbursing account ([D2. staff](D2-staff.md)) |
| initiated_at | TIMESTAMPTZ | NOT NULL, default now | |
| completed_at | TIMESTAMPTZ | null | set exactly when `completed` |
| nhcx_notice_txn_id | VARCHAR(128) | null | the ledger id ([G9. Ledger](../gateway/G9-ledger.md)) the last PaymentNotice went out as |
| nhcx_acknowledged_at | TIMESTAMPTZ | null | when the hospital acknowledged the notice |

#### D30K. KEYS AND INDEXES
- Primary key `id`. Unique `uq_payments_utr` on `utr_no`.
- Foreign keys: `case_id` references [D19. case](D19-case.md) `id` (`ON DELETE RESTRICT`); `initiated_by` references the account table (`ON DELETE SET NULL`).
- Checks: `ck_payments_mode`; `ck_payments_status`; `ck_payments_amount` (`> 0`); `ck_payments_tds` (percent 0 to 100, amount 0 to `payment_amount`); `ck_payments_net` (`net_payable = payment_amount - tds_amount`); `ck_payments_completion` (`completed` with UTR and time, else neither); `ck_payments_beneficiary` (account and IFSC for NEFT, RTGS, IMPS; UPI handle for UPI; nothing for Cheque).
- Indexes: `idx_payments_case` on `(case_id, initiated_at)`; `idx_payments_status` on `(status, initiated_at)`.

#### D30U. USED BY
- Screens: [S1. Overview](../screens/S1-overview.md), [S10. Payments](../screens/S10-payments.md)
- APIs: [A6. Payment Notice](../apis/A6-payment-notice.md), [A7. Payment Enquiry Answer](../apis/A7-payment-enquiry-answer.md), [A11. Transaction Related](../apis/A11-txn-related.md), [A14. Disburse](../apis/A14-disburse.md), [A15. Case Exchange Log](../apis/A15-case-exchange.md)
- Callbacks: [C10. Payment Enquiry](../callbacks/C10-payment-enquiry.md), [C11. Payment Acknowledgement](../callbacks/C11-payment-acknowledgement.md)
- FHIR: [F10. Task (claim actions and answers)](../fhir/F10-task-claim-actions.md), [F13. PaymentNotice](../fhir/F13-paymentnotice.md), [F14. PaymentReconciliation](../fhir/F14-paymentreconciliation.md)
- Database: [D2. staff](D2-staff.md), [D19. case](D19-case.md), [D32. id_sequence](D32-id-sequence.md)
- Tests: [T15. Payment Notices and Acknowledgement](../tests/T15-payment-noticed.md)
