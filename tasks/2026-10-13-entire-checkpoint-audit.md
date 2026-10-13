# Entire checkpoint completeness audit

Date: 2026-10-13 (Asia/Kolkata)
Session: df6f3ba4-1c63-4cdc-8c95-7d4cce61f0ea (GitHub Copilot app)

## Request

Check that Entire checkpoints hold the whole AI session: intent (initial
prompt), inputs, reasoning, tool calls, MCP calls, skill reads, plan drafts and
all other metadata Entire can track. Test this and fix inconsistencies before
the NHCX integration starts, because the project studies how the NHCX skills
help with a full integration. Confirm before any configuration change.

## Findings

Checked against checkpoint `8cf70d714162`, which the previous session deleted
at the user's request and is still readable at `add4526`. Also checked live in
this session with probes: an MCP call, a subagent, a skill load, a failed
skill load and failed subagents.

- **Complete up to the commit.** `full.jsonl` is Copilot's raw `events.jsonl`
  from session start to the commit: 1526 of the session's 1600 events. Each
  checkpoint repeats the whole log from the start. It holds prompts, the system
  prompt with custom instructions, replies with `reasoningText`, every tool call
  and result (`ask_user`, `sql`, `create`/`edit`), MCP calls (`mcpServerName`),
  skill loads (`skill.invoked`, with the full SKILL.md), subagent prompts, tool
  calls and results (tagged `agentId`), errors, hooks, compactions and premium
  requests.
- **Redaction.** 123 lines differ from the source. 119 are `reasoningOpaque`
  (encrypted). 4 are real secrets in tool output (env files, environment
  variables). No readable reasoning or content was lost.
- **Gap: turns after the last commit.** The previous session's last 74 events
  were never checkpointed, including a whole user prompt (the request to
  delete checkpoints).
- **Gap: Entire metadata for Copilot.** `model` is empty, `token_usage` is 0,
  `files_touched` is null, and `prompt.txt` holds only the first prompt. The
  data is in the transcript. Token totals come only in `session.shutdown`,
  after the last commit.
- **Bug: wrong child-commit session ID.** `entire session current` resolved by
  process ancestry to a subagent's session (`021183f1…`, and later a failed
  subagent `254d8586…`). Early in a session it can also resolve to the app's
  title generator (`66c5e633…`), because all of them share the Copilot
  process. Child commits would get the wrong `Entire-Session` trailer. A
  subagent's shell also exports its own `COPILOT_AGENT_SESSION_ID`, which no
  event links to the parent session.
- **Report script.** It counted subagent prompts as user prompts, listed failed
  skill loads, and ignored MCP servers, subagents, model changes, errors and
  `ask_user` answers.
- **Not Entire, noted:** subagents began failing with "400 The requested model
  is not supported" (Copilot side). The 13 ABDM skills in `.github/skills` are
  not offered to Copilot; only `nhcx-full` loads, so `abdm-fhir` gave "not
  found". Their frontmatter has extra keys (`type`, `domain`,
  `agent_consumers`, …) that `nhcx-full` lacks; this is the likely cause and was
  not tested.

## Decisions and rationale

The user approved all three fixes. Entire settings, agent hooks, and the
checkpoint backend were left unchanged.

1. **Child hook** (`scripts/install-child-entire-hooks.sh`, reinstalled in all
   four child repositories). It walks up the process tree to the
   `~/.copilot/session-state/<id>/inuse.<pid>.lock` that Copilot holds for the
   top-level session, and writes `Entire-Session: <top-level id>`. When the
   commit comes from a subagent, it also writes
   `Entire-Subagent: <COPILOT_AGENT_SESSION_ID>`. `entire session current` is
   now only a fallback, for agents other than Copilot.
2. **Workflow rule** (`AGENTS.md`, `README.md`). Every prompt ends with a parent
   task-record commit, including follow-ups and question-only prompts, so that
   Entire checkpoints the conversation up to that point. The substance of the
   final reply goes in the task record because the reply after the commit is
   not captured. This was chosen over an out-of-band transcript archive, which
   would bypass Entire.
3. **Report** (`scripts/checkpoint-report.py`).
   - It separates subagent activity from user prompts.
   - It lists models and model changes, skills actually loaded (with paths),
     MCP servers, a subagent table, errors, and counts of every event type.
   - It always shows `ask_user` answers. `--system` prints the instructions.
   - `--session <id>` / `--transcript <path>` read the live log, including
     uncommitted turns. `--ref` reads checkpoints from another commit.

## Repository changes

| Repository | Final commit | Changes |
| --- | --- | --- |
| parent (nhcx) | this task-record commit | AGENTS.md, README.md, both scripts, this record |
| care, care/care_abdm, care_fe, care_abdm_fe | none (hook only) | `.git/hooks/prepare-commit-msg` reinstalled; no tracked files changed |

## Validation

- **Hook.** Tested in a scratch repository: the main session got the correct
  ID. A simulated subagent got the parent ID plus `Entire-Subagent`. An existing
  trailer was not duplicated. Without the lock file, the fallback reproduced the
  old wrong ID (a failed subagent's session), which confirms the bug. `sh -n`
  passes on the installer and the generated hook.
- **Report.** Ran on the live session and on `8cf70d714162 --ref add4526`
  (1526 events, 6 prompts, MCP servers abdm-docs, nhcx-docs and
  github-mcp-server). The live run showed 1 user prompt, 5 subagents (3
  failed), `nhcx-full` loaded, nhcx-docs×1 and the `ask_user` answer. Running
  with no source gives a usage error.
- **Not tested.** Plan mode (no plan was drafted). Capture with Claude Code,
  Codex and the other agents.
- **Checkpoint.** Commit `0d3f293` got checkpoint `88097bc7f01f`. It holds one
  session: the subagent and title-generator sessions were not attached. It has
  the full transcript (674 events, `nhcx-full` load, nhcx-docs call, 5
  subagents with errors, the `ask_user` answer) and `task.json` for the 2
  completed subagents ("transcript path unresolvable"; their events are in
  the parent transcript). `entire checkpoint list` shows it.
  - Its `files_touched` lists AGENTS.md, the installer and this record. It
    omits README.md and the report script, which were changed through `bash`.
    That gap is documented in README.
  - This follow-up commit tests that a later checkpoint includes the turns
    after the first commit.

## Open items

- `entire doctor`: Codex has 7 hooks without an approval record. If Codex will
  be used, open `/hooks` in Codex and approve them.
- Check why the ABDM skills do not load, if they are needed.
- If subagents keep failing with the 400 model error, that is a Copilot app
  issue.

## Follow-up: checkpoints missing from `entire checkpoint list` (08:12 IST)

- **Request.** The user ran `entire checkpoint list` in the main checkout and saw
  no checkpoints.
- **Cause.** `entire checkpoint list` shows only checkpoints whose commits are on
  the current branch. Both checkpoints, `88097bc7f01f` and `bdb6d0438632`, exist
  on `entire/checkpoints/v1`, but their commits were only on
  `khavinshankar-entire-checkpoint-audit`, not on `main`. The worktree listed 2
  checkpoints; the main checkout listed 0.
- **Decision.** The user approved fast-forwarding `main` to this branch: no merge
  commit and no push. Fast-forwarding keeps the commit IDs, so the
  `Entire-Checkpoint` trailers stay valid. A squash or rebase would orphan them.

## Follow-up: checkpoints on `main` automatically, and `--full` (08:16 IST)

- **Request.**
  1. Record checkpoints directly on `main` with every commit.
  2. Fix "failed to parse transcript" in `entire checkpoint explain <id> --full`.
  3. Answer whether each checkpoint creates a new file.
- **Main (user chose option A over "branch" workspace sessions).**
  - New `scripts/ff-main.sh` runs from the shared parent `post-commit` hook
    after Entire's step and fast-forwards `main` to the new commit. It updates
    the main checkout with `merge --ff-only`, or uses `update-ref` if `main`
    isn't checked out anywhere.
  - It never merges, rebases or pushes, and never fails a commit. It skips with
    a warning if `main` has diverged or the main checkout has uncommitted
    tracked changes.
  - Disable it with `git config nhcx.autoFastForwardMain false`.
  - `scripts/install-parent-hooks.sh` appends the hook line once; rerun it
    after `entire enable` or an Entire upgrade.
  - Rejected option B: working directly on `main`. It needs no hook, but
    parallel sessions would share one checkout.
- **`--full` parse failure.** This is an Entire bug, still present upstream at
  `entireio/cli@4203b3d`.
  - `summarize.BuildCondensedTranscriptFromBytes` has no Copilot case, so it
    sends Copilot's raw `events.jsonl` to the Claude-format parser. The compact
    fallback expects already-compacted input. Entire's own Copilot compactor
    (`transcript/compact/copilot.go`) is never called on this path.
  - Fixing it needs a rebuilt binary, and Go isn't installed. The user chose
    not to patch, and to keep using `scripts/checkpoint-report.py`. The report
    now also accepts a commit (and uses its `Entire-Checkpoint` trailer), like
    `explain <commit>`.
- **Storage answer.** Each checkpoint adds one directory, `<id[:2]>/<id[2:]>/0/`,
  on the `entire/checkpoints/v1` branch only, not in the working tree. It holds
  `full.jsonl` (the raw log from session start), `transcript.jsonl` (compact),
  `metadata.json`, `prompt.txt` and `content_hash.txt`.
  - At the end of each turn, Entire's "Finalize transcript" commit rewrites
    that turn's checkpoints to the full turn transcript. So `88097bc7f01f` and
    `bdb6d0438632` have identical 1.2 MB / 719-event logs, which git stores
    once. `cacc67ea1c19` has 767 events.
  - Growth per checkpoint is the session's log size so far; git compresses the
    repeated content.
- **Validation.**
  - A scratch repo with a worktree tested 7 cases: fast-forward, dirty main
    checkout skipped, catch-up, diverged main skipped, commit on main is a
    no-op, `update-ref` when `main` isn't checked out, and disabled by config.
    All passed after one fix: the hook now runs the script with `sh`, because a
    non-executable script was being skipped.
  - The report resolves commit `0daf11b` to checkpoint `cacc67ea1c19`.
  - Real hook: this record's commit should print `ff-main: main -> <sha>`.

## Follow-up: why token usage is not captured (08:21 IST)

- **Cause.** Entire's Copilot code (`agent/copilotcli/transcript.go`,
  `extractTokenUsageFromEvents`) reads tokens from two places, and neither has
  data during a session:
  1. `session.shutdown` has the session totals (`modelMetrics`, `tokenDetails`),
     but Copilot writes it only when the session closes. Entire finalizes a
     turn's checkpoints at turn end (`HandleTurnEnd`) and never revisits them,
     so the totals never reach a checkpoint.
  2. As a fallback, Entire sums `outputTokens` on `assistant.message`, but
     Copilot 1.0.94 doesn't write that field. The only logs with
     `outputTokens` are in `session.shutdown` of already-closed sessions,
     such as the title generator's. The upstream code at `4203b3d` is
     unchanged.
- **Data that is captured.** Searching this session's log for token fields
  found:
  - `session.usage_checkpoint`: `totalNanoAiu`, `totalPremiumRequests`, and
    per-model `prompt_tokens`/`tool_tokens`
  - `subagent.completed/failed.totalTokens`
  - `session.compaction_*` token counts. This session was compacted once.
  - `tool.execution_complete...result_token_count`
- **Change.** `scripts/checkpoint-report.py` adds a "Usage before session end"
  line showing AI units, the latest prompt size, subagent tokens and compaction
  tokens. README documents the cause and says to use `--session <id>` after a
  session closes for exact totals. No Entire or Copilot configuration was
  changed; no setting could fix this.
- **Validation.**
  - Live session: 478.8 AI units, 45 premium requests, last prompt 94,093
    tokens, subagents 302,693 tokens, compaction 162,449 in / 3,840 out.
  - Closed title-generator session `2626c199`: shutdown totals of 10 in,
    794 out, 71,151 cache read, 24,493 cache write tokens.
  - Checkpoint `88097` still renders.
