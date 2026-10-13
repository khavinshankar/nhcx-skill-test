# T14. PMJAY Pre-authorisation Through the Payer Service

#### T14D. DESCRIPTION

On PMJAY the decision is taken on the NHCX Payer Service, outside the exchange ([A14. Adjudicator User Role](../apis/A14-adjudicator-user-role.md), [A15. Adjudicator Process Case](../apis/A15-adjudicator-process-case.md), payer service transport). A pre-authorisation is decided in one step, at PPD-Trust. PMJAY first acknowledges the request, then sends its decision; both arrive as [C5. Pre-auth Reply](../callbacks/C5-preauth-on-submit.md) on the leg's correlation id and neither is routed on its workflow id (CORE instruction 5).

**The sandbox may decide by itself.** For some packages the PMJAY sandbox auto-approves: `SB043F` came back approved (workflow 21) about 6 seconds after the acknowledgement, before any desk role held the case, and [A14. Adjudicator User Role](../apis/A14-adjudicator-user-role.md) then answered "No Data found with the caseid ..." [SANDBOX](../references/PAYERS.md#markers). The test therefore waits for either a desk role or a decision after the acknowledgement: when the decision arrives first, the desk steps are recorded as `skipped (sandbox auto-decided)` and the test still passes on the decision; only when [A14. Adjudicator User Role](../apis/A14-adjudicator-user-role.md) returns a role is the cycle run. A test that needs the desk to act ([T15. PMJAY Query Answered by Resubmission](T15-pmjay-query-by-resubmission.md), [T16. PMJAY Rejection and Enhancement](T16-pmjay-rejection-and-enhancement.md)) uses the package named by `NHCX_TEST_PMJAY_MANUAL_PACKAGE` ([T1. Test Configuration](T1-test-configuration.md)), one the sandbox does not auto-decide, and ends `blocked (sandbox)` when none is configured.

#### T14S. SETUP

A PMJAY claim with a package and its ruling, as [T13. PMJAY Eligibility, Package Master and Ruling](T13-pmjay-eligibility-and-package-master.md) leaves it; the Payer Service token from [T1. Test Configuration](T1-test-configuration.md) (or the facility's own session token).

#### T14G. GUI

1. [S4. Claim Creation Form](../screens/S4-claim-creation-form.md), [S9. Pre-authorisation](../screens/S9-preauthorisation.md): save the draft, then send the pre-authorisation; wait for PMJAY's acknowledgement on [S9. Pre-authorisation](../screens/S9-preauthorisation.md).
2. Payer side, through the payer driver: read the role; run the `approve` cycle. When [S9. Pre-authorisation](../screens/S9-preauthorisation.md) already shows the decision or [A14. Adjudicator User Role](../apis/A14-adjudicator-user-role.md) finds no case, record the step as skipped (sandbox auto-decided).
3. Wait on [S9. Pre-authorisation](../screens/S9-preauthorisation.md) for the decision.

#### T14L. CLI

1. [A4. Pre-auth Submit](../apis/A4-preauth-submit.md); wait for the first [C5. Pre-auth Reply](../callbacks/C5-preauth-on-submit.md) (the acknowledgement).
2. [A14. Adjudicator User Role](../apis/A14-adjudicator-user-role.md) with the case number read off the leg's payer reference (its last `/` segment, [PAYER](../references/PAYERS.md#markers)); "No Data found" with the decision already applied means the sandbox decided by itself: skip 3.
3. [A15. Adjudicator Process Case](../apis/A15-adjudicator-process-case.md) cycle with decision `approve`.
4. Wait for the next [C5. Pre-auth Reply](../callbacks/C5-preauth-on-submit.md).

#### T14X. EXPECT

- The send goes out under PMJAY's pre-authorisation workflow id ([PAYERS.md](../references/PAYERS.md#workflow-ids)) with the `AB-PMJAY` programme code on every line: the check compares each line's `programCode[0].coding[0].code` with the adapter's programme **code** (`AB-PMJAY`), never the whole `(code, display)` tuple, which never matches.
- Either [A14. Adjudicator User Role](../apis/A14-adjudicator-user-role.md) returns `PPD-Trust` and the cycle takes `Approve` there and stops `completed`, with one step in its trail and one `cycle_id`; or the sandbox auto-decided and the desk steps are recorded `skipped (sandbox auto-decided)` [SANDBOX](../references/PAYERS.md#markers).
- The decision arrives as [C5. Pre-auth Reply](../callbacks/C5-preauth-on-submit.md); the leg is `approved` with PMJAY's approved amount, shown on [S9. Pre-authorisation](../screens/S9-preauthorisation.md).
- Every action taken, and the cycle's trail, is recorded against the claim.
