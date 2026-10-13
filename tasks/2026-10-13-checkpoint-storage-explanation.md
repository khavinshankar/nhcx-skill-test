# Checkpoint storage and Copilot comparison

Date: 2026-10-13 (Asia/Kolkata)
Session: 01a134f3-9946-7563-a447-73465489e8ac (identified by Entire; no Entire session state exists)

## Request

Explain how checkpoints are stored and whether the configuration differs from GitHub Copilot.

## Answer and decisions

- This workspace uses Entire as a shared capture layer for Codex and Copilot CLI. Their agent hooks differ, but the intended durable checkpoint destination is the same parent Git repository's `entire/checkpoints/v1` branch.
- Parent task commits reference checkpoints using `Entire-Checkpoint: <id>`. Verified example: parent commit `6a89eb8` references `9a4c76d6187d`, whose files live under `9a/4c76d6187d/` on that branch. Files include `0/full.jsonl`, `0/transcript.jsonl`, `0/prompt.txt`, and metadata. They are Git objects on a separate branch, not ordinary files checked out on main.
- With the installed manual-commit workflow, a parent commit finalizes capture through that point. Agent transcripts may contain prompts, replies, tool calls/results and metadata according to what the agent logs; capture is not access to hidden reasoning. Later turns require another parent commit. The final reply after that commit is outside its capture, which is why its substance is written in this record.
- Code remains in four independent child repositories. Their session trailers and task-record commit references link code to the parent capture. Parent checkpoints are not child source snapshots; restoring child code requires the corresponding child Git history.
- Parent checkpoint pushing is disabled and the parent has no Git remote, so these checkpoints are local, not automatically uploaded to GitHub.
- Existing Copilot checkpoint metadata confirms agent `Copilot CLI` and strategy `manual-commit`. Codex has seven repository hooks, but `entire status` reports all seven need approval. `entire session current --json` identifies this Codex session and explicitly says Entire has no session state for it. Do not claim this chat is being checkpointed merely because this task record is committed.
- The next setup step is user review/trust of the hooks through Codex CLI `/hooks`, followed by verifying capture. No hook trust or configuration was changed for this explanatory request.
- Copilot's built-in features are distinct from Entire: VS Code checkpoints temporarily restore workspace files/chat; CLI rewind can restore conversation and optionally files; CLI compaction checkpoints are summaries. Using Copilot with Entire in this workspace adds the same Git-backed capture layer intended for Codex.

## Sources

- Local README.md, .entire/settings.json, .codex/hooks.json, .github/hooks/entire.json, scripts/install-child-entire-hooks.sh, and installed parent post-commit hook.
- https://learn.chatgpt.com/docs/hooks (non-managed hooks require review/trust; CLI `/hooks`).
- https://code.visualstudio.com/docs/agents/run/review-code-edits (temporary checkpoints versus Git).
- https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli/roll-back-changes
- https://docs.github.com/en/copilot/concepts/agents/copilot-cli/context-management

## Repository changes

Only this parent task record changed. Its final commit is the commit containing this file; no child code commits were needed and nothing was pushed.

## Validation

- Read Entire status and current-session diagnostics, agent hook definitions, Git log trailers, checkpoint branch tree and sample metadata; results described above.
- `git remote -v`: no parent remote.
- Initial Git status emitted a local fsmonitor IPC error; rerunning with `-c core.fsmonitor=false` succeeded and showed a clean worktree before this record was added.
- No application tests apply to this explanation-only task.

## Open items

Codex hook trust and successful transcript capture remain unverified. This task record preserves the answer independently of Entire capture.
