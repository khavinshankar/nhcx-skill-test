# L1. Discovery

#### L1G. GOAL
Find out what the target HMIS already has for every spec item: screens, APIs, callbacks, FHIR builders and parsers (mappers), database tables, and gateway pieces. Record each one as found, partial or missing, with the file and lines where it lives.

#### L1I. INPUTS
- The target repository.
- The NHCX knowledge source ([KNOWLEDGE.md](../references/KNOWLEDGE.md)).
- The spec indexes: [screens](../screens/INDEX.md), [apis](../apis/INDEX.md), [callbacks](../callbacks/INDEX.md), [fhir](../fhir/INDEX.md), [database](../database/INDEX.md), [gateway](../gateway/INDEX.md).

### L1.0 Pick the knowledge source
Call the nhcx-docs MCP `catalogue_info`. If it answers, the source is the MCP; record its catalogue version. If not, download the latest `nhcx-package` release zip into `nhcx-plan/knowledge/`, extract it and check it against `MANIFEST`, as [KNOWLEDGE.md](../references/KNOWLEDGE.md) describes. Write `nhcx-plan/knowledge.json`. Every later step reads NHCX facts from this source.

If neither is reachable (no MCP, and the release cannot be downloaded after 3 attempts, or its files fail the `MANIFEST` check), stop: log L1.0 as `blocked` with what was tried, tell the user, and do not continue to L1.1. Building from memory is not an allowed fallback.

### L1.1 Scan for NHCX before reading anything else
Search the whole target once for NHCX signatures before matching spec by spec: `x-hcx-`, `hcx`, `nhcx`, `coverageeligibility`, `preauth`, `claim/submit`, `paymentnotice`, `communication/request`, `JWE`, `RSA-OAEP`, `participant/get/policies`, `abdm`, `abha`, `resourceType`, `Bundle`, `nrces`. Record every hit with file and lines.
- **No hits at all:** the target is greenfield for NHCX. Every A, C, F and G id is `missing`: write one `items` entry per kind with `"spec": "A*"` (and so on) and `status: missing`, and match only screens (L1.4) and database (L1.7) spec by spec, since those depend on the HMIS's own screens and tables.
- **Hits:** match spec by spec (L1.4 to L1.8), starting from the files the scan found.

### L1.2 Identify the technology
Read the build files, entry points and folder layout. Record:
- which side of the exchange the target is, `provider` or `payer`, by the test in SKILL.md (WHICH SIDE). A `payer` target ends this skill's discovery here: log it, tell the user, and continue with the payer folder's SKILL.md and its own L1
- languages and versions; web framework; UI technology (server-rendered, SPA, mobile)
- database engine, ORM or query layer, migration tool and where migrations live
- how routes are declared; how background jobs or schedulers run
- test framework and how tests run; lint, type-check and build commands
- how configuration and secrets are read
- the HMIS navigation shell (sidebar, navbar, home screen) where a "Claims" entry would go

Then, the language being known, write the report builder and its wrappers ([LOG.md](LOG.md#logh-reporthtml)): `nhcx-plan/report.py` (or `report.mjs`, `report.php`, the target language's equivalent, standard library only), `nhcx-plan/make-report.sh` and `nhcx-plan/make-report.bat`. Run `make-report.sh once` (or the `.bat`) and open the page: at this point it shows the target, the skill and its version, L1 in progress, and every other file as "not yet written". Every later step rebuilds it through the same script.

### L1.3 Find the domain entities
Locate patient, practitioner (doctor, staff), organization (facility), encounter (admission, visit), diagnosis, procedure, billing and insurance entities. For each: model or table name, file and lines, primary key, and the fields that look relevant to D3, D2, D1, D4, D5 and D9.

### L1.4 Match screens (S1 to S16)
For each S spec, search the UI for a screen that does the same job (by route, title, form fields, table columns). Record the route, component or template file and lines, and which of the spec's fields, actions and states it covers.

### L1.5 Match APIs and callbacks (A1 to A17, C1 to C10)
Search for outbound NHCX or ABDM calls (paths such as `coverageeligibility`, `preauth`, `claim/submit`, `communication`, `paymentnotice`, `participant/get/policies`) and inbound routes (`/in/`, `/v1/`, `on_check`, `on_submit`, `callback`). Record handler files and lines, and which pseudocode steps of the spec they already do.

### L1.6 Match FHIR mappers (F1 to F19)
Search for code that builds or reads FHIR resources (`resourceType`, bundle builders, profile URLs, FHIR libraries). For each F spec record the builder or parser file and lines, the profile it uses, and elements it fills or reads.

### L1.7 Match database (D1 to D30)
Compare the target schema with each D spec: existing table, matching columns, missing columns, conflicting types or meanings.

### L1.8 Match the gateway (G1 to G11)
Look for NHCX protocol code: JWE encryption, `x-hcx-*` headers, ABDM session tokens, participant registry lookups, a message ledger. Record what exists and whether it runs in-process or as a separate service.

### L1.9 Write discovery.json
One entry per spec id. A spec with no match is still listed, as `missing`.

#### L1O. OUTPUT
`nhcx-plan/discovery.json`:

```json
{
  "target": {"repo": "<name>", "commit": "<sha>", "discovered_at": "<ISO time>"},
  "technology": {
    "side": "provider",
    "languages": [{"name": "", "version": ""}],
    "framework": "", "ui": "", "database": "", "orm": "",
    "migrations": {"tool": "", "dir": ""},
    "routing": {"file": "", "lines": ""},
    "jobs": "", "tests": {"framework": "", "command": ""},
    "lint": "", "typecheck": "", "build": "",
    "config": "", "navigation": {"file": "", "lines": ""}
  },
  "entities": [
    {"name": "patient", "spec": "D3", "model": "", "file": "", "lines": "", "key": ""}
  ],
  "items": [
    {
      "spec": "S9",
      "kind": "screen | api | callback | fhir | database | gateway",
      "status": "found | partial | missing",
      "locations": [{"file": "", "lines": "", "what": "handler | template | builder | model | migration"}],
      "covers": ["what of the spec already exists"],
      "gaps": ["what of the spec is absent"],
      "notes": ""
    }
  ],
  "corrections": []
}
```

#### L1L. LOG
Record in `nhcx-plan/progress.json` and regenerate `nhcx-plan/progress.md`, as [LOG.md](LOG.md) describes. One entry per sub-step. L1.0 logs the source chosen, and for the package the download, extraction and `MANIFEST` check. L1.1 logs the scan's hits (or that there were none). L1.2 logs the report builder and the two wrapper scripts as created, and the first build of `nhcx-plan/report.html`. L1.4 to L1.8 also log the spec ids they matched, and L1.9 logs `nhcx-plan/discovery.json` as created or modified.

#### L1X. EXIT
- `nhcx-plan/knowledge.json` names the source and its version; for the package, the zip and extracted folder are under `nhcx-plan/knowledge/` and match `MANIFEST`.
- Every S, A, C, F, D and G id from the indexes appears once in `items`, or its whole kind appears as one `missing` entry (`"spec": "A*"`) when L1.1 found no NHCX code.
- Every `found` or `partial` item has at least one location, and each location opens to the lines named.
- `technology` has no empty field the later steps need (framework, database, migrations, tests).
- Every sub-step of L1 has its `started` and closing entries in progress.json, and every file changed is named in one.
