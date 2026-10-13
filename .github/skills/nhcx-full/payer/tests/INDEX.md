# Tests

The end-to-end tests the skill writes into the target payer system, one spec per scenario. Every test runs two ways, and both are required: through the desk screens (GUI, a browser driving the S screens) and from the command line (CLI, a runner calling the A services). Both take the same configuration ([T1. Test Configuration](T1-test-configuration.md)), share the same runner contract ([T2. Test Runners](T2-test-runners.md)), and pass or fail on the same expectations. Each file has DESCRIPTION (D), SETUP (S), GUI (G), CLI (L) and EXPECT (X) sections, and refers to screens by S number, APIs by A number and callbacks by C number.

The hospital's side of every exchange is driven through the sandbox provider EMR ([A18. Provider Driver](../apis/A18-provider-driver.md)): the runner signs in to it by token login, has it send the message under test, and reads what it shows once this payer has answered. The facility code it sends as, and the members the tests seed here, are in [T1. Test Configuration](T1-test-configuration.md).

## Harness

| # | Test | Provider side | File |
|---|---|---|---|
| [T1](T1-test-configuration.md) | Test Configuration | both | [T1-test-configuration.md](T1-test-configuration.md) |
| [T2](T2-test-runners.md) | Test Runners | both | [T2-test-runners.md](T2-test-runners.md) |

## Coverage and plan

| # | Test | Provider side | File |
|---|---|---|---|
| [T3](T3-eligibility-answered.md) | Eligibility Validation and Discovery Answered | sandbox provider EMR | [T3-eligibility-answered.md](T3-eligibility-answered.md) |
| [T4](T4-auth-requirements-ruled.md) | Auth-requirements Ruling Answered | sandbox provider EMR | [T4-auth-requirements-ruled.md](T4-auth-requirements-ruled.md) |
| [T5](T5-insurance-plan-served.md) | Insurance Plan Served | sandbox provider EMR | [T5-insurance-plan-served.md](T5-insurance-plan-served.md) |

## Pre-authorisation

| # | Test | Provider side | File |
|---|---|---|---|
| [T6](T6-preauth-approved.md) | Pre-auth Received and Approved | sandbox provider EMR | [T6-preauth-approved.md](T6-preauth-approved.md) |
| [T7](T7-preauth-rejected.md) | Pre-auth Rejected | sandbox provider EMR | [T7-preauth-rejected.md](T7-preauth-rejected.md) |
| [T9](T9-enhancement-approved.md) | Enhancement Received and Approved | sandbox provider EMR | [T9-enhancement-approved.md](T9-enhancement-approved.md) |
| [T10](T10-preauth-cancelled.md) | Pre-auth Cancelled | sandbox provider EMR | [T10-preauth-cancelled.md](T10-preauth-cancelled.md) |
| [T11](T11-predetermination-quoted.md) | Predetermination Quoted | sandbox provider EMR | [T11-predetermination-quoted.md](T11-predetermination-quoted.md) |

## Queries

| # | Test | Provider side | File |
|---|---|---|---|
| [T8](T8-preauth-queried.md) | Pre-auth Queried and Answered | sandbox provider EMR | [T8-preauth-queried.md](T8-preauth-queried.md) |

## Claim

| # | Test | Provider side | File |
|---|---|---|---|
| [T12](T12-claim-approved.md) | Claim Received and Approved | sandbox provider EMR | [T12-claim-approved.md](T12-claim-approved.md) |
| [T13](T13-claim-lama-death.md) | LAMA and Death Claims | sandbox provider EMR | [T13-claim-lama-death.md](T13-claim-lama-death.md) |
| [T14](T14-reprocess-and-release.md) | Reprocess and Balance Release | sandbox provider EMR | [T14-reprocess-and-release.md](T14-reprocess-and-release.md) |

## Payment

| # | Test | Provider side | File |
|---|---|---|---|
| [T15](T15-payment-noticed.md) | Payment Notices and Acknowledgement | sandbox provider EMR | [T15-payment-noticed.md](T15-payment-noticed.md) |
| [T16](T16-payment-enquiry-answered.md) | Payment Enquiry Answered | sandbox provider EMR | [T16-payment-enquiry-answered.md](T16-payment-enquiry-answered.md) |

## Status and redelivery

| # | Test | Provider side | File |
|---|---|---|---|
| [T17](T17-status-answered.md) | Status Enquiry Answered | sandbox provider EMR | [T17-status-answered.md](T17-status-answered.md) |
| [T18](T18-redelivery-ignored.md) | Redelivery and Duplicates | sandbox provider EMR | [T18-redelivery-ignored.md](T18-redelivery-ignored.md) |

## Order

T1 and T2 first: nothing runs without the configuration and the two runners. Then coverage and plan, T3 to T5; pre-authorisation, T6, T7, T9, T10 and T11; queries, T8; claim, T12 to T14; payment, T15 and T16; then status and redelivery, T17 and T18. Within a group the order is the case's own: what the hospital sends first is tested first. Each test seeds its own member and enrolment and opens its own case, so tests run in any order and a failure in one leaves the next its own starting point.
