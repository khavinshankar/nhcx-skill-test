# Tests

Every end-to-end test the skill writes, in one list. Each row links to its full spec in [../tests/](../tests/INDEX.md). Every test runs through the desk screens (GUI) and from the command line (CLI); [T1. Test Configuration](../tests/T1-test-configuration.md) is the configuration both read and [T2. Test Runners](../tests/T2-test-runners.md) the runner contract both follow. The hospital's side is the sandbox provider EMR, driven through [A18. Provider Driver](../apis/A18-provider-driver.md). Step [L8](../steps/L8-e2e-tests.md) writes and runs them.

## Harness

| # | Test | Provider side | What it proves | Screens | APIs | Callbacks |
|---|---|---|---|---|---|---|
| [T1](../tests/T1-test-configuration.md) | Test Configuration | both | The one configuration every end-to-end test reads: the sandbox provider EMR, the facility code it sends as, the member ids seeded here, the mode, the waits. | [S4](../screens/S4-members.md), [S5](../screens/S5-subscriptions.md) | [A11](../apis/A11-txn-related.md), [A18](../apis/A18-provider-driver.md) | none |
| [T2](../tests/T2-test-runners.md) | Test Runners | both | The GUI and CLI runners, their shared contract: setup checks, driving the hospital through A18, waiting for a message to arrive, deciding on the desk, the report. | [S2](../screens/S2-cases.md), [S3](../screens/S3-case-desk.md), [S10](../screens/S10-payments.md) | [A11](../apis/A11-txn-related.md), [A12](../apis/A12-txn-fhir.md), [A13](../apis/A13-adjudicate.md), [A14](../apis/A14-disburse.md), [A15](../apis/A15-case-exchange.md), [A18](../apis/A18-provider-driver.md) | [C1](../callbacks/C1-callback-door.md), [C9](../callbacks/C9-communication.md), [C11](../callbacks/C11-payment-acknowledgement.md) |

## Coverage and plan

| # | Test | Provider side | What it proves | Screens | APIs | Callbacks |
|---|---|---|---|---|---|---|
| [T3](../tests/T3-eligibility-answered.md) | Eligibility Validation and Discovery Answered | sandbox provider EMR | The hospital checks a member by member id, then discovers by ABHA and mobile; in force, lapsed and no cover are each answered. | [S1](../screens/S1-overview.md), [S4](../screens/S4-members.md), [S5](../screens/S5-subscriptions.md), [S11](../screens/S11-fhir-preview.md) | [A1](../apis/A1-eligibility-answer.md), [A12](../apis/A12-txn-fhir.md), [A15](../apis/A15-case-exchange.md), [A18](../apis/A18-provider-driver.md) | [C2](../callbacks/C2-coverage-eligibility-check.md) |
| [T4](../tests/T4-auth-requirements-ruled.md) | Auth-requirements Ruling Answered | sandbox provider EMR | The hospital asks about a package set; the ruling names the rate, documents and forms. | [S1](../screens/S1-overview.md), [S7](../screens/S7-policy-configurator.md), [S8](../screens/S8-procedures.md), [S9](../screens/S9-procedure-configurator.md) | [A1](../apis/A1-eligibility-answer.md), [A12](../apis/A12-txn-fhir.md), [A15](../apis/A15-case-exchange.md), [A18](../apis/A18-provider-driver.md) | [C2](../callbacks/C2-coverage-eligibility-check.md) |
| [T5](../tests/T5-insurance-plan-served.md) | Insurance Plan Served | sandbox provider EMR | The hospital requests the package master by product and by an unknown code; the plan and the empty plan come back. | [S7](../screens/S7-policy-configurator.md), [S11](../screens/S11-fhir-preview.md) | [A2](../apis/A2-insurance-plan-answer.md), [A12](../apis/A12-txn-fhir.md), [A15](../apis/A15-case-exchange.md), [A18](../apis/A18-provider-driver.md) | [C3](../callbacks/C3-insurance-plan-request.md) |

## Pre-authorisation

| # | Test | Provider side | What it proves | Screens | APIs | Callbacks |
|---|---|---|---|---|---|---|
| [T6](../tests/T6-preauth-approved.md) | Pre-auth Received and Approved | sandbox provider EMR | A pre-authorisation opens a case, is acknowledged, every line is approved on the desk, and the verdict reaches the hospital. | [S2](../screens/S2-cases.md), [S3](../screens/S3-case-desk.md) | [A3](../apis/A3-preauth-answer.md), [A13](../apis/A13-adjudicate.md), [A15](../apis/A15-case-exchange.md), [A18](../apis/A18-provider-driver.md) | [C4](../callbacks/C4-preauth-submit.md) |
| [T7](../tests/T7-preauth-rejected.md) | Pre-auth Rejected | sandbox provider EMR | The desk rejects; the hospital reads outcome error with the reason. | [S2](../screens/S2-cases.md), [S3](../screens/S3-case-desk.md) | [A3](../apis/A3-preauth-answer.md), [A13](../apis/A13-adjudicate.md), [A15](../apis/A15-case-exchange.md), [A18](../apis/A18-provider-driver.md) | [C4](../callbacks/C4-preauth-submit.md) |
| [T9](../tests/T9-enhancement-approved.md) | Enhancement Received and Approved | sandbox provider EMR | The hospital adds lines under the same number; they join the case for a fresh decision; the enhancement verdict goes out (22). | [S2](../screens/S2-cases.md), [S3](../screens/S3-case-desk.md) | [A3](../apis/A3-preauth-answer.md), [A13](../apis/A13-adjudicate.md), [A15](../apis/A15-case-exchange.md), [A18](../apis/A18-provider-driver.md) | [C4](../callbacks/C4-preauth-submit.md) |
| [T10](../tests/T10-preauth-cancelled.md) | Pre-auth Cancelled | sandbox provider EMR | The hospital cancels with a Task; the case is withdrawn and PC02 goes back. | [S2](../screens/S2-cases.md), [S3](../screens/S3-case-desk.md) | [A9](../apis/A9-task-answer.md), [A15](../apis/A15-case-exchange.md), [A18](../apis/A18-provider-driver.md) | [C7](../callbacks/C7-task-submit.md) |
| [T11](../tests/T11-predetermination-quoted.md) | Predetermination Quoted | sandbox provider EMR | A predetermination is priced at once and opens no case. | [S1](../screens/S1-overview.md), [S2](../screens/S2-cases.md), [S5](../screens/S5-subscriptions.md) | [A10](../apis/A10-predetermination-quote.md), [A12](../apis/A12-txn-fhir.md), [A18](../apis/A18-provider-driver.md), [A19](../apis/A19-sandbox-scenarios.md) | [C6](../callbacks/C6-predetermination.md) |

## Queries

| # | Test | Provider side | What it proves | Screens | APIs | Callbacks |
|---|---|---|---|---|---|---|
| [T8](../tests/T8-preauth-queried.md) | Pre-auth Queried and Answered | sandbox provider EMR | The desk queries; the CommunicationRequest goes out; the hospital replies with a document; the case is back with the adjudicator and approved. | [S2](../screens/S2-cases.md), [S3](../screens/S3-case-desk.md) | [A5](../apis/A5-query-request.md), [A11](../apis/A11-txn-related.md), [A13](../apis/A13-adjudicate.md), [A15](../apis/A15-case-exchange.md), [A18](../apis/A18-provider-driver.md) | [C9](../callbacks/C9-communication.md) |

## Claim

| # | Test | Provider side | What it proves | Screens | APIs | Callbacks |
|---|---|---|---|---|---|---|
| [T12](../tests/T12-claim-approved.md) | Claim Received and Approved | sandbox provider EMR | The claim files the final bill on the pre-authorised case, is approved, the wallet is debited, and the verdict goes out on the claim's thread. | [S2](../screens/S2-cases.md), [S3](../screens/S3-case-desk.md), [S5](../screens/S5-subscriptions.md) | [A4](../apis/A4-claim-answer.md), [A13](../apis/A13-adjudicate.md), [A15](../apis/A15-case-exchange.md), [A18](../apis/A18-provider-driver.md) | [C5](../callbacks/C5-claim-submit.md) |
| [T13](../tests/T13-claim-lama-death.md) | LAMA and Death Claims | sandbox provider EMR | Claims discharged LAMA or DAMA and a death case are filed with their discharge blocks. | [S2](../screens/S2-cases.md), [S3](../screens/S3-case-desk.md) | [A13](../apis/A13-adjudicate.md), [A15](../apis/A15-case-exchange.md), [A18](../apis/A18-provider-driver.md) | [C5](../callbacks/C5-claim-submit.md) |
| [T14](../tests/T14-reprocess-and-release.md) | Reprocess and Balance Release | sandbox provider EMR | The hospital disputes a decided claim and asks for a balance; the case reopens, the cover comes back, and the new decision goes on the Task's thread. | [S2](../screens/S2-cases.md), [S3](../screens/S3-case-desk.md), [S5](../screens/S5-subscriptions.md) | [A9](../apis/A9-task-answer.md), [A13](../apis/A13-adjudicate.md), [A15](../apis/A15-case-exchange.md), [A18](../apis/A18-provider-driver.md) | [C7](../callbacks/C7-task-submit.md) |

## Payment

| # | Test | Provider side | What it proves | Screens | APIs | Callbacks |
|---|---|---|---|---|---|---|
| [T15](../tests/T15-payment-noticed.md) | Payment Notices and Acknowledgement | sandbox provider EMR | Finance raises and completes a payment; two notices go out; the hospital's acknowledgement is recorded. | [S10](../screens/S10-payments.md) | [A6](../apis/A6-payment-notice.md), [A11](../apis/A11-txn-related.md), [A13](../apis/A13-adjudicate.md), [A14](../apis/A14-disburse.md), [A15](../apis/A15-case-exchange.md), [A18](../apis/A18-provider-driver.md) | [C11](../callbacks/C11-payment-acknowledgement.md) |
| [T16](../tests/T16-payment-enquiry-answered.md) | Payment Enquiry Answered | sandbox provider EMR | The hospital asks where the money is; the reconciliation comes back. | [S3](../screens/S3-case-desk.md), [S10](../screens/S10-payments.md) | [A7](../apis/A7-payment-enquiry-answer.md), [A12](../apis/A12-txn-fhir.md), [A13](../apis/A13-adjudicate.md), [A14](../apis/A14-disburse.md), [A15](../apis/A15-case-exchange.md), [A18](../apis/A18-provider-driver.md) | [C10](../callbacks/C10-payment-enquiry.md) |

## Status and redelivery

| # | Test | Provider side | What it proves | Screens | APIs | Callbacks |
|---|---|---|---|---|---|---|
| [T17](../tests/T17-status-answered.md) | Status Enquiry Answered | sandbox provider EMR | The hospital asks where a thread stands, on the task route and with the status filter. | [S3](../screens/S3-case-desk.md) | [A8](../apis/A8-status-answer.md), [A12](../apis/A12-txn-fhir.md), [A13](../apis/A13-adjudicate.md), [A15](../apis/A15-case-exchange.md), [A18](../apis/A18-provider-driver.md) | [C8](../callbacks/C8-status-enquiry.md) |
| [T18](../tests/T18-redelivery-ignored.md) | Redelivery and Duplicates | sandbox provider EMR | The same pre-authorisation delivered twice opens one case; a second copy of a claim files its documents once. | [S2](../screens/S2-cases.md), [S3](../screens/S3-case-desk.md) | [A13](../apis/A13-adjudicate.md), [A15](../apis/A15-case-exchange.md), [A18](../apis/A18-provider-driver.md) | [C1](../callbacks/C1-callback-door.md), [C4](../callbacks/C4-preauth-submit.md), [C5](../callbacks/C5-claim-submit.md) |
