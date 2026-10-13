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
