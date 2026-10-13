# Entire capture fix and ABDM setup

Date: 2026-10-13 (Asia/Kolkata)
Session: bb890db5-0a1c-4465-b823-1c916088212b (GitHub Copilot app)

## Request

Configure ABDM correctly before starting the NHCX integration, covering both the
agent tooling and the care_abdm sandbox configuration. Make sure every AI chat,
its reasoning and its decisions are stored as Entire checkpoints.

## Decisions and rationale

- **Entire capture.** Copilot app sessions recorded hook events, but no events
  reached Entire because the repository's `.github/hooks/entire.json` hooks
  did not run. With the user's approval the same hooks were copied to
  `~/.copilot/hooks/entire.json`, which fires in every Copilot session. Entire
  does nothing in repositories where it is not enabled.
- **Git index.** `feature.manyFiles=true` turns on `index.skipHash`, so Git
  wrote the index without a checksum and Entire failed with "index decoder:
  invalid checksum". The fix was `git config index.skipHash false` in the
  parent repository's local config, then an index rewrite.
- **Reasoning capture.** The Copilot transcript contains messages, tool calls
  and results, and the reasoning summaries the app records. Entire stores
  that transcript. Nothing beyond what the app records is captured.
- **ABDM agent tooling.** ABDM has no agent-setup page like NHCX's. The user
  chose to install all 13 skills from `nha-in/docs`
  `plugins/abdm-integrators-assistant` (commit 446281e, skills version 0.10.0)
  into `.github/skills`. The `abdm-docs` and `nhcx-docs` MCP servers were
  already registered in `~/.copilot/mcp-config.json`; both point at the same
  URL.
- **care_abdm config (Docker).** No tracked files were changed. care's README
  says the `plug_config.py` change must not be committed, so the plugin is
  loaded through `ADDITIONAL_PLUGS` instead.
  - `care/docker-compose.abdm.local.yaml` (local-only, listed in care's
    `.git/info/exclude`) sets the plugin's build arg, its runtime env and
    `PYTHONPATH=/app/care_abdm` so edits to the mounted source take effect
    live. It also loads `care/.env` into the backend and celery containers.
  - `care/.env` (gitignored): the user added the client ID, secret and
    `BACKEND_DOMAIN`. Non-secret sandbox URLs were then appended, checked
    against docs.abdm.gov.in: gateway `https://dev.abdm.gov.in/api/hiecm`,
    `X-CM-ID: sbx`.
  - `care_fe/.env.local` (gitignored): `REACT_CARE_API_URL=http://localhost:9000`
    and `REACT_ENABLED_APPS="ohcnetwork/care_abdm_fe@localhost:5173"`.
- **Bridge URL.** The credentials belong to the shared bridge `SBX_000224`
  ("CoronaSafe Network"). The user confirmed authority to change it, and the
  bridge URL was moved from `https://api.staging.ohc.network/api/abdm` to
  `https://9k-personal.khavinshankar.dev/api/abdm`. To roll back, PATCH the
  old URL.

## Repository changes

| Repository | Final commit | Changes |
| --- | --- | --- |
| . (parent) | this commit | 13 ABDM skills in `.github/skills`; README capture notes; this record |
| care | uncommitted (local-only files) | `.env`, `docker-compose.abdm.local.yaml`, `.git/info/exclude` |
| care/care_abdm | none | unchanged at b2b4250 |
| care_fe | uncommitted (local-only file) | `.env.local` |
| care_abdm_fe | none | unchanged at d77e05a; `node_modules`/`dist` from a validation build |

Outside the repositories: `~/.copilot/hooks/entire.json` was added, and the
parent Git config gained `index.skipHash=false`.

## Validation

- A fresh `copilot -p` session from this folder logged session-start,
  turn-start, turn-end and session-end in Entire, each once, with no index
  error.
- The index trailer is a real SHA instead of zeros.
- `make build` / `make up` with the override: the `abdm-0.2.0` plugin was
  installed and all five services were healthy.
- In the container, `abdm` loads from `/app/care_abdm`, the app is installed,
  migrations `0001`–`0002` are applied and nothing is pending.
- `POST /gateway/v3/sessions` with the user's credentials returned 200 with
  `expiresIn` 1200. The plugin's `Request.auth_header()` fetched and cached
  the token. The first attempt returned `None` once and could not be
  reproduced.
- `PATCH /gateway/v3/bridge/url` returned 202, and `bridge-services` now shows
  the new URL with `active=true`.
- A public POST to `<BACKEND_DOMAIN>/api/abdm/api/v3/hip/token/on-generate-token`
  reached the local backend, which returned 401 for an unsigned call, as
  expected.
- `care_abdm_fe`: `npm ci && npm run build` succeeded; the regenerated
  `public/version.json` was reverted.
- Not tested: a full ABDM flow with a real signed callback; care_fe was not
  installed or run.

## Open items

- Start the frontends with `care_abdm_fe: npm run start`, then
  `care_fe: npm run setup && npm install && npm run dev`.
- The dev Dockerfile runs `COPY .`, so `care/.env` is copied into the local
  `care_local` image. Do not push that image.
- OHC staging no longer receives callbacks for `SBX_000224` until the bridge
  URL is restored.
- The `nhcx-docs` and `abdm-docs` MCP entries are duplicates; one can be
  removed.
- Run care with
  `make up docker_config_file="docker-compose.local.yaml -f docker-compose.abdm.local.yaml"`.
