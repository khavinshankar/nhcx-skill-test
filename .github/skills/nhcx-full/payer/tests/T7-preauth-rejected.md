# T7. Pre-auth Rejected

#### T7D. DESCRIPTION

A pre-authorisation filed by [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md) is rejected on the desk through [A13. Adjudicate](../apis/A13-adjudicate.md); [A3. Pre-auth Answer](../apis/A3-preauth-answer.md) sends the rejection (workflow 23) as `outcome` `error` with the reason in the process note, and the case closes at stage `rejected`.

#### T7S. SETUP

One member under the [T1. Test Configuration](T1-test-configuration.md) prefix enrolled on the default product, with the cover period having started ten days ago (inside a waiting period the adjudicator will cite). A desk account that may decide cases.

#### T7G. GUI

1. Hospital side, through the provider driver ([T2. Test Runners](T2-test-runners.md)): open a case, check eligibility, fetch the plan, add a line and send the pre-authorisation.
2. [S2. Cases](../screens/S2-cases.md): open the pending case.
3. [S3. Case Desk](../screens/S3-case-desk.md): reject the line with a remark, then reject the case with the remark "Within the waiting period.".
4. [S3. Case Desk](../screens/S3-case-desk.md): the case stands at stage `rejected`; the exchange log shows the rejection out.
5. Hospital side: the pre-authorisation tab shows rejected with the payer's words.

#### T7L. CLI

1. Seed the member and enrolment.
2. Through [A18. Provider Driver](../apis/A18-provider-driver.md), send the pre-authorisation.
3. Wait for the case through [A15. Case Exchange Log](../apis/A15-case-exchange.md).
4. Reject the line and the case through [A13. Adjudicate](../apis/A13-adjudicate.md) with the remark.
5. Read the exchange log through [A15. Case Exchange Log](../apis/A15-case-exchange.md); read the hospital's side through [A18. Provider Driver](../apis/A18-provider-driver.md).

#### T7X. EXPECT

- The acknowledgement (workflow 20, `response.partial`) went out at filing, as in [T6. Pre-auth Received and Approved](T6-preauth-approved.md).
- The line is `rejected` with `approved_amount` 0; the case's adjudication is `rejected` with the remark; the stage is `rejected`.
- The verdict goes out on `v1/preauth/on_submit` on the submission's thread, workflow 23, `response.complete`, `outcome` `error`, claim-level status `rejected`, the remark as a process note ([F9. ClaimResponse](../fhir/F9-claimresponse.md)).
- The hospital's side shows the pre-authorisation rejected with the reason, and offers a fresh pre-authorisation rather than a resubmission.
- A further pre-authorisation under the same claim number from the same hospital opens a new case ([C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md)), because a rejected case is closed.
