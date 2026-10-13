# G10. Beneficiary Registry

#### G10E. ENTRY
In-process:

- `registry.policies_search(query) -> RegistryReply` (A1)
- `registry.abha_link(body) -> RegistryReply`
- `registry.abha_delink(body) -> RegistryReply`

Calls out, as the default participant, with its session token (G3):

| Function | URL |
|---|---|
| `policies_search` | `POST <urls.participant>/participant/get/policies` |
| `abha_link` | `POST <urls.participant>/participant/link/abha/policy` |
| `abha_delink` | `POST <urls.participant>/participant/delink/abha/policy` |

#### G10D. DESCRIPTION
Pass-through to the ABDM participant service. The gateway models none of it: policies and their ABHA links are the registry's records. It adds the session token, refreshes it once on a 401, and hands back the registry's status and body untouched. No FHIR, no JWE, no protocol headers, no ledger row.

The registry reports "nothing linked to this identifier" as an error (HTTP 400, `NHCX-1016`, "No policies found") [SANDBOX](../references/PAYERS.md#markers). The status is passed through, not translated, so A1 reads that as zero policies.

Every call uses the default participant's session, whichever facility asks. On a deployment hosting several participants with their own credentials, the search still runs as the default one [REF](../references/PAYERS.md#markers).

#### G10Q. INPUT
`policies_search(query)`:

| Field | Type | Default | Meaning |
|---|---|---|---|
| `identifiertype` | string | see below | `MemberId`, `MobileNo` or `AbhaNumber`; passed as given, not checked |
| `identifiervalue` | string | none | the identifier; required |
| `mobile` | string | none | older spelling, read only when `identifiertype` is empty: becomes `MobileNo` / value [REF](../references/PAYERS.md#markers) |
| `abhaNo` | string | none | older spelling, read only when `identifiertype` and `mobile` are empty: becomes `AbhaNumber` / value |

Only `{identifiertype, identifiervalue}` is sent upstream. With `identifiertype` empty and only `identifiervalue` given, an empty type is sent.

`abha_link(body)`, `abha_delink(body)`: a JSON object, forwarded exactly as given. Its fields are the registry's to define.

#### G10S. OUTPUT
`RegistryReply`:

| Field | Meaning |
|---|---|
| `status` | the registry's HTTP status, as is (2xx, 400, 401, 5xx, ...) |
| `body` | the registry's JSON body; a non-JSON body becomes `{"error": "<text>"}` |

A search that found policies (sandbox): status 200, body a top-level array [SANDBOX](../references/PAYERS.md#markers):

```json
[{"abhanumber": "91703412374240", "memberid": "MD5SLS4X5", "mobilenumber": "",
  "payerid": "<payer code>", "processingid": "<payer code>", "productid": "PMJAY/HP/S/G",
  "productname": "PMJAY for Himachal", "sno": "200013271"}]
```

The application treats a `status` that is not 2xx as an error whose message is read from `body` (A1 looks for "No policies found").

Errors raised before or instead of a registry answer (code, retryable):

| Code | Retryable | When |
|---|---|---|
| `NO_IDENTIFIER` | no | search with no value after the fallbacks |
| `TOKEN_UNREACHABLE`, `TOKEN_BAD_JSON` | yes | session service transport or body failure (G3) |
| `TOKEN_HTTP_<n>` | when n >= 500 or 429 | session service refused the credentials |
| `TOKEN_MISSING`, `TOKEN_REQUEST` | no | no token in the answer; request not buildable |
| `CERT_FETCH_UNREACHABLE`, `CERT_FETCH_READ_ERROR` | yes | registry transport failure. The code carries the registry client's generic label, not "policy" |
| `CERT_FETCH_REQUEST` | no | request not buildable |
| `MARSHAL_ERROR` | no | body not encodable |

A second 401 after the refresh is not an error: it comes back as `status` 401.

#### G10P. PSEUDOCODE

```text
policies_search(q):
    kind, value = q.identifiertype, q.identifiervalue        // strings, else ""
    if kind == "":
        if q.mobile != "":      kind, value = "MobileNo",   q.mobile
        else if q.abhaNo != "": kind, value = "AbhaNumber", q.abhaNo
    if value == "": raise NO_IDENTIFIER "identifiervalue (or mobile / abhaNo) is required"
    return post_registry("participant/get/policies", {identifiertype: kind, identifiervalue: value})

abha_link(body):   return post_registry("participant/link/abha/policy", body)
abha_delink(body): return post_registry("participant/delink/abha/policy", body)

post_registry(path, body):
    url = trim_right(urls.participant, "/") + "/" + path
    status, raw = post_with_token(url, body, label = "CERT_FETCH")   // G3P; default participant's token
    if raw is not valid JSON: raw = {"error": raw as text}
    return {status, body: raw}
```

#### G10U. USED BY
- APIs: [A1. Policy Search](../apis/A1-policy-search.md)
- Gateway: [G1. Embedding](G1-embedding.md), [G3. Session Token](G3-session-token.md), [G4. Registry and Certificates](G4-registry.md), [G7. Send](G7-send.md)
