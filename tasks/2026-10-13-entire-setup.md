# Enable parent workspace session tracking

Date: 2026-10-13 (Asia/Kolkata)
Session: not recorded (hooks installed during this conversation)

## Request

Track cross-repository AI work centrally in nhcx and enable all agent
integrations supported by the installed Entire version.

## Decisions and rationale

- Keep the four code repositories independent and ignored by the parent.
- Use parent task records to preserve decisions and link child commits.
- Enable Codex, Claude Code, Copilot CLI, Cursor, Factory AI Droid, Gemini CLI,
  and OpenCode through Entire 0.5.5's configuration command.
- Keep checkpoint uploads and telemetry disabled. No parent remote is set.
- Preserve existing child repository configuration and history.

## Repository changes

Only the parent tracking repository was configured. No child code changed.
This record belongs to the parent's initial setup commit.

## Validation

`entire status --detailed` reports enabled with all seven integrations.
Settings confirm `push_sessions: false` and `telemetry: false`.
`git check-ignore` confirms all four child repositories are excluded.

## Open items

Start a fresh supported-agent session from nhcx, accept any hook trust prompt,
complete a task, and inspect its parent commit with `entire explain --commit HEAD`.
Live transcript capture has not yet been verified.
