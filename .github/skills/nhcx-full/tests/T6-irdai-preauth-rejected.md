# T6. IRDAI Pre-authorisation Rejected and Sent Again

#### T6D. DESCRIPTION

A rejection ends the leg `rejected`, not `queried`, and carries the payer's reason. The provider can then send a fresh pre-authorisation ([A4. Pre-auth Submit](../apis/A4-preauth-submit.md)), which the payer decides on its own.

#### T6S. SETUP

A claim ready for pre-authorisation, as [T4. IRDAI Insurance Plan and Authorisation Requirements](T4-irdai-plan-and-auth-requirements.md) leaves it.

#### T6G. GUI

1. [S9. Pre-authorisation](../screens/S9-preauthorisation.md): send the pre-authorisation.
2. Payer side, through the payer driver: reject with the remark "Not covered: e2e rejection".
3. Wait; read the reason on [S9. Pre-authorisation](../screens/S9-preauthorisation.md).
4. Send it again from [S9. Pre-authorisation](../screens/S9-preauthorisation.md); approve it through the payer driver; wait.

#### T6L. CLI

1. [A4. Pre-auth Submit](../apis/A4-preauth-submit.md); [A14. Adjudicator User Role](../apis/A14-adjudicator-user-role.md); [A15. Adjudicator Process Case](../apis/A15-adjudicator-process-case.md) `reject` with the remark; wait for [C5. Pre-auth Reply](../callbacks/C5-preauth-on-submit.md).
2. [A4. Pre-auth Submit](../apis/A4-preauth-submit.md) again for the same claim; [A14. Adjudicator User Role](../apis/A14-adjudicator-user-role.md); [A15. Adjudicator Process Case](../apis/A15-adjudicator-process-case.md) `approve`; wait for [C5. Pre-auth Reply](../callbacks/C5-preauth-on-submit.md).

#### T6X. EXPECT

- A reject with no remark is refused before any call, with the A15 message; with the remark it is accepted.
- The first leg ends `rejected` with the payer's reason shown on [S9. Pre-authorisation](../screens/S9-preauthorisation.md); it is not `queried`.
- The second send travels on a new correlation id and ends `approved`; the rejected leg stays in the claim's history.
