# T2. Test Runners

#### T2D. DESCRIPTION

Every test in this folder is written twice, once per runner, and both are required. The GUI runner proves an operator can work the case through the desk; the CLI runner proves the services do it without the screens, and is what a pipeline runs. They share one scenario per test: the same seeded member, the same hospital messages, the same desk decisions, the same expectations. A test is `pass` only when every runner it was asked to run passes.

The CLI runner calls the application's services (A) as functions inside the application's process (a management command, a console task, a script run with the application's context), never the gateway over HTTP (CORE instruction 1). Everything a test changes goes through the same services and callbacks the screens use, so both runners exercise the same code.

The hospital's messages are not this payer's to send. Both runners drive them through the provider driver ([A18. Provider Driver](../apis/A18-provider-driver.md)): the sandbox provider EMR sends the check, the plan request, the pre-authorisation, the claim, the Task or the reply, and the message arrives at this payer through [G8. Receive](../gateway/G8-receive.md) and [C1. Callback Door](../callbacks/C1-callback-door.md) like any other.

#### T2S. SETUP

Where the files go, in the target's own test layout:

| Path | Holds |
|---|---|
| `tests/nhcx/e2e/config.example.env` | Every [T1. Test Configuration](T1-test-configuration.md) variable, no secrets. |
| `tests/nhcx/e2e/scenarios/` | One scenario per test (`t06_preauth_approved`), written once and run by both runners. |
| `tests/nhcx/e2e/gui/` | The GUI runner: the target's browser automation (the one the target already uses, else Playwright). |
| `tests/nhcx/e2e/cli/` | The CLI runner and its command (`nhcx-payer-e2e`), registered the target's way (npm script, management command, Gradle task, Make target). |
| `tests/nhcx/e2e/provider/` | The provider driver: token sign-in to the sandbox provider EMR and its claim calls, through [A18. Provider Driver](../apis/A18-provider-driver.md). |

Before the first test, both runners run the setup checks of [G11. Startup Checks and Health](../gateway/G11-startup-checks.md) (session token, participant record, certificate match, endpoint probe), then sign in to the sandbox provider EMR through [A18. Provider Driver](../apis/A18-provider-driver.md) and check that the facility named in `NHCX_PAYER_TEST_FACILITY` is one it works, and stop with `blocked`, cause `setup`, if any fails.

#### T2G. GUI

- Sign in through the desk's login screen, then drive the screens a test names, by their visible labels, the way an adjudicator or a finance operator would: [S2. Cases](../screens/S2-cases.md) to open a case, [S3. Case Desk](../screens/S3-case-desk.md) for everything decided on it, [S10. Payments](../screens/S10-payments.md) for money.
- Take a screenshot at the end of each step and on every failure, into `tests/nhcx/e2e/artifacts/<test>/`.
- Read results off the screen (stage chips, line decisions, amounts, the exchange log) as the S spec describes them, never off the database.
- Run headless by default; `--headed` shows the browser, for a person watching the run.
- The hospital's side is not a desk screen: no S spec drives [A18. Provider Driver](../apis/A18-provider-driver.md). The GUI runner sends the hospital's messages through the same provider driver as the CLI, between the screen steps, and reads their outcome back on the desk.

#### T2L. CLI

The command, in the target's form:

```
nhcx-payer-e2e list
nhcx-payer-e2e check
nhcx-payer-e2e run [T3 T6 ... | coverage | preauth | claim | payment] [--mode cli|gui|both] [--headed] [--report <path>]
```

`run` prints each step as it happens, one line each, so a person can watch it:

```
06:37:52 T6 cli PASS hospital sends the pre-authorisation     -> 202, correlation 5b1f0c1e
06:37:54 T6 cli PASS case opened and acknowledged             -> CL/26/0T00000VS, preauth, pending, ack 20
06:37:59 T6 cli PASS desk approves every line and the case    -> approved, 48500
06:38:03 T6 cli PASS hospital reads the verdict               -> approved, workflow 21
```

It exits 0 when every test asked for passed, 1 when any failed, 2 when any was blocked by configuration or setup.

#### T2X. EXPECT

**Waiting for a message to arrive.** A step that sends from the hospital waits until this payer has taken the message in: the case, quote or reconciliation it produces is visible through [A15. Case Exchange Log](../apis/A15-case-exchange.md) (CLI) or on [S3. Case Desk](../screens/S3-case-desk.md) (GUI). After `NHCX_PAYER_TEST_WAIT_SECONDS` the step fails with the message's correlation id and, when the driver returned one, the ledger id, so it can be traced in [G9. Ledger](../gateway/G9-ledger.md).

**Waiting on the hospital.** The two threads this payer waits on, a query's reply ([C9. Communication](../callbacks/C9-communication.md)) and a payment acknowledgement ([C11. Payment Acknowledgement](../callbacks/C11-payment-acknowledgement.md)), wait for the callback first. After `NHCX_PAYER_TEST_POLL_AFTER_SECONDS` the step also polls the ledger ([A11. Transaction Related](../apis/A11-txn-related.md), [A12. Transaction FHIR](../apis/A12-txn-fhir.md)), and a reply found there is applied by the same callback handler (CORE instruction 4).

**Deciding on the desk.** A decision is always read then taken: the case and its lines first ([A15. Case Exchange Log](../apis/A15-case-exchange.md)), then the line decisions and the case decision ([A13. Adjudicate](../apis/A13-adjudicate.md)), or the payment ([A14. Disburse](../apis/A14-disburse.md)). The decision taken and the answer's transaction id are recorded with the test.

**Fresh members and cases.** Every test seeds its own member and enrolment under the [T1. Test Configuration](T1-test-configuration.md) prefix and has the hospital open its own case, so tests run in any order and a failure leaves nothing another test depends on.

**The report.** Both runners write into `NHCX_PAYER_TEST_REPORT`, one entry per test and runner:

```json
{
  "run_at": "<ISO time>",
  "config": {"facility": "", "member_prefix": "", "app_url": "set | missing"},
  "setup_checks": [{"check": "session token", "result": "pass | fail", "detail": ""}],
  "tests": [
    {
      "id": "T6", "runner": "gui | cli",
      "member": "", "case": "", "correlation_ids": [], "answer_txn_ids": [], "decisions": [],
      "steps": [{"at": "", "what": "", "result": "pass | fail", "got": ""}],
      "result": "pass | fail | blocked | skipped",
      "cause": "ours | sandbox | setup", "detail": "", "attempts": 1
    }
  ],
  "summary": {"pass": 0, "fail": 0, "blocked": 0, "skipped": 0}
}
```

**Triage.** A failure is ours (fix, then re-run the test), the sandbox's or the sandbox provider EMR's (retry, then report), or setup (back to the setup checks). At most 3 attempts per test and runner.
