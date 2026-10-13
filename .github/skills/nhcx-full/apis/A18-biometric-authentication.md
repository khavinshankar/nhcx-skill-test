# A18. Biometric Authentication

#### A18E. ENDPOINT
Not an NHCX exchange: these are ABDM calls made by the application directly, as plain JSON, with no JWE, no protocol headers, no callback and no ledger row. Two hosts, and getting the host right is the first thing:

| Method | Calls | Sandbox base | Production |
|---|---|---|---|
| Fingerprint, iris, token refresh | `POST /auth/init`, `POST /auth/verify`, `GET /auth/refresh/token` | `https://apisbx.abdm.gov.in/hcx/abha/biometric` | not published; take it from the onboarding letter |
| Face | `POST /faceauth/init`, `POST /capture/pid`, `POST /v2/auth/verify` | `https://apisbx.abdm.gov.in/pmjay/sbxhcx/abdmproxy/abha/biometric` | not published |
| The patient's phone | the ABHA app opens `https://phrsbx.abdm.gov.in/face-auth?txnId=<txnId>` from a QR code | | not published |

Headers, every call: `Authorization: Bearer <ABDM session token>` from [G3. Session Token](../gateway/G3-session-token.md) (not `bearer_auth`, which the exchange reads; the wrong header draws a 401 that looks like an expired token). The fingerprint, iris and face-verify calls add `process` (`Preauth` at admission and before a pre-authorisation, `Discharge` at discharge and at every visit of a cyclic case) and `payerid` (the participant code of the payer the authentication is performed for, sent **as is**, for example `<payer code>` with its `@hcx` suffix; the knowledge source's `nhcx.endpoint.abha-biometric-*` atoms and `nhcx.concept.biometric-authentication` say "sending the payer's participant code in payerid") [PAYER](../references/PAYERS.md#markers). The face calls add `REQUEST-ID` (a fresh UUID) and `TIMESTAMP` (UTC, ISO 8601).

The source of the calls is the knowledge source: the NHCX package's `apis/14-biometric/` (six Bruno requests) and `docs/03-Building a Provider/03-Biometric Authentication.md`; on the MCP, `search_docs "biometric authentication"` and the endpoint atoms `nhcx.endpoint.abha-biometric-*`. NHA's own list calls this nha:D2.

#### A18D. DESCRIPTION
Proof that the patient was really at the hospital: the beneficiary authenticated against their ABHA, biometrically, and the **user token** that results carried on the exchange. It is done on the Verification tab of the case ([S18. Beneficiary Verification](../screens/S18-beneficiary-verification.md)), **optional for any payer and required by PMJAY**: a token the desk has taken rides on the sends to any payer, and only a payer whose adapter requires proof of presence refuses a request without it ([PAYERS.md](../references/PAYERS.md)).

**The stage follows the stay.** While the patient is admitted (or not yet admitted) the authentication is stage `Preauth` (the scheme's process type `Preauth`): its token rides on the eligibility check and the pre-authorisation. Once the admission is discharged the tab asks for a fresh one at stage `Discharge`, whose token rides on the claim. The desk never chooses the stage; the admission's state does. The methods need not match across a case: fingerprint at admission and face at discharge is fine.

All three methods are built, because any one of them may be the only one that works for a given patient [PAYER](../references/PAYERS.md#markers):

| Method | `authMode` | `scope` on init | How the capture reaches the application |
|---|---|---|---|
| Fingerprint | `FINGERPRINT` | `["abha-login", "aadhaar-bio-verify"]` | the device's PID block from the RD service on the desk machine, sent in `authData.bio.fingerPrintAuthPid` with `authMethods ["bio"]` |
| Iris | `IRIS` | `["abha-login", "aadhaar-iris-verify"]` | the PID block in `authData.iris.irisAuthPid` with `authMethods ["iris"]` |
| Face | `FACE_AUTH` | `["abha-enrol", "face-auth"]` on `faceauth/init` | the patient scans a QR code with the ABHA app and completes the scan on their phone; the application polls `capture/pid` until `COMPLETE`, then verifies with the Aadhaar number, RSA encrypted |

Fingerprint and iris are an init-then-verify pair on one host. `auth/init` names the ABHA number **with hyphens** (`91-4455-7788-2211`, the opposite of the envelope convention) as `loginId`, `loginHint` `abha-number`, `otpSystem` `aadhaar`, and answers a `txnId`. `auth/verify` sends that `txnId` and the PID block and answers the tokens. Face is four steps on the other host: `faceauth/init` answers a `txnId`; the application shows `https://phrsbx.abdm.gov.in/face-auth?txnId=<txnId>` as a QR code; `capture/pid` with the `txnId` answers `{"status": "PENDING"}` until the patient has finished and `{"status": "COMPLETE"}` after (poll it, there is no callback); `v2/auth/verify` sends `authData.face {txnId, aadhaar, mobile}` with `authMethods ["face_auth"]` and `authMode FACE_AUTH`, where `aadhaar` is the 12 digits sealed under the ABHA service's own certificate, the same key the M1 enrolment calls seal an Aadhaar with ([A19. ABHA Create and Verify (ABDM M1)](A19-abha-m1.md): `GET /abha/api/v3/profile/public/certificate`, `RSA/ECB/OAEPWithSHA-1AndMGF1Padding`, base64, fetched once an hour). There is no separate face-auth key to configure. The Aadhaar number is never logged, never stored and never checked as a 12-digit number after sealing.

A successful fingerprint or iris verify answers `authResult success`, a `token` (the user token, `expiresIn` 1800 seconds, thirty minutes), a `refreshToken` (`refreshExpiresIn` 1296000 seconds, fifteen days) and the ABHA `accounts` matched. The face verify (`v2/auth/verify`) answers a different shape (knowledge source `nhcx.endpoint.abha-biometric-v2-auth-verify`): no `authResult`; the tokens under `tokens` (`tokens.token`, `tokens.expiresIn`, `tokens.refreshToken`, `tokens.refreshExpiresIn`, the expiries as **strings**); and the account under `ABHAProfile` (`ABHANumber`). Read both shapes: a token is present when either `token` or `tokens.token` is, and the absence of `authResult` is not a failure. Both tokens are kept against the case ([D31. biometric_auth](../database/D31-biometric-auth.md)) and never shown on a screen or returned by an API. The refresh call (`GET auth/refresh/token` with `R-token: Bearer <refresh token>` beside `Authorization`, `process` and `payerid`) returns a new user token and a **new refresh token whose fifteen days run from that moment**; the old refresh token is discarded. Refresh automatically for the duration of a transaction cycle and at least once in every ten days; a token that has lapsed and cannot be refreshed means a fresh authentication.

**Where the token goes.** The sending APIs, for any payer, read the newest verified authentication for the patient, the payer and the stage ([D31. biometric_auth](../database/D31-biometric-auth.md), `current`): refresh it first when the user token has lapsed and the refresh token has not, then put the user token in the request's JWE headers under the user-token header, with `x-hcx-ben-abha-id` carrying the beneficiary's ABHA number beside it. NHA has not published the user-token header's name [SANDBOX](../references/PAYERS.md#markers); it is a module setting (`biometric_token_header`, default `x-hcx-user-token`) to be corrected from the onboarding letter. [A2. Coverage Eligibility Check](A2-coverage-eligibility-check.md) (every purpose, stage Preauth), [A4. Pre-auth Submit](A4-preauth-submit.md) (stage Preauth, enhancements and predeterminations too) and [A5. Claim Submit](A5-claim-submit.md) (stage Discharge) all do this; when no token is held, the headers go out as they always did.

**When a capture is impossible** under PMJAY (trauma, amputations, unreadable biometrics): the hospital obtains an Aadhaar exemption consent signed by the patient and a hospital representative, stores it against the beneficiary ([D28. claim_document](../database/D28-claim-document.md), category `INF`, code `ODN`), and the desk answers the scheme's consent questionnaire on the leg's forms card instead of sending a token: the **Authentication Consent** form (PMJAY questionnaire `100024`: item `100093` "Medical Superintendent Declaration Form (During Admission)", an `attachment`, and `100095` "Remarks", a `string`) at pre-authorisation on [S9. Pre-authorisation](../screens/S9-preauthorisation.md); the **Discharge Consent** form (questionnaire `100466`: item `135477` "Medical Superintendent Declaration Form (During Discharge)", an `attachment`) at the claim on [S11. Claim Submission](../screens/S11-claim-submission.md) ([F7. QuestionnaireResponse](../fhir/F7-questionnaireresponse.md), [A4. Pre-auth Submit](A4-preauth-submit.md), [A5. Claim Submit](A5-claim-submit.md)). **The application cannot answer these forms by itself**: their questions are attachments, the signed declaration the desk uploads. What the application does is offer the form on the leg's forms card whenever it holds no token for the stage, whether or not the ruling or the plan lists it (PMJAY's ruling names `100024` at pre-authorisation; nothing names `100466` at the claim), and leave it out when it holds a token: a token and a consent are not both sent. Without either the pre-authorisation is refused PAYR-1256 and the claim PAYR-1363. A cyclic procedure has no fallback: the payer pays only for cycles with a live capture, every visit needs a real capture with `process` `Discharge`, and a refresh token is accepted only at the final claim [PAYER](../references/PAYERS.md#markers).

**Whose ABHA is not linked to their PMJAY card** cannot be authenticated this way at all; the scheme's other KYC procedures apply, and the consent route is not the answer for them.

Which payers: every payer takes the token when the desk has one; the `pmjay` adapter requires it (or the consent) and the others do not ([PAYERS.md](../references/PAYERS.md)). The consent fallback is PMJAY's alone: for another payer with no token, the sends go out as they always did. The tab ([S18. Beneficiary Verification](../screens/S18-beneficiary-verification.md)) says "Required by this payer" or "Optional for this payer".

Refused before any call:
- "Choose a patient." / "Choose the payer the authentication is for."
- fingerprint or iris without a 14-digit ABHA number: "A fingerprint or iris authentication names the ABHA number, 14 digits."
- verify without a capture: "Capture the fingerprint on the device and send its PID block." (likewise iris); face without 12 Aadhaar digits: "An Aadhaar number has 12 digits."
- a refresh whose refresh token has lapsed: "The refresh token has lapsed; authenticate the beneficiary again."

Errors from the service are shown in its words. **K-547** on a fingerprint or iris verify means the device capture was asked with `lr` as `N` in the wrapped Aadhaar data hash: the WADH is `Base64(SHA-256("2.5" + "F" + "Y" + "Y" + "N" + "N"))` for fingerprint, with `lr` **Y**. On the exchange, a request with neither a valid token nor the matching consent is refused by name: `PAYR-1256` at pre-authorisation, `PAYR-1363` at the claim; a lapsed or wrong token `PAYR-1272` and `PAYR-1366`; a cycle without a capture `PAYR-1367`, two captures on one date `PAYR-1369`.

#### A18Q. REQUEST

The application's own endpoints, all behind the session, and what each posts to ABDM.

| Endpoint | Body | Posts to ABDM |
|---|---|---|
| `GET biometric?patient_id&payer_code` | | nothing; lists the attempts, the `current` token per stage, and `required` (the payer refuses a request without one) |
| `POST biometric/init` | `patient_id`, `payer_code`, `preauth_id` (optional), `stage` (`Preauth` or `Discharge`), `method` (`FINGERPRINT`, `IRIS`, `FACE_AUTH`), `abha_no` (optional; else the case's, else the patient's) | `auth/init` with `{scope, loginHint: "abha-number", loginId: <ABHA with hyphens>, otpSystem: "aadhaar", authMode}`; for face `faceauth/init` with `{scope: ["abha-enrol", "face-auth"]}` |
| `POST biometric/:id/capture` | | face only: `capture/pid` with `{txnId}` |
| `POST biometric/:id/verify` | `pid` (fingerprint, iris), or `aadhaar_encrypted` and `mobile` (face: the Aadhaar number sealed **in the page** under the ABHA service's certificate, [A19. ABHA Create and Verify (ABDM M1)](A19-abha-m1.md)'s `seal` with the certificate from `GET abha/certificate`; a number in clear is refused) | `auth/verify` with `{scope, authData: {authMethods: [bio or iris], bio or iris: {txnId, <pid key>: pid}}, authMode}`; for face `v2/auth/verify` with `{authData: {authMethods: ["face_auth"], face: {txnId, aadhaar: <sealed>, mobile}}, authMode: "FACE_AUTH"}` |
| `POST biometric/:id/refresh` | | `GET auth/refresh/token` with `R-token` |

The capture itself: the RD service of the registered device answers on `http://127.0.0.1:11100` to `11120`, method `CAPTURE`, with a `PidOptions` XML naming `fCount 1`, `fType 2`, `format 0`, `pidVer 2.0`, `env P` and the `wadh` above; the desk screen tries each port and sends the `PidData` XML it gets back as `pid`. A desk whose device is elsewhere pastes the PID block.

#### A18S. RESPONSE
`init` answers the attempt ([D31. biometric_auth](../database/D31-biometric-auth.md), status `initiated`, with the service's `txnId` and message) and, for face, the `qr_url` to show. `capture` answers the attempt and the service's `status` (`PENDING` or `COMPLETE`); `COMPLETE` moves the attempt to `captured`. `verify` answers the attempt as `verified`, with `token_valid` true, `token_expires_at`, `refresh_expires_at` and the ABHA matched; a refusal leaves it `failed` with the service's message. `refresh` answers the attempt with the new expiries. The listing answers `required` (whether the payer's adapter refuses a request without a token or consent), the `header` the token rides under, every attempt newest first, and `preauth` and `discharge`: the attempt whose token a send would carry now at each stage, or none.

Data: [D31. biometric_auth](../database/D31-biometric-auth.md), [D3. patient](../database/D3-patient.md), [D9. claim](../database/D9-claim.md)

#### A18P. PSEUDOCODE

```
function abdm_headers(payer_code, stage, with_process):
    h = {Authorization: "Bearer " + session_token()}        // G3, the ABDM session
    if with_process: h.process = stage; h.payerid = payer_code        // the participant code as is, not its numeric part
    return h

function face_headers(h): h["REQUEST-ID"] = uuid(); h.TIMESTAMP = now_utc_iso(); return h

function init(patient_id, payer_code, preauth_id, stage, method, abha_no):
    abha = digits(abha_no or preauth.abha_number or patient.abha_number)
    if method != FACE_AUTH and len(abha) != 14: refuse "A fingerprint or iris authentication names the ABHA number, 14 digits."
    row = INSERT biometric_auth (patient_id, preauth_id, payer_code, stage, method, status initiated, abha)
    if method == FACE_AUTH:
        answer = POST face_base + "/faceauth/init" {scope: ["abha-enrol", "face-auth"]} with face_headers(abdm_headers(payer_code, stage, false))
    else:
        answer = POST bio_base + "/auth/init" {scope: scope(method), loginHint: "abha-number",
                     loginId: hyphenate(abha), otpSystem: "aadhaar", authMode: method} with abdm_headers(payer_code, stage, true)
    if answer failed or no txnId: row.status = failed; row.message = reason; raise
    row.txn_id = answer.txnId; row.message = answer.message
    return row, qr_url = face_qr_base + "?txnId=" + row.txn_id when FACE_AUTH

function capture(row):                                   // face only, polled by the screen
    answer = POST face_base + "/capture/pid" {txnId: row.txn_id} with face_headers(abdm_headers(row.payer_code, row.stage, false))
    if answer.status == "COMPLETE" and row.status == initiated: row.status = captured
    return row, answer.status

function verify(row, pid, aadhaar_encrypted, mobile):
    if row.method == FACE_AUTH:
        sealed = aadhaar_encrypted                     // sealed in the page with A19's seal; the server never sees the number
        answer = POST face_base + "/v2/auth/verify" {authData: {authMethods: ["face_auth"],
                     face: {txnId: row.txn_id, aadhaar: sealed, mobile}}, authMode: "FACE_AUTH"}
                 with face_headers(abdm_headers(row.payer_code, row.stage, true))
    else:
        key = "bio" if FINGERPRINT else "iris"; pidkey = "fingerPrintAuthPid" if FINGERPRINT else "irisAuthPid"
        answer = POST bio_base + "/auth/verify" {scope: scope(row.method), authData: {authMethods: [key],
                     key: {txnId: row.txn_id, pidkey: pid}}, authMode: row.method} with abdm_headers(row.payer_code, row.stage, true)
    t = answer.tokens or answer                      // face: tokens {...}, no authResult; bio/iris: top level with authResult
    if answer failed or (answer.authResult present and answer.authResult != "success") or no t.token:
        row.status = failed; row.message = reason; raise
    row.status = verified; row.user_token = t.token; row.token_expires_at = now + int(t.expiresIn)   // face sends the expiries as strings
    row.refresh_token = t.refreshToken; row.refresh_expires_at = now + int(t.refreshExpiresIn)
    row.abha = digits(answer.accounts[0].ABHANumber or answer.ABHAProfile.ABHANumber or row.abha); row.verified_at = now

function refresh(row):
    if row.refresh_expires_at <= now: refuse "The refresh token has lapsed; authenticate the beneficiary again."
    h = abdm_headers(row.payer_code, row.stage, true); h["R-token"] = "Bearer " + row.refresh_token
    answer = GET bio_base + "/auth/refresh/token" with h
    row.user_token = answer.token; row.token_expires_at = now + answer.expiresIn
    if answer.refreshToken: row.refresh_token = answer.refreshToken; row.refresh_expires_at = now + answer.refreshExpiresIn

// what every send calls (A2, A4, A5), for any payer
function biometric_headers(patient_id, payer_code, stage):
    row = newest biometric_auth WHERE patient_id, payer_code, stage, status verified
          AND (token_expires_at > now OR refresh_expires_at > now)
    if none: return {}
    if row.token_expires_at <= now: refresh(row)         // on failure: return {}; PMJAY's consent stands in, another payer gets no token
    return {settings.biometric_token_header: row.user_token, "x-hcx-ben-abha-id": row.abha}
```

#### A18U. USED BY
- Screens: [S4. Claim Creation Form](../screens/S4-claim-creation-form.md), [S11. Claim Submission](../screens/S11-claim-submission.md), [S14. Patient Registration Form](../screens/S14-patient-registration-form.md), [S18. Beneficiary Verification](../screens/S18-beneficiary-verification.md)
- APIs: [A2. Coverage Eligibility Check](A2-coverage-eligibility-check.md), [A4. Pre-auth Submit](A4-preauth-submit.md), [A5. Claim Submit](A5-claim-submit.md), [A19. ABHA Create and Verify (ABDM M1)](A19-abha-m1.md)
- FHIR: [F6. Questionnaire](../fhir/F6-questionnaire.md)
- Database: [D12. claim_plan_form](../database/D12-claim-plan-form.md), [D31. biometric_auth](../database/D31-biometric-auth.md)
- Tests: [T13. PMJAY Eligibility, Package Master and Ruling](../tests/T13-pmjay-eligibility-and-package-master.md), [T19. PMJAY Beneficiary Verification and ABHA](../tests/T19-pmjay-biometric-and-abha.md)
