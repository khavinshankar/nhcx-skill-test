# NHCX workspace session tracking

This parent repository records task summaries and cross-repository decisions.
The code repositories are independent: care, care/care_abdm, care_fe,
and care_abdm_fe. Read the applicable instructions inside each before editing it.

Start workspace-wide AI sessions from this directory. Entire capture requires
installed, trusted agent hooks; do not assume a transcript was captured merely
because a commit succeeded. Run `entire status` to check configuration.

Entire checkpoints are stored only in this parent repository. The parent
task-record commit carries the checkpoint for the whole task, including work
done in child repositories. Child commits get an `Entire-Session` trailer from
the hook that `scripts/install-child-entire-hooks.sh` installs. Do not enable
Entire in child repositories.

For each completed task that changes files:

1. Validate the changes and record the actual results.
2. Commit only the task's changes in each affected code repository, unless the
   user asks to leave changes uncommitted. Preserve unrelated changes.
3. Create a concise `tasks/YYYY-MM-DD-short-title.md` with the request, decisions
   and rationale, affected repositories and final commit IDs, validation results,
   and open items. Include a session ID if available; never invent one.
4. Commit the task record in this parent repository. Do not push automatically.

Use Asia/Kolkata dates. Questions alone do not require code commits. Record
explanations and tradeoffs explicitly; do not claim access to hidden reasoning.
Do not add nested repositories as gitlinks or copy their source into the parent.
The parent tracks summaries and commit references, not child source snapshots.
