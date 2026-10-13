# A19. ABHA Create and Verify (ABDM M1)

#### A19E. ENDPOINT
Not an NHCX exchange: ABDM's ABHA service, called **from the application's server**, never from the operator's browser. The server carries the ABDM session token from [G3. Session Token](../gateway/G3-session-token.md) on `Authorization: Bearer`, a fresh `REQUEST-ID` (UUID) and `TIMESTAMP` (UTC, ISO 8601 with milliseconds) on every call, plain JSON, no JWE and no ledger row. Sandbox base `https://abhasbx.abdm.gov.in/abha/api/v3`; production is published by ABDM and confirmed in the onboarding letter. The page talks only to the application's own endpoints (A19Q) and holds only the flow's `txn_id`: **the session token, the X-token and the T-token never reach the browser.** Handing the facility's session token to a page would let any operator act as the facility on every ABDM call for as long as the token lives, so it stays server-side; the flow's X-token and T-token are kept on the server for the flow's few minutes, keyed by `txnId` and the signed-in user, and discarded after. The identifiers the person types are still sealed in the page under the service's public certificate before they are posted, so an Aadhaar number or OTP never travels in clear (the server seals a value only when the page could not).

**The calls, their bodies, headers, responses and errors are read from the MCP, not from this spec.** The `nhcx-docs` MCP server (also published as `abdm-docs`) serves the whole of ABDM's HIE-CM catalogue beside NHCX, and M1 is its first milestone: open its `abdm-m1` prompt (the M1 router), or read these directly with `get`:

| What | MCP id |
|---|---|
| Create an ABHA from an Aadhaar OTP, end to end | `hiecm.flow.m1-create-abha-aadhaar-otp` |
| Verify an existing ABHA by mobile OTP, with the account chooser | `hiecm.flow.m1-login-by-mobile` |
| Which verification method to offer | `hiecm.concept.m1-verification-methods` |
| The encryption certificate every sealed field needs | `m1_get_v3_profile_public_certificate` |
| Send the Aadhaar OTP; verify it and create | `m1_post_v3_enrollment_request_otp_aadhaar_otp`, `m1_post_v3_enrollment_enrol_byaadhaar_otp` |
| Address suggestions; claim the address | `m1_get_v3_enrollment_enrol_suggestion_create_abha_aadhaar_otp`, `m1_post_v3_enrollment_enrol_abha_address_create_abha_aadhaar_otp` |
| Send the OTP for an ABHA number; verify it | `m1_post_v3_profile_login_request_otp_abha_number_abha_otp`, `m1_post_v3_profile_login_verify_abha_number_abha_otp` |
| Send the OTP for a mobile; verify it; choose the account | `m1_post_v3_profile_login_request_otp_mobile`, `m1_post_v3_profile_login_verify_mobile_otp`, `m1_post_v3_profile_login_verify_user` |
| Read the profile the X-token opens | `m1_get_v3_profile_account` |
| Why a call failed | `decode_error` with the `ABDM-` code, and the troubleshooting atoms `everything-returns-401` and `otp-never-arrives` |

`search` with `milestone: M1` lists the other M1 flows (demographic, face, fingerprint and iris creation, child ABHA, find ABHA, update mobile), none of which this skill builds. The GitHub package (knowledge source option 2) carries no M1 at all: M1 needs the MCP, or the same atoms read on the ABDM developer portal at the `doc_url` the MCP returns.

#### A19D. DESCRIPTION
The ABHA number is what links a claim to an admission ([S4. Claim Creation Form](../screens/S4-claim-creation-form.md), [D3. patient](../database/D3-patient.md)), and under PMJAY it is the account the beneficiary is authenticated against ([A18. Biometric Authentication](A18-biometric-authentication.md)). A number typed at the desk is a number nobody checked. This API puts a **verified** ABHA on the file, two ways, and fills the file from what the ABHA service says about the person: name, gender, date of birth, mobile, ABHA number and address.

**Verify an existing ABHA.** By its number, or by the mobile it is registered against. The identifier is sealed under the service's certificate and sent with `scope ["abha-login", "mobile-verify"]`, `loginHint` `abha-number` or `mobile`, `otpSystem abdm`; the OTP goes to the mobile either way. Verifying the OTP by ABHA number answers the account and the X-token directly, and the profile is read with it. Verifying by mobile answers the accounts on that mobile (a shared family phone holds several) and a short-lived T-token: the desk picks the account, `verify/user` with the chosen `ABHANumber` and the same `txnId` under `T-token` answers the X-token, and then the profile. Always call `verify/user` on the mobile path, even with one account listed. The account list carries **masked** ABHA numbers (`xx-xxxx-xxxx-1234`, `m1_post_v3_profile_login_verify_mobile_otp`), so `verify/user` sends the listed value exactly as given, or a full 14-digit number whose last digits match it; never reformat the masked value as digits.

**Create an ABHA from an Aadhaar OTP.** With the person present and their consent recorded (consent code `abha-enrollment`, version `1.4`): the Aadhaar number sealed as `loginId` with `scope ["abha-enrol"]`, `loginHint aadhaar`, `otpSystem aadhaar`; the OTP goes to the mobile registered against the Aadhaar, which may not be the phone in the room. `enrol/byAadhaar` with the sealed OTP, the communication mobile and the consent answers `ABHAProfile`, the tokens and **`isNew`**: an Aadhaar that already has an ABHA returns that account with `isNew` false, so read it before telling anyone something was created. A new account then gets its address: suggestions with the `TRANSACTION_ID` header, the chosen one claimed with `preferred 1`; an account left with only its default address is a half-finished job the person will not recognise later.

Rules, both ways:
- The Aadhaar number, the OTP and the identifiers are sealed **in the page** under the certificate from `/profile/public/certificate` (RSA/ECB/OAEPWithSHA-1AndMGF1Padding, base64; WebCrypto's `RSA-OAEP` with `SHA-1` on an `spki` import of the key; the server hands the certificate to the page and caches it for an hour). The server passes the sealed values through to the service and never stores or logs them; the audit event for the OTP step carries the last four digits of an Aadhaar at most.
- The session token, the X-token and the T-token stay **on the server**, keyed by the flow's `txnId` and the signed-in user, for fifteen minutes; none of them is ever sent to the browser, and the page holds only `txn_id`. The gateway session token is never sent as an X-token; the server refreshes it through [G3. Session Token](../gateway/G3-session-token.md) when the service answers 401.
- The profile written onto the file: `abha_number` (14 digits, shown as `xx-xxxx-xxxx-xxxx`), `abha_address` (the preferred address, else the first `phrAddress`), `name` (`name`, else first, middle and last), `gender` (`M` `F` `O` to Male, Female, Other), `birth_date` (`dob` as `DD-MM-YYYY`, or day, month and year), `phone` (left blank when the service masks it as `******0903`). A blank field on the form is filled; a typed one is kept.
- A person already on the register under that ABHA is opened, not registered again; the register's unique ABHA refuses a second file anyway ([D3. patient](../database/D3-patient.md)).

Refused before any call: "An Aadhaar number has 12 digits.", "Ask for the OTP first.", "Enter the OTP that was sent.", "A mobile number has 10 digits.", "An ABHA number has 14 digits.", "Enter the ABHA number, or the mobile it is registered against.", "An ABHA address is 8 to 18 letters, digits, dots or underscores.", "Choose one of the accounts listed.", and on a lapsed login: "The login has lapsed; ask for the OTP again."

A refusal from the service is shown in its words: the `error.code` and `error.message` block, else the field it named invalid. Every call failing the same way is a session or header problem (`everything-returns-401` on the MCP).

#### A19Q. REQUEST

The application's endpoints, behind the session, one per step of the flow; each makes the service call named in A19E **on the server** and answers the page only what the next step needs. The page never sees a token.

| Endpoint | Body | Answers |
|---|---|---|
| `GET abha/certificate` | | `public_key` (the service's certificate, for the page to seal with), `expires_at` |
| `POST abha/enrol/otp`, `/enrol/verify`, `GET abha/enrol/suggestions`, `POST abha/enrol/address`, `POST abha/login/otp`, `/login/verify`, `/login/select` | the function's inputs below, sealed values as sealed by the page | the function's answer below, never a token |

Each step writes one audit line (`enrol_otp_sent`, `enrolled`, `address_set`, `login_otp_sent`, `login_verified`, `login_selected`) on the server; the page cannot write the trail.

The server's ABHA client, which the endpoints call, exposes the flow as these functions; each makes the service call named in A19E.

| Function | Takes | Answers |
|---|---|---|
| `enrolOtp` | `aadhaar`; `txn_id` to resend | `txn_id`, `message` (the masked mobile the OTP went to) |
| `enrolVerify` | `txn_id`, `otp`, `mobile` (optional) | `txn_id`, `is_new`, `profile`, `message` |
| `suggestions` | `txn_id` | `addresses` |
| `enrolAddress` | `txn_id`, `abha_address` (with or without `@sbx` or `@abdm`) | `abha_no`, `abha_address` |
| `loginOtp` | `abha_no` or `mobile` | `txn_id`, `message`, `hint` (`abha-number` or `mobile`) |
| `loginVerify` | `txn_id`, `otp` | `txn_id`, `hint`, `accounts`; by number also `profile` |
| `loginSelect` | `txn_id`, `abha_no` | `profile` |
| `seal` (page side) | a value | the value sealed under the service's certificate (from `GET abha/certificate`), for every identifier and OTP above and for the face authentication's Aadhaar ([A18. Biometric Authentication](A18-biometric-authentication.md)) |

`profile`: `{abha_no, abha_address, name, gender, dob, mobile, status}`. `accounts`: `[{abha_no, name, abha_address, status}]`.

#### A19S. RESPONSE
What the screens do with it ([S13. Patient List](../screens/S13-patient-list.md), [S14. Patient Registration Form](../screens/S14-patient-registration-form.md), [S15. Patient Detail](../screens/S15-patient-detail.md)): "Register with ABHA" runs a verify or create first and opens the registration form filled from the profile, so the desk confirms rather than types; the form's own "Verify or create an ABHA" fills a form already open; a patient on file gets "Link ABHA" or "Verify ABHA", which writes the ABHA number and address onto the row. The X-token is not kept beyond the flow and never leaves the server: nothing else in this skill reads the ABHA profile, and the biometric calls ([A18. Biometric Authentication](A18-biometric-authentication.md)) take their own tokens.

Data: [D3. patient](../database/D3-patient.md)

#### A19P. PSEUDOCODE

```
// PAGE: seals what the person types, holds only txn_id, calls the application's endpoints
function certificate(): webcrypto.importKey("spki", der(GET abha/certificate .public_key), {name: "RSA-OAEP", hash: "SHA-1"})  // the server caches it one hour
function seal(value):   return base64(webcrypto.encrypt({name: "RSA-OAEP"}, certificate(), utf8(value)))
// every screen step: POST abha/<step> with the sealed values; the answer never carries a token

// SERVER: the calls' exact shapes: get(<MCP id>) from the table in A19E; runs in the application
function abha_call(method, path, body, extra):
    headers = {Authorization: "Bearer " + gateway.token().token, "REQUEST-ID": uuid(), TIMESTAMP: now_utc_iso_ms()} + extra   // G3
    answer = http(method, abha_base + path, body, headers)
    if answer.status == 401 and first attempt: gateway.refresh_token(); retry once
    if answer.status >= 300: raise refusal(answer)        // error.code and error.message, else the invalid field
    return answer.body
function remember(txn_id, state): server-side store keyed (txn_id, current user), expires in 15 minutes; never returned to the page
function recall(txn_id):          that state, or none
function audit(action, subject, detail):  audit "abha." + action, entity abha, id subject[:64], detail[:200]

function enrol_otp(aadhaar, txn_id = none):
    d = digits(aadhaar); if len(d) != 12: refuse "An Aadhaar number has 12 digits."
    body = {scope: ["abha-enrol"], loginHint: "aadhaar", loginId: seal(d), otpSystem: "aadhaar"} + (txnId: txn_id if given)
    answer = abha_call(POST, "/enrollment/request/otp", body)
    audit("enrol_otp_sent", answer.txnId, "aadhaar ending " + d[8:])                  // the last four digits, nothing more
    return {txn_id: answer.txnId, message: answer.message}

function enrol_verify(txn_id, otp, mobile):
    answer = abha_call(POST, "/enrollment/enrol/byAadhaar", {
        authData: {authMethods: ["otp"], otp: {txnId: txn_id, otpValue: seal(digits(otp))} + (mobile: last10(mobile) if given)},
        consent: {code: "abha-enrollment", version: "1.4"}})
    profile = profile_from(answer.ABHAProfile or answer); remember(answer.txnId, {token: answer.tokens.token, x: true}); audit("enrolled", profile.abha_no, "new=" + answer.isNew)
    return {txn_id: answer.txnId or txn_id, is_new: answer.isNew, profile, message: answer.message}

function suggestions(txn_id):  return abha_call(GET, "/enrollment/enrol/suggestion", none, {TRANSACTION_ID: txn_id}).abhaAddressList
function enrol_address(txn_id, address):
    a = strip_suffix(address, "@sbx", "@abdm"); check 8..18 chars of [A-Za-z0-9._], first alphanumeric
    answer = abha_call(POST, "/enrollment/enrol/abha-address", {txnId: txn_id, abhaAddress: a, preferred: 1})
    audit("address_set", format(answer.healthIdNumber), answer.preferredAbhaAddress)
    return {abha_no: format(answer.healthIdNumber), abha_address: answer.preferredAbhaAddress}

function login_otp(abha_no, mobile):
    if abha_no: hint, value = "abha-number", digits(abha_no) (14) else hint, value = "mobile", last10(mobile) (10)
    answer = abha_call(POST, "/profile/login/request/otp", {scope: ["abha-login", "mobile-verify"], loginHint: hint, loginId: seal(value), otpSystem: "abdm"})
    remember(answer.txnId, {hint}); audit("login_otp_sent", answer.txnId, hint); return {txn_id: answer.txnId, message: answer.message, hint}

function login_verify(txn_id, otp):
    s = recall(txn_id)
    answer = abha_call(POST, "/profile/login/verify", {scope: ["abha-login", "mobile-verify"],
                 authData: {authMethods: ["otp"], otp: {txnId: txn_id, otpValue: seal(digits(otp))}}})
    if answer.authResult not "success": raise "The ABHA service did not verify the OTP: " + answer.message
    accounts = [account_from(a) for a in answer.accounts]
    if s.hint == "mobile": remember(txn_id, {token: answer.token, hint}); return {txn_id, accounts, hint}   // T-token
    remember(txn_id, {token: answer.token, x: true, hint}); audit("login_verified", txn_id, "by ABHA number")
    return {txn_id, accounts, hint, profile: profile_with(answer.token) or accounts[0]}

function login_select(txn_id, abha_no):
    s = recall(txn_id) or refuse "The login has lapsed; ask for the OTP again."
    chosen = the listed account whose ABHANumber equals abha_no as given, or whose last digits match a full number typed
             or refuse "Choose one of the accounts listed."
    answer = abha_call(POST, "/profile/login/verify/user", {ABHANumber: chosen.ABHANumber /* masked, as listed */, txnId: txn_id}, {"T-token": "Bearer " + s.token})
    remember(txn_id, {token: answer.token, x: true}); audit("login_selected", abha_no, "by mobile"); return {txn_id, profile: profile_with(answer.token)}

function profile_with(x_token):  return profile_from(abha_call(GET, "/profile/account", none, {"X-token": "Bearer " + x_token}))
```

#### A19U. USED BY
- Screens: [S13. Patient List](../screens/S13-patient-list.md), [S14. Patient Registration Form](../screens/S14-patient-registration-form.md), [S18. Beneficiary Verification](../screens/S18-beneficiary-verification.md)
- APIs: [A18. Biometric Authentication](A18-biometric-authentication.md)
- Database: [D3. patient](../database/D3-patient.md)
- Tests: [T19. PMJAY Beneficiary Verification and ABHA](../tests/T19-pmjay-biometric-and-abha.md)
