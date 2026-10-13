# Entire workspace checkpoint hub

Date: 2026-10-13 (Asia/Kolkata)
Session: bb890db5-0a1c-4465-b823-1c916088212b (GitHub Copilot app)

## Request

`entire explain` showed no checkpoints on `main`. Track Entire checkpoints at
repository level on `entire/checkpoints/v1` so that `entire explain` works.
Cover all child repositories (care, care_abdm, care_fe, care_abdm_fe). Keep a
full picture of agent work so findings about agent performance with specific
skills can be shared.

## Decisions and rationale

- **Why nothing was listed.** The data was already on the parent's
  `entire/checkpoints/v1`. The list view only shows checkpoints whose commits
  are on the current branch, and checkpoint `877e47e9a4a1` was only on this
  worktree branch, not `main`. The fix is to merge task branches into `main`.
- **Upgraded Entire from 0.5.5 to 0.11.4** (with the user's approval). 0.5.5
  printed "failed to parse transcript" for Copilot sessions. A scratch test
  showed 0.11.4 parses them and lists touched files.
  - Tradeoff: 0.11 replaces `entire explain` with `entire checkpoint list` and
    `entire checkpoint explain`.
  - 0.11 also drops Gemini CLI, so `entire doctor` removed its hooks.
  - The old binary is at `~/.local/bin/entire-0.5.5.bak`.
- **Parent repository is the only checkpoint store.** In a scratch test with
  0.11.4, a Copilot session started in the parent committed in a nested child
  repository and in the parent. Only the parent commit got a checkpoint, even
  with Entire enabled in the child. Entire does not route checkpoints across
  repositories, so the parent task-record commit carries the checkpoint for
  the whole task. Its transcript covers child-repo work.
- **Child commits link back by session ID.** Agent shells expose the session
  (`entire session current` resolves it via `caller-env`). A local
  `prepare-commit-msg` hook in each child repository adds
  `Entire-Session: <id>`. Commits made outside an agent session resolve as
  `other-worktree` and get no trailer. The installer
  (`scripts/install-child-entire-hooks.sh`) is tracked here; the hooks live
  in each child's `.git/hooks`, so no child source changes.
- **care_fe.** Upstream care_fe tracks Entire settings that push to
  `ohcnetwork/care_fe-checkpoints`. Entire's git hooks are not installed in
  that checkout, so it stays inactive, and it is documented as not to be
  enabled.
- **Reasoning.** Checkpoints store the raw Copilot transcript (`full.jsonl`),
  including the reasoning summaries the app records. 0.11.4 also stores a
  compact transcript (`transcript.jsonl`).
- **Copilot display bug in Entire 0.11.4.** `checkpoint explain` shows only the
  first prompt, and `--full` fails. Its parser has no Copilot case, and it
  compacts only transcripts from external agent plugins. The stored data is
  complete, so `scripts/checkpoint-report.py` renders it from
  `entire/checkpoints/v1`. The report covers metadata, model and effort,
  premium requests, skills invoked, tool counts and failures, child
  repositories referenced, linked parent and child commits, and a timeline
  with optional reasoning and tool results.
- **Re-attach.** The checkpoint this session created under 0.5.5 had no
  compact transcript. I moved the session state file aside
  (`/tmp/bb890-session-0.5.5.json`) and re-attached with 0.11.4. That
  refreshed checkpoint `877e47e9a4a1` with the full transcript, which is now
  linked to both parent commits.

## Repository changes

| Repository | Final commit | Changes |
| --- | --- | --- |
| . (parent) | this commit | Hooks refreshed for 0.11.4, Gemini hooks removed, child-hook installer, checkpoint report script, README/AGENTS docs, this record |
| care, care/care_abdm, care_fe, care_abdm_fe | none | Untracked local `.git/hooks/prepare-commit-msg` only |

Outside the repositories:
- `~/.local/bin/entire` and `git-remote-entire` were upgraded to 0.11.4.
- `~/.copilot/hooks/entire.json` was refreshed to the 0.11.4 format.

## Validation

- Scratch nested repos with 0.11.4: the parent commit got checkpoint
  `01M4SGFJ…`, the transcript parsed, and `notes.md` was listed. The child
  commit got no checkpoint.
- `entire doctor`: Claude Code, Copilot CLI and OpenCode hook configs are OK;
  Gemini hooks were removed; no stuck sessions. Codex reads the hooks from the
  main checkout, so that warning clears after the merge to `main`.
- Child hook run directly and through a real `git commit` in a throwaway
  repo: the trailer was added, the merge source was skipped, and a non-agent
  call resolved as `other-worktree`, so no trailer.
- After the re-attach, checkpoint `877e47e9a4a1` has `full.jsonl` (1.9 MB) and
  `transcript.jsonl` (156 entries), with intent "which all mcp servers…".
- After fast-forwarding `main` in the main checkout, `entire checkpoint list`
  on `main` shows checkpoint `877e47e9a4a1`.
- `scripts/checkpoint-report.py 877e` reports 6 prompts, 150 replies (109
  with reasoning), 151 tool calls (4 failed), 1 compaction, 75 premium
  requests, all four child repositories, and both parent commits. An unknown
  ID exits with an error.
- The ABDM client secret from `care/.env` does not appear in either stored
  transcript.

## Open items

- Upstream Entire bug: Copilot transcripts don't render in `checkpoint
  explain`. Not yet reported to entireio/cli.
- Turns after the final re-attach in this session are only in the local
  Copilot session state until the next attach.
- Transcripts include the full system prompt and pasted images; review them
  before sharing outside the team.
- Copilot checkpoints show token totals of 0, both in 0.11.4 and in the
  scratch test.
- Sessions started directly inside a child repository are not captured in the
  parent.
