# T1. Test Configuration

#### T1D. DESCRIPTION

Every end-to-end test reads one configuration, and nothing in a test hard-codes a participant code, a member id, a URL or a credential (CORE instruction 3 and 9). The configuration is read from the environment, with a file as a fallback: `tests/nhcx/e2e/config.example.env` is committed with every variable and no secret, and a `tests/nhcx/e2e/.env` beside it (ignored by version control) holds the real values.

**The hospital's side is fixed.** The tests drive the sandbox provider EMR through [A18. Provider Driver](../apis/A18-provider-driver.md). It is not a setting and has no variable: its screens are at `https://nhcxai.abdm.gov.in/uat/`, its API at `https://nhcxai.abdm.gov.in/api/provider`. It is signed in to only by token login, with this payer's own ABDM session token ([G3. Session Token](../gateway/G3-session-token.md)): there is no username, password or account to configure or ask for [SANDBOX](../references/PAYERS.md#markers).

**Asked from the integrator.** One value only the integrator has: the facility participant code the sandbox provider EMR sends as, which must be a participant whose registry `endpoint_url` points at that EMR. Before the first test, ask the integrator for it when it is unset, and write the answer into `tests/nhcx/e2e/.env`. Never guess it and never take it from an example. Without it every test from T3 on is `blocked` with that reason.

**Members are seeded here, not asked for.** Each test registers its own member and enrolment on this payer's desk ([S4. Members](../screens/S4-members.md), [S5. Subscriptions](../screens/S5-subscriptions.md)) under a prefix, so the hospital's search finds cover this payer knows and no test depends on another's data. The member's ABHA number is minted from the prefix and the test id; it is a sandbox convenience, not a real number [SANDBOX](../references/PAYERS.md#markers).

#### T1S. SETUP

| Variable | Meaning | Default |
|---|---|---|
| `NHCX_PAYER_TEST_MODE` | `gui`, `cli` or `both`: which runner the command starts. | `both` |
| `NHCX_PAYER_TEST_ONLY` | Comma-separated test ids to run (`T6,T7`), or a group (`preauth`, `claim`). | every test |
| `NHCX_PAYER_TEST_APP_URL` | Where the desk is served, for the GUI runner. | none: GUI tests are `blocked` without it |
| `NHCX_PAYER_TEST_USER`, `NHCX_PAYER_TEST_PASSWORD` | A desk account that may decide cases and release payments (admin, or one adjudicator and one finance account), for the GUI runner and, where the CLI needs a session, for the CLI runner. | none |
| `NHCX_PAYER_TEST_FACILITY` | The facility participant code the sandbox provider EMR sends as. | none: asked from the integrator |
| `NHCX_PAYER_TEST_MEMBER_PREFIX` | The prefix of the member ids the tests seed on this payer. | `E2E-` |
| `NHCX_PAYER_TEST_WAIT_SECONDS` | How long a step waits for a message to reach this payer, or for the hospital's side to show the answer, before it fails. | `120` |
| `NHCX_PAYER_TEST_POLL_AFTER_SECONDS` | How long a step waits for a callback the payer is expecting (a query reply, a payment acknowledgement) before it also polls the ledger ([A11. Transaction Related](../apis/A11-txn-related.md)). | `30` |
| `NHCX_PAYER_TEST_REPORT` | Where the run is written. | `nhcx-plan/e2e.json` |

This payer's own participant code, client id and secret, private key and public URL are the application's configuration, not the tests': the tests use whatever the application runs with, and [T2. Test Runners](T2-test-runners.md) checks them before the first test.

#### T1G. GUI

The GUI runner reads the same variables. It signs in to `NHCX_PAYER_TEST_APP_URL` with `NHCX_PAYER_TEST_USER` and `NHCX_PAYER_TEST_PASSWORD` through the desk's own login screen, never by planting a session, so the sign-in itself is under test.

#### T1L. CLI

The CLI runner reads the same variables and takes three flags that override them for one run: `--only <ids or group>`, `--mode cli|gui|both` and `--report <path>`. `list` prints every test with the group it belongs to and whether its configuration is complete; `check` prints the resolved configuration with every secret shown as `set` or `missing`, never its value, and names the integrator value still missing.

#### T1X. EXPECT

- A variable that is unset and has no default blocks only the tests that need it, and says which variable.
- Nothing asks for or stores a password for the sandbox provider EMR.
- The facility code comes from the integrator, asked once; nothing else is asked for.
- The resolved configuration is written into the report (secrets as `set` or `missing`), so a result can be read against the facility and members it ran with.
- No participant code, member id, URL or credential appears in a test file.
