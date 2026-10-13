# A16. Gateway Token

#### A16E. ENDPOINT

In-process: `gateway.token(participant)` ([G3. Session Token](../gateway/G3-session-token.md)), for the facility's participant code ([G2. Configuration and Participants](../gateway/G2-configuration.md)). No HTTP call from the application to G. G3 hands back the ABDM session token it holds for that participant's client id, fetching it from the ABDM sessions service when missing or within a minute of expiry.

#### A16D. DESCRIPTION

The NHCX Payer Service (A14, A15), the adjudication desk the PMJAY adapter uses for sandbox testing (see [PAYERS.md](../references/PAYERS.md)) [PAYER](../references/PAYERS.md#markers), wants an ABDM bearer token. When the deployment has a payer service token configured, that token is used and G3 is not asked. Otherwise the token is taken from G3, which holds the ABDM session for the participant this facility sends as.

G3 is asked before every payer service A14 and A15 call. The application caches no token; G3 keeps its own per client id and refreshes it before it expires.

#### A16Q. REQUEST

The argument passed to G3:

| Argument | Required | Notes |
|---|---|---|
| `participant` | no | The facility's full participant code (for example `<facility code>`). Blank when the facility has no participant code. A blank code uses the default participant; a code G does not host raises `UNKNOWN_PARTICIPANT` (G3). |

```
gateway.token(participant = "<facility code>")
```

#### A16S. RESPONSE

The token string:

```
"eyJhbGciOiJSUzI1NiIs..."
```

The value is sent to the payer service as both `Authorization: Bearer <token>` and `bearer_auth: Bearer <token>`.

Errors: a G3 error (`code`, `message`, `retryable`), for example `TOKEN_UNREACHABLE` when the ABDM sessions service cannot be reached, `TOKEN_HTTP_<n>` when it refuses the client credentials, or `TOKEN_MISSING`. It is shown on the adjudicator page as "No payer-service token: set the payer service token or fix the session token (`<code>: <message>`)." and is the reason the lookup or action failed.

#### A16P. PSEUDOCODE

When: before every payer service A14 and A15 call. Nothing is cached by the application and nothing is written to the database.

Data: [D1. organization](../database/D1-organization.md) (the facility's participant code).

```text
TOKEN():
  if a payer service token is configured: return it          # G3 not asked
  participant = facility participant code, or ""
  try:
      return gateway.token(participant).token                 # G3 Session Token, in-process
  on G3 error e:
      fail "No payer-service token: set the payer service token or fix the session token (<e.code>: <e.message>)."

Use:
  payer service call: headers Authorization = "Bearer " + token and bearer_auth = "Bearer " + token
  TOKEN fails: the message is the lookup's or action's failure on the adjudicator page
```

#### A16U. USED BY
- APIs: [A14. Adjudicator User Role](A14-adjudicator-user-role.md), [A15. Adjudicator Process Case](A15-adjudicator-process-case.md)
- Database: [D1. organization](../database/D1-organization.md)
- Gateway: [G1. Embedding](../gateway/G1-embedding.md), [G3. Session Token](../gateway/G3-session-token.md)
- Tests: [T1. Test Configuration](../tests/T1-test-configuration.md)
