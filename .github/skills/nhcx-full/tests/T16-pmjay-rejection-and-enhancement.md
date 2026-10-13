# T16. PMJAY Rejection and Enhancement

#### T16D. DESCRIPTION

A rejection is taken once at the role holding the case and ends the leg `rejected`. An enhancement ([A4. Pre-auth Submit](../apis/A4-preauth-submit.md), kind `enhancement`) on an approved PMJAY case is a leg of its own, decided through the same role walk ([A15. Adjudicator Process Case](../apis/A15-adjudicator-process-case.md)).

#### T16S. SETUP

Two PMJAY claims with a package and its ruling ([T13. PMJAY Eligibility, Package Master and Ruling](T13-pmjay-eligibility-and-package-master.md)), the first quoting the package named by `NHCX_TEST_PMJAY_MANUAL_PACKAGE` ([T1. Test Configuration](T1-test-configuration.md)): the sandbox auto-approves `SB043F` before any desk can reject it, so a rejection is not drivable on it, and the test ends `blocked`, cause `sandbox`, when no manual package is configured [SANDBOX](../references/PAYERS.md#markers). Before each claim is opened the runner cancels any open PMJAY pre-authorisation of the beneficiary ([T2. Test Runners](T2-test-runners.md)).

#### T16G. GUI

1. First claim, [S9. Pre-authorisation](../screens/S9-preauthorisation.md): send; payer side: `reject` cycle with a remark; wait; read the reason.
2. Second claim, quoting `MG072C` (one cycle, ₹1,500, the seed's enhanceable package, [T13. PMJAY Eligibility, Package Master and Ruling](T13-pmjay-eligibility-and-package-master.md)), [S9. Pre-authorisation](../screens/S9-preauthorisation.md): send; payer side: `approve`; then raise an enhancement on [S9. Pre-authorisation](../screens/S9-preauthorisation.md) adding a second cycle (₹1,500); payer side: `approve`; wait.

#### T16L. CLI

1. [A4. Pre-auth Submit](../apis/A4-preauth-submit.md); [A14. Adjudicator User Role](../apis/A14-adjudicator-user-role.md); [A15. Adjudicator Process Case](../apis/A15-adjudicator-process-case.md) cycle `reject` with a remark; wait for [C5. Pre-auth Reply](../callbacks/C5-preauth-on-submit.md).
2. [A4. Pre-auth Submit](../apis/A4-preauth-submit.md) with `MG072C`, one cycle; approve cycle; wait; [A4. Pre-auth Submit](../apis/A4-preauth-submit.md) enhancement adding a second cycle; [A14. Adjudicator User Role](../apis/A14-adjudicator-user-role.md); [A15. Adjudicator Process Case](../apis/A15-adjudicator-process-case.md) cycle `approve`; wait for [C5. Pre-auth Reply](../callbacks/C5-preauth-on-submit.md).

#### T16X. EXPECT

- The reject cycle stops `decided`; the first leg is `rejected` with PMJAY's reason shown, not `queried`.
- The enhancement goes out under the enhancement workflow id on a new correlation id; once approved, the approved total is ₹3,000, the two cycles.
