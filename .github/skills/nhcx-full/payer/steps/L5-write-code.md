# L5. Write Code

#### L5G. GOAL
Write the code in the order of code-plan.json, one file at a time, and keep `nhcx-plan/code.json` current so every file says which screens, APIs, callbacks, FHIR resources, tables and gateway parts it implements, and where.

#### L5I. INPUTS
- `nhcx-plan/code-plan.json`, `nhcx-plan/mapping.json`.
- The spec files for the ids each file implements. The pseudocode (P sections), field tables (FnF, DnC) and verbatim messages are the source of truth.

### L5.1 Take the next file
Pick the lowest `order` not yet `written`. Open every spec it implements, the specs its row in [READSETS.md](../references/READSETS.md) lists, and the files it depends on. Nothing else needs reading for this file.

### L5.2 Write it
- Follow the pseudocode step for step; keep refusal and validation messages verbatim from the spec.
- Take field sources from mapping.json, never from guesses.
- Take NHCX facts (paths, headers, profiles, codes, workflow ids) from the knowledge source; when it contradicts a spec on protocol, follow it and log a `corrected` entry.
- Match the target's conventions recorded in code-plan.json.
- Database changes go through the target's migration tool, never by editing the schema by hand.
- Secrets (client secret, private key, api keys, the callback token) come from configuration, never from code.

### L5.3 Make it build
Run the target's build, lint and type-check for the changed files. Fix until clean (at most 3 rounds, then mark the file `blocked` with the error).

### L5.4 Record it in code.json
Add or update the file's entry: status, the spec ids it implements, and for each function or component its line range and the spec part it implements (for example `A3P step "acknowledge"`, `F9:item[]`, `D19.stage`).

### L5.5 Commit per batch
When a batch from code-plan.json is fully written and builds, commit it with code.json. Then continue with L5.1.

#### L5O. OUTPUT
`nhcx-plan/code.json`:

```json
{
  "files": [
    {
      "path": "",
      "status": "written | blocked",
      "plan_step": "P4.2",
      "implements": {"screens": [], "apis": ["A3"], "callbacks": ["C4"], "fhir": ["F9", "F17"], "database": ["D19"], "gateway": []},
      "symbols": [
        {"name": "", "lines": "", "implements": ["A3P", "F9:total[]", "D19.adjudication_status"]}
      ],
      "migrations": [{"file": "", "tables": ["D19"]}],
      "build": {"ok": true, "command": "", "notes": ""},
      "blocked_reason": ""
    }
  ],
  "coverage": {"S": [], "A": [], "C": [], "F": [], "D": [], "G": []},
  "corrections": []
}
```

`coverage` lists, per prefix, the spec ids implemented by at least one written file; it is recomputed after each file.

#### L5L. LOG
Record in `nhcx-plan/progress.json` and regenerate `nhcx-plan/progress.md`, as [LOG.md](LOG.md) describes. One entry per file: L5.2 names the source file created or modified with its line range and the spec ids it implements; L5.3 logs each build round and its result; L5.4 logs the `nhcx-plan/code.json` update; L5.5 logs the commit and fills `commit` on the batch's entries. Migrations are logged as files like any other.

#### L5X. EXIT
- Every file in code-plan.json is `written` (or `blocked` with a reason the user has seen).
- `coverage` contains every spec id the plan delivers.
- Every `lines` range in code.json matches the current file.
- Every sub-step of L5 has its `started` and closing entries in progress.json, and every file changed is named in one.
