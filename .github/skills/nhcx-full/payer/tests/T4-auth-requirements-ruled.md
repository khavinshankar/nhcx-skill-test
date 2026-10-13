# T4. Auth-requirements Ruling Answered

#### T4D. DESCRIPTION

An eligibility check with purpose `auth-requirements` and items arrives on [C2. Coverage Eligibility Check](../callbacks/C2-coverage-eligibility-check.md); [A1. Eligibility Answer](../apis/A1-eligibility-answer.md) answers per item with the package rate and the documents and forms wanted at each stage, in the dialect the hospital reads [PAYER](../references/PAYERS.md#markers). This is the ruling the hospital's pre-authorisation tab is built from.

#### T4S. SETUP

One member under the [T1. Test Configuration](T1-test-configuration.md) prefix enrolled on the default product. A procedure in the registry ([S8. Procedures](../screens/S8-procedures.md), [S9. Procedure Configurator](../screens/S9-procedure-configurator.md)) with a package rate, four documents wanted at pre-authorisation and two at claim, and treatment-guideline questions, and covered by the product ([S7. Policy Configurator](../screens/S7-policy-configurator.md)).

#### T4G. GUI

1. [S9. Procedure Configurator](../screens/S9-procedure-configurator.md): open the procedure and read its rate, document rules per phase and questions.
2. Hospital side, through the provider driver ([T2. Test Runners](T2-test-runners.md)): open a case for the member, fetch the plan, add the procedure as a line, and run the validate (auth-requirements) check.
3. [S1. Overview](../screens/S1-overview.md): the activity shows the ruling answered.
4. Hospital side: the validate tab lists the documents due at pre-authorisation and the treatment-guideline form.

#### T4L. CLI

1. Seed the member and enrolment; read the procedure's rules through the desk's services.
2. Through [A18. Provider Driver](../apis/A18-provider-driver.md), send `auth-requirements` with the procedure as the one item.
3. Read the answer through [A15. Case Exchange Log](../apis/A15-case-exchange.md) or [A12. Transaction FHIR](../apis/A12-txn-fhir.md).

#### T4X. EXPECT

- The answer goes on `v1/coverageeligibility/on_check` with the request's correlation id and `response.complete`.
- One `insurance[0].item` per item asked, with `authorizationRequired` true, the benefit typed `Procedure` and `allowedMoney` equal to the package rate ([F3. CoverageEligibilityResponse](../fhir/F3-coverage-eligibility-response.md)).
- `authorizationSupporting` names each document wanted, with `Type: pre` on the four pre-authorisation documents and `Type: claim` on the two claim documents, and one entry carrying `fullUrl:` of the procedure's Questionnaire ([F6. Questionnaire](../fhir/F6-questionnaire.md)) [PAYER](../references/PAYERS.md#markers).
- The hospital's side lists the four documents and the one form on its pre-authorisation tab.
- [D31. audit_log](../database/D31-audit-log.md) holds an `eligibility.auth_requirements` entry naming the item count.
