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
- **Reasoning.** Checkpoints store the raw Copilot transcript, including the
  reasoning summaries the app records. `--full` shows prompts, replies and
  tool calls; `--raw-transcript` also includes reasoning.

## Repository changes

| Repository | Final commit | Changes |
| --- | --- | --- |
| . (parent) | this commit | Hooks refreshed for 0.11.4, Gemini hooks removed, installer script, README/AGENTS docs, this record |
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
- The re-attach of this session and the list on `main` are verified after
  this commit; see the open items.

## Open items

- Copilot checkpoints show token totals of 0, both in 0.11.4 and in the
  scratch test.
- Sessions started directly inside a child repository are not captured in the
  parent.
