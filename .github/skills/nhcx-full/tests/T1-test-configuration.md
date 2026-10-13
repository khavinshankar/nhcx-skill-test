# T1. Test Configuration

#### T1D. DESCRIPTION

Every end-to-end test reads one configuration, and nothing in a test hard-codes a participant code, a member id, a URL or a credential (CORE instruction 3 and 9). The configuration is read from the environment, with a file as a fallback: `tests/nhcx/e2e/config.example.env` is committed with every variable and no secret, and a `tests/nhcx/e2e/.env` beside it (ignored by version control) holds the real values.

The two test payers and their defaults are the table in [PAYERS.md](../references/PAYERS.md#test-participants). A default applies only when its variable is unset.

**No passwords for the payer side.** The IRDAI payer desk is fixed and is signed in to by token login with the facility's own ABDM session token ([A14. Adjudicator User Role](../apis/A14-adjudicator-user-role.md)); the NHCX Payer Service takes the same token. Nothing about either desk is configured or asked for.

**Asked from the integrator.** The PMJAY tests (T13 to T18) need one value only the integrator has: a PMJAY beneficiary's member id the sandbox knows. Before the first PMJAY test, ask the integrator for it when it is unset, and write the answer into `tests/nhcx/e2e/.env`. Never guess it, never take it from an example or another test, and never reuse the IRDAI beneficiary. Without it every PMJAY test is `blocked` with that reason; the IRDAI tests still run. The beneficiary's ABHA number comes back from the registry with the policy, and the facility's HFR id is the one on its own record ([D1. organization](../database/D1-organization.md)): neither is asked for.

**The PMJAY package master is requested, not waited for.** PMJAY answers a plan request in 15 to 60 minutes, or not at all within a session, and refuses a second request meanwhile ([PAYERS.md](../references/PAYERS.md#test-participants)) [SANDBOX](../references/PAYERS.md#markers). The tests send the request once, note its correlation id, and go on with a seeded package master (`NHCX_TEST_PMJAY_PLAN_SEED`, [T13. PMJAY Eligibility, Package Master and Ruling](T13-pmjay-eligibility-and-package-master.md)) so nothing waits on it. Whenever the real plan does arrive ([C4. Insurance Plan Reply](../callbacks/C4-insuranceplan-on-request.md)) it replaces the seed for that claim, and later tests use it.

#### T1S. SETUP

| Variable | Meaning | Default |
|---|---|---|
| `NHCX_TEST_MODE` | `gui`, `cli` or `both`: which runner the command starts. | `both` |
| `NHCX_TEST_ONLY` | Comma-separated test ids to run (`T5,T6`), or a payer (`irdai`, `pmjay`). | every test |
| `NHCX_TEST_APP_URL` | Where the HMIS is served, for the GUI runner. | none: GUI tests are `blocked` without it |
| `NHCX_TEST_USER`, `NHCX_TEST_PASSWORD` | An HMIS account allowed to open claims, for the GUI runner and, where the CLI needs a session, for the CLI runner. In a facility-scoped HMIS this is a user holding a role **at the test facility**: a superuser with no facility role is answered 403 by the claim routes. | none |
| `NHCX_TEST_FACILITY` | The facility the claims are raised at, in a facility-scoped HMIS (its id or external id). | none: `blocked` in a facility-scoped target |
| `NHCX_TEST_DOCTOR` | A practitioner at that facility with an HPR id, for the care team ([D2. practitioner](../database/D2-practitioner.md)). | none: the runner picks the first practitioner with an HPR id, else `blocked` |
| `NHCX_TEST_DIAGNOSIS` | The ICD-10 code the pre-authorisation quotes. | the first `diagnosis` concept with an ICD-10 code ([D8. terminology](../database/D8-terminology.md)) |
| `NHCX_TEST_PMJAY_MANUAL_PACKAGE` | A seeded PMJAY package the sandbox does **not** decide by itself, for the tests that need the desk to query or reject ([T15. PMJAY Query Answered by Resubmission](T15-pmjay-query-by-resubmission.md), [T16. PMJAY Rejection and Enhancement](T16-pmjay-rejection-and-enhancement.md)); the sandbox auto-approves `SB043F` [SANDBOX](../references/PAYERS.md#markers). | none: those tests are `blocked (sandbox)` |
| `NHCX_TEST_SLOWMO_MS` | Milliseconds to pause between GUI actions, for a person watching a headed run. | `0` |
| `NHCX_TEST_BROWSER_CHANNEL` | The browser channel the GUI runner launches (`chromium`, `chrome`, `msedge`). | `chromium` |
| `NHCX_TEST_IRDAI_PAYER` | The IRDAI test payer's participant code. | PAYERS.md |
| `NHCX_TEST_IRDAI_MEMBER_ID` | The IRDAI test beneficiary's member id. | PAYERS.md |
| `NHCX_TEST_PMJAY_PAYER` | The PMJAY test payer's participant code. | PAYERS.md |
| `NHCX_TEST_PMJAY_MEMBER_ID` | A PMJAY beneficiary the sandbox knows. | none: asked from the integrator |
| `NHCX_TEST_PMJAY_PLAN_SEED` | The package master the PMJAY tests run on while the real one has not arrived: a file of packages in the shape [T13. PMJAY Eligibility, Package Master and Ruling](T13-pmjay-eligibility-and-package-master.md) gives. | `tests/nhcx/e2e/fixtures/pmjay-plan.json` |
| `NHCX_TEST_PLAN_WAIT_SECONDS` | How long [T4. IRDAI Insurance Plan and Authorisation Requirements](T4-irdai-plan-and-auth-requirements.md) waits for the IRDAI plan (the IRDAI test payer answers in seconds). The PMJAY plan is never waited for. | `120` |
| `NHCX_TEST_PMJAY_SERVICE_TOKEN` | Bearer token for the NHCX Payer Service. | the facility's own session token ([A16. Gateway Token](../apis/A16-gateway-token.md)) |
| `NHCX_TEST_WAIT_SECONDS` | How long a step waits for the payer's answer before it fails. | `120` |
| `NHCX_TEST_POLL_AFTER_SECONDS` | How long a step waits for the callback before it also polls the ledger (A10 to A13). | `30` |
| `NHCX_TEST_REPORT` | Where the run is written. | `nhcx-plan/e2e.json` |

The facility's own participant code, client id and secret, private key and public URL are the application's configuration, not the tests': the tests use whatever the application runs with, and [T2. Test Runners](T2-test-runners.md) checks them before the first test.

#### T1G. GUI

The GUI runner reads the same variables. It signs in to `NHCX_TEST_APP_URL` with `NHCX_TEST_USER` and `NHCX_TEST_PASSWORD` through the HMIS's own login screen, never by planting a session, so the sign-in itself is under test.

#### T1L. CLI

The CLI runner reads the same variables and takes three flags that override them for one run: `--only <ids or payer>`, `--mode cli|gui|both` and `--report <path>`. `list` prints every test with the payer it runs against and whether its configuration is complete; `check` prints the resolved configuration with every secret shown as `set` or `missing`, never its value, and lists the integrator values still missing.

#### T1X. EXPECT

- A variable that is unset and has no default blocks only the tests that need it, and says which variable.
- Nothing asks for or stores a password for either payer desk.
- The PMJAY member id comes from the integrator, asked once; nothing else is asked for.
- The resolved configuration is written into the report (secrets as `set` or `missing`), so a result can be read against the payer and member it ran with.
- No participant code, member id, URL or credential appears in a test file.
