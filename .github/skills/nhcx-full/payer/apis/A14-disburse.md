# A14. Disburse

#### A14E. ENDPOINT

Inbound to the application (the desk's own JSON endpoints), behind a signed-in session with a payer desk role:

| Call | Does |
|---|---|
| `POST /payments` | raises a payment against an approved case; with `utr_no` it is raised and completed in one step |
| `POST /payments/:id/complete` | records the bank's UTR on an initiated payment |
| `POST /payments/:id/fail` | marks an initiated payment as returned by the bank |
| `GET /payments`, `GET /payments/:id` | lists and reads payments (`?search=`, `?status=`, `?case_id=`, `?limit=&offset=`) |

Roles: every desk role may release a payment; the reference sandbox is worked by one person wearing every hat, and the audit trail records who released what [REF](../references/PAYERS.md#markers). A production target keeps disbursement to finance and admin.

#### A14D. DESCRIPTION

Money moves against a case whose `adjudication_status` is `approved`, in one or more instalments, and never beyond the approved total. The case row is locked while a payment is raised, and every payment that is not `failed` (completed or still initiated) counts against the total, so two terminals cannot each release the last instalment.

**Two ways to pay.** With a `utr_no` the transfer has already been made: the payment is raised and completed in one transaction, nothing is left `initiated` for a second visit, and the timeline gets one event. Without one the payment waits as `initiated` until `.../complete` records the UTR, or `.../fail` records what the bank said.

**TDS.** `tds_percent` left out means the configured default (2 percent in the reference [REF](../references/PAYERS.md#markers)), not zero. The split is rounded once: `tds_amount` = round2(amount x percent / 100), `net_payable` = round2(amount - tds), so the three numbers on the advice note always add up.

**Beneficiary by rail.** NEFT, RTGS and IMPS need an account number and an IFSC (four letters, a zero, then six characters); UPI needs a UPI id (`name@bank`); a cheque needs neither.

**The UTR is unique.** One UTR is one movement of money; recording it twice would settle a case that was paid once. Between 8 and 40 characters, upper-cased.

**Completing.** The amount is added to D19 `total_paid`; when the paid total reaches the approved total the case's stage becomes `settled` and the timeline says "Case Fully Settled". A failed payment leaves `total_paid` alone: the money never left, and the amount is available to release again.

**Telling the hospital.** When the deployment pushes payment notices and the case came off the exchange, every raise and every completion sends [A6. Payment Notice](A6-payment-notice.md): once when the payment is initiated (no UTR), once when the UTR is recorded, on a fresh thread each time, with the same PaymentNotice id so the hospital reads the second as the first moving on. A gateway that is down does not undo the payment; the notice's transaction is left blank and the desk offers the notice again ([S10. Payments](../screens/S10-payments.md)).

**Messages, verbatim.** "Choose a case to pay against", "Enter an amount greater than zero", "TDS must be between 0 and 100 percent", "Choose a payment mode", "Enter the beneficiary's name", "Enter the account number", "Enter the IFSC", "An IFSC is four letters, a zero, then six characters", "Enter the UPI id", "Enter a UPI id in the form name@bank", "Enter the UTR the bank returned", "A UTR is between 8 and 40 characters", "Record what the bank said, so the retry is not a guess", "Sign in to release a payment", "No case with that id", "This claim has not been approved for disbursement yet", "That is more than the approved amount still outstanding" (field `payment_amount`: "Reduce this to the remaining balance or less"), "That payment has already been completed or failed", "That UTR has already been recorded against another payment", "A bank transfer needs an account number and IFSC; UPI needs a UPI id", "No payment with that id".

Data: [D30. payment](../database/D30-payment.md), [D19. case](../database/D19-case.md), [D26. case_timeline](../database/D26-case-timeline.md), [D31. audit_log](../database/D31-audit-log.md).

#### A14Q. REQUEST

**Raise**, `POST /payments`:

| Field | Type | Required | Notes |
|---|---|---|---|
| `case_id` | string | yes | an approved case ([D19. case](../database/D19-case.md)) |
| `payment_amount` | number | yes | gross, greater than zero, at most the approved amount still outstanding |
| `tds_percent` | number | no | 0 to 100; left out means the configured default |
| `mode` | string | yes | `NEFT`, `RTGS`, `IMPS`, `UPI`, `Cheque` |
| `beneficiary` | object | yes | `{"name", "account_no", "ifsc", "bank_name", "upi_id"}`; which are required depends on `mode` |
| `utr_no` | string | no | with it the payment is raised and completed in one step |

```json
{"case_id": "CASE-1017", "payment_amount": 69000, "tds_percent": 2, "mode": "NEFT",
 "beneficiary": {"name": "Apollo Multi-Specialty Hospital", "account_no": "0123456789", "ifsc": "HDFC0001234", "bank_name": "HDFC Bank"},
 "utr_no": "UTR20260930101405"}
```

**Complete**, `POST /payments/:id/complete`: `{"utr_no": "UTR20260930101405"}`.

**Fail**, `POST /payments/:id/fail`: `{"note": "Account closed; returned by the beneficiary bank"}`.

#### A14S. RESPONSE

`201` on a raise, `200` on complete and fail, with the payment ([D30. payment](../database/D30-payment.md)) as the desk shows it:

| Key | Content |
|---|---|
| `id` | `PAY-<year>-<serial>` [REF](../references/PAYERS.md#markers) |
| `case_id`, `claim_no`, `member_name`, `hospital_name`, `approved_amount` | the case, snapshotted |
| `payment_amount`, `tds_percent`, `tds_amount`, `net_payable`, `mode` | the split |
| `beneficiary` | `{"name", "account_no", "ifsc", "bank_name", "upi_id"}` |
| `utr_no`, `status`, `failure_note` | `status` is `initiated`, `completed` or `failed` |
| `initiated_at`, `completed_at`, `initiated_by` | |
| `nhcx_notice_txn_id` | the transaction the notice went out as ([A6. Payment Notice](A6-payment-notice.md)); blank when nobody on the exchange was told |
| `nhcx_acknowledged_at` | when the hospital acknowledged it ([C11. Payment Acknowledgement](../callbacks/C11-payment-acknowledgement.md)) |

```json
{"id": "PAY-2026-0007", "case_id": "CASE-1017", "claim_no": "CL/26/0SE0000V9",
 "payment_amount": 69000, "tds_percent": 2, "tds_amount": 1380, "net_payable": 67620, "mode": "NEFT",
 "beneficiary": {"name": "Apollo Multi-Specialty Hospital", "account_no": "0123456789", "ifsc": "HDFC0001234", "bank_name": "HDFC Bank"},
 "utr_no": "UTR20260930101405", "status": "completed",
 "initiated_at": "2026-09-30T10:14:05.000Z", "completed_at": "2026-09-30T10:14:05.000Z", "initiated_by": "Meera Iyer",
 "nhcx_notice_txn_id": "7UPG004A"}
```

Errors: `422` with `fields` for a bad body; `403` "Sign in to release a payment"; `404`; `409` with the case and payment messages above.

#### A14P. PSEUDOCODE

When: the disbursement desk's "Release payment", "Record UTR" and "Mark failed" actions ([S10. Payments](../screens/S10-payments.md)), and the payer driver of the provider-side tests, which pays the sandbox payer's cases the same way.

```text
VALIDATE_PAYMENT(request):
    case_id not blank                 or "Choose a case to pay against"
    payment_amount > 0                or "Enter an amount greater than zero"
    tds = request.tds_percent if given else configured default; 0 <= tds <= 100 or "TDS must be between 0 and 100 percent"
    mode in PaymentModes              or "Choose a payment mode"
    beneficiary.name not blank        or "Enter the beneficiary's name"
    if mode in (NEFT, RTGS, IMPS):    account_no or "Enter the account number"; ifsc or "Enter the IFSC";
                                      ifsc matches ^[A-Z]{4}0[A-Z0-9]{6}$ or "An IFSC is four letters, a zero, then six characters"
    if mode == UPI:                   upi_id or "Enter the UPI id"; matches name@bank or "Enter a UPI id in the form name@bank"
    if utr_no given: utr = upper(trim(utr_no)); 8 <= len(utr) <= 40 or "A UTR is between 8 and 40 characters"

RAISE(request, actor):
    input = VALIDATE_PAYMENT(request)   # every problem at once, 422
    if not CanDisburse(actor.role): refuse 403 "Sign in to release a payment"
    in one transaction:
        id = INITIATE(input, actor, announce = utr blank)
        if utr: COMPLETE_TX(id, utr, actor)
    audit (D31): "payment.disbursed" (one step) or "payment.initiated"
    payment = D30[id]
    payment = A6.push_notice(payment)   # best effort; the payment stands whatever the gateway does
    return 201 payment

INITIATE(input, actor, announce):        # inside the caller's transaction
    case = D19 by input.case_id, locked   or refuse 404 "No case with that id"
    if case.adjudication_status != approved: refuse 409 "This claim has not been approved for disbursement yet"
    committed = sum(D30.payment_amount where case_id and status != failed)
    if round2(committed + input.payment_amount) > case.total_approved:
        refuse 409 "That is more than the approved amount still outstanding"
    tds = round2(amount * percent / 100); net = round2(amount - tds)
    id = "PAY-<year>-<next 'payment' serial (D32), 4 digits>"
    insert D30: id, case_id, payment_amount, tds_percent, tds_amount, net_payable, mode,
                beneficiary_*, status initiated, initiated_by actor, initiated_at now
    if announce: append D26 "Disbursement Initiated": "<amount> initiated via <mode>, <tds> withheld as TDS at <percent>%, <net> net payable to <beneficiary>."
    return id

COMPLETE(id, utr, actor):
    utr = upper(trim(utr)); validate as above; if not CanDisburse: refuse 403
    in one transaction: COMPLETE_TX(id, utr, actor)
    audit "payment.completed"; payment = A6.push_notice(D30[id]); return 200 payment

COMPLETE_TX(id, utr, actor):
    payment = D30[id], locked            or refuse 404 "No payment with that id"
    if payment.status != initiated:      refuse 409 "That payment has already been completed or failed"
    case = D19[payment.case_id], locked
    write D30: status completed, utr_no = utr, completed_at now      # unique utr: 409 "That UTR has already been recorded against another payment"
    paid = round2(case.total_paid + payment.payment_amount)
    write D19: total_paid = paid; stage = settled when paid >= case.total_approved
    append D26 "Disbursement Completed (UTR: <utr>)": "<amount> paid via <mode>. <net> net after <percent>% TDS of <tds>."
    if settled: append D26 "Case Fully Settled": "The approved amount has been disbursed in full. Case closed.", by "Settlement Engine"

FAIL(id, note, actor):
    note not blank                       or "Record what the bank said, so the retry is not a guess"
    if not CanDisburse: refuse 403
    payment = D30[id], locked; if status != initiated: refuse 409 "That payment has already been completed or failed"
    write D30: status failed, failure_note = note          # total_paid untouched
    append D26 "Disbursement Failed": "<amount> was returned by the bank. <note>", type error
    audit "payment.failed"; return 200 payment
```

#### A14U. USED BY
- Screens: [S10. Payments](../screens/S10-payments.md)
- APIs: [A6. Payment Notice](A6-payment-notice.md), [A18. Provider Driver](A18-provider-driver.md)
- Callbacks: [C11. Payment Acknowledgement](../callbacks/C11-payment-acknowledgement.md)
- FHIR: [F13. PaymentNotice](../fhir/F13-paymentnotice.md)
- Database: [D2. staff](../database/D2-staff.md), [D19. case](../database/D19-case.md), [D26. case_timeline](../database/D26-case-timeline.md), [D30. payment](../database/D30-payment.md)
- Tests: [T2. Test Runners](../tests/T2-test-runners.md), [T15. Payment Notices and Acknowledgement](../tests/T15-payment-noticed.md), [T16. Payment Enquiry Answered](../tests/T16-payment-enquiry-answered.md)
