# Knowledge Source

The specs in this skill say what to build in the payer system. The NHCX knowledge source says what the exchange itself requires: API paths and headers, FHIR profiles and example bundles, codes, workflow ids, error codes, go-live rules. Every step that needs NHCX facts reads them from one knowledge source, chosen once at the start of L1 and recorded in `nhcx-plan/knowledge.json`.

## Two options, in order

### Option 1: the nhcx-docs MCP server

Use it when it is connected. Test by calling `catalogue_info`: an answer means it is available, and the answer gives the catalogue version to record.

| Tool | Use it to |
|---|---|
| `catalogue_info` | confirm the server is up; read the catalogue version and build time |
| `search_docs` | find anything by words: a concept, a flow, a rule, a base URL |
| `list_operations`, `get_operation` | list the NHCX APIs; read one API's method, path, headers and body |
| `list_atoms`, `get_atom`, `related_atoms` | read one unit of documentation (concept, flow, endpoint, callback, error, test) and what it links to |
| `list_fhir_profiles`, `get_fhir_profile`, `get_fhir_example` | read an NRCeS profile and an example bundle |
| `validate_fhir` | check a built bundle against the NHCX profiles |
| `validate_request` | check a request envelope and headers |
| `decode_error` | explain an NHCX or payer error code (for example `NHCX-1016`, `PAYR-1008`) |

### Option 2: the NHCX package from GitHub

Use it when the MCP server is not connected. Take the latest release of `github.com/nha-in/nhcx-package` and keep it in the target repository under `nhcx-plan/`.

1. Read the latest release: `GET https://api.github.com/repos/nha-in/nhcx-package/releases/latest`. Take `tag_name` and the asset named `nhcx-package-v<version>.zip` (at the time of writing: `1.0.0`, `https://github.com/nha-in/nhcx-package/releases/download/1.0.0/nhcx-package-v1.0.0.zip`, about 1.4 MB zipped, 361 files).
2. Save it as `nhcx-plan/knowledge/nhcx-package-v<version>.zip` and extract it to `nhcx-plan/knowledge/nhcx-package/`.
3. Check the extracted files against `MANIFEST` (it lists every file with its size and sha256). A mismatch means a bad download: fetch again, at most 3 times, then stop and report.
4. When a newer release exists than the one already in `nhcx-plan/knowledge/`, replace it and note the change in `knowledge.json` and the progress log. Never mix files from two versions.

What the package holds:

| Path | Holds | Use it for |
|---|---|---|
| `MANIFEST` | version, build time, every file with size and sha256 | the version to record; download check |
| `docs/` | the NHCX documentation: 01 Overview, 02 Getting Started, 03 Building a Provider, 04 Building a Payer, 05 FHIR Reference, 06 Reference, 07 Go Live | concepts, flows, the payer's answers and the hospital's messages (04 Building a Payer is the chapter for this skill), FHIR rules, error codes, troubleshooting, production cutover |
| `apis/` | every NHCX API as a Bruno request (`.bru`), grouped `01-session` to `14-biometric`, with `environments/` | method, path, headers and body of each call |
| `fhir/` | example bundles per NHA use case, generic and PMJAY (for example `fhir/C5/C5-approved-wf21-pmjay.json`, a payer's pre-authorisation approval) | building the answers this payer sends and checking them; the hospital's messages as test fixtures |
| `mappings/` | per NHA use case, every data element and where it sits in the FHIR bundle | field mapping (L2) |
| `usecases.yaml` | every NHA use case, A1 to E1, and the bundle types | finding the right bundle for an exchange |
| `workflow.yaml` | every workflow code: meaning, sender, `x-hcx-status` | workflow ids and statuses |
| `nhcx-error.yaml` | gateway, standard payer and reference payer error codes | decoding errors |
| `baseurl.yaml` | the addresses per environment | sandbox and production URLs |
| `corpus/` | a search index of the above | full-text lookup |

Links inside the package's `docs/README.md` are absolute paths from the machine that built it. Follow them by their folder and file name under `nhcx-plan/knowledge/nhcx-package/docs/`, not as written.

## ABHA, ABDM's M1

A member's ABHA is created or verified through ABDM's ABHA service ([A20. ABHA Create and Verify (ABDM M1)](../apis/A20-abha-m1.md)), and that is ABDM's HIE-CM milestone M1, not NHCX. The same MCP server serves it (the server is published as `nhcx-docs` and as `abdm-docs`; both answer `catalogue_info`), and it is the only source: the NHCX package has no M1 at all. Read M1 like this:

| Need | Call |
|---|---|
| The router for the milestone | the `abdm-m1` prompt |
| The flows this skill builds | `get hiecm.flow.m1-create-abha-aadhaar-otp`, `get hiecm.flow.m1-login-by-mobile` |
| Every M1 flow, concept and endpoint | `search` with `milestone: M1` and a `type` |
| One call's exact body, headers and responses | `get <operation id>`, the ids listed in A20 |
| The encryption certificate and what it seals | `get m1_get_v3_profile_public_certificate` |
| Why a call failed | `decode_error` with the `ABDM-` code; the troubleshooting atoms `everything-returns-401` and `otp-never-arrives` |

Without the MCP, open the same atoms on the ABDM developer portal at the `doc_url` an earlier `search` returned, and record `"m1": "portal"` in `knowledge.json`.

## Which lookup for which question

| Question | MCP | Package |
|---|---|---|
| What is the path, method and header set of an NHCX call? | `get_operation` | `apis/<group>/*.bru` |
| What does a bundle for this exchange look like? | `get_fhir_example` | `fhir/<use case>/*.json` |
| What does a profile require? | `get_fhir_profile` | `docs/05-FHIR Reference/` |
| Is this bundle valid? | `validate_fhir` | compare with `fhir/` and `mappings/`; no offline validator ships |
| Where does this data element go? | `get_atom`, `related_atoms` | `mappings/<use case>.yaml` |
| What does this workflow id or status mean? | `search_docs` | `workflow.yaml` |
| What does this error code mean? | `decode_error` | `nhcx-error.yaml`, `docs/06-Reference/` |
| What changes for production? | `search_docs` | `docs/07-Go Live/` |

## Ids do not match

The package and the MCP catalogue number things by NHA's own use-case codes (A1 is "Get participant list", B1 the eligibility check, C5 the pre-authorisation replies). This skill's A, C and F ids are its own: `A1` is this payer's eligibility answer, `C5` the claim a hospital submits. Always write the knowledge source's id with its origin, for example `nha:C5` or `pkg:fhir/C5/C5-approved-wf21.json`, and this skill's ids bare (`C5`).

## When the knowledge source and the specs disagree

- On the protocol (paths, headers, FHIR profiles and elements, code systems, workflow ids, error codes, statuses) the knowledge source wins. Record the difference under `corrections` in the current step's plan file and as a `corrected` entry in the progress log, naming the spec id and the knowledge source reference.
- On what the application does with a message (screens, tables, matching rules, which leg a reply settles) the specs win.
- Behaviour the specs describe as specific to one scheme dialect (PMJAY, or the sandbox payer's own) is checked against the knowledge source before it is copied.

## Where the steps use it

| Step | Use |
|---|---|
| L1 | L1.0 picks the source and writes `nhcx-plan/knowledge.json`; L1.1, L1.5 and L1.6 use it to recognise NHCX code in the target payer system |
| L2 | FHIR elements, code systems and data element placement |
| L5 | paths, headers, profiles and codes while writing |
| L6 | `validate_fhir` and `validate_request`, or comparison with the package bundles |
| L7 | example bundles as the hospital's messages: test fixtures for callbacks and parsers |
| L8 | error decoding and troubleshooting; go-live rules |

## nhcx-plan/knowledge.json

```json
{
  "source": "mcp | package",
  "mcp": {"server": "nhcx-docs", "catalogue_version": "", "built_at": ""},
  "package": {
    "repo": "nha-in/nhcx-package",
    "version": "",
    "asset": "nhcx-package-v<version>.zip",
    "zip": "nhcx-plan/knowledge/nhcx-package-v<version>.zip",
    "dir": "nhcx-plan/knowledge/nhcx-package/",
    "manifest_checked": true
  },
  "checked_at": "<ISO time>",
  "corrections": []
}
```

Only the block for the chosen source is filled. Choosing, downloading, checking and replacing the source are logged in `nhcx-plan/progress.json` like any other sub-step.
