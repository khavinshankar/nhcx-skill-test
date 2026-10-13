# CARE NHCX integration (provider side, full)

Date: 2026-10-13 (Asia/Kolkata)
Session: b76b6c16-5c3f-467f-98f4-30325eb3c0d1

## Request

"Do a full NHCX integration for CARE HMIS". Follow-ups:
- "update the registry with this url; and test out the flows".
- The integrator gave sandbox participant `1000004455@hcx`, the ABDM client from the env, the backend domain as the public URL, the encryption private key, and PMJAY member `SBXSTG007`.

## Decisions and rationale

- **Skill and side:** followed `.github/skills/nhcx-full` v1.4.0 (L1–L8), provider side. Plan files are in `care/nhcx-plan/`, and the report is `care/nhcx-plan/report.html`.
- **Where the code lives:** in CARE core, at the user's choice. The backend is the Django app `care.nhcx`; the screens are in `care_fe`. No plugin.
- **Existing CARE modules stay intact:** NHCX data sits in one-to-one extension tables (facility and practitioner NHCX profiles), and ABHA is stored as a `PatientIdentifier`.
- **Gateway inside the app:** the gateway runs in-process. Inbound routes are `/in/<path>`, `/v1/<path>` and `/api/gateway/`. The facility API is `/api/v1/facility/<id>/nhcx/`, and global routes are `/api/v1/nhcx/`. Sends happen outside DB transactions, because CARE sets `ATOMIC_REQUESTS`. Celery tasks refresh tokens and prune the ledger only when `NHCX_ROLE` is set.
- **Tests:** unit and dry-run tests are in `care/nhcx/tests/`. A loopback-only network guard scoped to `care.nhcx` keeps them off the network, and NHCX is pinned off in the test settings.
- **E2E harness:**
  - CLI: `manage.py nhcx_e2e`.
  - GUI: a Playwright runner in `care_fe/tests/nhcx`.
  - Host wrapper: `care/scripts/nhcx-e2e.sh`.
- **Secrets stay outside every repo:** the key, gateway config, cleaned env, ledger and archive are in `~/.nhcx/sandbox/` (mode 600/700), along with the launcher `run-worktree.sh`. The e2e `.env` is gitignored. The private key was pasted into chat, so this transcript contains it; rotate it if it is more than a throwaway sandbox key.
- **Dev environment (user approved):**
  - `care-backend-1` and `care-celery-1` are stopped. `care-nhcx-backend` and `care-nhcx-celery` serve this worktree on :9000.
  - The `nhcx` 0001 and 0002 migrations are applied to the dev DB.
  - `docker run --env-file` kept the quotes in `.env`, which broke the ABDM session call; it now uses a quote-stripped copy.
- **Registry (user approved):** `endpoint_url` for `1000004455@hcx` was changed from `https://api.staging.ohc.network/api/nhcx` to `https://9k-personal.khavinshankar.dev/in` with `/participant/update`. Callbacks for this participant no longer reach staging.
- **Departure from the skill:** query answers are now sent as `request.initiated`, following the nhcx-docs flows. CORE.md:90 says `response.complete`, but NHCX refused that with NHCX-1011.
- **Other gaps and departures, recorded in the plan files:**
  - Seven user messages were written where the spec gave none.
  - Uncertain points: which encounter fields the biometric `stage_for` reads, the source of the adjudicator's IRDAI case number, and the identifier-type system URL.
  - Frontend: ABHA values are sent to the server in plain text and encrypted there. Gender "Other" is left blank.
  - G8 spec conflict on recording an unmatched delivery: the code records it.

## Repository changes

| Repository | Final commit | Changes |
| --- | --- | --- |
| care (branch nhcx-integration) | 98f0b3389, 5be8fd0e8, b83705220, 2e17717bc, 4d9be7ffb | Models, migrations, gateway, FHIR, services, callbacks, API, settings and URLs; L6 fixes; L7 dry-run and isolation tests; e2e harness and sandbox fixes; `nhcx-plan/` |
| care_fe (branch nhcx-integration) | 6b18d4fb9, 46077c631 | Claims screens S1–S12 and S17–S18, Claims nav, ABHA and practitioner additions (S13–S16), Playwright GUI e2e runner |

## Validation

- **Unit and dry-run:** `manage.py test care.nhcx` passes all 282 tests. These include S1–S12 dry flows (IRDAI and PMJAY) that run the real gateway crypto against a fake NHCX. ruff is clean.
- **Frontend:** `tsc --noEmit`, eslint and prettier are clean. Some screens are covered only by these checks and the GUI runs below.
- **L6:** all 189 files have a validation entry: 178 passed, 11 fixed, 0 failed.
- **L8 setup (G11):** the session token, participant record, certificate match, and probe through the registered public endpoint all pass.
- **L8 results against the live sandbox (CLI / GUI):**
  - T3, T4, T5 and T13 pass in both.
  - T6–T11, T18 and T19 pass in CLI; their GUI walks are not written yet (skipped).
  - T14 passes in CLI and is blocked in GUI (PMJAY wallet, PAYR-1235).
  - T12 is blocked: the IRDAI member's cover is used up.
  - T15 is blocked: the sandbox auto-approves SB043F, so it needs `NHCX_TEST_PMJAY_MANUAL_PACKAGE`.
  - T17 is blocked: a payer-desk 500 on the query path, then the wallet ran out. Its approve path passed.
  - T16 **fails, on our side**: a claim line holds one row per code (D16), but PMJAY wants a new item per cycle (PAYR-1274).
  - Totals: 17 pass, 1 fail, 4 blocked, 12 skipped. Details are in `care/nhcx-plan/e2e.json`.

## Open items

- Fix T16: allow a new claim item per cycle for PMJAY enhancement.
- Confirm the `request.initiated` change for query answers against the sandbox once the PMJAY wallet is topped up.
- Write the GUI walks for T6–T12 and T15–T19.
- Re-run the blocked tests once the wallet, the member's cover and a manual package are available.
- The L8 exit is not checked.
- Restore the dev environment when done: `docker rm -f care-nhcx-backend care-nhcx-celery && docker start care-celery-1 care-backend-1`. Decide whether the registry `endpoint_url` should go back to staging.
- Nothing is pushed.
