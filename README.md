# NHCX workspace tracking

This Git repository is the central task journal for four independent code
repositories: `care`, `care/care_abdm`, `care_fe`, and `care_abdm_fe`.
Their directories are ignored here. Code history remains in those repositories;
task records link their final commit IDs to workspace-wide decisions.

## Setup status

The parent Git repository has Entire 0.5.5 enabled for all seven integrations
supported by this installed version: Codex, Claude Code, GitHub Copilot CLI,
Cursor, Factory AI Droid, Gemini CLI, and OpenCode. These are agent integrations,
not model-provider integrations; capture depends on using a supported agent.
Existing child repository settings have not been changed; `care_fe` still has
its original Entire configuration.

To check configuration from a terminal:

```sh
cd /Users/khavinshankar/Documents/egov/nhcx
entire status --detailed
```

Review and trust the generated hooks in your agent if prompted, then start a
fresh session from this folder. Agent applications must be installed separately
and have `entire` on their PATH. Checkpoint uploads and telemetry are disabled.
No remote or backup destination has been configured for the parent.

## Workflow

After a completed coding task, commit the relevant changes in each affected
repository, write a task record here using `tasks/TEMPLATE.md`, and commit that
record. Existing changes unrelated to the task must not be included.

With hooks working, verify the parent commit's session association:

```sh
entire status
entire explain --commit HEAD
```

These commands match the installed Entire 0.5.5. End-to-end capture has not yet
been verified. Parent checkpoints do not contain child repository source
snapshots; use the linked child commits to inspect or restore code.
