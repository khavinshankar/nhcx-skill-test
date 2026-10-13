# G6. Encryption

#### G6E. ENTRY

In-process functions, no network:

| Function | Purpose |
|---|---|
| `encrypt(payload, recipient_public_key, headers)` | compact JWE for an outbound message |
| `decrypt(compact, private_key)` | plaintext of an inbound JWE |
| `parse_header(compact)` | the protected header, without decrypting |
| `is_compact_jwe(s)` | whether a string has the five-part compact shape |
| `decode_key_material(text)` | PEM, from PEM or base64 of PEM |
| `parse_private_key(text)` | RSA private key, PKCS#8 or PKCS#1 |
| `parse_public_key(text)` | RSA public key from a certificate, `PUBLIC KEY` or `RSA PUBLIC KEY` block |

The JWE travels in the JSON body the gateway posts to NHCX (G7) and NHCX posts to the gateway (G8): `{"payload": "<compact JWE>"}`, with `"type": "JWEPayload"` added on outbound `on_` APIs.

#### G6D. DESCRIPTION

Every NHCX payload is a compact JWE: encrypted to the recipient's registered certificate (G4), openable only with the recipient's private key (G2). The protected header carries the `x-hcx-*` headers (G5) in clear, so the recipient can be read before any key is used.

**Outbound algorithms.** Key management `RSA-OAEP-256` (RSA-OAEP with SHA-256), content encryption `A256GCM`. The protected header holds `alg` and `enc` set by the encryption itself, plus every header passed in except `alg`, `enc` and `typ`: the first two would misreport the algorithm, and NHCX validates the header against a schema that admits only `alg`, `enc` and the `x-hcx-*` keys. No compression, no `kid`. The payload is the FHIR bundle as compact JSON bytes (G7).

**Inbound algorithms accepted.** Key management `RSA-OAEP-256` or `RSA-OAEP`. Content encryption `A256GCM`, `A128GCM`, `A192GCM`, `A256CBC-HS512`, `A128CBC-HS256`, `A192CBC-HS384` [REF](../references/PAYERS.md#markers). Anything else fails to parse.

**Compact shape.** Five dot-separated parts with a non-empty first part (the protected header). An empty encrypted key part passes the shape check; decryption then fails.

**Reading the header without the key.** `parse_header` base64url-decodes the first part (padding tolerated) and parses it as a JSON object. The inbound path uses it to pick the addressed profile and to record refused messages with their ids (G8).

**Which key opens an inbound message** is decided in G8: the addressed profile's key first, then every other distinct key held, and `DECRYPT_FAILED` when none opens it.

**Key material.** Accepted as plain PEM, or as base64 of a PEM (standard or URL alphabet, padded or not), which is how the registry and many configs carry it. Only the first PEM block is read, so a certificate chain yields the leaf. Private keys: PKCS#8 (`BEGIN PRIVATE KEY`) first, then PKCS#1 (`BEGIN RSA PRIVATE KEY`); the key must be RSA. Public keys: `PUBLIC KEY` (PKIX), `RSA PUBLIC KEY` (PKCS#1), otherwise the block is parsed as an X.509 certificate and its RSA key used.

**Concurrency.** All functions are pure; keys are read-only after startup and safe to share.

#### G6Q. INPUT

`encrypt`:

| Argument | Notes |
|---|---|
| `payload` | bytes, must not be empty |
| `recipient_public_key` | RSA public key from G4; must be present |
| `headers` | the protected header set from G5 |

`decrypt`:

| Argument | Notes |
|---|---|
| `compact` | compact JWE string |
| `private_key` | a profile's RSA private key (G2) |

`parse_header`, `is_compact_jwe`: the compact string. Key parsing: the key text from the config (after `${ENV}` and `@file`, G2) or the registry's certificate (G4).

#### G6S. OUTPUT

`encrypt` returns the compact JWE: `<protected header>.<encrypted key>.<iv>.<ciphertext>.<tag>`, each base64url without padding. The decoded protected header looks like:

```json
{"alg": "RSA-OAEP-256", "enc": "A256GCM",
 "x-hcx-sender_code": "<facility code>", "x-hcx-recipient_code": "<payer code>",
 "x-hcx-api_call_id": "...", "x-hcx-request_id": "...", "x-hcx-correlation_id": "...",
 "x-hcx-status": "request.initiated", "x-hcx-timestamp": "2026-09-21T12:00:05+0530"}
```

`decrypt` returns the plaintext bytes. `parse_header` returns the header map. `is_compact_jwe` returns a boolean.

Errors, verbatim (plain errors; the callers wrap them into the gateway error shape of G3S):

| Function | Message | Wrapped by the caller as |
|---|---|---|
| `encrypt` | `no recipient public key` | `ENCRYPT_ERROR` "encrypt payload" (G7) |
| `encrypt` | `payload is empty` | `ENCRYPT_ERROR` |
| `encrypt` | `create encrypter: <cause>`, `encrypt: <cause>` | `ENCRYPT_ERROR` |
| `decrypt` | `no private key` | a failed attempt; `DECRYPT_FAILED` when every key fails (G8) |
| `decrypt`, `parse_header` | `payload is not a compact JWE (expected five dot-separated parts)` | not reached on the inbound path: G8 checks `is_compact_jwe` first and refuses with `INVALID_JWE` `"payload" must be a compact JWE string` |
| `decrypt` | `parse JWE: <cause>`, `decrypt: <cause>` | a failed attempt, as above |
| `parse_header` | `decode JWE header: <cause>`, `JWE header is not a JSON object: <cause>` | `INVALID_JWE` "unreadable JWE protected header" (G8) |
| `parse_private_key` | `no PEM block found in private key material`, `private key is not an RSA key`, `private key is neither PKCS#8 nor PKCS#1: <cause>` | startup failure (G2) |
| `parse_public_key` | `no PEM block found in certificate material`, `parse public key: <cause>`, `public key is not an RSA key`, `parse certificate: <cause>`, `certificate public key is not an RSA key` | `CERT_NOT_FOUND` (G4) |

#### G6P. PSEUDOCODE

```text
is_compact_jwe(s):
  parts = split(trim(s), ".")
  return len(parts) == 5 and parts[0] != ""

encrypt(payload, pub, headers):
  if pub is none: fail "no recipient public key"
  if payload is empty: fail "payload is empty"
  extra = {k: v for (k, v) in headers if k not in ["alg", "enc", "typ"]}
  jwe = JWE(alg = RSA-OAEP-256, enc = A256GCM, key = pub, protected header += extra)
        or fail "create encrypter: <cause>"
  jwe.encrypt(payload) or fail "encrypt: <cause>"
  return compact serialisation of jwe

decrypt(compact, priv):
  if priv is none: fail "no private key"
  if not is_compact_jwe(compact): fail NOT_COMPACT
  obj = parse compact, allowing key algorithms [RSA-OAEP-256, RSA-OAEP]
        and content encryptions [A256GCM, A128GCM, A192GCM, A256CBC-HS512, A128CBC-HS256, A192CBC-HS384]
        or fail "parse JWE: <cause>"
  return obj.decrypt(priv) or fail "decrypt: <cause>"

parse_header(compact):
  if not is_compact_jwe(compact): fail NOT_COMPACT
  first = split(trim(compact), ".")[0]
  raw = base64url_decode_unpadded(trimRight(first, "=")) or fail "decode JWE header: <cause>"
  return parse raw as JSON object or fail "JWE header is not a JSON object: <cause>"

decode_key_material(text):
  text = trim(text)
  if text contains "-----BEGIN": return text
  for enc in [base64 std padded, std unpadded, url padded, url unpadded]:
      if enc.decode(text) succeeds and the result contains "-----BEGIN": return result
  return text

parse_private_key(text):
  block = first PEM block of decode_key_material(text) or fail "no PEM block found in private key material"
  if block parses as PKCS#8:
      return it if RSA, else fail "private key is not an RSA key"
  return block parsed as PKCS#1 or fail "private key is neither PKCS#8 nor PKCS#1: <cause>"

parse_public_key(text):
  block = first PEM block of decode_key_material(text) or fail "no PEM block found in certificate material"
  if block.type == "PUBLIC KEY": parse PKIX, must be RSA
  else if block.type == "RSA PUBLIC KEY": parse PKCS#1
  else: parse X.509 certificate or fail "parse certificate: <cause>"; its key must be RSA
```

#### G6U. USED BY
- Screens: [S5. Claim Master](../screens/S5-claim-master.md)
- APIs: [A12. Transaction FHIR](../apis/A12-txn-fhir.md)
- FHIR: [F1. Bundle](../fhir/F1-bundle.md)
- Gateway: [G2. Configuration and Participants](G2-configuration.md), [G4. Registry and Certificates](G4-registry.md), [G5. Protocol Headers](G5-protocol-headers.md), [G7. Send](G7-send.md), [G8. Receive](G8-receive.md)
