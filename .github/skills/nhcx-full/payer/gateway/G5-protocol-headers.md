# G5. Protocol Headers

#### G5E. ENTRY

In-process functions, no network:

| Function | Purpose |
|---|---|
| `build_protected_headers(headers, path)` | the complete `x-hcx-*` set for an outbound message |
| `new_id()`, `is_id(s)`, `ensure_id(s)` | UUID minting and checking for the three id headers |
| `default_status(path)` | `x-hcx-status` when the caller gave none |
| `is_response_path(path)` | whether the API is a response (`on_`) API |
| `entity_type(path)` | entity name for the 202 acceptance body and the ledger |
| `normalize_code(code)`, `same_code(a, b)` | participant code spelling |
| `clean_path(path)` | trims slashes off an NHCX API path |
| `target_url(base, path)` | NHCX gateway URL for an API path |
| `timestamp()`, `ack_timestamp(t)` | the two timestamp formats |
| `get_string(headers, key)` | a trimmed string header value, "" when absent or not a string |

Header names (protected header of the JWE, G6):

| Constant | Header |
|---|---|
| API call id | `x-hcx-api_call_id` |
| request id | `x-hcx-request_id` |
| correlation id | `x-hcx-correlation_id` |
| timestamp | `x-hcx-timestamp` |
| status | `x-hcx-status` |
| sender | `x-hcx-sender_code` |
| recipient | `x-hcx-recipient_code` |
| workflow id | `x-hcx-workflow_id` |

`target_url` builds the NHCX URL: with sandbox `urls.nhcx` `https://apisbx.abdm.gov.in/hcx/v1` and path `v1/preauth/submit` it is `https://apisbx.abdm.gov.in/hcx/v1/preauth/submit`; production is `https://apis.abdm.gov.in/hcx/v1/preauth/submit`.

#### G5D. DESCRIPTION

Every NHCX message carries its routing and tracking headers in the JWE protected header, not in HTTP headers. The application supplies what it knows (recipient, and the correlation and workflow ids when answering or continuing a thread); the gateway completes the rest.

**Rules of `build_protected_headers`.**
- Caller values win, trimmed. Empty strings and nulls are dropped. Non-string values (objects, numbers) are kept as given.
- Sender and recipient are normalised to the `@hcx` spelling; a blank or non-string one is removed. The sender is filled with the default participant's code afterwards by the send (G7), not here.
- `x-hcx-correlation_id`, `x-hcx-request_id` and `x-hcx-api_call_id` are kept only when each is a plain UUID (36 characters, 8-4-4-4-12). Anything else, including a missing value, is replaced by a fresh random UUID. NHCX accepts no other spelling, so a caller-supplied non-UUID id is silently lost; the ids actually used come back in the send result (G7) and must be stored from there.
- `x-hcx-status` defaults by path: `response.complete` for `on_` APIs, `request.initiated` otherwise. The default is only a fallback: an acknowledgement goes on an `on_` path yet travels as `response.partial` (A3, A4), and a query goes on `v1/communication/request` as `request.initiated` (A5), so the sending API sets the status itself ([PAYERS.md](../references/PAYERS.md)).
- `x-hcx-timestamp` defaults to now.
- `x-hcx-workflow_id` is removed when blank; it is never generated.
- Any other header the caller passes (for example `x-hcx-error_details`) goes through unchanged. `alg`, `enc` and `typ` are dropped later by encryption (G6).

**Correlation on replies.** A response API must carry the request's correlation id. Every answering API (A1 to A4, A7 to A10) passes the id of the request it answers; when one is missing, the send fills it from the ledger (G7, G9); this module only generates.

**Timestamps.**
- `x-hcx-timestamp`: `YYYY-MM-DDThh:mm:ss+hhmm`, local time with a colon-less offset, for example `2023-11-06T13:22:06+0530`. It uses the process's local time zone, so a server or container on UTC writes `+0000`; set the time zone to India if IST is wanted [REF](../references/PAYERS.md#markers).
- The 202 acceptance body (G8) uses `DD/MM/YYYY hh:mm:ss:mmm` with milliseconds, for example `06/11/2023 13:22:06:042`.
- The session call (G3) uses RFC 3339 in UTC; that is not this module.

**Path rules.** A path is cleaned of surrounding slashes and spaces. It is a response path when its last segment starts with `on_` (`v1/preauth/on_submit`, `v1/coverageeligibility/on_check`, `v1/communication/on_request`, `v1/paymentnotice/on_request`, `v1/on_status`). `target_url` tolerates `/v1` on the base and `v1/` on the path without doubling it.

**Entity types** (from the path): the second-to-last segment, or the last when the second-to-last is `v1`; a leading `on_` is removed; `paymentnotice` becomes `payment` [REF](../references/PAYERS.md#markers).

| Path | Entity |
|---|---|
| `v1/coverageeligibility/check`, `v1/coverageeligibility/on_check` | `coverageeligibility` |
| `v1/insuranceplan/request`, `.../on_request` | `insuranceplan` |
| `v1/preauth/submit`, `.../on_submit` | `preauth` |
| `v1/claim/submit`, `.../on_submit` | `claim` |
| `v1/task/submit`, `.../on_submit` | `task` |
| `v1/communication/request`, `.../on_request` | `communication` |
| `v1/paymentnotice/request`, `.../on_request` | `payment` |
| `v1/status`, `v1/on_status` | `status` |
| `v1/error` | `error` |

**Codes.** `normalize_code` trims and appends `@hcx` when missing; empty stays empty. `same_code` compares normalised codes case-insensitively.

#### G5Q. INPUT

`build_protected_headers`:

| Argument | Type | Notes |
|---|---|---|
| `headers` | map of string to any | the caller's values; may be empty or null |
| `path` | string | NHCX API path, for example `v1/claim/submit` |

| Header | Default when missing or invalid |
|---|---|
| `x-hcx-sender_code` | removed here; the send fills the default participant's code (G7) |
| `x-hcx-recipient_code` | removed; the send then fails `NO_RECIPIENT` (G7) |
| `x-hcx-correlation_id` | fresh UUID (on a response path the send may first take it from the ledger) |
| `x-hcx-request_id` | fresh UUID |
| `x-hcx-api_call_id` | fresh UUID |
| `x-hcx-status` | `request.initiated`, or `response.complete` on an `on_` path |
| `x-hcx-timestamp` | now, local time, `2006-01-02T15:04:05-0700` layout |
| `x-hcx-workflow_id` | removed |

`target_url(base, path)`: `base` is `urls.nhcx` (G2).

#### G5S. OUTPUT

`build_protected_headers` returns a new map; it never fails. Example for `v1/preauth/on_submit` with only the recipient and the request's correlation id given:

```json
{
  "x-hcx-sender_code": "<payer code>",
  "x-hcx-recipient_code": "<facility code>",
  "x-hcx-correlation_id": "0b8a8d0e-6a53-4a36-8d6e-7f1b3c9d2a11",
  "x-hcx-request_id": "5f2c1e7a-4b0d-4e3f-9a8c-2d6b7e1f0c33",
  "x-hcx-api_call_id": "c3e9f7a2-1d4b-4c8e-b6a0-9f2e5d7c1b44",
  "x-hcx-status": "response.complete",
  "x-hcx-timestamp": "2026-09-21T12:00:05+0530"
}
```

(The sender shown is added by the send, G7; the correlation id is the hospital's, kept.)

Other returns: `is_id` boolean; `ensure_id` the trimmed UUID or a new one; `default_status` one of the two status strings; `entity_type` a string, possibly empty; `normalize_code` a string; `target_url` an absolute URL, or the base alone for an empty path. None of these fail.

#### G5P. PSEUDOCODE

```text
normalize_code(code):
  code = trim(code)
  if code == "" or code ends with "@hcx": return code
  return code + "@hcx"
same_code(a, b): return lower(normalize_code(a)) == lower(normalize_code(b))
clean_path(p):   return trim(trim_spaces(p), "/")

is_id(s):
  s = trim(s)
  return len(s) == 36 and s parses as a UUID
ensure_id(s):    return is_id(s) ? trim(s) : new_uuid()

is_response_path(path):
  segs = split(clean_path(path), "/")
  return last(segs) starts with "on_"
default_status(path): return is_response_path(path) ? "response.complete" : "request.initiated"

entity_type(path):
  segs = split(clean_path(path), "/")
  if len(segs) == 1: e = segs[0]
  else:
      e = segs[len-2]
      if e == "v1": e = segs[len-1]
  e = remove prefix "on_" from e
  return e == "paymentnotice" ? "payment" : e

get_string(h, key): return (h[key] is a string) ? trim(h[key]) : ""

build_protected_headers(in, path):
  out = {}
  for (k, v) in in:
      if v is a string: if trim(v) != "": out[k] = trim(v)
      else if v is not null: out[k] = v
  for k in [x-hcx-sender_code, x-hcx-recipient_code]:
      c = normalize_code(get_string(out, k))
      if c != "": out[k] = c else delete out[k]
  out[x-hcx-correlation_id] = ensure_id(get_string(out, x-hcx-correlation_id))
  out[x-hcx-request_id]     = ensure_id(get_string(out, x-hcx-request_id))
  out[x-hcx-api_call_id]    = ensure_id(get_string(out, x-hcx-api_call_id))
  if get_string(out, x-hcx-status) == "":    out[x-hcx-status] = default_status(path)
  if get_string(out, x-hcx-timestamp) == "": out[x-hcx-timestamp] = timestamp()
  if get_string(out, x-hcx-workflow_id) == "": delete out[x-hcx-workflow_id]
  return out

timestamp():       return format(local now, "YYYY-MM-DDThh:mm:ss" + sign + "hhmm")
ack_timestamp(t):  return format(t, "DD/MM/YYYY hh:mm:ss") + ":" + zero_pad(milliseconds(t), 3)

target_url(base, path):
  base = trimRight(trim(base), "/")
  path = clean_path(path)
  if path == "": return base
  if base ends with "/v1" and path starts with "v1/": base = base without the trailing "/v1"
  return base + "/" + path
```

#### G5U. USED BY
- Screens: [S12. Organisation](../screens/S12-organisation.md)
- APIs: [A1. Eligibility Answer](../apis/A1-eligibility-answer.md), [A3. Pre-auth Answer](../apis/A3-preauth-answer.md), [A5. Query Request](../apis/A5-query-request.md), [A8. Status Answer](../apis/A8-status-answer.md)
- FHIR: [F1. Bundle](../fhir/F1-bundle.md)
- Gateway: [G2. Configuration and Participants](G2-configuration.md), [G4. Registry and Certificates](G4-registry.md), [G6. Encryption](G6-encryption.md), [G7. Send](G7-send.md), [G8. Receive](G8-receive.md), [G9. Ledger](G9-ledger.md)
