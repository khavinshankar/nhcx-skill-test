# T9. Enhancement Received and Approved

#### T9D. DESCRIPTION

After an approval, the hospital sends the pre-authorisation again with lines added. [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md) recognises the comeback by the prior it names or by the claim number, files the added lines on the same case for a fresh decision, and keeps the new correlation id as the thread the verdict answers. [A3. Pre-auth Answer](../apis/A3-preauth-answer.md) then sends the enhancement's approval (workflow 22) on that thread.

#### T9S. SETUP

One member under the [T1. Test Configuration](T1-test-configuration.md) prefix enrolled on the default product with cover enough for both rounds. A desk account that may decide cases.

#### T9G. GUI

1. Hospital side, through the provider driver ([T2. Test Runners](T2-test-runners.md)): open a case, check eligibility, fetch the plan, add one line and send the pre-authorisation.
2. [S3. Case Desk](../screens/S3-case-desk.md): approve the line and the case (as [T6. Pre-auth Received and Approved](T6-preauth-approved.md)).
3. Hospital side: add an ICU line to the approved pre-authorisation and send the enhancement.
4. [S2. Cases](../screens/S2-cases.md): the same case, no second one, back at stage `preauth`, pending, with the enhancement count 1; open it.
5. [S3. Case Desk](../screens/S3-case-desk.md): the original line stays approved; the added line is pending in round 1; the exchange log shows the enhancement in on a new correlation id.
6. [S3. Case Desk](../screens/S3-case-desk.md): approve the added line and the case.
7. Hospital side: the pre-authorisation tab shows the enhancement approved.

#### T9L. CLI

1. Seed the member and enrolment; through [A18. Provider Driver](../apis/A18-provider-driver.md), send and have approved a one-line pre-authorisation (as [T6. Pre-auth Received and Approved](T6-preauth-approved.md)).
2. Through [A18. Provider Driver](../apis/A18-provider-driver.md), send the enhancement with one added line.
3. Wait for the case through [A15. Case Exchange Log](../apis/A15-case-exchange.md): the line count, the round, the exchange log.
4. Approve the added line and the case through [A13. Adjudicate](../apis/A13-adjudicate.md).
5. Read the exchange log through [A15. Case Exchange Log](../apis/A15-case-exchange.md); read the hospital's side through [A18. Provider Driver](../apis/A18-provider-driver.md).

#### T9X. EXPECT

- The delivery is answered `enhancement` with the same case id; the case count does not grow; nothing goes out until a person decides.
- The case is at stage `preauth`, adjudication `pending`, `enhancement_count` 1; the added line carries `enhancement_no` 1; [D19. case](../database/D19-case.md) holds the enhancement's correlation id as the pre-auth thread.
- The verdict goes out on `v1/preauth/on_submit` on the enhancement's correlation id, workflow 22, `response.complete`, with every line adjudicated ([F9. ClaimResponse](../fhir/F9-claimresponse.md)); the case advances to stage `claim`.
- The same enhancement delivered again is answered `duplicate` and files nothing.
- The hospital's side shows the enhancement approved, the pre-auth reference kept.
