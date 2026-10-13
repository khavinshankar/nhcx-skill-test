# L8. End-to-end Tests

#### L8G. GOAL
Run the integrated system against the NHCX sandbox with real sandbox participants and prove each exchange completes: the hospital's message arrives through G8, the desk files or answers it, the answer goes out, and the hospital's side shows the result.

#### L8I. INPUTS
- `nhcx-plan/dry-run.json` all passing.
- Sandbox credentials: the payer's participant code, client id and secret, the private key of the registered certificate, and a public URL NHCX can reach (registered as `endpoint_url`).
- The sandbox provider EMR that sends to this payer (signed in to by token login, [A18. Provider Driver](../apis/A18-provider-driver.md)), and members seeded in this payer's registry with the ids the tests send under ([T1. Test Configuration](../tests/T1-test-configuration.md)).

### L8.1 Check the setup
Run G11 checks: session token, participant record, certificate match, endpoint probe. Stop and report if any fails; nothing else is meaningful until they pass.

### L8.2 Write the tests
Write every test in [TESTS.md](../references/TESTS.md) that SCOPE holds, from its T spec: the configuration ([T1. Test Configuration](../tests/T1-test-configuration.md)) and the two runners ([T2. Test Runners](../tests/T2-test-runners.md)) first, then one scenario per test. Every scenario is run by both runners, GUI and CLI; a test written for only one of them is not done.

Every test's hospital side is the sandbox provider EMR, driven through [A18. Provider Driver](../apis/A18-provider-driver.md) ([PAYERS.md](../references/PAYERS.md#test-participants)). Tests whose specs this skill does not hold are left out.

Nothing is asked from the integrator beyond the payer's own credentials: the facility code the provider EMR sends as is read from its own record after token login, and the members the tests send about are seeded here by [T1. Test Configuration](../tests/T1-test-configuration.md).

### L8.3 Run them
Run the CLI runner first (`nhcx-payer-e2e run --mode cli`), then the GUI runner (`--mode gui`), in the order of [../tests/](../tests/INDEX.md). For each test, wait for the hospital's message by callback and fall back to polling after a bounded time ([T2. Test Runners](../tests/T2-test-runners.md)); record correlation ids and ledger ids so a failure can be traced in G9.

### L8.4 Drive the hospital's side
Where the hospital must send or read, take it through A18 as each test says: the eligibility check, the plan request, the pre-authorisation and its enhancement, the cancel, the claim, the reprocess, the query reply, the payment acknowledgement and the status enquiry. In the GUI runner too, since no desk screen drives the hospital's side; the desk's own decisions are taken through the screens.

### L8.5 Record and triage
Both runners write `nhcx-plan/e2e.json` in the shape [T2. Test Runners](../tests/T2-test-runners.md) gives. A failure is classed as ours (fix, then re-run L6 and L7 for the changed files), the sandbox's (retry within the limit, then report), or setup (back to L8.1). At most 3 attempts per test and runner.

#### L8O. OUTPUT
The test files ([T2. Test Runners](../tests/T2-test-runners.md) gives the layout), and `nhcx-plan/e2e.json`, one entry per test and runner, in the shape [T2. Test Runners](../tests/T2-test-runners.md) gives.

#### L8L. LOG
Record in `nhcx-plan/progress.json` and regenerate `nhcx-plan/progress.md`, as [LOG.md](LOG.md) describes. One entry per sub-step, and one per test attempt and runner (the test id as `item`) with its correlation and ledger ids and result. A fix made because of a failure is logged as its own entry naming the files changed, then the re-run of L6 and L7 for them.

#### L8X. EXIT
- Every test in SCOPE is written for both runners, and passes in both, is `skipped` for a reason the scheme profile gives (for example the resubmission query mode), or is `blocked` with a sandbox, setup or configuration cause the user has seen.
- The ledger ids recorded for each test exist in G9.
- Every sub-step of L8 has its `started` and closing entries in progress.json, and every file changed is named in one.
