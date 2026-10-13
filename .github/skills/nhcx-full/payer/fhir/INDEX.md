# FHIR

The FHIR resources this payer reads from a hospital's bundles and builds for its answers. APIs (A) and callbacks (C) refer to these by F number. Each file has RESOURCE (R), DESCRIPTION (D), FIELDS (F) and USED BY (U) sections. Direction is from this payer's side: `received` is read out of a hospital's bundle, `sent` is built by this payer, `both` is read and built.

Received resources are parsed as plain maps and never fail on a shape they merely do not know: a reference that resolves to nothing leaves its field blank, a resource with nothing usable is dropped, and the whole bundle is kept on the exchange log so it can be read again later. Sent resources follow the scheme's wire shape [PAYER](../references/PAYERS.md#markers): a collection bundle identified by the hospital's claim number, every resource tagged `SUBSETTED`, resolvable `https` fullUrls under this payer's base, and the Patient, both Organizations and the Coverage beside the focal resource.

## Envelope

| # | Resource | Direction | File |
|---|---|---|---|
| [F1](F1-bundle.md) | Bundle | both | [F1-bundle.md](F1-bundle.md) |

## Eligibility and plan

| # | Resource | Direction | File |
|---|---|---|---|
| [F2](F2-coverage-eligibility-request.md) | CoverageEligibilityRequest | received | [F2-coverage-eligibility-request.md](F2-coverage-eligibility-request.md) |
| [F3](F3-coverage-eligibility-response.md) | CoverageEligibilityResponse | sent | [F3-coverage-eligibility-response.md](F3-coverage-eligibility-response.md) |
| [F4](F4-task-insuranceplan.md) | Task (InsurancePlan request) | received | [F4-task-insuranceplan.md](F4-task-insuranceplan.md) |
| [F5](F5-insuranceplan.md) | InsurancePlan | sent | [F5-insuranceplan.md](F5-insuranceplan.md) |
| [F6](F6-questionnaire.md) | Questionnaire | sent | [F6-questionnaire.md](F6-questionnaire.md) |

## Pre-authorisation and claim

| # | Resource | Direction | File |
|---|---|---|---|
| [F7](F7-questionnaireresponse.md) | QuestionnaireResponse | received | [F7-questionnaireresponse.md](F7-questionnaireresponse.md) |
| [F8](F8-claim.md) | Claim | received | [F8-claim.md](F8-claim.md) |
| [F9](F9-claimresponse.md) | ClaimResponse | sent | [F9-claimresponse.md](F9-claimresponse.md) |
| [F10](F10-task-claim-actions.md) | Task (claim actions and answers) | both | [F10-task-claim-actions.md](F10-task-claim-actions.md) |

## Queries and payment

| # | Resource | Direction | File |
|---|---|---|---|
| [F11](F11-communicationrequest.md) | CommunicationRequest | sent | [F11-communicationrequest.md](F11-communicationrequest.md) |
| [F12](F12-communication.md) | Communication | received | [F12-communication.md](F12-communication.md) |
| [F13](F13-paymentnotice.md) | PaymentNotice | both | [F13-paymentnotice.md](F13-paymentnotice.md) |
| [F14](F14-paymentreconciliation.md) | PaymentReconciliation | sent | [F14-paymentreconciliation.md](F14-paymentreconciliation.md) |

## Parties and supporting resources

| # | Resource | Direction | File |
|---|---|---|---|
| [F15](F15-patient.md) | Patient | both | [F15-patient.md](F15-patient.md) |
| [F16](F16-practitioner.md) | Practitioner | received | [F16-practitioner.md](F16-practitioner.md) |
| [F17](F17-organization.md) | Organization | both | [F17-organization.md](F17-organization.md) |
| [F18](F18-coverage.md) | Coverage | both | [F18-coverage.md](F18-coverage.md) |
| [F19](F19-other-resources.md) | Other resources | received | [F19-other-resources.md](F19-other-resources.md) |
