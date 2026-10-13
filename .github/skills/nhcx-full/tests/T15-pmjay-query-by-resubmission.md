# T15. PMJAY Query Answered by Resubmission

#### T15D. DESCRIPTION

PMJAY asks in `resubmit` mode ([PAYERS.md](../references/PAYERS.md)): the query is a ClaimResponse on the case's own thread ([C5. Pre-auth Reply](../callbacks/C5-preauth-on-submit.md)), and it is answered by sending the pre-authorisation again ([A4. Pre-auth Submit](../apis/A4-preauth-submit.md)) under the pre-auth query-response workflow id, with `x-hcx-status` `response.complete` (CORE confusions). A CommunicationRequest from PMJAY ([C9. Payer Communication](../callbacks/C9-communication-request.md)) is a notification: it is acknowledged, never answered.

#### T15S. SETUP

A PMJAY pre-authorisation sent and acknowledged, as step 1 of [T14. PMJAY Pre-authorisation Through the Payer Service](T14-pmjay-preauth-adjudicated.md) leaves it, **quoting the package named by `NHCX_TEST_PMJAY_MANUAL_PACKAGE`** ([T1. Test Configuration](T1-test-configuration.md)): the sandbox auto-approves `SB043F` within seconds, before any desk can query it, so this test is not drivable on it. With no manual package configured the test ends `blocked`, cause `sandbox`, with that reason [SANDBOX](../references/PAYERS.md#markers).

#### T15G. GUI

1. Payer side: run the `query` cycle with a remark.
2. [S9. Pre-authorisation](../screens/S9-preauthorisation.md): wait for the query; read it; answer it by editing and sending the pre-authorisation again.
3. Payer side: run the `approve` cycle; wait on [S9. Pre-authorisation](../screens/S9-preauthorisation.md).

#### T15L. CLI

1. [A14. Adjudicator User Role](../apis/A14-adjudicator-user-role.md); [A15. Adjudicator Process Case](../apis/A15-adjudicator-process-case.md) cycle `query` with a remark; wait for [C5. Pre-auth Reply](../callbacks/C5-preauth-on-submit.md) (queried).
2. [A4. Pre-auth Submit](../apis/A4-preauth-submit.md) as the query answer on the same thread.
3. [A14. Adjudicator User Role](../apis/A14-adjudicator-user-role.md); [A15. Adjudicator Process Case](../apis/A15-adjudicator-process-case.md) cycle `approve`; wait for [C5. Pre-auth Reply](../callbacks/C5-preauth-on-submit.md).

#### T15X. EXPECT

- The query cycle stops `decided` at the role holding the case; the leg is `queried` with PMJAY's remark shown on [S9. Pre-authorisation](../screens/S9-preauthorisation.md).
- The answer travels on the leg's own correlation id, under the query-response workflow id, with `response.complete`.
- The leg ends `approved`; no Communication reply is sent to PMJAY at any point.
