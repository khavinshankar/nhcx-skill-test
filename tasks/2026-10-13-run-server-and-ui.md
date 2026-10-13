# Run server and UI with plugins

Date: 2026-10-13 (Asia/Kolkata)
Session: f1f2f5ee-39ed-4c11-893a-95c1b8c4cdc0

## Request

"run the server and ui along with plugs"

## What was done

- **Backend:** already running and healthy; left as is. `care-nhcx-backend` (:9000) and `care-nhcx-celery` serve
  the NHCX worktree `khavinshankar-silver-sniffle/care` (branch `nhcx-integration`) with the `care_abdm` plug
  mounted from the main checkout (`ADDITIONAL_PLUGS`, `PYTHONPATH=/app/care_abdm`). DB, redis and minio
  containers are up.
- **Plugin FE:** `care_abdm_fe` (main checkout, `develop`) runs with `npm start` (vite build --watch plus preview) on :5173.
  `remoteEntry.js` returns 200.
- **UI:** `care_fe` from the same NHCX worktree (`nhcx-integration`) runs with `npm run dev` on :4000, so the UI matches the backend.
  The gitignored `.env.local` was copied from the main `care_fe` into it:
  `REACT_CARE_API_URL=http://localhost:9000`, `REACT_ENABLED_APPS="ohcnetwork/care_abdm_fe@localhost:5173"`.
  The main `care_fe` checkout has no `node_modules`.
- Both FE servers are detached background processes started by this session.

## Validation

- `curl` returned 200 from :4000 and :5173, and from :5173/assets/remoteEntry.js.
- `/api/v1/` returned 403 without auth, which is expected, and `/ping/` returned 200.

## Open items

- None in any repository; no code changed. To stop the FE servers, kill the vite processes on :4000 and :5173.
