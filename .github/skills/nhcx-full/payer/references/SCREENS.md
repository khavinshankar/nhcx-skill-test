# Screens

Every screen of the desk, the registry, the configuration and the finance flows, in one list. Each row links to its full spec in [../screens/](../screens/INDEX.md). Routes are the application's own; S4 to S9 are screens most payer systems already have, and only their NHCX additions are built.

## Desk

| # | Screen | Route | What it does | APIs | Callbacks |
|---|---|---|---|---|---|
| [S1](../screens/S1-overview.md) | Overview | `/` | The desk's home: counts of cases by stage, money approved and paid, cover lapsing, recent activity, and the queue of cases waiting on a person. | none | none |
| [S2](../screens/S2-cases.md) | Cases | `/cases` | Every case addressed to this payer, filtered by stage, search and money still owed; opens the case desk. | [A13](../apis/A13-adjudicate.md) | [C4](../callbacks/C4-preauth-submit.md), [C5](../callbacks/C5-claim-submit.md), [C7](../callbacks/C7-task-submit.md) |
| [S3](../screens/S3-case-desk.md) | Case Desk | `/cases/:id` | One case from pre-authorisation to settlement: the dossier the hospital sent, per-line decisions, approve, reject or query, documents, the timeline, the exchange log and the FHIR preview. | [A3](../apis/A3-preauth-answer.md), [A4](../apis/A4-claim-answer.md), [A5](../apis/A5-query-request.md), [A9](../apis/A9-task-answer.md), [A13](../apis/A13-adjudicate.md), [A15](../apis/A15-case-exchange.md), [A19](../apis/A19-sandbox-scenarios.md) | [C4](../callbacks/C4-preauth-submit.md), [C5](../callbacks/C5-claim-submit.md), [C7](../callbacks/C7-task-submit.md), [C9](../callbacks/C9-communication.md) |

## Registry

| # | Screen | Route | What it does | APIs | Callbacks |
|---|---|---|---|---|---|
| [S4](../screens/S4-members.md) | Members | `/members` | The beneficiary directory: register, edit and retire members, with the ABHA number the exchange matches on. | [A1](../apis/A1-eligibility-answer.md), [A20](../apis/A20-abha-m1.md) | [C2](../callbacks/C2-coverage-eligibility-check.md), [C4](../callbacks/C4-preauth-submit.md) |
| [S5](../screens/S5-subscriptions.md) | Subscriptions | `/subscriptions` | Enrolments of a member on a product: cover period, wallet and its ledger, family members, pause and resume, and the ABHA policy link through the registry. | [A1](../apis/A1-eligibility-answer.md), [A13](../apis/A13-adjudicate.md), [A16](../apis/A16-abha-policy-link.md) | [C2](../callbacks/C2-coverage-eligibility-check.md) |

## Configuration

| # | Screen | Route | What it does | APIs | Callbacks |
|---|---|---|---|---|---|
| [S6](../screens/S6-policies.md) | Policies | `/policies` | The products on offer, their sum assured, subscribers and status; opens the configurator. | [A2](../apis/A2-insurance-plan-answer.md) | [C3](../callbacks/C3-insurance-plan-request.md) |
| [S7](../screens/S7-policy-configurator.md) | Policy Configurator | `/policies/new`, `/policies/edit/:id` | Configures one product as the InsurancePlan the exchange will serve: covered procedures, SNOMED coverage clauses and benefits with limits, exclusions, sub-limits and aliases. | [A2](../apis/A2-insurance-plan-answer.md) | none |
| [S8](../screens/S8-procedures.md) | Procedures | `/procedures` | The procedure registry the plan and the rulings are built from: code, category, package rate, and which documents each phase wants. | [A1](../apis/A1-eligibility-answer.md), [A2](../apis/A2-insurance-plan-answer.md), [A10](../apis/A10-predetermination-quote.md) | [C6](../callbacks/C6-predetermination.md) |
| [S9](../screens/S9-procedure-configurator.md) | Procedure Configurator | `/procedures/new`, `/procedures/edit/:id` | Configures one procedure: codes, package rate, the treatment-guideline questions asked at pre-authorisation, and the required documents per phase. | [A1](../apis/A1-eligibility-answer.md), [A2](../apis/A2-insurance-plan-answer.md) | none |
| [S11](../screens/S11-fhir-preview.md) | FHIR Preview | `/fhir` | Renders what this payer would put on the exchange right now: a policy as InsurancePlan, an enrolment as CoverageEligibilityResponse, a case as ClaimResponse, CommunicationRequest or PaymentReconciliation. | [A1](../apis/A1-eligibility-answer.md), [A2](../apis/A2-insurance-plan-answer.md), [A3](../apis/A3-preauth-answer.md), [A4](../apis/A4-claim-answer.md), [A5](../apis/A5-query-request.md), [A7](../apis/A7-payment-enquiry-answer.md), [A15](../apis/A15-case-exchange.md) | none |
| [S12](../screens/S12-organisation.md) | Organisation | `/organisation` | The payer's own record: name, IRDAI registration, ROHINI id, the NHCX participant code and processing code, and contact details, which every bundle carries as the payer Organization. | [A16](../apis/A16-abha-policy-link.md), [A17](../apis/A17-participant-lookup.md) | none |

## Finance

| # | Screen | Route | What it does | APIs | Callbacks |
|---|---|---|---|---|---|
| [S10](../screens/S10-payments.md) | Payments | `/payments` | The disbursement desk: approved cases with money owed, raising a payment, recording the UTR or a failure, and the payment notices that went out. | [A6](../apis/A6-payment-notice.md), [A14](../apis/A14-disburse.md) | [C11](../callbacks/C11-payment-acknowledgement.md) |
