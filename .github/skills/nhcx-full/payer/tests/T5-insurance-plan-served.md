# T5. Insurance Plan Served

#### T5D. DESCRIPTION

A plan request Task arrives on [C3. Insurance Plan Request](../callbacks/C3-insurance-plan-request.md) and [A2. Insurance Plan Answer](../apis/A2-insurance-plan-answer.md) answers with the InsurancePlan bundle ([F5. InsurancePlan](../fhir/F5-insuranceplan.md)) at once. Proved twice: for a product this payer has filed, found by its UIN, by an alias and by the enrolment id the eligibility answer handed the hospital; and for a code nothing matches, which gets the empty plan rather than silence.

#### T5S. SETUP

One member under the [T1. Test Configuration](T1-test-configuration.md) prefix enrolled on a product configured on [S7. Policy Configurator](../screens/S7-policy-configurator.md) with a UIN, one alias, two covered procedures with rates, one coverage clause with a benefit and limit, one exclusion and one sub-limit.

#### T5G. GUI

1. [S7. Policy Configurator](../screens/S7-policy-configurator.md): read the product's UIN, alias, procedures, clause, exclusion and sub-limit.
2. [S11. FHIR Preview](../screens/S11-fhir-preview.md): preview the product as InsurancePlan.
3. Hospital side, through the provider driver ([T2. Test Runners](T2-test-runners.md)): open a case for the member, run the eligibility check, then fetch the insurance plan.
4. Hospital side: the plan tab lists the two packages with their rates.
5. Hospital side: request a plan under a policy code nothing here matches (a fresh case with the policy code overridden).

#### T5L. CLI

1. Seed the member, the enrolment and the product.
2. Through [A18. Provider Driver](../apis/A18-provider-driver.md), send the plan request by the product's UIN, then by its alias, then by the enrolment id.
3. Send it by an unknown code.
4. Read each answer through [A15. Case Exchange Log](../apis/A15-case-exchange.md) or [A12. Transaction FHIR](../apis/A12-txn-fhir.md).

#### T5X. EXPECT

- Every request is answered on `v1/insuranceplan/on_request` on its own correlation id with `response.complete`.
- The plan carries this payer's Organization, the InsurancePlan with the product's name and UIN, one `plan.specificCost` per covered procedure with its rate, the coverage clause with its benefit and limit, the exclusion and the sub-limit, and one Questionnaire per procedure with questions ([F5. InsurancePlan](../fhir/F5-insuranceplan.md), [F6. Questionnaire](../fhir/F6-questionnaire.md)).
- UIN, alias and enrolment id all resolve to the same product; the three answers name the same plan.
- The unknown code gets a bundle with the Organization and no InsurancePlan; the delivery is recorded as `no_plan`; the hospital's side reports an empty package master rather than a timeout.
- [D31. audit_log](../database/D31-audit-log.md) holds `insuranceplan.answered` entries naming the product, and one `insuranceplan.no_plan` naming the code asked.
