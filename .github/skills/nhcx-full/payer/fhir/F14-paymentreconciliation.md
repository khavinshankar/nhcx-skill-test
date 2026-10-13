# F14. PaymentReconciliation

#### F14R. RESOURCE
`PaymentReconciliation`, no profile, the `SUBSETTED` tag (F1), at `<payer base>/v1/paymentnotice/request/paymentreconciliation/<claim number>`. Direction: sent beside the PaymentNotice (F13) on `v1/paymentnotice/request` by [A6. Payment Notice](../apis/A6-payment-notice.md) and on `v1/paymentnotice/on_request` by [A7. Payment Enquiry Answer](../apis/A7-payment-enquiry-answer.md). On its own, with an `OperationOutcome` and the payer Organization, it is the answer to an enquiry about a claim this payer does not hold.

#### F14D. DESCRIPTION
What the money was made of. A hospital reads the amount, the date, the UTR and the `detail[]` lines into its payment record and counts a notice as paid when the status is `paid` or `cleared` and a UTR is present [PAYER](../references/PAYERS.md#markers); the reconciliation is where those live.

**Lines.** For every completed payment on the case ([D30. payment](../database/D30-payment.md), `status` `completed`; the one payment when the notice is about one), in order of initiation: a `TDS` line for the tax withheld when it is more than zero, then a `Payment` line for the net paid, each dated the day the payment completed. Each line has `id` `<payment id>/TDS` or `<payment id>/Payment`, an identifier typed `PLAC` "Placer Identifier" whose system the reference spells with a doubled scheme, `https://https://nrces.in/ndhm/fhir/r4/ValueSet-ndhm-identifier-type-code.html` [REF](../references/PAYERS.md#markers); write the single-scheme URL, `https://nrces.in/ndhm/fhir/r4/ValueSet-ndhm-identifier-type-code.html`, unless the knowledge source's example says otherwise, since no hospital reader matches on it, and `type` the kind on `http://hl7.org/fhir/ValueSet/payment-type`.

**Totals.** `paymentAmount` the sum of net paid, `paymentDate` the day of the last completed payment (today when nothing completed), `paymentIdentifier` the last completed payment's UTR typed `UTR` "Unique Transaction Reference" on `https://nrces.in/ndhm/fhir/r4/CodeSystem/ndhm-identifier-type-code`, `system` `<payer base>/utr`. A notice raised before the transfer completes therefore carries no UTR and a zero amount; the notice sent again on completion carries both, and the hospital overwrites its earlier record by the notice ([A6. Payment Notice](../apis/A6-payment-notice.md)).

**Nothing paid** is still an answer: a zero amount, no detail lines, and the disposition saying where the claim stands (the F13 table). The render notes it.

**The error answer** ([A7. Payment Enquiry Answer](../apis/A7-payment-enquiry-answer.md)). A hospital's enquiry naming a claim this payer does not hold, or one it holds but cannot answer, gets a bundle of three entries: this reconciliation with `outcome` `error`, `disposition` the reason, a zero amount and today's date; an `OperationOutcome` at `<base>/operationoutcome/<claim number>` with one issue, `severity` `error`, `code` `not-found`, `details.text` the reason, `diagnostics` `claim <number>`; and the payer Organization with its name. Both resources say the same thing so a reader that looks for either finds it. The scheme never answers a notice, so there is no capture to hold this to [REF](../references/PAYERS.md#markers).

`outcome` and `disposition` are written on the error answer only; a normal reconciliation carries the disposition sentence and no outcome.

#### F14F. FIELDS
| Element written | From | Notes |
|---|---|---|
| `identifier[0]` | type `CLN`, `system` `<payer base>/v1/claim`, `value` the hospital's claim number (`D19.nhcx_claim_submission_ref`, else `D19.nhcx_claim_ref`) | |
| `status` | `active` | |
| `created` | now, IST | |
| `outcome` | `error` | error answer only |
| `disposition` | the F13 sentence, or the refusal reason | |
| `paymentDate` | `D30.completed_at` (date part) of the last completed payment, else today | |
| `paymentAmount` | sum of `D30.net_payable`, `INR` | zero when nothing completed |
| `paymentIdentifier` | type `UTR`, `system` `<payer base>/utr`, `value` `D30.utr_no` of the last completed payment | left out until one completes |
| `detail[].id` | `<D30.id>/TDS`, `<D30.id>/Payment` | |
| `detail[].identifier` | type `PLAC`, `system` `<payer base>/v1/claim`, `value` the same id | |
| `detail[].type.coding[0]` | `TDS` or `Payment` on `http://hl7.org/fhir/ValueSet/payment-type` | code and display the same |
| `detail[].date` | `D30.completed_at` (date part) | |
| `detail[].amount.value` | `D30.tds_amount`, `D30.net_payable` | the TDS line only when more than zero |
| OperationOutcome `issue[0]` | `error`, `not-found`, `details.text` the reason, `diagnostics` `claim <number>` | error answer only |

#### F14U. USED BY
- APIs: [A6. Payment Notice](../apis/A6-payment-notice.md), [A7. Payment Enquiry Answer](../apis/A7-payment-enquiry-answer.md), [A15. Case Exchange Log](../apis/A15-case-exchange.md)
- Callbacks: [C10. Payment Enquiry](../callbacks/C10-payment-enquiry.md)
- FHIR: [F1. Bundle](F1-bundle.md), [F13. PaymentNotice](F13-paymentnotice.md), [F15. Patient](F15-patient.md), [F18. Coverage](F18-coverage.md)
- Database: [D30. payment](../database/D30-payment.md)
- Tests: [T15. Payment Notices and Acknowledgement](../tests/T15-payment-noticed.md), [T16. Payment Enquiry Answered](../tests/T16-payment-enquiry-answered.md)
