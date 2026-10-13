# T10. IRDAI Claim Approved, Part-approved and Rejected

#### T10D. DESCRIPTION

After discharge the claim leg goes out ([A5. Claim Submit](../apis/A5-claim-submit.md)) against the approved pre-authorisation and is decided by the payer, answered by [C6. Claim Reply](../callbacks/C6-claim-on-submit.md). A part-approval is decided per line: the payer approves less than was claimed on one or more lines.

#### T10S. SETUP

Three claims, each with an approved pre-authorisation ([T5. IRDAI Pre-authorisation Approved](T5-irdai-preauth-approved.md)) and a discharge recorded.

#### T10G. GUI

1. [S11. Claim Submission](../screens/S11-claim-submission.md) on the first claim: enter the bill lines matching the approval; send; payer side: approve.
2. [S11. Claim Submission](../screens/S11-claim-submission.md) on the second: send two lines; payer side: decide the lines first ([A15. Adjudicator Process Case](../apis/A15-adjudicator-process-case.md), the desk's line decision): the first `approved` in full, the second `partially_approved` at less than claimed; then `approve` the case.
3. [S11. Claim Submission](../screens/S11-claim-submission.md) on the third: send; payer side: reject with a remark.
4. Read each verdict on [S11. Claim Submission](../screens/S11-claim-submission.md).

#### T10L. CLI

1. For each claim: [A5. Claim Submit](../apis/A5-claim-submit.md); [A14. Adjudicator User Role](../apis/A14-adjudicator-user-role.md); then [A15. Adjudicator Process Case](../apis/A15-adjudicator-process-case.md): `approve`; or the two line decisions followed by `approve`; or `reject` with a remark; wait for [C6. Claim Reply](../callbacks/C6-claim-on-submit.md).

#### T10X. EXPECT

- Each claim goes out under the claim workflow id on its own correlation id, referring to its pre-authorisation.
- The first is `approved` for the claimed amount; the second is approved at the sum of the line amounts the payer allowed, with each line's allowed amount shown; the third is `rejected` with its reason.
- `outcome: complete` on the rejection is not read as an approval (CORE confusions).
