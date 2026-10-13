# Fix insurance-plan fetch backend crash

Date: 2026-10-13 (Asia/Kolkata)
Session: 01a13514-4be6-7a81-8333-139b13be13b5

## Request and findings

User reported that fetching an insurance plan takes down the backend and produces a network error. Docker confirmed care-nhcx-backend exited at 17:14:35 IST with OOMKilled=true and exit code 247. SQL-printing logs stopped during cached plan reuse for claim database ID 105. The active startup script enabled runserver_plus --print-sql in both normal and debugger modes. Earlier investigation had already reproduced memory exhaustion while pretty-printing SQL containing the approximately 33 MB plan JSON.

## Fix and rationale

Removed --print-sql in both startup branches and documented why: formatting large JSON INSERT/UPDATE statements exhausts development-container memory. Restarted the existing container with the patched mounted script. This preserves application behavior and removes the expensive development logging. No database schema or plan-storage changes. Unrelated edits in the active worktree and the parent's existing PROGRESS.md deletion were preserved.

Affected repository: care, nhcx-integration worktree at /Users/khavinshankar/.copilot/repos/copilot-worktrees/nhcx/khavinshankar-silver-sniffle/care.
Final code commit: d5fe6e7239a4e9c8e06643349967f0dce1806285.
The child hook omitted the session trailer; the verified session ID was explicitly added to the commit. Entire status reported enabled and this session active; commit success alone is not proof of capture. No push.

## Validation and result

- bash -n scripts/start-dev.sh and scoped git diff --check passed.
- Container process list confirms both runserver processes run without --print-sql.
- Retried the affected claim's real HTTP POST plan endpoint using a short-lived local admin token, after confirming a cached ready plan exists. No token was printed. The request reused the cached plan and did not need an outbound payer request.
- HTTP 200 in 4.13 seconds; resulting plan ready with 2543 benefits and 15 forms.
- Post-fetch /ping/ returned HTTP 200 and {"status": "OK"}.
- Backend memory approximately 613.7 MiB of 3.825 GiB after fetch; Running=true and OOMKilled=false.

Final reply: Fixed the backend crash caused by SQL pretty-printing of the large insurance-plan JSON. Backend restarted; the previously failing fetch now succeeds and its plan is ready. Refresh the UI and continue.

## Limits / open items

No browser click-through or new external payer callback was exercised. Existing duplication of large plan JSON remains a separate storage/memory optimization. This fix addresses the reproduced development-server crash; no broad test suite was needed for removing a startup logging flag.
