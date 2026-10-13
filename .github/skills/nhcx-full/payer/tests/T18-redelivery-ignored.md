# T18. Redelivery and Duplicates

#### T18D. DESCRIPTION

NHCX redelivers a message it did not see accepted, and a hospital may send the same bundle twice. [C1. Callback Door](../callbacks/C1-callback-door.md) takes a message in once by its `x-hcx-api_call_id` ([D28. nhcx_delivery](../database/D28-nhcx-delivery.md)), a pre-authorisation on a correlation id already filed opens no second case ([C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md)), a claim delivered again files its documents once ([C5. Claim Submit](../callbacks/C5-claim-submit.md)), and an answer is not sent twice.

#### T18S. SETUP

One member under the [T1. Test Configuration](T1-test-configuration.md) prefix enrolled on the default product. The gateway's redelivery reachable in the test: the provider driver can re-deliver the last message it sent, or the runner replays the archived envelope through [G8. Receive](../gateway/G8-receive.md) with the same headers [SANDBOX](../references/PAYERS.md#markers).

#### T18G. GUI

1. Hospital side, through the provider driver ([T2. Test Runners](T2-test-runners.md)): send a pre-authorisation with two documents.
2. [S2. Cases](../screens/S2-cases.md): one case, pending; open it; [S3. Case Desk](../screens/S3-case-desk.md) shows two documents.
3. Replay the same delivery.
4. [S2. Cases](../screens/S2-cases.md): still one case; [S3. Case Desk](../screens/S3-case-desk.md) still shows two documents; the exchange log shows one pre-auth in and one acknowledgement out.
5. [S3. Case Desk](../screens/S3-case-desk.md): approve the case; replay the pre-authorisation once more; nothing changes and no further verdict goes out.
6. Hospital side: file the claim with two documents; replay it; [S3. Case Desk](../screens/S3-case-desk.md) shows the claim's two documents once.

#### T18L. CLI

1. Seed the member and enrolment; through [A18. Provider Driver](../apis/A18-provider-driver.md), send the pre-authorisation with two documents; wait for the case through [A15. Case Exchange Log](../apis/A15-case-exchange.md).
2. Replay the delivery; read the case count, the documents and the exchange log through [A15. Case Exchange Log](../apis/A15-case-exchange.md).
3. Approve the case through [A13. Adjudicate](../apis/A13-adjudicate.md); replay again; read the exchange log.
4. Through [A18. Provider Driver](../apis/A18-provider-driver.md), file the claim with two documents; replay it; read the documents.

#### T18X. EXPECT

- The first delivery is answered `filed`; every replay of it is answered `duplicate` with the same case id and claim number.
- The case count does not grow; the documents stay at two; [D28. nhcx_delivery](../database/D28-nhcx-delivery.md) holds one row for the api call id.
- The acknowledgement went out once; after the approval the verdict went out once; a replay sends nothing.
- The replayed claim is answered `duplicate` and its documents are filed once.
- A replay that arrives with a new api call id but the same correlation id is still one case: the correlation id is unique on [D19. case](../database/D19-case.md).
