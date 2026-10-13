# L4. Code Planning

#### L4G. GOAL
Decide how the code is written before writing it: the module layout in the target, every file to create or change, the functions in it, the spec items each implements, and the order to write them in.

#### L4I. INPUTS
- `nhcx-plan/plan.json`.
- `nhcx-plan/discovery.json` technology and conventions.

### L4.1 Adopt the target's conventions
Read three or four existing modules of the same kind (a screen, a route handler, a model, a migration, a test) and record the conventions to copy: naming, folder layout, error handling, logging, how forms validate, how money and dates are stored, how tests are named. New code reads like the surrounding code.

### L4.2 Lay out the modules
Start from [references/SCAFFOLDING.md](../references/SCAFFOLDING.md) (module layout, file list, dependency rules, configuration) and map each part onto the target's structure:
- gateway (G1 to G11), in-process, with its configuration file and key material outside the repository
- FHIR builders and parsers (F), one per resource or bundle
- case services (the A pseudocode) and the callback door and handlers (C1 to C11)
- models and migrations (D)
- screens (S) and the navigation entries

### L4.3 List every file
For each file: path, create or modify, the plan step (P ids) it belongs to, the spec ids it implements, its public functions or components with a one-line purpose, and the files it depends on.

### L4.4 Order the work
Order files so each compiles and can be tested when written: migrations and models, then gateway, then FHIR mappers, then services and callbacks, then screens. Group them into batches that match the plan phases.

### L4.5 Plan the tests alongside
For each file, the test file that will cover it in L7, and which spec rules the tests must pin (validation messages, status transitions, the decision-to-ClaimResponse mapping, the wallet debit).

#### L4O. OUTPUT
`nhcx-plan/code-plan.json`:

```json
{
  "conventions": [{"topic": "error handling", "rule": "", "example": {"file": "", "lines": ""}}],
  "modules": [{"name": "gateway", "dir": "", "specs": ["G1", "G11"]}],
  "files": [
    {
      "order": 12,
      "path": "",
      "action": "create | modify",
      "plan_step": "P4.2",
      "implements": {"screens": [], "apis": ["A3"], "callbacks": [], "fhir": ["F9"], "database": ["D19"], "gateway": []},
      "functions": [{"name": "", "purpose": ""}],
      "depends_on": [""],
      "test_file": ""
    }
  ],
  "batches": [{"id": "B3", "phase": "P3", "files": [12, 13, 14]}],
  "corrections": []
}
```

#### L4L. LOG
Record in `nhcx-plan/progress.json` and regenerate `nhcx-plan/progress.md`, as [LOG.md](LOG.md) describes. One entry per sub-step. L4.3 logs one entry per file it plans (the path as `item`), and every write to `nhcx-plan/code-plan.json`.

#### L4X. EXIT
- Every step in plan.json is covered by at least one file.
- Every spec id delivered by the plan appears under some file's `implements`.
- The order respects `depends_on`, and every file has a test file.
- Every sub-step of L4 has its `started` and closing entries in progress.json, and every file changed is named in one.
