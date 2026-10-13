# T2. Test Runners

#### T2D. DESCRIPTION

Every test in this folder is written twice, once per runner, and both are required. The GUI runner proves an operator can do it through the screens; the CLI runner proves the services do it without the screens, and is what a pipeline runs. They share one scenario per test: the same setup, the same payer decisions, the same expectations. A test is `pass` only when every runner it was asked to run passes.

The CLI runner calls the application's services (A) as functions inside the application's process (a management command, a console task, a script run with the application's context), never the gateway over HTTP (CORE instruction 1). Everything a test changes goes through the same services and callbacks the screens use, so both runners exercise the same code.

#### T2S. SETUP

Where the files go, in the target's own test layout:

| Path | Holds |
|---|---|
| `tests/nhcx/e2e/config.example.env` | Every [T1. Test Configuration](T1-test-configuration.md) variable, no secrets. |
| `tests/nhcx/e2e/scenarios/` | One scenario per test (`t05_irdai_preauth_approved`), written once and run by both runners. |
| `tests/nhcx/e2e/gui/` | The GUI runner: the target's browser automation (the one the target already uses, else Playwright). |
| `tests/nhcx/e2e/cli/` | The CLI runner and its command (`nhcx-e2e`), registered the target's way (npm script, management command, Gradle task, Make target). |
| `tests/nhcx/e2e/payer/` | The payer-side drivers: the IRDAI desk transport and the Payer Service role walk, both through [A14. Adjudicator User Role](../apis/A14-adjudicator-user-role.md) and [A15. Adjudicator Process Case](../apis/A15-adjudicator-process-case.md). |

Before the first test, both runners run the setup checks of [G11. Startup Checks and Health](../gateway/G11-startup-checks.md) (session token, participant record, certificate match, endpoint probe) and stop with `blocked`, cause `setup`, if any fails.

#### T2G. GUI

- Sign in through the HMIS login screen, then drive the screens a test names, by their visible labels, the way an operator would: [S5. Claim Master](../screens/S5-claim-master.md) to open a claim, [S6. Claim Detail](../screens/S6-claim-detail.md) and its tabs for everything after.
- Take a screenshot at the end of each step and on every failure, into `tests/nhcx/e2e/artifacts/<test>/`.
- Read results off the screen (status chips, amounts, messages) as the S spec describes them, never off the database.
- Run headless by default; `--headed` shows the browser, for a person watching the run, slowed by `NHCX_TEST_SLOWMO_MS` between actions.
- When the test's patient is already on the patient master, start from it: "Search insurance policy" on the chart ([S15. Patient Detail](../screens/S15-patient-detail.md)) or the patient-list row ([S13. Patient List](../screens/S13-patient-list.md)) opens [S1. Search Policy](../screens/S1-search-policy.md) prefilled, so the case is linked to the patient when it opens.
- Save the pre-authorisation draft ([S4. Claim Creation Form](../screens/S4-claim-creation-form.md)) before the first send; [S9. Pre-authorisation](../screens/S9-preauthorisation.md) disables the send until it is saved.
- Read a refusal off the red line under the tabs, and ignore toasts the step did not cause.
- The payer's side is not a provider screen: no S spec drives [A14. Adjudicator User Role](../apis/A14-adjudicator-user-role.md) or [A15. Adjudicator Process Case](../apis/A15-adjudicator-process-case.md). The GUI runner takes the payer's decisions through the same payer driver as the CLI (`tests/nhcx/e2e/payer/`), between the screen steps, and reads their outcome back on the screens.

#### T2L. CLI

The command, in the target's form:

```
nhcx-e2e list
nhcx-e2e check
nhcx-e2e run [T3 T5 ... | irdai | pmjay] [--mode cli|gui|both] [--headed] [--report <path>]
```

`run` prints each step as it happens, one line each, so a person can watch it:

```
06:37:52 T5 cli PASS provider sends the pre-authorisation   -> 202, correlation 5b1f0c1e
06:37:55 T5 cli PASS payer desk opens the case              -> CASE-1017, preauth, pending
06:37:59 T5 cli PASS provider receives the approval         -> approved, 48500
```

It exits 0 when every test asked for passed, 1 when any failed, 2 when any was blocked by configuration or setup.

#### T2X. EXPECT

**Waiting for the payer.** Every step that waits on the payer waits for the callback first. After `NHCX_TEST_POLL_AFTER_SECONDS` it also polls the ledger ([A10. Transaction Related](../apis/A10-txn-related.md) to [A13. Transaction List](../apis/A13-txn-list.md)), and a reply found there is applied by the same callback handler (CORE instruction 4). After `NHCX_TEST_WAIT_SECONDS` the step fails with the leg's correlation id and ledger ids, so it can be traced in [G9. Ledger](../gateway/G9-ledger.md).

**Deciding the payer's side.** A decision is always read then taken: the role or case first ([A14. Adjudicator User Role](../apis/A14-adjudicator-user-role.md)), then the action ([A15. Adjudicator Process Case](../apis/A15-adjudicator-process-case.md)). IRDAI decisions go to the IRDAI payer desk; PMJAY decisions walk the Payer Service roles as A15 describes. The decision taken, its trail and the `cycle_id` are recorded with the test.

**Fresh claims.** Every test opens its own claim for the test beneficiary, so tests run in any order and a failure leaves nothing another test depends on.

**One open pre-authorisation per PMJAY beneficiary.** PMJAY keeps one active pre-authorisation per beneficiary and hospital and refuses a second with PAYR-1238 "Beneficiary is having an active preauthorization request at this hospital ... cancel ... or raise a claim" [PAYER](../references/PAYERS.md#markers). A claim the payer refused does not release it, and earlier runs from other desks on the same participant leave their own open (one from an earlier month had to be closed by hand). So before a PMJAY test opens a fresh claim the runner itself frees the beneficiary: it finds every case of the beneficiary whose pre-authorisation is `submitting`, `approved`, `partial` or `queried` with no claim filed and cancels it ([A6. Task Submit (cancel, status, reprocess, release)](../apis/A6-task-submit.md) cancel, reason `administrativeerror`), waiting for [C7. Cancel Reply](../callbacks/C7-cancel-on-submit.md); a case it cannot see (another desk's) is reported as the cause when PAYR-1238 still comes back. Tests are ordered so a pending claim never blocks the next test's pre-authorisation.

**The GUI runner, in particular.** It starts from the patient master when the claim's patient already exists in the HMIS ("Search insurance policy" on the chart or the patient list, [S13. Patient List](../screens/S13-patient-list.md), [S15. Patient Detail](../screens/S15-patient-detail.md)), so the case opens linked to the patient; it saves the S4 draft before the first send (S9 refuses the send until the draft is saved); it reads results off the page, where a red line under the tabs is the refusal to read and unrelated toasts are ignored; and it offers a headed, slowed mode (`--headed`, `NHCX_TEST_SLOWMO_MS`, `NHCX_TEST_BROWSER_CHANNEL`, [T1. Test Configuration](T1-test-configuration.md)) for a person to watch. Checks on codes compare the code alone (for example a line's `programCode` code with the adapter's programme code), never a `(code, display)` tuple.

**The report.** Both runners write into `NHCX_TEST_REPORT`, one entry per test and runner:

```json
{
  "run_at": "<ISO time>",
  "config": {"irdai_payer": "", "irdai_member": "", "pmjay_payer": "", "pmjay_member": "set | missing"},
  "setup_checks": [{"check": "session token", "result": "pass | fail", "detail": ""}],
  "tests": [
    {
      "id": "T5", "runner": "gui | cli",
      "claim": "", "correlation_ids": [], "ledger_ids": [], "decisions": [],
      "steps": [{"at": "", "what": "", "result": "pass | fail", "got": ""}],
      "result": "pass | fail | blocked | skipped",
      "cause": "ours | sandbox | setup", "detail": "", "attempts": 1
    }
  ],
  "summary": {"pass": 0, "fail": 0, "blocked": 0, "skipped": 0}
}
```

**Triage.** A failure is ours (fix, then re-run the test), the sandbox's (retry, then report), or setup (back to the setup checks). At most 3 attempts per test and runner.
