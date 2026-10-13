# L8. End-to-end Tests

#### L8G. GOAL
Run the integrated system against the NHCX sandbox with real sandbox participants and prove each exchange completes: the message goes out, the payer's answer comes back through G8, and the screens show the result.

#### L8I. INPUTS
- `nhcx-plan/dry-run.json` all passing.
- Sandbox credentials: the facility's participant code, client id and secret, the private key of the registered certificate, and a public URL NHCX can reach (registered as `endpoint_url`).
- A sandbox payer that answers (for example the scheme's sandbox payer, or a hosted test payer), and test beneficiaries with known member ids or ABHA numbers.

### L8.1 Check the setup
Run G11 checks: session token, participant record, certificate match, endpoint probe. Stop and report if any fails; nothing else is meaningful until they pass. Two checks G11 does not make: confirm that the **public endpoint reaches the application** end to end (a `POST` to the public `/healthz` through whatever tunnel or reverse proxy fronts it; a tunnel can answer 502 while the application is up), and that the **frontend the GUI runner drives actually renders** (open one page and read a known label; a dev server missing a generated asset breaks every page the same way), so a GUI run does not fail on the shell.

### L8.2 Write the tests
Write every test in [TESTS.md](../references/TESTS.md) that SCOPE holds, from its T spec: the configuration ([T1. Test Configuration](../tests/T1-test-configuration.md)) and the two runners ([T2. Test Runners](../tests/T2-test-runners.md)) first, then one scenario per test. Every scenario is run by both runners, GUI and CLI; a test written for only one of them is not done.

The IRDAI tests ([T3. IRDAI Policy Search and Eligibility](../tests/T3-irdai-policy-and-eligibility.md) to [T12. IRDAI Reprocess and Balance Release](../tests/T12-irdai-reprocess-and-release.md)) run against the IRDAI test payer and the PMJAY tests ([T13. PMJAY Eligibility, Package Master and Ruling](../tests/T13-pmjay-eligibility-and-package-master.md) to [T18. PMJAY Payment Notice, Status Refusal and Cancel](../tests/T18-pmjay-payment-status-cancel.md)) against the PMJAY test payer ([PAYERS.md](../references/PAYERS.md#test-participants)). Tests whose specs this skill does not hold are left out.

Before writing the PMJAY tests, ask the integrator for the PMJAY beneficiary's member id when it is unset ([T1. Test Configuration](../tests/T1-test-configuration.md)); do not guess it, and ask for nothing else: the ABHA number comes from the registry, the HFR id from the facility's record, and both payer desks are signed in to with the facility's ABDM session token. PMJAY's package master takes up to an hour and is never waited for: the tests request it once and run on a seeded one ([T13. PMJAY Eligibility, Package Master and Ruling](../tests/T13-pmjay-eligibility-and-package-master.md)).

### L8.3 Run them
Run the CLI runner first (`nhcx-e2e run --mode cli`), then the GUI runner (`--mode gui`), in the order of [../tests/](../tests/INDEX.md). For each test, wait for the answer by callback and fall back to polling after a bounded time ([T2. Test Runners](../tests/T2-test-runners.md)); record correlation ids and ledger ids so a failure can be traced in G9.

### L8.4 Drive the payer side
Where the payer must decide, take it through A14 and A15 as each test says: the IRDAI payer desk (fixed, signed in to by token login) for the IRDAI test payer, the NHCX Payer Service role walk for PMJAY. In the GUI runner too, since no provider screen drives the payer's side.

### L8.5 Record and triage
Both runners write `nhcx-plan/e2e.json` in the shape [T2. Test Runners](../tests/T2-test-runners.md) gives. A failure is classed as ours (fix, then re-run L6 and L7 for the changed files), the sandbox's (retry within the limit, then report), or setup (back to L8.1). At most 3 attempts per test and runner.

#### L8O. OUTPUT
The test files ([T2. Test Runners](../tests/T2-test-runners.md) gives the layout), and `nhcx-plan/e2e.json`, one entry per test and runner, in the shape [T2. Test Runners](../tests/T2-test-runners.md) gives.

#### L8L. LOG
Record in `nhcx-plan/progress.json` and regenerate `nhcx-plan/progress.md`, as [LOG.md](LOG.md) describes. One entry per sub-step, and one per test attempt and runner (the test id as `item`) with its correlation and ledger ids and result. A fix made because of a failure is logged as its own entry naming the files changed, then the re-run of L6 and L7 for them.

#### L8X. EXIT
- Every test in SCOPE is written for both runners, and passes in both, is `skipped` for a reason the payer adapter gives (for example no status enquiry), or is `blocked` with a sandbox, setup or configuration cause the user has seen (for example no PMJAY member id set).
- The ledger ids recorded for each test exist in G9.
- Every sub-step of L8 has its `started` and closing entries in progress.json, and every file changed is named in one.
