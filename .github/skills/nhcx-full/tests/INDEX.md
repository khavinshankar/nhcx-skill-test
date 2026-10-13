# Tests

The end-to-end tests the skill writes into the target, one spec per scenario. Every test runs two ways, and both are required: through the screens (GUI, a browser driving the S screens) and from the command line (CLI, a runner calling the A services). Both take the same configuration ([T1. Test Configuration](T1-test-configuration.md)), share the same runner contract ([T2. Test Runners](T2-test-runners.md)), and pass or fail on the same expectations. Each file has DESCRIPTION (D), SETUP (S), GUI (G), CLI (L) and EXPECT (X) sections, and refers to screens by S number, APIs by A number and callbacks by C number.

The IRDAI tests run against the IRDAI test payer and decide its side through the IRDAI payer desk (A14, A15). The PMJAY tests run against the PMJAY test payer and decide its side through the NHCX Payer Service role walk (A14, A15). Both payers, their member ids and the variables that override them are in [PAYERS.md](../references/PAYERS.md#test-participants).

## Harness

| # | Test | Payer | File |
|---|---|---|---|
| [T1](T1-test-configuration.md) | Test Configuration | both | [T1-test-configuration.md](T1-test-configuration.md) |
| [T2](T2-test-runners.md) | Test Runners | both | [T2-test-runners.md](T2-test-runners.md) |

## IRDAI payer

| # | Test | Payer | File |
|---|---|---|---|
| [T3](T3-irdai-policy-and-eligibility.md) | IRDAI Policy Search and Eligibility | IRDAI test payer | [T3-irdai-policy-and-eligibility.md](T3-irdai-policy-and-eligibility.md) |
| [T4](T4-irdai-plan-and-auth-requirements.md) | IRDAI Insurance Plan and Authorisation Requirements | IRDAI test payer | [T4-irdai-plan-and-auth-requirements.md](T4-irdai-plan-and-auth-requirements.md) |
| [T5](T5-irdai-preauth-approved.md) | IRDAI Pre-authorisation Approved | IRDAI test payer | [T5-irdai-preauth-approved.md](T5-irdai-preauth-approved.md) |
| [T6](T6-irdai-preauth-rejected.md) | IRDAI Pre-authorisation Rejected and Sent Again | IRDAI test payer | [T6-irdai-preauth-rejected.md](T6-irdai-preauth-rejected.md) |
| [T7](T7-irdai-query-answered.md) | IRDAI Query Answered | IRDAI test payer | [T7-irdai-query-answered.md](T7-irdai-query-answered.md) |
| [T8](T8-irdai-enhancement.md) | IRDAI Enhancement | IRDAI test payer | [T8-irdai-enhancement.md](T8-irdai-enhancement.md) |
| [T9](T9-irdai-cancel-and-status.md) | IRDAI Status Enquiry and Cancel | IRDAI test payer | [T9-irdai-cancel-and-status.md](T9-irdai-cancel-and-status.md) |
| [T10](T10-irdai-claim.md) | IRDAI Claim Approved, Part-approved and Rejected | IRDAI test payer | [T10-irdai-claim.md](T10-irdai-claim.md) |
| [T11](T11-irdai-payment.md) | IRDAI Payment Notice and Acknowledgement | IRDAI test payer | [T11-irdai-payment.md](T11-irdai-payment.md) |
| [T12](T12-irdai-reprocess-and-release.md) | IRDAI Reprocess and Balance Release | IRDAI test payer | [T12-irdai-reprocess-and-release.md](T12-irdai-reprocess-and-release.md) |

## PMJAY payer and its adjudication

| # | Test | Payer | File |
|---|---|---|---|
| [T13](T13-pmjay-eligibility-and-package-master.md) | PMJAY Eligibility, Package Master and Ruling | PMJAY test payer | [T13-pmjay-eligibility-and-package-master.md](T13-pmjay-eligibility-and-package-master.md) |
| [T14](T14-pmjay-preauth-adjudicated.md) | PMJAY Pre-authorisation Through the Payer Service | PMJAY test payer | [T14-pmjay-preauth-adjudicated.md](T14-pmjay-preauth-adjudicated.md) |
| [T15](T15-pmjay-query-by-resubmission.md) | PMJAY Query Answered by Resubmission | PMJAY test payer | [T15-pmjay-query-by-resubmission.md](T15-pmjay-query-by-resubmission.md) |
| [T16](T16-pmjay-rejection-and-enhancement.md) | PMJAY Rejection and Enhancement | PMJAY test payer | [T16-pmjay-rejection-and-enhancement.md](T16-pmjay-rejection-and-enhancement.md) |
| [T17](T17-pmjay-claim-adjudicated.md) | PMJAY Claim Through the Role Walk | PMJAY test payer | [T17-pmjay-claim-adjudicated.md](T17-pmjay-claim-adjudicated.md) |
| [T18](T18-pmjay-payment-status-cancel.md) | PMJAY Payment Notice, Status Refusal and Cancel | PMJAY test payer | [T18-pmjay-payment-status-cancel.md](T18-pmjay-payment-status-cancel.md) |
| [T19](T19-pmjay-biometric-and-abha.md) | PMJAY Beneficiary Verification and ABHA | PMJAY test payer | [T19-pmjay-biometric-and-abha.md](T19-pmjay-biometric-and-abha.md) |

## Order

T1 and T2 first: nothing runs without the configuration and the two runners. Then the IRDAI tests in order, T3 to T12, then the PMJAY tests, T13 to T19. Within a payer the order is the claim's own: eligibility and plan, pre-authorisation, the payer's questions, claim, payment, and what follows a decision. Each test opens its own claim, so a failure in one does not leave the next without a starting point.
