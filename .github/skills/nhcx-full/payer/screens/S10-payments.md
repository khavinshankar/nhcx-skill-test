# S10. Payments Screen

#### S10R. ROUTE
`/payments`

| Endpoint | Purpose |
|---|---|
| `GET cases?awaiting_payment=true` | The queue: approved cases with money still outstanding |
| `GET payments?search=&status=&case_id=` | The register |
| `POST payments` | Raise a payment; with `utr_no`, raise and complete it in one step |
| `POST payments/:id/complete` | Record the UTR on an initiated payment |
| `POST payments/:id/fail` | Mark a transfer the bank returned |
| `GET payments/:id` | One payment, with the notice transaction and the acknowledgement time |

Breadcrumb: Payments

#### S10D. DESCRIPTION
Adjudication decides; finance disburses. This screen releases the money owed on approved claims, withholds TDS, records the bank's UTR, and settles the case when it has been paid in full ([A14. Disburse](../apis/A14-disburse.md), [D30. payment](../database/D30-payment.md)). Every movement of money is told to the hospital over the exchange as a payment notice ([A6. Payment Notice](../apis/A6-payment-notice.md)): once when the payment is raised, and again with the UTR when it completes. The hospital's acknowledgement comes back on the notice's thread ([C11. Payment Acknowledgement](../callbacks/C11-payment-acknowledgement.md)) and is recorded on the payment.

**Who may act.** Releasing a payment is finance's or an admin's ("Sign in to release a payment" for others); in the reference sandbox it is open to every signed-in role, the audit trail recording who released what [SANDBOX](../references/PAYERS.md#markers).

**Approved Claims Awaiting Disbursement (n)**, one card per case in the queue: the claim number, the patient, the hospital; "Approved ₹x"; a progress bar "Paid Ratio (`<percent>`%)" with "Remaining: ₹y"; and a "Release ₹y" button. A case leaves the queue the moment its last instalment settles. Empty: "Nothing awaiting disbursement" with "Approved claim cases appear here once an adjudicator clears them for payment."

**Release Payment dialog**, "Release Payment & Record UTR":

| Field | Control | Rule |
|---|---|---|
| Select Approved Claim Case | select, "`<claim no>` - `<patient>` - Approved: ₹x"; choosing one fills the amount with the remaining balance and the beneficiary with the hospital | "Choose a case to pay against" |
| Disbursement Amount (₹) | number | "Enter an amount greater than zero"; more than the balance still outstanding, counting every payment not failed: "That is more than the approved amount still outstanding" with "Reduce this to the remaining balance or less"; a case not approved: "This claim has not been approved for disbursement yet" |
| TDS Rate (%) | number, default the deployment's rate (the reference screen starts at 10%, the server at 2% [REF](../references/PAYERS.md#markers)) | "TDS must be between 0 and 100 percent" |
| Breakdown | Gross Disbursed Amount, "TDS Deduction (`<rate>`%): - ₹", "Net Bank Transfer Amount: ₹" computed live; the server recomputes and the database checks `net = amount - tds` | |
| Mode | NEFT, RTGS, IMPS, UPI, Cheque | "Choose a payment mode" |
| Beneficiary Bank Account | name; account number and IFSC for a bank transfer; UPI id for UPI; nothing for a cheque | "Enter the beneficiary's name"; "Enter the account number"; "Enter the IFSC", "An IFSC is four letters, a zero, then six characters"; "Enter the UPI id", "Enter a UPI id in the form name@bank"; from the schema: "A bank transfer needs an account number and IFSC; UPI needs a UPI id" |
| UTR (optional) | when the transfer has already been made | "A UTR is between 8 and 40 characters"; upper-cased; unique: "That UTR has already been recorded against another payment" |

Without a UTR the payment is raised as `initiated` and the hospital is told the money is on the way; the toast reads "Payment `<id>` initiated, the hospital has been notified. Record the UTR once the bank confirms." With a UTR the payment is raised and completed in one transaction and the case's paid total moves at once. Payment ids are `PAY-<year>-<serial>` ([D32. id_sequence](../database/D32-id-sequence.md)) [REF](../references/PAYERS.md#markers).

**Payment & Disbursement History (n)**, the register. Columns: Payment ID, Claim / Case ID (the claim number over the case id), Hospital Beneficiary (name; bank and account underneath), Gross Claim (₹), TDS Withheld (₹, amber), Net Disbursed (₹, green), UTR Reference (or "Awaiting UTR" in amber italics), Status (`completed` green, `initiated` amber, `failed` red), Actions ("Record UTR" on an initiated payment; "Disbursed" on a completed one). Empty: "No disbursements yet" with "Disburse an approved claim from the queue above to start the register."

**Record UTR dialog**, "Record UTR Transaction Reference": Payment ID and Net Transfer Amount, then "Bank UTR / Ref Number" with the note "Filled in for the sandbox; overtype it with the reference the bank returned. Recording it completes the disbursement and notifies the hospital." (the sandbox mints `UTR<yyyymmdd><8 digits>` because it has no bank [SANDBOX](../references/PAYERS.md#markers)). "Enter the UTR the bank returned". Completing adds the amount to the case's paid total and settles the case (stage `settled`, timeline "Case Fully Settled") once the approved amount has gone out in full; the notice goes out again with the UTR ([A6. Payment Notice](../apis/A6-payment-notice.md)). Toast: "UTR `<utr>` recorded! Disbursement completed successfully." A payment already completed or failed: "That payment has already been completed or failed".

**Fail** (`POST payments/:id/fail`, no button in the reference [REF](../references/PAYERS.md#markers)): a note is required, "Record what the bank said, so the retry is not a guess". The money never left, so the paid total is untouched and the amount is available to disburse again.

**Notice trail.** Each payment records the transaction its notice went out as and when the hospital acknowledged it (`nhcx_notice_txn_id`, `nhcx_acknowledged_at`, [D30. payment](../database/D30-payment.md)); the case's exchange log (S3.4) shows the notices and the acknowledgement.

Timeline events on the case: "Disbursement Initiated" ("₹x initiated via `<mode>`, ₹t withheld as TDS at r%, ₹n net payable to `<beneficiary>`."), "Disbursement Completed (UTR: `<utr>`)", "Case Fully Settled", "Disbursement Failed".

API: [A6. Payment Notice](../apis/A6-payment-notice.md)

API: [A14. Disburse](../apis/A14-disburse.md)

Callback: [C11. Payment Acknowledgement](../callbacks/C11-payment-acknowledgement.md)

Data: [D19. case](../database/D19-case.md)

Data: [D30. payment](../database/D30-payment.md)

#### S10L. LAYOUT
The arrangement below is the reference desk's [REF](../references/PAYERS.md#markers): follow the target payer system's own screen conventions. What is required is in DESCRIPTION and ACTIONS: the queue, the fields and their rules, the register columns, the statuses and the messages.

```
|------------------------------------------------------------------|
| Payment Queue                                                    |
| Release the money owed on approved claims, TDS is withheld ...   |
|------------------------------------------------------------------|
| [Approved Claims Awaiting Disbursement (2)]                      |
|  +------------------------+ +------------------------+           |
|  | CL/26/0SE0000V9        | | CL/26/0SE0000VB        |           |
|  | Ramesh Kumar  Approved | | ...                    |           |
|  | Apollo        ₹1,20,000| |                        |           |
|  | Paid Ratio (0%)  Remaining: ₹1,20,000              |           |
|  | [====================]                             |           |
|  |   [(bank) Release ₹1,20,000]                       |           |
|  +------------------------+ +------------------------+           |
|------------------------------------------------------------------|
| [Payment & Disbursement History (7)]                             |
|  Payment ID | Claim / Case ID | Hospital Beneficiary | Gross |   |
|  TDS Withheld | Net Disbursed | UTR Reference | Status | Actions |
|  PAY-2026-0007 | CL/26/... | Apollo (HDFC 9910..) | ₹1,20,000 |  |
|  ₹2,400 | ₹1,17,600 | Awaiting UTR | INITIATED | [Record UTR]    |
|------------------------------------------------------------------|
| Dialog: Release Payment & Record UTR                             |
|  Select Approved Claim Case [CL/26/... - Ramesh - ₹1,20,000 v]   |
|  Disbursement Amount (₹) [120000]   TDS Rate (%) [2.0]           |
|  Gross ₹1,20,000 | TDS (2%) - ₹2,400 | Net ₹1,17,600             |
|  Beneficiary Bank Account [Apollo ...] [account] [IFSC]          |
|                                   [Cancel] [Initiate Payment]    |
|------------------------------------------------------------------|
```

- Two cards: the queue as a grid of case cards with a progress bar, then the register as a table (stacked cards on small screens).
- The release dialog shows the TDS breakdown as a shaded box between the amount fields and the beneficiary fields.
- The UTR dialog is small: the payment summary and one input.

#### S10A. ACTIONS
1. Release ₹y: open the release dialog for that case.
2. Initiate Payment: validate and raise the payment; the notice goes out ([A6. Payment Notice](../apis/A6-payment-notice.md)); with a UTR, complete it in the same step.
3. Record UTR: open the UTR dialog; "Confirm & Complete Disbursement" completes the payment, settles the case when paid in full, and sends the notice again with the UTR.
4. Fail a payment (over the endpoint): record the bank's note; the amount returns to the queue [REF](../references/PAYERS.md#markers).
5. Search: narrow the register by payment id, UTR, claim number, patient, hospital or beneficiary.
