# Steps

How to build NHCX claims processing into an existing payer system (the target system), from first look to end-to-end tests. Each step reads the specs, works on the target's source, and writes one JSON file under `nhcx-plan/` at the root of the target repository. The next step starts from that file, so a step is done only when its file is written and its exit condition holds.

| # | Step | Reads | Writes |
|---|---|---|---|
| L1 | [Discovery](L1-discovery.md) | the target source, every spec | `nhcx-plan/discovery.json` |
| L2 | [Mapping](L2-mapping.md) | discovery.json, D, F, S | `nhcx-plan/mapping.json` |
| L3 | [Integration Planning](L3-integration-planning.md) | discovery.json, mapping.json | `nhcx-plan/plan.json` |
| L4 | [Code Planning](L4-code-planning.md) | plan.json, the target's conventions | `nhcx-plan/code-plan.json` |
| L5 | [Write Code](L5-write-code.md) | code-plan.json, the specs | source files, `nhcx-plan/code.json` |
| L6 | [Validate Code](L6-validate-code.md) | code.json, the specs | `nhcx-plan/validation.json` |
| L7 | [Dry-run Tests](L7-dry-run-tests.md) | code.json, validation.json | test files, `nhcx-plan/dry-run.json` |
| L8 | [End-to-end Tests](L8-e2e-tests.md) | dry-run.json, sandbox credentials | test files, `nhcx-plan/e2e.json` |
| all | [Knowledge Source](../references/KNOWLEDGE.md) | nhcx-docs MCP, or the GitHub package | `nhcx-plan/knowledge.json`, `nhcx-plan/knowledge/` |
| all | [Progress Log](LOG.md) | every step | `nhcx-plan/progress.json`, `nhcx-plan/progress.md`, and `nhcx-plan/report.html` at the end of every prompt, built by `report.py` (or the target language's equivalent) with `make-report.sh` and `make-report.bat` |

## Spec ids

Every JSON file refers to the specs by id, never by copying them:

| Prefix | Folder | Example |
|---|---|---|
| S | [screens/](../screens/INDEX.md) | `S3`, `S3.1` |
| A | [apis/](../apis/INDEX.md) | `A3` |
| C | [callbacks/](../callbacks/INDEX.md) | `C4` |
| F | [fhir/](../fhir/INDEX.md) | `F9`, or an element: `F9:item[].adjudication[]` |
| D | [database/](../database/INDEX.md) | `D19`, or a column: `D19.stage` |
| G | [gateway/](../gateway/INDEX.md) | `G7` |

## Source locations

Anything found in or written to the target is located as `{"file": "<path from the repo root>", "lines": "<start>-<end>"}`. Line ranges are refreshed whenever the file changes; a location that no longer matches is a defect in the plan file, not in the code.

## Rules for every step

- Start every step by re-reading the Instructions and Confusions in [CORE.md](../references/CORE.md); they override anything in a step that seems to disagree.
- Log as you go: every sub-step's start and end, every file changed and every plan file written goes into `nhcx-plan/progress.json`, with `nhcx-plan/progress.md` regenerated from it ([LOG.md](LOG.md)).
- Treat marked statements as [PAYERS.md](../references/PAYERS.md) says: [REF](../references/PAYERS.md#markers) may be chosen differently (record it in plan.json), [PAYER](../references/PAYERS.md#markers) values come from the scheme profile and are never hard-coded, [SANDBOX](../references/PAYERS.md#markers) behaviour is not relied on in production.
- Take NHCX facts from the knowledge source recorded in `nhcx-plan/knowledge.json` ([KNOWLEDGE.md](../references/KNOWLEDGE.md)), never from memory.
- Work from the target's source as it is. Record what exists before proposing anything new.
- One JSON file per step, pretty-printed, stable key order, committed with the code it describes.
- Every item carries a `status`. A step may not finish with an item whose status is `unknown`.
- When a step finds that an earlier step's file is wrong, fix that file first and note it under `corrections` in the current one.
- Loops are bounded: each step names its retry limit, and hitting it is reported as `blocked` with the reason, never skipped.
