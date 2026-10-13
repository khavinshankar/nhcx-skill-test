# T11. IRDAI Payment Notice and Acknowledgement

#### T11D. DESCRIPTION

A payment is started by the payer: the notice arrives on `v1/paymentnotice/request` ([C10. Payment Notice](../callbacks/C10-paymentnotice-request.md)) and the provider acknowledges it on `on_request` ([A8. Payment Notice Acknowledgement](../apis/A8-paymentnotice-on-request.md)), the opposite way round from every exchange the provider starts (CORE confusions). A claim may be paid in instalments, each its own notice.

#### T11S. SETUP

- A claim approved at the claim stage ([T10. IRDAI Claim Approved, Part-approved and Rejected](T10-irdai-claim.md)).
- The payer raises the payment on the IRDAI payer desk through its payment calls ([A15. Adjudicator Process Case](../apis/A15-adjudicator-process-case.md), "the payer's other acts"): raise with `utr_no` to pay in one step, or raise then complete. The payment is the payer's act, not a provider screen, so both runners do it through the payer driver.

#### T11G. GUI

1. Payer side: pay part of the approved amount, with a UTR; wait on [S12. Payments](../screens/S12-payments.md).
2. Payer side: pay the rest as a second instalment; wait on [S12. Payments](../screens/S12-payments.md).

#### T11L. CLI

1. Payer side: first instalment; wait for [C10. Payment Notice](../callbacks/C10-paymentnotice-request.md); check [A8. Payment Notice Acknowledgement](../apis/A8-paymentnotice-on-request.md) went out.
2. Payer side: second instalment; wait for [C10. Payment Notice](../callbacks/C10-paymentnotice-request.md); check [A8. Payment Notice Acknowledgement](../apis/A8-paymentnotice-on-request.md) again.

#### T11X. EXPECT

- Each notice is matched to the claim by the claim number it carries (CORE instruction 5) and acknowledged once ([A8. Payment Notice Acknowledgement](../apis/A8-paymentnotice-on-request.md) accepted, NHCX 202).
- [S12. Payments](../screens/S12-payments.md) shows each payment with its amount, TDS, net paid and UTR; the claim shows paid once the instalments cover the approved amount.
- The second instalment is recorded beside the first, never over it: two payments, two UTRs, and a total that adds them.
