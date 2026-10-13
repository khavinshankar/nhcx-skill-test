# Screens

Every screen of the claim, patient and practitioner flows, in one list. Each row links to its full spec in [../screens/](../screens/INDEX.md). Routes are the application's own; "tab" means a tab of the claim page S6.

## Claims

| # | Screen | Route | What it does | APIs | Callbacks |
|---|---|---|---|---|---|
| [S1](../screens/S1-search-policy.md) | Search Policy | `claims/search` | Starts a new claim: the operator enters one identifier (member id, mobile or ABHA number) and searches the beneficiary registry. | [A1](../apis/A1-policy-search.md) | none |
| [S2](../screens/S2-select-policy.md) | Select Policy | `claims/search/results` | Lists the policies found, and opens a new claim case around the one picked, landing on S6. | [A1](../apis/A1-policy-search.md) | none |
| [S3](../screens/S3-policy-discovery.md) | Policy Discovery | `claims/view/:caseid/eligibility` | Shows the beneficiary and policy, sends the eligibility check, and shows the verdict and wallet. | [A2](../apis/A2-coverage-eligibility-check.md), [A10](../apis/A10-txn-related.md), [A11](../apis/A11-txn-dispatch.md), [A12](../apis/A12-txn-fhir.md), [A13](../apis/A13-txn-list.md) | [C2](../callbacks/C2-coverage-eligibility-on-check.md) |
| [S4](../screens/S4-claim-creation-form.md) | Claim Creation Form | `claims/view/:caseid/validate`, `claims/view/:caseid/preauth` | Links the case to the patient's current admission by ABHA number, and captures the pre-auth draft: stay, ICD-10 diagnoses, treating team, package and items. | [A18](../apis/A18-biometric-authentication.md) | none |
| [S5](../screens/S5-claim-master.md) | Claim Master | `claims/list` | Lists every claim case with beneficiary, policy, payer, balance, stage and status, filterable by status; the entry point to S1 and S6. | none | none |
| [S6](../screens/S6-claim-detail.md) | Claim Detail | `claims/view/:caseid` | The case shell: header chips, next-action buttons and the tabs in episode order. Polls every waiting leg on load. | [A17](../apis/A17-claim-state.md) | [C1](../callbacks/C1-callback-door.md), [C7](../callbacks/C7-cancel-on-submit.md) |
| [S7](../screens/S7-insurance-plan.md) | Insurance Plan | `claims/view/:caseid/plan` | Fetches and browses the payer's package master: packages (S7.1), forms (S7.2) and a form's questions (S7.3). | [A3](../apis/A3-insurance-plan-request.md), [A10](../apis/A10-txn-related.md), [A11](../apis/A11-txn-dispatch.md) | [C4](../callbacks/C4-insuranceplan-on-request.md) |
| [S8](../screens/S8-line-items.md) | Line Items | `claims/view/:caseid/lines` | Picks procedures, implants and ward tiers from the package master (S8.1), and asks the payer which need authorisation (S8.2). | [A2](../apis/A2-coverage-eligibility-check.md), [A10](../apis/A10-txn-related.md), [A11](../apis/A11-txn-dispatch.md) | [C3](../callbacks/C3-auth-requirements-on-check.md) |
| [S9](../screens/S9-preauthorisation.md) | Pre-authorisation | `claims/view/:caseid/preauth` | Answers the payer's forms, attaches documents, sends the pre-auth (or a quote, an enhancement, a query answer), shows the verdict, and cancels or asks status. | [A2](../apis/A2-coverage-eligibility-check.md), [A4](../apis/A4-preauth-submit.md), [A6](../apis/A6-task-submit.md), [A10](../apis/A10-txn-related.md), [A11](../apis/A11-txn-dispatch.md) | [C5](../callbacks/C5-preauth-on-submit.md), [C7](../callbacks/C7-cancel-on-submit.md), [C8](../callbacks/C8-enquiry-on-submit.md) |
| [S10](../screens/S10-communication.md) | Communication | `claims/view/:caseid/communication` | Shows the payer's queries, notifications and notes per leg, and replies to a query with text and documents. | [A7](../apis/A7-communication-on-request.md) | [C9](../callbacks/C9-communication-request.md) |
| [S11](../screens/S11-claim-submission.md) | Claim Submission | `claims/view/:caseid/claim` | Records the discharge, collects claim-stage documents and forms, sends the claim, shows the verdict, and asks status, reprocess or release. | [A5](../apis/A5-claim-submit.md), [A6](../apis/A6-task-submit.md), [A10](../apis/A10-txn-related.md), [A11](../apis/A11-txn-dispatch.md), [A18](../apis/A18-biometric-authentication.md) | [C6](../callbacks/C6-claim-on-submit.md), [C8](../callbacks/C8-enquiry-on-submit.md) |
| [S12](../screens/S12-payments.md) | Payments | `claims/view/:caseid/payments` | Shows each payment notice with its breakdown and acknowledgement, and re-sends a failed acknowledgement. | [A8](../apis/A8-paymentnotice-on-request.md) | [C10](../callbacks/C10-paymentnotice-request.md) |
| [S17](../screens/S17-beneficiary-discovery.md) | Beneficiary Discovery | `claims/discovery` | A page of its own for a discovery check: the operator picks the payer, names the person by one identifier and adds the Aadhaar, mobile and member id as additional information. | [A2](../apis/A2-coverage-eligibility-check.md) | [C2](../callbacks/C2-coverage-eligibility-on-check.md) |
| [S18](../screens/S18-beneficiary-verification.md) | Beneficiary Verification | `claims/view/:caseid/verification` | The Verification tab: the beneficiary authenticated against their ABHA by fingerprint, iris or face, optional for any payer and required by PMJAY, at the stage the stay is at (Preauth while admitted, Discharge once discharged). | [A2](../apis/A2-coverage-eligibility-check.md), [A4](../apis/A4-preauth-submit.md), [A5](../apis/A5-claim-submit.md), [A18](../apis/A18-biometric-authentication.md), [A19](../apis/A19-abha-m1.md) | none |

## Patient

| # | Screen | Route | What it does | APIs | Callbacks |
|---|---|---|---|---|---|
| [S13](../screens/S13-patient-list.md) | Patient List | `patients/list` | Finds a registered patient by name, MRN, mobile or ABHA, and opens the chart or registers a new patient. | [A19](../apis/A19-abha-m1.md) | none |
| [S14](../screens/S14-patient-registration-form.md) | Patient Registration Form | `patients/new`, `patients/edit/:id` | Registers or edits a patient, including the ABHA number and address that link a claim to an admission. | [A4](../apis/A4-preauth-submit.md), [A5](../apis/A5-claim-submit.md), [A18](../apis/A18-biometric-authentication.md), [A19](../apis/A19-abha-m1.md) | none |
| [S15](../screens/S15-patient-detail.md) | Patient Detail | `patients/view/:id` | The chart: overview, encounters, problems and allergies, vitals, laboratory and billing. | [A4](../apis/A4-preauth-submit.md), [A5](../apis/A5-claim-submit.md) | none |

## Practitioner

| # | Screen | Route | What it does | APIs | Callbacks |
|---|---|---|---|---|---|
| [S16](../screens/S16-practitioner-master.md) | Practitioner Master | `practitioners/list` | Adds, edits and retires doctors, with the HPR id, registration and qualification the claim's care team sends; active doctors fill every picker. | [A4](../apis/A4-preauth-submit.md), [A5](../apis/A5-claim-submit.md) | none |
