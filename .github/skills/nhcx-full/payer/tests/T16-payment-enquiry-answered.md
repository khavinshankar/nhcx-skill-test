# T16. Payment Enquiry Answered

#### T16D. DESCRIPTION

A hospital's own PaymentNotice, asking where the money is, arrives on [C10. Payment Enquiry](../callbacks/C10-payment-enquiry.md) naming the claim number; [A7. Payment Enquiry Answer](../apis/A7-payment-enquiry-answer.md) answers at once with the case's payments reconciled ([F14. PaymentReconciliation](../fhir/F14-paymentreconciliation.md)), or with an error outcome when the claim is unknown.

#### T16S. SETUP

One member under the [T1. Test Configuration](T1-test-configuration.md) prefix enrolled on the default product. A claim approved and paid in full with a UTR (as [T15. Payment Notices and Acknowledgement](T15-payment-noticed.md), one-step disbursement, with notices switched off so the only exchange about money is the enquiry).

#### T16G. GUI

1. Hospital side, through the provider driver ([T2. Test Runners](T2-test-runners.md)): send, have approved, file and have approved a claim; [S10. Payments](../screens/S10-payments.md): disburse in one step with a UTR.
2. Hospital side: on the payments tab, ask where the money is.
3. [S3. Case Desk](../screens/S3-case-desk.md): the exchange log shows the enquiry in and the reconciliation out.
4. Hospital side: the payments tab shows the reconciliation with the UTR, the net paid and the TDS.
5. Hospital side: ask about a claim number this payer never had.

#### T16L. CLI

1. Seed, send, approve, file, approve through [A18. Provider Driver](../apis/A18-provider-driver.md) and [A13. Adjudicate](../apis/A13-adjudicate.md); disburse through [A14. Disburse](../apis/A14-disburse.md).
2. Through [A18. Provider Driver](../apis/A18-provider-driver.md), send the payment enquiry for the case's claim number; read the answer through [A15. Case Exchange Log](../apis/A15-case-exchange.md) or [A12. Transaction FHIR](../apis/A12-txn-fhir.md).
3. Through [A18. Provider Driver](../apis/A18-provider-driver.md), send an enquiry under an unknown claim number; read the answer through [A12. Transaction FHIR](../apis/A12-txn-fhir.md).

#### T16X. EXPECT

- The delivery is answered `answered` with the case id; one answer goes out on `v1/paymentnotice/on_request` on the enquiry's correlation id, `response.complete`.
- The PaymentReconciliation carries the UTR as an identifier, the net paid as its amount, the TDS withheld, and a payment status of `cleared` when settled in full ([F14. PaymentReconciliation](../fhir/F14-paymentreconciliation.md)).
- The unknown claim is answered too, `unknown_claim`, with an OperationOutcome and `outcome` `error`, never a refusal.
- The hospital's side shows the payment reconciled with the UTR.
