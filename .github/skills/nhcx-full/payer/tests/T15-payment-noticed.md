# T15. Payment Notices and Acknowledgement

#### T15D. DESCRIPTION

Money moving is told twice: when finance raises a payment through [A14. Disburse](../apis/A14-disburse.md), [A6. Payment Notice](../apis/A6-payment-notice.md) sends a PaymentNotice with the reconciliation (workflow 30) on a fresh thread; when the UTR is recorded, the same notice goes again with the UTR. The hospital's acknowledgement Task arrives on [C11. Payment Acknowledgement](../callbacks/C11-payment-acknowledgement.md) and the payment is marked acknowledged. A one-step disbursement with a UTR sends one notice.

#### T15S. SETUP

One member under the [T1. Test Configuration](T1-test-configuration.md) prefix enrolled on the default product. A claim approved as in [T12. Claim Received and Approved](T12-claim-approved.md), leaving the case at stage `payment` with money owed. A desk account that may release payments. Payment notices switched on in the application's settings ([A6. Payment Notice](../apis/A6-payment-notice.md)).

#### T15G. GUI

1. Hospital side, through the provider driver ([T2. Test Runners](T2-test-runners.md)): send, have approved, file and have approved a claim (as [T12. Claim Received and Approved](T12-claim-approved.md)).
2. [S10. Payments](../screens/S10-payments.md): the case is listed as awaiting payment with the approved total owed; raise a payment for the full amount by NEFT with the hospital's bank details, without a UTR.
3. [S10. Payments](../screens/S10-payments.md): the payment is `initiated`; its notice transaction is recorded.
4. Hospital side: the payments tab shows the notice, initiated, for the net amount.
5. [S10. Payments](../screens/S10-payments.md): complete the payment with a UTR.
6. [S10. Payments](../screens/S10-payments.md): the payment is `completed`; the case is settled; then, once the hospital has acknowledged, the payment shows acknowledged.
7. Hospital side: the payments tab shows the notice completed with the UTR and acknowledged.

#### T15L. CLI

1. Seed, send, approve, file and approve through [A18. Provider Driver](../apis/A18-provider-driver.md) and [A13. Adjudicate](../apis/A13-adjudicate.md).
2. Raise the payment without a UTR through [A14. Disburse](../apis/A14-disburse.md); read the payment and the exchange log through [A15. Case Exchange Log](../apis/A15-case-exchange.md).
3. Complete it with a UTR through [A14. Disburse](../apis/A14-disburse.md); read again.
4. Wait for the acknowledgement on the payment, polling the notice's thread through [A11. Transaction Related](../apis/A11-txn-related.md) after `NHCX_PAYER_TEST_POLL_AFTER_SECONDS`.
5. On a second approved case, disburse in one call with a UTR through [A14. Disburse](../apis/A14-disburse.md); read the exchange log.

#### T15X. EXPECT

- Raising the payment sends one notice on `v1/paymentnotice/request` to the hospital, workflow 30, `x-hcx-status` `request.initiated`, on a correlation id the gateway minted; its amount is the net payable; the bundle is PaymentNotice, PaymentReconciliation and the parties ([F13. PaymentNotice](../fhir/F13-paymentnotice.md), [F14. PaymentReconciliation](../fhir/F14-paymentreconciliation.md)); [D30. payment](../database/D30-payment.md) records the notice transaction.
- Completing with the UTR sends the same notice (same PaymentNotice `fullUrl`) again, now carrying the UTR as its identifier; the payment is `completed` and the case `settled` when nothing approved is left.
- The hospital's acknowledgement (a Task with output `paymentack`) is filed on the right case; the payment's `nhcx_acknowledged_at` is set; the delivery is answered `acknowledged`.
- The one-step disbursement sends one notice with the UTR.
- With notices switched off, completing a payment records no notice transaction and nothing goes out.
