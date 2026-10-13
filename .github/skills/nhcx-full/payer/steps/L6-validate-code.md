# L6. Validate Code

#### L6G. GOAL
Check every written file against the specs it claims to implement, one file at a time, and record the result. Validation reads code against spec; it does not run the system (L7 and L8 do).

#### L6I. INPUTS
- `nhcx-plan/code.json`.
- The spec files named under each file's `implements` and `symbols`.

### L6.1 Take one file
Take the next file in code.json that has no validation entry, or whose content changed since its last one. Validate only that file in this pass.

### L6.2 Check each claimed spec part
For every `symbols[].implements` entry, compare the code with the spec:
- pseudocode (A, C, G): every step present, in order; every branch and failure path handled; status values written exactly as specified
- messages: every refusal and validation message verbatim
- FHIR (F): every element in FnF filled from the mapped source, with the right system and code; profiles and bundle order as in F1; a bundle built by the file passes `validate_fhir` (MCP), or matches the package's example bundle for that exchange
- database (D): columns, types, nullability, defaults, keys and indexes as in DnC and DnK; the rules the schema must hold (a line's decision and its money agree, one primary diagnosis, a completed payment has a UTR) as constraints, not handler code
- screens (S): fields, options, columns, chips, empty states and actions as in SnD, SnL and SnA

### L6.3 Check the file as code
Build, lint and type-check pass; no secret in code; errors surface as the spec says (for example a failed send keeps its ids; a decision already made is not un-made by a gateway that is down); no dead code left from generation.

### L6.4 Record and fix
Record each finding with the spec part, the lines and a severity. Fix `error` findings in the same pass, re-validate the file, and update code.json line ranges. At most 3 rounds per file; after that mark it `failed` with the open findings.

#### L6O. OUTPUT
`nhcx-plan/validation.json`:

```json
{
  "files": [
    {
      "path": "",
      "validated_at": "<ISO time>",
      "content_hash": "",
      "status": "passed | fixed | failed",
      "checks": [
        {"spec": "A3P", "result": "pass | fail", "lines": "", "finding": "", "severity": "error | warning", "fixed": true}
      ],
      "rounds": 1
    }
  ],
  "summary": {"passed": 0, "fixed": 0, "failed": 0},
  "corrections": []
}
```

#### L6L. LOG
Record in `nhcx-plan/progress.json` and regenerate `nhcx-plan/progress.md`, as [LOG.md](LOG.md) describes. One entry per file validated (the path as `item`), with the checks failed and each fix made in the same round as its own entry, naming the lines changed. Every write to `nhcx-plan/validation.json` and every line-range update to `nhcx-plan/code.json` is logged.

#### L6X. EXIT
- Every file in code.json has an entry whose `content_hash` matches the current file.
- No file is `failed` without the user having seen its open findings.
- Every sub-step of L6 has its `started` and closing entries in progress.json, and every file changed is named in one.
