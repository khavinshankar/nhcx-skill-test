# T8. Pre-auth Queried and Answered

#### T8D. DESCRIPTION

The query loop in `communication` mode [PAYER](../references/PAYERS.md#markers): an adjudicator queries a line and the case through [A13. Adjudicate](../apis/A13-adjudicate.md); no verdict goes out, and [A5. Query Request](../apis/A5-query-request.md) sends a CommunicationRequest (workflow 24) on a thread of its own; the hospital's Communication arrives on [C9. Communication](../callbacks/C9-communication.md) and is filed with its document; the case is pending again and is approved as in [T6. Pre-auth Received and Approved](T6-preauth-approved.md).

#### T8S. SETUP

One member under the [T1. Test Configuration](T1-test-configuration.md) prefix enrolled on the default product. A desk account that may decide cases.

#### T8G. GUI

1. Hospital side, through the provider driver ([T2. Test Runners](T2-test-runners.md)): open a case, check eligibility, fetch the plan, add an implant line and a surgery line, and send the pre-authorisation.
2. [S2. Cases](../screens/S2-cases.md): open the pending case.
3. [S3. Case Desk](../screens/S3-case-desk.md): mark the implant line queried with "Operative notes are missing.", then query the case with the same remark.
4. [S3. Case Desk](../screens/S3-case-desk.md): the case shows a query open; the exchange log shows the acknowledgement and the CommunicationRequest out, and nothing on the pre-auth thread.
5. Hospital side: the communication tab shows the query; reply with text and attach a PDF filed as operation theatre notes (`OTR`).
6. [S3. Case Desk](../screens/S3-case-desk.md): the reply is on the timeline, the document is under documents with code `OTR`, the case is pending again with the query closed.
7. [S3. Case Desk](../screens/S3-case-desk.md): approve both lines and the case.
8. Hospital side: the pre-authorisation tab shows approved.

#### T8L. CLI

1. Seed the member and enrolment; through [A18. Provider Driver](../apis/A18-provider-driver.md), send the pre-authorisation with two lines.
2. Wait for the case through [A15. Case Exchange Log](../apis/A15-case-exchange.md); query the implant line and the case through [A13. Adjudicate](../apis/A13-adjudicate.md).
3. Read the exchange log through [A15. Case Exchange Log](../apis/A15-case-exchange.md): the query's correlation id and transaction.
4. Through [A18. Provider Driver](../apis/A18-provider-driver.md), reply to the query with text and one document.
5. Wait for the reply on the case through [A15. Case Exchange Log](../apis/A15-case-exchange.md), polling the query thread through [A11. Transaction Related](../apis/A11-txn-related.md) after `NHCX_PAYER_TEST_POLL_AFTER_SECONDS`.
6. Approve the lines and the case through [A13. Adjudicate](../apis/A13-adjudicate.md); read the hospital's side through [A18. Provider Driver](../apis/A18-provider-driver.md).

#### T8X. EXPECT

- Querying sends no ClaimResponse: after the acknowledgement, the only message out is the CommunicationRequest on `v1/communication/request`, workflow 24, `x-hcx-status` `request.initiated`, on a fresh correlation id the gateway minted ([F11. CommunicationRequest](../fhir/F11-communicationrequest.md)); the case keeps that id as its query thread.
- The request carries a Task coded `poll` with reason `additionalinfo` and one payload with the remark [PAYER](../references/PAYERS.md#markers).
- The reply is filed on the case: the text on the timeline, one document under code `OTR`, the queried line back to `pending`, the adjudication `pending`, the query thread cleared ([D19. case](../database/D19-case.md)).
- The approval goes out on the submission's thread, workflow 21, as in [T6. Pre-auth Received and Approved](T6-preauth-approved.md).
- The hospital's side shows the query, the reply sent, then the approval.
