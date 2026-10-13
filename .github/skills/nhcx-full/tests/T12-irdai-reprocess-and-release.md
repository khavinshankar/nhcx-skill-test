# T12. IRDAI Reprocess and Balance Release

#### T12D. DESCRIPTION

Both go out as a Task ([A6. Task Submit (cancel, status, reprocess, release)](../apis/A6-task-submit.md)) under the reprocess workflow id, with a reason code ([PAYERS.md](../references/PAYERS.md)): `claimrejected` or `rejectiondisputed` for a rejected claim, `partialpayment` for a partly paid one. The payer acknowledges on `v1/task/on_submit` ([C8. Enquiry Reply](../callbacks/C8-enquiry-on-submit.md)) and decides again on the case.

#### T12S. SETUP

A claim rejected at the claim stage ([T10. IRDAI Claim Approved, Part-approved and Rejected](T10-irdai-claim.md)) and a claim paid in part ([T11. IRDAI Payment Notice and Acknowledgement](T11-irdai-payment.md), first instalment only).

#### T12G. GUI

1. [S11. Claim Submission](../screens/S11-claim-submission.md) on the rejected claim: ask for a reprocess with reason `claimrejected` and a remark; wait.
2. Payer side: approve the case again; wait on [S11. Claim Submission](../screens/S11-claim-submission.md).
3. [S11. Claim Submission](../screens/S11-claim-submission.md) on the partly paid claim: ask for the balance with reason `partialpayment`; wait.

#### T12L. CLI

1. [A6. Task Submit (cancel, status, reprocess, release)](../apis/A6-task-submit.md) reprocess on the rejected claim; wait for [C8. Enquiry Reply](../callbacks/C8-enquiry-on-submit.md); [A14. Adjudicator User Role](../apis/A14-adjudicator-user-role.md); [A15. Adjudicator Process Case](../apis/A15-adjudicator-process-case.md) `approve`; wait for [C6. Claim Reply](../callbacks/C6-claim-on-submit.md).
2. [A6. Task Submit (cancel, status, reprocess, release)](../apis/A6-task-submit.md) release on the partly paid claim; wait for [C8. Enquiry Reply](../callbacks/C8-enquiry-on-submit.md).

#### T12X. EXPECT

- Each Task goes out on the claim's thread and is acknowledged.
- After the payer approves again, the rejected claim shows `approved` and keeps the earlier rejection in its history.
- The release request is shown against the partly paid claim with its reason; a later payment for the balance is recorded as a further instalment ([T11. IRDAI Payment Notice and Acknowledgement](T11-irdai-payment.md)).
