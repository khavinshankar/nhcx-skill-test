# Fix local claims list HTTP 500

Date: 2026-10-13 (Asia/Kolkata)

## Request and finding

The facility claims endpoint for `95deeee5-a4e6-4ab3-8401-13018f45c121`, with `limit=20&offset=0`, returned HTTP 500. Backend logs showed `ProgrammingError: column nhcx_claim.beneficiary_member_id does not exist`.

The running `care-nhcx-backend` mounts the `nhcx-integration` worktree at `/Users/khavinshankar/.copilot/repos/copilot-worktrees/nhcx/khavinshankar-silver-sniffle/care`, whose HEAD was `53d6d332f`. Its existing migration `0003_claim_beneficiary_member_id` was unapplied. It adds a nullable, optional character field, so applying the existing migration corrects the schema without changing application code.

## Action and validation

- Ran `docker exec care-nhcx-backend python manage.py migrate nhcx --noinput`: `nhcx.0003_claim_beneficiary_member_id... OK`.
- Requested the exact route through Django's authenticated APIClient against the local database as user 1 (the user ID seen in the failing request logs): HTTP 200, count 105, 20 results returned. Only status and counts were printed. This verifies the application route and database; it was not a browser-session test.
- No source files changed in any child repository; no child commit was needed. Only this parent task record is committed. Nothing pushed.

## Outcome and open items

The local claims endpoint is fixed; refresh the Claims page. No restart is required for this database migration. No remaining blocker for the reported error.

`entire status` reported capture enabled but seven Codex hooks requiring approval. Transcript/checkpoint capture is therefore not confirmed, and no session ID is claimed.
