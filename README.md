# NHCX workspace tracking

This Git repository is the central task journal for four independent code
repositories: `care`, `care/care_abdm`, `care_fe`, and `care_abdm_fe`.
Their directories are ignored here. Code history remains in those repositories;
task records link their final commit IDs to workspace-wide decisions.

## Review this skill-assisted implementation

Start with [findings.md](findings.md): 13 human-tested observations, with documented fixes separated from unresolved gaps. The [original implementation task](tasks/2026-10-13-care-nhcx-integration.md) records the request, skill, commits and test results. The skill itself is [.github/skills/nhcx-full/SKILL.md](.github/skills/nhcx-full/SKILL.md).

All four code repositories are published as branches in this same GitHub repository, preserving their independent histories. This avoids gitlinks to unavailable repositories and keeps the parent as a task journal. The exact commits are pinned in [review/repositories.json](review/repositories.json).

| Local directory | GitHub branch |
| --- | --- |
| `care` | [repos/care](https://github.com/khavinshankar/nhcx-skill-test/tree/repos/care) |
| `care/care_abdm` | [repos/care-abdm](https://github.com/khavinshankar/nhcx-skill-test/tree/repos/care-abdm) |
| `care_fe` | [repos/care-fe](https://github.com/khavinshankar/nhcx-skill-test/tree/repos/care-fe) |
| `care_abdm_fe` | [repos/care-abdm-fe](https://github.com/khavinshankar/nhcx-skill-test/tree/repos/care-abdm-fe) |

From a fresh clone:

```sh
git clone https://github.com/khavinshankar/nhcx-skill-test.git
cd nhcx-skill-test
python3 scripts/checkout-review-repos.py
python3 scripts/checkpoint-report.py --session 01a134f3-9946-7563-a447-73465489e8ac
```

The report command needs only Python 3 and Git. Its fixed transcript export is included under `review/sessions/`, so it does not require Entire or access to the author's home directory. The export takes precedence over live lookup for that session. **That session concerns checkpoint storage/report tooling; it is not the original NHCX implementation session.**

To inspect the original implementation transcript, fetch the checkpoint branch and render its checkpoint:

```sh
git fetch origin entire/checkpoints/v1:refs/heads/entire/checkpoints/v1
python3 scripts/checkpoint-report.py 2ed3e27169ce
# Optional: include captured tool results.
python3 scripts/checkpoint-report.py 2ed3e27169ce --results
```

Original implementation session: `b76b6c16-5c3f-467f-98f4-30325eb3c0d1`. The code branches contain subsequent fixes too; use the original task's commit IDs to distinguish the initial implementation from repairs. Transcripts are recorded evidence with capture limits, not proof that every step was captured or that all workflows passed.

[Uncommitted beneficiary-selection patches](review/wip/README.md) preserve work in progress separately from committed code. They are not applied by the checkout script. Ignored runtime secrets, databases and installed dependencies are excluded; configure the applications using their own documentation to run them.

## Setup status

The parent Git repository has Entire 0.11.4 enabled for Codex, Claude Code,
GitHub Copilot CLI, Cursor, Factory AI Droid and OpenCode. Entire 0.11 dropped
Gemini CLI, so its hooks were removed. These are agent integrations, not
model-provider integrations; capture depends on using a supported agent.
Automatic checkpoint uploads and telemetry are disabled. This review repository
is published explicitly to `khavinshankar/nhcx-skill-test`.

To check configuration from a terminal:

```sh
cd /Users/khavinshankar/Documents/egov/nhcx
entire status
entire doctor
```

Agent applications must be installed separately and have `entire` on their
PATH.

## How checkpoints are tracked across repositories

The parent repository is the only checkpoint store. Entire keeps all
checkpoint data (full agent transcripts, prompts, tool calls and results,
recorded reasoning summaries, and touched files) on the parent's
`entire/checkpoints/v1` branch. It attaches a checkpoint to a commit
through an `Entire-Checkpoint` trailer.

- Start agent sessions from this parent folder or one of its worktrees. Entire
  links a session only to commits in the repository where the session started.
  A commit in a child repository never gets its own checkpoint; this was
  tested with Entire 0.11.4, including with Entire enabled in the child.
- Each task ends with a parent commit (the task record), and that commit
  carries the checkpoint. The checkpoint transcript covers everything the
  agent did in every child repository.
- Child repositories have a local `prepare-commit-msg` hook that adds
  `Entire-Session: <session id>` to commits made from an agent session, and
  `Entire-Subagent: <id>` when a Copilot subagent made the commit. Install
  or reinstall it with `scripts/install-child-entire-hooks.sh`. Commits made
  outside an agent session get no trailer. For Copilot the hook finds the
  top-level session from the `inuse.<pid>.lock` that Copilot holds in
  `~/.copilot/session-state/<id>/`. It does not use `entire session current`
  for Copilot: that resolves by process ancestry and can return a subagent or
  the app's title-generator session, which share the Copilot process.
- Entire checkpoints a session only at a parent commit, and only up to that
  commit. Turns after a session's last parent commit are never checkpointed,
  so every prompt ends with a task-record commit (see `AGENTS.md`).
- `care_fe` tracks its own upstream Entire settings, which push to
  `ohcnetwork/care_fe-checkpoints`. Entire is not installed in that checkout,
  so nothing is captured or pushed there. Do not run `entire enable` in
  `care_fe` unless upstream capture is intended.

### Viewing checkpoints

Entire 0.11 replaced `entire explain` with `entire checkpoint ...`. Listing is
scoped to the current branch. Copilot app sessions commit on their own worktree
branches, so the parent `post-commit` hook runs `scripts/ff-main.sh` after
Entire's step. It fast-forwards `main` to each new commit, which makes the
checkpoint appear in `entire checkpoint list` on `main`.

- The hook never merges, rebases or pushes. It skips with a warning when
  `main` has commits the branch lacks (such as a parallel session's work) or
  when the main checkout has uncommitted tracked changes. Merge those branches
  manually without squashing or rebasing, so the `Entire-Checkpoint` trailers
  stay on `main`.
- Install the hook with `scripts/install-parent-hooks.sh`. Rerun it after
  `entire enable` or an Entire upgrade, because those rewrite the hooks.
- Disable it with `git config nhcx.autoFastForwardMain false`.
- This applies only to the parent repository. Child repositories have no
  checkpoints.

```sh
entire checkpoint list                      # checkpoints on this branch
entire checkpoint explain <id|commit>       # works from any branch
entire checkpoint explain <id> --full       # full parsed transcript
entire checkpoint explain <id> --raw-transcript  # raw JSONL, incl. reasoning
entire checkpoint list --session <session-id>
entire session list
git -C care_fe log --grep 'Entire-Session: <session-id>'  # child commits
```

Entire 0.11.4 stores Copilot transcripts in full but cannot display them:
`explain` shows only the first prompt, and `--full` prints "failed to parse
transcript". That's an Entire bug, still present upstream at `4203b3d`
(2026-10-12). `explain --full` sends Copilot's raw event log to the
Claude-format parser. Entire's Copilot compactor (`transcript/compact/copilot.go`)
would parse it, but the display path never calls it. The user chose not to
build a patched binary. Claude Code and the other agents render normally. For Copilot
checkpoints, use the report script, which reads the same data from
`entire/checkpoints/v1`:

```sh
scripts/checkpoint-report.py <id|commit>                  # summary + timeline
scripts/checkpoint-report.py <id> --reasoning --results   # plus reasoning and tool output
scripts/checkpoint-report.py <id> --system                # plus system prompt and instructions
scripts/checkpoint-report.py --session <session-id>       # live log, incl. uncommitted turns
```

The report now accepts all agents through Entire's
`entire session info <id> --transcript` API. If Entire has not registered a
session, it searches native Copilot, Codex (including archived sessions),
Claude Code, Cursor JSONL and Factory Droid JSONL locations. Codex discovery
honors `CODEX_HOME`; Claude discovery honors `CLAUDE_CONFIG_DIR`. OpenCode and
other storage layouts use Entire's API or an explicit JSON/JSONL export:

```sh
python3 scripts/checkpoint-report.py --session <codex-or-other-agent-session-id>
python3 scripts/checkpoint-report.py --transcript /absolute/path/to/transcript.jsonl
python3 scripts/checkpoint-report.py --transcript /absolute/path/to/opencode-export.json
```

Copilot keeps its detailed report. Codex responses/tool calls, Claude-style
message blocks (also used by other agents), role/content messages and OpenCode
message/parts exports get a common report. Provider-specific metrics are shown
only when parsed from the log; unsupported event types are counted explicitly.
Use `--raw-events` to include all original records, including instructions,
recorded reasoning and tool results. This is a fallback view, not a promise of
equally detailed parsing for every agent/version. Live discovery does not
register a session with Entire or prove a checkpoint exists. Missing sessions
produce an actionable error instead of a Python traceback.

The detailed Copilot report lists the models and model changes, reasoning effort, premium
requests, skills loaded (with the SKILL.md path), MCP servers used, subagents
with their status and tokens, errors, tool counts and failures, child
repositories referenced, and linked parent and child commits. Its timeline
labels subagent activity and shows each `ask_user` question with the user's
answer. Entire's own Copilot metadata leaves `model` empty, `token_usage` at 0
and `files_touched` null; the report reads these from the transcript instead.

### What a Copilot checkpoint contains (verified 2026-10-13)

`full.jsonl` is Copilot's raw `events.jsonl` from session start up to the
commit. Each checkpoint repeats the whole log, so later checkpoints of a
session lose nothing earlier. It records:

- user prompts, the system prompt with custom instructions (`AGENTS.md`), and
  the available skills and tools
- assistant replies with recorded reasoning text (`reasoningText`), the model
  per reply, model changes and reasoning effort
- every tool call with arguments and result, including `ask_user` questions and
  answers, `sql` todos, and plan files written with `create` or `edit`
- MCP calls, with `mcpServerName` and the MCP tool name
- skill loads (`skill.invoked`, with the SKILL.md path and full content)
- subagents: start, prompt, tool calls, replies, and completion or failure
  with tokens, all tagged with `agentId`
- hook runs, errors, compactions and premium-request usage

Gaps:

- Turns after the last parent commit (see above).
- **Token totals are missing** (`token_usage` is 0). Entire 0.11.4 reads Copilot
  tokens from two places, and neither has data during a session:
  - `session.shutdown` has the session totals, but Copilot writes it only when
    the session closes. That's after the last turn, and Entire doesn't revisit
    checkpoints it has already finalized.
  - As a fallback, Entire sums `outputTokens` on `assistant.message`, but
    Copilot 1.0.94 no longer writes that field. The upstream code at
    `4203b3d` is unchanged.
  - Checkpoints do keep some usage data: cumulative AI units and premium
    requests (`session.usage_checkpoint`), the latest prompt size, subagent
    `totalTokens`, compaction token use, and each tool's
    `result_token_count`. The report shows these.
  - For exact totals after a session is closed, run
    `scripts/checkpoint-report.py --session <id>`. It reads the live log,
    which then contains `session.shutdown`.
- Entire redacts secrets, and also redacts parts of `reasoningOpaque`, which
  is encrypted and unreadable anyway. `reasoningText` is kept.
- `files_touched` lists only files changed with the `edit` and `create`
  tools, not files changed through `bash`; use the commit diff. Subagent
  `tasks/<tool id>/task.json` entries say "transcript unavailable" because
  the subagent's events are in the parent transcript, not a separate file.
  Failed subagents get no `task.json`.
- Files outside the repository, such as `~/.copilot/session-state/<id>/files/`
  and `session.db`, are not stored. Their contents appear only through the
  tool calls that wrote them.
- Copilot subagents and the app's title generator register separate Entire
  sessions with no transcript of their own. They show in
  `entire session list` and are harmless: subagent activity is in the parent
  transcript.

### Capture requirements (verified 2026-10-13)

- GitHub Copilot app sessions did not run the repository's
  `.github/hooks/entire.json`, so the same hooks are also installed at user
  level in `~/.copilot/hooks/entire.json`. Copilot loads hooks when a session
  starts. To capture a session that was already running, use
  `entire session attach <id> -a copilot-cli`.
- `feature.manyFiles` made Git write an index without a checksum, which Entire
  could not read ("index decoder: invalid checksum"). The parent repository
  sets `index.skipHash=false` in its local Git config to prevent this.
- Entire 0.5.5 could not parse Copilot transcripts ("failed to parse
  transcript"); 0.11.4 can. The 0.5.5 binary is kept at
  `~/.local/bin/entire-0.5.5.bak`.

## Workflow

After a completed coding task, commit the relevant changes in each affected
repository, write a task record here using `tasks/TEMPLATE.md`, and commit that
record. Existing changes unrelated to the task must not be included.
Parent checkpoints do not contain child repository source snapshots; use the
linked child commits to inspect or restore code.
