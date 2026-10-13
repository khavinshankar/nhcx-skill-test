# T12. Claim Received and Approved

#### T12D. DESCRIPTION

After discharge the hospital's Claim with use `claim` arrives on [C5. Claim Submit](../callbacks/C5-claim-submit.md) and is filed on the pre-authorised case: the final bill replaces the estimate, the discharge is read, the documents are filed, [A4. Claim Answer](../apis/A4-claim-answer.md) acknowledges (workflow 25). The desk decides through [A13. Adjudicate](../apis/A13-adjudicate.md); approving the claim debits the wallet and [A4. Claim Answer](../apis/A4-claim-answer.md) sends the verdict (workflow 26) on the claim's own thread.

#### T12S. SETUP

One member under the [T1. Test Configuration](T1-test-configuration.md) prefix enrolled on the default product; note the wallet balance. A pre-authorisation approved as in [T6. Pre-auth Received and Approved](T6-preauth-approved.md). A desk account that may decide cases.

#### T12G. GUI

1. Hospital side, through the provider driver ([T2. Test Runners](T2-test-runners.md)): on the approved pre-authorisation, record a normal discharge, attach the discharge summary and the final bill, and file the claim with two lines (surgery, implant).
2. [S2. Cases](../screens/S2-cases.md): the case is at stage `claim`, pending; open it.
3. [S3. Case Desk](../screens/S3-case-desk.md): the lines are the final bill's; the discharge date and type are on the admission; the discharge summary and bill are under documents; the exchange log shows the claim in and the acknowledgement out on a new correlation id.
4. [S3. Case Desk](../screens/S3-case-desk.md): approve the surgery line in full, partially approve the implant line with a cut and a remark, then approve the claim.
5. [S3. Case Desk](../screens/S3-case-desk.md): the case is at stage `payment`; the exchange log shows the verdict out.
6. [S5. Subscriptions](../screens/S5-subscriptions.md): the enrolment's wallet is down by the approved total, with a ledger entry naming the case.
7. Hospital side: the claim tab shows approved with the amounts per item.

#### T12L. CLI

1. Seed the member and enrolment; through [A18. Provider Driver](../apis/A18-provider-driver.md), send and approve a pre-authorisation (as [T6. Pre-auth Received and Approved](T6-preauth-approved.md)).
2. Through [A18. Provider Driver](../apis/A18-provider-driver.md), record the discharge and file the claim with two lines and two documents.
3. Wait for the case through [A15. Case Exchange Log](../apis/A15-case-exchange.md): stage, lines, admission, documents, exchange log.
4. Decide the lines and approve the claim through [A13. Adjudicate](../apis/A13-adjudicate.md).
5. Read the wallet through the desk's services and the exchange log through [A15. Case Exchange Log](../apis/A15-case-exchange.md); read the hospital's side through [A18. Provider Driver](../apis/A18-provider-driver.md).

#### T12X. EXPECT

- The delivery is answered `filed` on the pre-auth's case, stage `claim`; [D19. case](../database/D19-case.md) holds the claim's correlation id apart from the pre-auth's, and the pre-auth's answer stays recorded.
- The acknowledgement goes out on `v1/claim/on_submit` on the claim's correlation id, workflow 25, `response.partial`.
- `total_claimed` is the final bill, not the estimate; the discharge date and type are on the case; the documents are filed under this payer's codes.
- The verdict goes out on `v1/claim/on_submit` on the claim's correlation id, to the submitter, workflow 26, `response.complete`, `use` `claim`, `outcome` `partial` (a cut), claim-level status `approved`, the hospital's claim number echoed ([F9. ClaimResponse](../fhir/F9-claimresponse.md)); the case is at stage `payment`.
- The wallet balance equals the balance before minus the approved total, with one [D8. wallet_entry](../database/D8-wallet-entry.md) debit entry.
- The exchange log reads in `preauth`, out, out, in `claim`, out, out.
- The hospital's side shows the claim approved with the approved total.
