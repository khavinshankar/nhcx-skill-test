# T18. PMJAY Payment Notice, Status Refusal and Cancel

#### T18D. DESCRIPTION

PMJAY pays with a payment notice ([C10. Payment Notice](../callbacks/C10-paymentnotice-request.md)), acknowledged by [A8. Payment Notice Acknowledgement](../apis/A8-paymentnotice-on-request.md) under PMJAY's payment acknowledgement workflow id. PMJAY does not answer a status enquiry: it refuses the Task ([A6. Task Submit (cancel, status, reprocess, release)](../apis/A6-task-submit.md) status) with PAYR-1018, or PAYR-1008 with a reason code, and the case's state is read from its desk instead ([PAYERS.md](../references/PAYERS.md)). A cancel ([A6. Task Submit (cancel, status, reprocess, release)](../apis/A6-task-submit.md) cancel) is answered by [C7. Cancel Reply](../callbacks/C7-cancel-on-submit.md).

#### T18S. SETUP

- A PMJAY claim approved at the claim stage ([T17. PMJAY Claim Through the Role Walk](T17-pmjay-claim-adjudicated.md)), for the payment.
- A PMJAY pre-authorisation sent and not yet decided, for the status enquiry and the cancel.

#### T18G. GUI

1. [S12. Payments](../screens/S12-payments.md) on the approved claim: wait for the payment notice.
2. [S9. Pre-authorisation](../screens/S9-preauthorisation.md) on the pending claim: ask for the status; wait; then cancel with a reason; wait.

#### T18L. CLI

1. Wait for [C10. Payment Notice](../callbacks/C10-paymentnotice-request.md) on the approved claim; check [A8. Payment Notice Acknowledgement](../apis/A8-paymentnotice-on-request.md) went out.
2. [A6. Task Submit (cancel, status, reprocess, release)](../apis/A6-task-submit.md) status on the pending leg; wait for the refusal.
3. [A14. Adjudicator User Role](../apis/A14-adjudicator-user-role.md) on the same leg, as the source of its state.
4. [A6. Task Submit (cancel, status, reprocess, release)](../apis/A6-task-submit.md) cancel on the pending leg; wait for [C7. Cancel Reply](../callbacks/C7-cancel-on-submit.md).

#### T18X. EXPECT

- The payment notice is matched by its claim number and acknowledged under PMJAY's acknowledgement workflow id; [S12. Payments](../screens/S12-payments.md) shows it. PMJAY's sandbox pays on its own schedule [SANDBOX](../references/PAYERS.md#markers): a notice that does not arrive within the wait is `blocked`, cause `sandbox`, not a failure.
- The status enquiry is refused as PAYERS.md says, and the refusal is recorded as the expected answer (a pass), with the role from [A14. Adjudicator User Role](../apis/A14-adjudicator-user-role.md) shown as the case's state.
- The cancel is answered and the pending leg ends `cancelled`.
