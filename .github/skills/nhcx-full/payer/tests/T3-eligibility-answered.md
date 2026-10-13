# T3. Eligibility Validation and Discovery Answered

#### T3D. DESCRIPTION

The first exchange of every case: a CoverageEligibilityRequest arrives on [C2. Coverage Eligibility Check](../callbacks/C2-coverage-eligibility-check.md) and is answered on the spot by [A1. Eligibility Answer](../apis/A1-eligibility-answer.md). Three answers are proved: cover in force (with the wallet as the benefit), cover that lapsed (found, answered `inforce` false with the reason), and a person this payer does not know (answered, not refused).

#### T3S. SETUP

Three members under the [T1. Test Configuration](T1-test-configuration.md) prefix, seeded on [S4. Members](../screens/S4-members.md) and [S5. Subscriptions](../screens/S5-subscriptions.md): one enrolled on the default product with the cover period open today; one enrolled for a period that ended last year; and one registered with no enrolment at all. Each has a distinct ABHA number and mobile.

#### T3G. GUI

1. [S4. Members](../screens/S4-members.md) and [S5. Subscriptions](../screens/S5-subscriptions.md): register the three members and the two enrolments; note the in-force member's wallet balance.
2. Hospital side, through the provider driver ([T2. Test Runners](T2-test-runners.md)): search the in-force member by member id and run the validation check; then discover by ABHA number and by mobile.
3. Hospital side: run the check for the lapsed member, then for the member with no cover.
4. [S1. Overview](../screens/S1-overview.md): the overview's recent activity shows the three answers.
5. [S11. FHIR Preview](../screens/S11-fhir-preview.md): preview the in-force enrolment as CoverageEligibilityResponse and compare it with what went out.

#### T3L. CLI

1. Seed the three members and two enrolments through the desk's services.
2. Through [A18. Provider Driver](../apis/A18-provider-driver.md), send `validation` by member id, then `discovery` by ABHA and by mobile, for the in-force member.
3. Read each answer this payer sent through [A15. Case Exchange Log](../apis/A15-case-exchange.md) on the transaction the driver reported, or through [A12. Transaction FHIR](../apis/A12-txn-fhir.md).
4. Repeat for the lapsed member and the unknown member.

#### T3X. EXPECT

- Every check is answered on `v1/coverageeligibility/on_check` on the request's own correlation id with `x-hcx-status` `response.complete`; nothing waits for a person.
- In force: `insurance[0].inforce` true, the benefit's `allowedMoney` equal to the wallet balance seeded, the payer's Patient carrying this payer's member record ([F3. CoverageEligibilityResponse](../fhir/F3-coverage-eligibility-response.md)); the hospital's side shows the policy eligible with that balance.
- Lapsed: the enrolment is found and answered `inforce` false with the period that ended; the delivery is recorded as `lapsed`; the hospital's side shows not eligible.
- No cover: a no-cover response goes back rather than a refusal; the delivery is recorded as `no_cover`.
- Discovery by ABHA and by mobile find the same enrolment as the member id did.
- [D31. audit_log](../database/D31-audit-log.md) holds one `eligibility.answered`, one `eligibility.lapsed` and one `eligibility.no_cover` entry naming the facility and the correlation ids.
