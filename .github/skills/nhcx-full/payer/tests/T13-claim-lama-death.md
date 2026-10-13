# T13. LAMA and Death Claims

#### T13D. DESCRIPTION

Two claims whose discharge is not a normal one: a patient who left against medical advice (LAMA or DAMA) and a patient who died. [C5. Claim Submit](../callbacks/C5-claim-submit.md) reads the discharge block ([F8. Claim](../fhir/F8-claim.md)) into the case and files the claim like any other; the desk sees how the stay ended before it decides. A claim with no pre-authorisation opens a case at the claim stage.

#### T13S. SETUP

Two members under the [T1. Test Configuration](T1-test-configuration.md) prefix enrolled on the default product. One pre-authorisation approved as in [T6. Pre-auth Received and Approved](T6-preauth-approved.md) for the first member. A desk account that may decide cases.

#### T13G. GUI

1. Hospital side, through the provider driver ([T2. Test Runners](T2-test-runners.md)): on the approved pre-authorisation, record the discharge as LAMA and file the claim.
2. [S2. Cases](../screens/S2-cases.md): open the case; [S3. Case Desk](../screens/S3-case-desk.md) shows the discharge type LAMA and the date on the admission.
3. Hospital side: for the second member, without a pre-authorisation, record a death with the date and time of death and file the claim directly.
4. [S2. Cases](../screens/S2-cases.md): a new case at stage `claim`, pending, for the second member; open it.
5. [S3. Case Desk](../screens/S3-case-desk.md): the discharge type is Deceased with the date; the dossier is the claim's.
6. [S3. Case Desk](../screens/S3-case-desk.md): approve the first claim; reject the second with a remark.
7. Hospital side: the first claim shows approved, the second rejected with the reason.

#### T13L. CLI

1. Seed the two members and enrolments; through [A18. Provider Driver](../apis/A18-provider-driver.md), send and approve a pre-authorisation for the first.
2. Through [A18. Provider Driver](../apis/A18-provider-driver.md), file the LAMA claim on it; wait for the case through [A15. Case Exchange Log](../apis/A15-case-exchange.md).
3. Through [A18. Provider Driver](../apis/A18-provider-driver.md), file the death claim for the second member with no pre-authorisation; wait for the new case.
4. Decide both through [A13. Adjudicate](../apis/A13-adjudicate.md); read the exchange logs through [A15. Case Exchange Log](../apis/A15-case-exchange.md).

#### T13X. EXPECT

- The LAMA claim is filed on the pre-authorised case with `discharge_type` `LAMA` and the discharge date ([D19. case](../database/D19-case.md)); the delivery is recorded so the sandbox counts it as a LAMA claim [SANDBOX](../references/PAYERS.md#markers).
- The death claim opens a case at stage `claim` for the member it names, with `discharge_type` `Deceased` and the date; the delivery is recorded as a death claim.
- Both are acknowledged on `v1/claim/on_submit` with workflow 25, `response.partial`.
- The approval goes out with workflow 26; the rejection with workflow 291, `outcome` `error`, the remark as a process note; the rejected case stands at stage `rejected` ([F9. ClaimResponse](../fhir/F9-claimresponse.md)).
- A claim filed against a pre-authorisation that is cancelled or rejected is refused, with the reason on the wire.
