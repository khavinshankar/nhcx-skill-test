# Generic checkpoint and live-session reports

Date: 2026-10-13 (Asia/Kolkata)
Session: 01a134f3-9946-7563-a447-73465489e8ac

## Request

Fix `checkpoint-report.py --session` assuming a Copilot events.jsonl path for a
Codex session, and make reporting work across agent providers.

## Decisions and rationale

- Yes, the old script was Copilot-specific. It hardcoded the Copilot session
  directory and rejected other transcript formats when rendering checkpoints.
- Registered sessions now use Entire's agent-independent session metadata and
  raw-transcript API. This lets Entire handle provider-specific live storage.
- If Entire has no readable transcript, discover native Copilot, Codex,
  Claude, Cursor JSONL and Factory Droid JSONL logs. Honor CODEX_HOME and
  CLAUDE_CONFIG_DIR and include archived Codex sessions. Ambiguous matches
  require an explicit path rather than silently selecting one.
- Keep Copilot's detailed report unchanged. Add a common report for Codex
  response items, Claude-style message/tool blocks, role/content records and
  OpenCode JSON message/parts exports. Accept JSON documents as well as JSONL.
  Entire-backed discovery is agent-independent; parsing depth depends on the
  schema. Unknown event types are counted, and --raw-events can show the full
  original records. Do not claim rich native parsing for every future format.
- Preserve system/reasoning/result display switches. Do not decode encrypted
  reasoning. Codex event-message mirrors are excluded from conversational
  counts to avoid double counting. Cumulative token counters use the latest
  value instead of summing successive totals.
- Read bounded live snapshots and tolerate only an unterminated partial final
  JSONL record. Malformed complete records fail explicitly. Missing files or
  sessions now produce concise errors with next steps rather than tracebacks.
- Reading a native Codex log does not establish Entire checkpoint capture or
  change hook trust. The user's exact command now works independently of that
  configuration gap.

## Repository changes

Only the parent repository changed: scripts/checkpoint-report.py,
scripts/checkpoint_transcripts.py, scripts/test_checkpoint_report.py,
README.md, .gitignore, and this record. The final commit is the commit
containing this record. No child repository changes or commits; no push.

## Validation

- User's exact Codex session command: passed, with session/model/tool/token
  summary and conversation timeline, using the native rollout log.
- Copilot live session 54642942-8c13-4ae7-a23f-355474803734: passed through
  Entire's live transcript API.
- Copilot checkpoint 9a4c76d6187d: passed; `cmp` confirmed byte-for-byte
  identical output to the pre-change script.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s scripts -p 'test_*.py'`:
  11 tests passed. Coverage includes Codex duplicate suppression/usage,
  visibility flags, Claude tool blocks, OpenCode exports, Copilot regression,
  unknown events/raw view, partial JSONL, Entire API routing, local discovery,
  ambiguous/missing sessions, invalid IDs/JSON, and CLI errors without traceback.
- `git -c core.fsmonitor=false diff --check`: passed.

## Open items and limits

- Codex hook approval remains outstanding; no hook configuration was changed.
- Real local end-to-end checks covered Codex and Copilot. Claude-style and
  OpenCode formats use synthetic regression fixtures. Cursor/Droid native
  discovery and other Entire agents were not tested against real sessions.
- OpenCode or other unsupported native storage layouts require registration
  with Entire or an explicit exported JSON/JSONL path. Unknown formats remain
  inspectable through --raw-events without invented summary metrics.

## Final reply substance

The script was Copilot-specific; it is now agent-aware. Re-run the original
command unchanged. Registered agents use Entire's API; this Codex session is
found directly in native storage. Structured parsing covers Codex, Copilot,
Claude-style and OpenCode export formats, with raw-event fallback for others.
All 11 tests pass and existing Copilot checkpoint output is unchanged.
