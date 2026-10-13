# T5. IRDAI Pre-authorisation Approved

#### T5D. DESCRIPTION

The happy path of the pre-authorisation leg: [A4. Pre-auth Submit](../apis/A4-preauth-submit.md) sends it, the payer decides on its own desk ([A14. Adjudicator User Role](../apis/A14-adjudicator-user-role.md) then [A15. Adjudicator Process Case](../apis/A15-adjudicator-process-case.md), IRDAI transport), and the decision comes back as [C5. Pre-auth Reply](../callbacks/C5-preauth-on-submit.md).

#### T5S. SETUP

A claim with a plan line and its ruling, as [T4. IRDAI Insurance Plan and Authorisation Requirements](T4-irdai-plan-and-auth-requirements.md) leaves it. The IRDAI desk needs no account: [A14. Adjudicator User Role](../apis/A14-adjudicator-user-role.md) signs in to it by token login.

#### T5G. GUI

1. [S4. Claim Creation Form](../screens/S4-claim-creation-form.md): fill the pre-authorisation (admission, treating doctor, diagnosis, the plan line, requested amount) and send it from [S9. Pre-authorisation](../screens/S9-preauthorisation.md).
2. Payer side, through the payer driver ([T2. Test Runners](T2-test-runners.md)): read the case on the IRDAI desk, then approve with remarks.
3. Wait on [S9. Pre-authorisation](../screens/S9-preauthorisation.md) for the payer's answer.

#### T5L. CLI

1. Build and send the pre-authorisation through [A4. Pre-auth Submit](../apis/A4-preauth-submit.md).
2. Read the case with [A14. Adjudicator User Role](../apis/A14-adjudicator-user-role.md) (IRDAI transport: sign in, find the case by the leg's claim number).
3. Take `approve` with [A15. Adjudicator Process Case](../apis/A15-adjudicator-process-case.md).
4. Wait for [C5. Pre-auth Reply](../callbacks/C5-preauth-on-submit.md).

#### T5X. EXPECT

- The send is accepted (NHCX 202) and the leg is stored under the ids the send returned (CORE confusions).
- The IRDAI desk finds the case by the leg's claim number, pending, with the claimed amount.
- [C5. Pre-auth Reply](../callbacks/C5-preauth-on-submit.md) arrives on the leg's correlation id; the leg is `approved` with the approved amount; [S9. Pre-authorisation](../screens/S9-preauthorisation.md) shows it approved with that amount.
- The decision is recorded against the claim ([A15. Adjudicator Process Case](../apis/A15-adjudicator-process-case.md)).
