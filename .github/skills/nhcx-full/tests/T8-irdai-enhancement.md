# T8. IRDAI Enhancement

#### T8D. DESCRIPTION

An enhancement is a pre-authorisation send ([A4. Pre-auth Submit](../apis/A4-preauth-submit.md), kind `enhancement`) on an approved case, asking to raise the approved amount. Each is its own leg, answered by [C5. Pre-auth Reply](../callbacks/C5-preauth-on-submit.md). The claim's approved total is the approved pre-authorisation plus every approved enhancement.

#### T8S. SETUP

A claim with an approved pre-authorisation, as [T5. IRDAI Pre-authorisation Approved](T5-irdai-preauth-approved.md) leaves it.

#### T8G. GUI

1. [S9. Pre-authorisation](../screens/S9-preauthorisation.md): raise an enhancement with an added line and amount; send it.
2. Payer side, through the payer driver: approve.
3. [S9. Pre-authorisation](../screens/S9-preauthorisation.md): raise a second enhancement; payer side: reject with a remark.
4. Read the approved total on [S9. Pre-authorisation](../screens/S9-preauthorisation.md).

#### T8L. CLI

1. [A4. Pre-auth Submit](../apis/A4-preauth-submit.md) with kind `enhancement` and the added line; [A14. Adjudicator User Role](../apis/A14-adjudicator-user-role.md); [A15. Adjudicator Process Case](../apis/A15-adjudicator-process-case.md) `approve`; wait for [C5. Pre-auth Reply](../callbacks/C5-preauth-on-submit.md).
2. [A4. Pre-auth Submit](../apis/A4-preauth-submit.md) enhancement again; [A14. Adjudicator User Role](../apis/A14-adjudicator-user-role.md); [A15. Adjudicator Process Case](../apis/A15-adjudicator-process-case.md) `reject` with a remark; wait for [C5. Pre-auth Reply](../callbacks/C5-preauth-on-submit.md).

#### T8X. EXPECT

- Each enhancement goes out under the enhancement workflow id ([PAYERS.md](../references/PAYERS.md#workflow-ids)) on a new correlation id.
- The approved enhancement raises the approved total by its approved amount; the rejected one leaves the total unchanged and shows its reason.
- The original approval is not changed by either answer.
