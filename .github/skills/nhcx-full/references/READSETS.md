# Read Sets

What to read before implementing one spec, so a task never needs the whole skill. Each row is one screen, API, callback or gateway part, and the FHIR, database and gateway specs it links to, followed through their own links (tables and hub specs such as the bundle envelope F1 and the claim table D9 are listed but not followed further). Only specs this skill holds are listed.

Always read, whatever the task: [CORE.md](CORE.md) (addresses and the exchange table), [F1. Bundle](../fhir/F1-bundle.md) (every bundle), [D9. claim](../database/D9-claim.md) (every case), [C1. Callback Door](../callbacks/C1-callback-door.md) (every reply), and the knowledge source ([KNOWLEDGE.md](KNOWLEDGE.md)).

## Screens

| To implement | What it is | Read with it |
|---|---|---|
| [S1](../screens/S1-search-policy.md) | Search Policy | nothing else |
| [S2](../screens/S2-select-policy.md) | Select Policy | [D9](../database/D9-claim.md), [D30](../database/D30-counter.md) |
| [S3](../screens/S3-policy-discovery.md) | Policy Discovery | [D9](../database/D9-claim.md) |
| [S4](../screens/S4-claim-creation-form.md) | Claim Creation Form | [D2](../database/D2-practitioner.md), [D3](../database/D3-patient.md), [D4](../database/D4-encounter.md), [D5](../database/D5-condition.md), [D8](../database/D8-terminology.md), [D9](../database/D9-claim.md), [D16](../database/D16-claim-line.md), [D25](../database/D25-claim-diagnosis.md), [D26](../database/D26-claim-care-team.md), [D27](../database/D27-claim-item.md) |
| [S5](../screens/S5-claim-master.md) | Claim Master | nothing else |
| [S6](../screens/S6-claim-detail.md) | Claim Detail | nothing else |
| [S7](../screens/S7-insurance-plan.md) | Insurance Plan | [D10](../database/D10-claim-plan.md), [D11](../database/D11-claim-plan-benefit.md), [D12](../database/D12-claim-plan-form.md) |
| [S8](../screens/S8-line-items.md) | Line Items | [D10](../database/D10-claim-plan.md), [D11](../database/D11-claim-plan-benefit.md), [D13](../database/D13-claim-auth.md), [D14](../database/D14-claim-auth-item.md), [D15](../database/D15-claim-auth-requirement.md), [D16](../database/D16-claim-line.md) |
| [S9](../screens/S9-preauthorisation.md) | Pre-authorisation | [D9](../database/D9-claim.md), [D11](../database/D11-claim-plan-benefit.md), [D12](../database/D12-claim-plan-form.md), [D15](../database/D15-claim-auth-requirement.md), [D16](../database/D16-claim-line.md), [D17](../database/D17-claim-form-answer.md), [D18](../database/D18-claim-preauth.md), [D19](../database/D19-claim-predetermination.md), [D23](../database/D23-claim-query.md), [D28](../database/D28-claim-document.md), [D29](../database/D29-claim-enquiry.md), [D30](../database/D30-counter.md) |
| [S10](../screens/S10-communication.md) | Communication | [D9](../database/D9-claim.md), [D15](../database/D15-claim-auth-requirement.md), [D23](../database/D23-claim-query.md), [D28](../database/D28-claim-document.md) |
| [S11](../screens/S11-claim-submission.md) | Claim Submission | [D9](../database/D9-claim.md), [D11](../database/D11-claim-plan-benefit.md), [D12](../database/D12-claim-plan-form.md), [D15](../database/D15-claim-auth-requirement.md), [D16](../database/D16-claim-line.md), [D17](../database/D17-claim-form-answer.md), [D20](../database/D20-claim-submission.md), [D21](../database/D21-claim-payment.md), [D23](../database/D23-claim-query.md), [D28](../database/D28-claim-document.md), [D29](../database/D29-claim-enquiry.md) |
| [S12](../screens/S12-payments.md) | Payments | [D9](../database/D9-claim.md), [D20](../database/D20-claim-submission.md), [D21](../database/D21-claim-payment.md), [D22](../database/D22-claim-payment-detail.md), [G7](../gateway/G7-send.md) |
| [S13](../screens/S13-patient-list.md) | Patient List | [D3](../database/D3-patient.md) |
| [S14](../screens/S14-patient-registration-form.md) | Patient Registration Form | [D3](../database/D3-patient.md) |
| [S15](../screens/S15-patient-detail.md) | Patient Detail | [D3](../database/D3-patient.md), [D4](../database/D4-encounter.md), [D5](../database/D5-condition.md), [D6](../database/D6-observation.md), [D7](../database/D7-allergy.md), [D8](../database/D8-terminology.md) |
| [S16](../screens/S16-practitioner-master.md) | Practitioner Master | [F16](../fhir/F16-practitioner.md), [D2](../database/D2-practitioner.md), [D8](../database/D8-terminology.md), [D26](../database/D26-claim-care-team.md) |
| [S17](../screens/S17-beneficiary-discovery.md) | Beneficiary Discovery | [F2](../fhir/F2-coverage-eligibility-request.md), [F15](../fhir/F15-patient.md), [D9](../database/D9-claim.md) |
| [S18](../screens/S18-beneficiary-verification.md) | Beneficiary Verification | [D3](../database/D3-patient.md), [D31](../database/D31-biometric-auth.md) |

## APIs

| To implement | What it is | Read with it |
|---|---|---|
| [A1](../apis/A1-policy-search.md) | Policy Search | [D9](../database/D9-claim.md), [G3](../gateway/G3-session-token.md), [G4](../gateway/G4-registry.md), [G10](../gateway/G10-beneficiary-registry.md) |
| [A2](../apis/A2-coverage-eligibility-check.md) | Coverage Eligibility Check | [F1](../fhir/F1-bundle.md), [F2](../fhir/F2-coverage-eligibility-request.md), [F15](../fhir/F15-patient.md), [F16](../fhir/F16-practitioner.md), [F17](../fhir/F17-organization.md), [F18](../fhir/F18-coverage.md), [F19](../fhir/F19-other-resources.md), [D9](../database/D9-claim.md), [D13](../database/D13-claim-auth.md), [D14](../database/D14-claim-auth-item.md), [D15](../database/D15-claim-auth-requirement.md), [G5](../gateway/G5-protocol-headers.md), [G7](../gateway/G7-send.md), [G8](../gateway/G8-receive.md), [G9](../gateway/G9-ledger.md) |
| [A3](../apis/A3-insurance-plan-request.md) | Insurance Plan Request | [F1](../fhir/F1-bundle.md), [F4](../fhir/F4-task-insuranceplan.md), [D10](../database/D10-claim-plan.md), [D11](../database/D11-claim-plan-benefit.md), [D12](../database/D12-claim-plan-form.md), [G5](../gateway/G5-protocol-headers.md), [G7](../gateway/G7-send.md), [G8](../gateway/G8-receive.md), [G9](../gateway/G9-ledger.md) |
| [A4](../apis/A4-preauth-submit.md) | Pre-auth Submit | [F1](../fhir/F1-bundle.md), [F7](../fhir/F7-questionnaireresponse.md), [F8](../fhir/F8-claim.md), [F15](../fhir/F15-patient.md), [F16](../fhir/F16-practitioner.md), [F17](../fhir/F17-organization.md), [F18](../fhir/F18-coverage.md), [F19](../fhir/F19-other-resources.md), [D18](../database/D18-claim-preauth.md), [D19](../database/D19-claim-predetermination.md), [G5](../gateway/G5-protocol-headers.md), [G7](../gateway/G7-send.md), [G8](../gateway/G8-receive.md), [G9](../gateway/G9-ledger.md) |
| [A5](../apis/A5-claim-submit.md) | Claim Submit | [F1](../fhir/F1-bundle.md), [F7](../fhir/F7-questionnaireresponse.md), [F8](../fhir/F8-claim.md), [F15](../fhir/F15-patient.md), [F16](../fhir/F16-practitioner.md), [F17](../fhir/F17-organization.md), [F18](../fhir/F18-coverage.md), [F19](../fhir/F19-other-resources.md), [D20](../database/D20-claim-submission.md), [G5](../gateway/G5-protocol-headers.md), [G7](../gateway/G7-send.md), [G8](../gateway/G8-receive.md), [G9](../gateway/G9-ledger.md) |
| [A6](../apis/A6-task-submit.md) | Task Submit (cancel, status, reprocess, release) | [F1](../fhir/F1-bundle.md), [F10](../fhir/F10-task-claim-actions.md), [F17](../fhir/F17-organization.md), [D18](../database/D18-claim-preauth.md), [D29](../database/D29-claim-enquiry.md), [G5](../gateway/G5-protocol-headers.md), [G7](../gateway/G7-send.md), [G8](../gateway/G8-receive.md), [G9](../gateway/G9-ledger.md) |
| [A7](../apis/A7-communication-on-request.md) | Communication Reply | [F1](../fhir/F1-bundle.md), [F8](../fhir/F8-claim.md), [F10](../fhir/F10-task-claim-actions.md), [F11](../fhir/F11-communicationrequest.md), [F12](../fhir/F12-communication.md), [F15](../fhir/F15-patient.md), [F16](../fhir/F16-practitioner.md), [F17](../fhir/F17-organization.md), [F18](../fhir/F18-coverage.md), [D23](../database/D23-claim-query.md), [D28](../database/D28-claim-document.md), [G5](../gateway/G5-protocol-headers.md), [G7](../gateway/G7-send.md), [G8](../gateway/G8-receive.md), [G9](../gateway/G9-ledger.md) |
| [A8](../apis/A8-paymentnotice-on-request.md) | Payment Notice Acknowledgement | [F1](../fhir/F1-bundle.md), [F14](../fhir/F14-payment-acknowledgement.md), [F17](../fhir/F17-organization.md), [D21](../database/D21-claim-payment.md), [G5](../gateway/G5-protocol-headers.md), [G7](../gateway/G7-send.md), [G9](../gateway/G9-ledger.md) |
| [A10](../apis/A10-txn-related.md) | Transaction Related | nothing else |
| [A11](../apis/A11-txn-dispatch.md) | Transaction Dispatch | nothing else |
| [A12](../apis/A12-txn-fhir.md) | Transaction FHIR | nothing else |
| [A13](../apis/A13-txn-list.md) | Transaction List | nothing else |
| [A14](../apis/A14-adjudicator-user-role.md) | Adjudicator User Role | [D1](../database/D1-organization.md), [D9](../database/D9-claim.md), [D18](../database/D18-claim-preauth.md), [D20](../database/D20-claim-submission.md), [G3](../gateway/G3-session-token.md) |
| [A15](../apis/A15-adjudicator-process-case.md) | Adjudicator Process Case | [D1](../database/D1-organization.md), [D9](../database/D9-claim.md), [D18](../database/D18-claim-preauth.md), [D20](../database/D20-claim-submission.md), [D24](../database/D24-claim-adjudication.md), [G3](../gateway/G3-session-token.md) |
| [A16](../apis/A16-gateway-token.md) | Gateway Token | [D1](../database/D1-organization.md), [G2](../gateway/G2-configuration.md), [G3](../gateway/G3-session-token.md) |
| [A17](../apis/A17-claim-state.md) | Claim State | nothing else |
| [A18](../apis/A18-biometric-authentication.md) | Biometric Authentication | [F7](../fhir/F7-questionnaireresponse.md), [D3](../database/D3-patient.md), [D9](../database/D9-claim.md), [D28](../database/D28-claim-document.md), [D31](../database/D31-biometric-auth.md), [G3](../gateway/G3-session-token.md) |
| [A19](../apis/A19-abha-m1.md) | ABHA Create and Verify (ABDM M1) | [D3](../database/D3-patient.md), [G3](../gateway/G3-session-token.md) |

## Callbacks

| To implement | What it is | Read with it |
|---|---|---|
| [C1](../callbacks/C1-callback-door.md) | Callback Door | nothing else |
| [C2](../callbacks/C2-coverage-eligibility-on-check.md) | Coverage Eligibility Verdict | [G8](../gateway/G8-receive.md) |
| [C3](../callbacks/C3-auth-requirements-on-check.md) | Authorisation Requirements Ruling | [G8](../gateway/G8-receive.md) |
| [C4](../callbacks/C4-insuranceplan-on-request.md) | Insurance Plan Reply | [G8](../gateway/G8-receive.md) |
| [C5](../callbacks/C5-preauth-on-submit.md) | Pre-auth Reply | [F9](../fhir/F9-claimresponse.md), [G8](../gateway/G8-receive.md), [G9](../gateway/G9-ledger.md) |
| [C6](../callbacks/C6-claim-on-submit.md) | Claim Reply | [F9](../fhir/F9-claimresponse.md), [G8](../gateway/G8-receive.md), [G9](../gateway/G9-ledger.md) |
| [C7](../callbacks/C7-cancel-on-submit.md) | Cancel Reply | [G8](../gateway/G8-receive.md) |
| [C8](../callbacks/C8-enquiry-on-submit.md) | Enquiry Reply | [G8](../gateway/G8-receive.md) |
| [C9](../callbacks/C9-communication-request.md) | Payer Communication | [G8](../gateway/G8-receive.md) |
| [C10](../callbacks/C10-paymentnotice-request.md) | Payment Notice | [G8](../gateway/G8-receive.md) |

## Gateway

| To implement | What it is | Read with it |
|---|---|---|
| [G1](../gateway/G1-embedding.md) | Embedding | nothing else |
| [G2](../gateway/G2-configuration.md) | Configuration and Participants | nothing else |
| [G3](../gateway/G3-session-token.md) | Session Token | nothing else |
| [G4](../gateway/G4-registry.md) | Registry and Certificates | nothing else |
| [G5](../gateway/G5-protocol-headers.md) | Protocol Headers | nothing else |
| [G6](../gateway/G6-encryption.md) | Encryption | nothing else |
| [G7](../gateway/G7-send.md) | Send | nothing else |
| [G8](../gateway/G8-receive.md) | Receive | nothing else |
| [G9](../gateway/G9-ledger.md) | Ledger | nothing else |
| [G10](../gateway/G10-beneficiary-registry.md) | Beneficiary Registry | nothing else |
| [G11](../gateway/G11-startup-checks.md) | Startup Checks and Health | nothing else |
