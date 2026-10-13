# T6. Pre-auth Received and Approved

#### T6D. DESCRIPTION

The happy path of the pre-authorisation leg: the Claim arrives on [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md), a case opens for the enrolment it names, [A3. Pre-auth Answer](../apis/A3-preauth-answer.md) acknowledges it at once (queued, workflow 20), an adjudicator decides on [S3. Case Desk](../screens/S3-case-desk.md) through [A13. Adjudicate](../apis/A13-adjudicate.md), and [A3. Pre-auth Answer](../apis/A3-preauth-answer.md) sends the verdict (workflow 21) on the submission's thread.

#### T6S. SETUP

One member under the [T1. Test Configuration](T1-test-configuration.md) prefix enrolled on the default product with the cover period open and the wallet untouched. A desk account that may decide cases.

#### T6G. GUI

1. Hospital side, through the provider driver ([T2. Test Runners](T2-test-runners.md)): open a case for the member, run the eligibility check, fetch the plan, add one covered line, attach a document, and send the pre-authorisation.
2. [S2. Cases](../screens/S2-cases.md): the case appears at stage `preauth`, pending, under the hospital's claim number; open it.
3. [S3. Case Desk](../screens/S3-case-desk.md): the dossier shows the patient as this payer's member, the hospital, the admission, the diagnosis, the doctor, the line and the document; the exchange log shows the pre-auth in and the acknowledgement out.
4. [S3. Case Desk](../screens/S3-case-desk.md): approve the line in full with a remark, then approve the case with remarks.
5. [S3. Case Desk](../screens/S3-case-desk.md): the exchange log shows the verdict out; the case stands at stage `claim`.
6. Hospital side: the pre-authorisation tab shows approved with the approved amount.

#### T6L. CLI

1. Seed the member and enrolment.
2. Through [A18. Provider Driver](../apis/A18-provider-driver.md), send the pre-authorisation for one covered line.
3. Wait for the case through [A15. Case Exchange Log](../apis/A15-case-exchange.md); read its lines and exchange log.
4. Approve the line, then the case, through [A13. Adjudicate](../apis/A13-adjudicate.md).
5. Read the exchange log again through [A15. Case Exchange Log](../apis/A15-case-exchange.md); read the hospital's side through [A18. Provider Driver](../apis/A18-provider-driver.md).

#### T6X. EXPECT

- The delivery is answered `filed` with the case id and claim number; [D19. case](../database/D19-case.md) holds the correlation id, sender, recipient and the hospital's claim number; the patient on the case is the seeded member, not the name the hospital typed.
- The acknowledgement goes out on `v1/preauth/on_submit` on the submission's correlation id, workflow 20, `x-hcx-status` `response.partial`, `outcome` `queued` ([F9. ClaimResponse](../fhir/F9-claimresponse.md)); nothing else goes out until a person decides.
- The line is `approved` with `approved_amount` equal to the claimed amount; the case's adjudication is `approved` with the remarks, the adjudicator and the time.
- The verdict goes out once on the same thread, workflow 21, `response.complete`, `outcome` `complete`, claim-level status `approved`, one item adjudication per line, the hospital's claim number echoed ([F9. ClaimResponse](../fhir/F9-claimresponse.md)); a second decision sends nothing.
- The exchange log reads in `preauth`, out `claimresponse` (acknowledged), out `claimresponse` (verdict).
- The hospital's side shows the pre-authorisation approved with the amount and this payer's case number as the pre-auth reference.
