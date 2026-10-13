# A17. Participant Lookup

#### A17E. ENDPOINT

In-process: `registry.participant(code)`, [G4. Registry and Certificates](../gateway/G4-registry.md), which searches the ABDM participant service with the session token ([G3. Session Token](../gateway/G3-session-token.md)): `POST {registry}/participant/search` (NHA use case `nha:A1`). Plain JSON, no JWE, no protocol headers, no ledger row. G4 caches a record it has fetched; a code it does not know is answered as not found, not as an error.

Reached from the desk's own endpoint, behind a signed-in session with a payer desk role:

| Call | Does |
|---|---|
| `GET /participants/lookup?codes=a,b` | names up to 50 participant codes in one call |

#### A17D. DESCRIPTION

Everything this payer receives is addressed by participant code: the hospital a case came from is `<facility code>`, and the codes this payer itself answers for are on its own record ([D1. payer](../database/D1-payer.md)) and in the gateway's hosted list ([G2. Configuration and Participants](../gateway/G2-configuration.md)). The desk shows those codes as names wherever a person reads them: beside the hospital on the case list and the case desk ([S2. Cases](../screens/S2-cases.md), [S3. Case Desk](../screens/S3-case-desk.md)), and beside each code on the organisation screen ([S12. Organisation](../screens/S12-organisation.md)) when the payer's codes are edited.

The registry is the only authority on who a code belongs to. Names are never stored beside a code; they are looked up when a screen shows them and cached by G4 for the session, so a participant that re-registers under a new name is read correctly.

Codes are canonicalised before the lookup: trimmed, the `@hcx` suffix added when missing, matched on their numeric part case-insensitively, duplicates dropped, and anything that is not a participant code left out. An unknown code comes back with `found` false and blank fields rather than invented ones, since an operator typing a code that does not exist yet is an ordinary thing. A registry that cannot be reached fails the whole call, so a blank name is never mistaken for an answer; a registry that refuses one code (a bad token on that record, a code it rejects) leaves that one blank and answers the rest.

**Messages, verbatim.** "Look up at most 50 codes at a time" (422); "No gateway is configured to ask the registry" (503, when G2 has no registry URL); "The gateway could not be reached: <message>" (502).

Data: [D1. payer](../database/D1-payer.md), [D19. case](../database/D19-case.md).

**Where the codes come from.** The case list reads `nhcx_sender_code` off every row it shows and asks for the distinct codes once, so a page of forty cases from three hospitals costs three lookups, or none when G4 already holds them. The organisation screen asks for `nhcx_participant_id` and `nhcx_processing_id` as they are typed, so an operator sees "Sandbox Payer" appear beside the code before saving, and a code the registry does not know is saved with the warning "The registry knows no participant under this code" rather than refused: a code is issued before its record is public [SANDBOX](../references/PAYERS.md#markers).

**What the lookup is not.** It does not fetch certificates (G4 does that for [G7. Send](../gateway/G7-send.md) when a message is encrypted), it does not write the registry (certificate upload and endpoint updates are done once, at onboarding), and it is not the beneficiary registry: a member's policies are this payer's own tables, never searched at ABDM.

#### A17Q. REQUEST

**From the desk**: `GET /participants/lookup?codes=<facility code>,<payer code>`; codes separated by commas, spaces or newlines.

**To G4**, one call per code:

| Field | Type | Notes |
|---|---|---|
| `code` | string | canonical, with the `@hcx` suffix |

```
registry.participant("<facility code>")
```

#### A17S. RESPONSE

G4 returns the registry's record for the code. The registry answers in more than one shape (a list under `participantdetails`, under `participants`, a bare list, or one object) [SANDBOX](../references/PAYERS.md#markers); G4 reduces each to the fields the desk reads:

| Field | From the registry |
|---|---|
| `code` | `participant_code` (or `participantcode`, `participantid`), the record whose code matches the one asked when several come back |
| `name` | `participant_name` (or `participantname`, `name`) |
| `roles` | `role_code[]` (or `roles[]`, or a comma-separated `roles`), for example `provider`, `payer` |
| `status` | `status`, for example `Active` |
| `found` | false when the registry knows no such code |

**To the desk**, `200`:

```json
{"items": [
  {"code": "<facility code>", "name": "Apollo Multi-Specialty Hospital", "roles": ["provider"], "status": "Active", "found": true},
  {"code": "<payer code>", "name": "Sandbox Payer", "roles": ["payer"], "status": "Active", "found": true}
 ], "total": 2}
```

Errors: `422` "Look up at most 50 codes at a time"; `503` "No gateway is configured to ask the registry"; `502` "The gateway could not be reached: <message>" when the registry never answered.

#### A17P. PSEUDOCODE

When: the case list and case desk render a hospital's code, the organisation screen shows this payer's own codes, and the sandbox provider EMR's participant picker names its payers [SANDBOX](../references/PAYERS.md#markers). Nothing is written to the database.

```text
LOOKUP(raw_codes):
    codes = []
    for raw in split(raw_codes, on ",", " ", newline):
        code = canonical(raw)            # trimmed; "@hcx" added; matched on the numeric part
        if code blank or code in codes or not a participant code: continue
        append code
    if len(codes) > 50: refuse 422 "Look up at most 50 codes at a time"
    if registry not configured (G2): refuse 503 "No gateway is configured to ask the registry"
    items = []
    for code in codes:
        try:
            participant = registry.participant(code)          # G4: cached, else POST participant/search
        on G4 error e:
            if e is unreachable (transport failure, TOKEN_UNREACHABLE, CERT_FETCH_UNREACHABLE):
                refuse 502 "The gateway could not be reached: " + e.message
            participant = {code, found: false}                 # the registry refused this one code
        append REDUCE(code, participant)
    return 200 {items, total: len(items)}

REDUCE(code, record):
    if record is none or not found: return {code, name: "", roles: [], status: "", found: false}
    return {code: record.code, name: record.name, roles: record.roles, status: record.status, found: true}
```

On the screens a code whose lookup found nothing is shown as the bare code, and a lookup that failed shows the code with the muted note "registry unavailable" rather than blocking the page.

#### A17U. USED BY
- Screens: [S12. Organisation](../screens/S12-organisation.md)
- Gateway: [G4. Registry and Certificates](../gateway/G4-registry.md)
