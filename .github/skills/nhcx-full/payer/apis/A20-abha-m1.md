# A20. ABHA Create and Verify (ABDM M1)

#### A20E. ENDPOINT
Not an NHCX exchange: ABDM's ABHA service, called **from the page, in the desk's browser**, never from the desk's server. The server's part is two doors behind its session: `GET abha/session` hands the page the ABDM session token from [G3. Session Token](../gateway/G3-session-token.md) (the gateway mints it for the payer's participant, and the page cannot hold the credentials that mint it), its expiry and the service's base URL; `POST abha/events` takes one audit line per step. The page carries the token on `Authorization: Bearer`, a fresh `REQUEST-ID` (UUID) and `TIMESTAMP` (UTC, ISO 8601 with milliseconds) on every call, plain JSON, no JWE and no ledger row. Sandbox base `https://abhasbx.abdm.gov.in/abha/api/v3`; production is published by ABDM and confirmed in the onboarding letter. The service answers CORS preflights for the page's origin (the sandbox for any origin), which is what makes the page the caller; the server, which may run where the service's host does not even resolve, makes no ABHA call. [SANDBOX](../references/PAYERS.md#markers) Production's CORS policy is confirmed before go-live.

**The calls, their bodies, headers, responses and errors are read from the MCP, not from this spec.** The `nhcx-docs` MCP server (also published as `abdm-docs`) serves the whole of ABDM's HIE-CM catalogue beside NHCX, and M1 is its first milestone: open its `abdm-m1` prompt (the M1 router), or read these directly with `get`:

| What | MCP id |
|---|---|
| Create an ABHA from an Aadhaar OTP, end to end | `hiecm.flow.m1-create-abha-aadhaar-otp` |
| Verify an existing ABHA by mobile OTP, with the account chooser | `hiecm.flow.m1-login-by-mobile` |
| The encryption certificate every sealed field needs | `m1_get_v3_profile_public_certificate` |
| Send the Aadhaar OTP; verify it and create | `m1_post_v3_enrollment_request_otp_aadhaar_otp`, `m1_post_v3_enrollment_enrol_byaadhaar_otp` |
| Address suggestions; claim the address | `m1_get_v3_enrollment_enrol_suggestion_create_abha_aadhaar_otp`, `m1_post_v3_enrollment_enrol_abha_address_create_abha_aadhaar_otp` |
| Send the OTP for an ABHA number; verify it | `m1_post_v3_profile_login_request_otp_abha_number_abha_otp`, `m1_post_v3_profile_login_verify_abha_number_abha_otp` |
| Send the OTP for a mobile; verify it; choose the account | `m1_post_v3_profile_login_request_otp_mobile`, `m1_post_v3_profile_login_verify_mobile_otp`, `m1_post_v3_profile_login_verify_user` |
| Read the profile the X-token opens | `m1_get_v3_profile_account` |
| Why a call failed | `decode_error` with the `ABDM-` code, and the troubleshooting atoms `everything-returns-401` and `otp-never-arrives` |

The GitHub package (knowledge source option 2) carries no M1 at all: M1 needs the MCP, or the same atoms read on the ABDM developer portal at the `doc_url` the MCP returns.

#### A20D. DESCRIPTION
A member's ABHA number is the handle a hospital's eligibility check and pre-authorisation carry to find the person ([C2. Coverage Eligibility Check](../callbacks/C2-coverage-eligibility-check.md), [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md)), and the account their enrolment is linked to at ABDM ([A16. ABHA Policy Link](A16-abha-policy-link.md)). A number typed at the desk is a number nobody checked. This API puts a **verified** ABHA on the member, two ways, and fills the record from what the ABHA service says: name, gender, date of birth, mobile and the ABHA number.

**Verify an existing ABHA.** By its number, or by the mobile it is registered against. The identifier is sealed under the service's certificate and sent with `scope ["abha-login", "mobile-verify"]`, `loginHint` `abha-number` or `mobile`, `otpSystem abdm`; the OTP goes to the mobile either way. Verifying the OTP by ABHA number answers the account and the X-token directly, and the profile is read with it. Verifying by mobile answers the accounts on that mobile and a short-lived T-token: the desk picks the account, `verify/user` with the chosen `ABHANumber` and the same `txnId` under `T-token` answers the X-token, and then the profile. Always call `verify/user` on the mobile path, even with one account listed.

**Create an ABHA from an Aadhaar OTP.** With the person present and their consent recorded (consent code `abha-enrollment`, version `1.4`): the Aadhaar number sealed as `loginId` with `scope ["abha-enrol"]`, `loginHint aadhaar`, `otpSystem aadhaar`; the OTP goes to the mobile registered against the Aadhaar. `enrol/byAadhaar` with the sealed OTP, the communication mobile and the consent answers `ABHAProfile`, the tokens and **`isNew`**: an Aadhaar that already has an ABHA returns that account with `isNew` false, so read it before telling anyone something was created. A new account then gets its address: suggestions with the `TRANSACTION_ID` header, the chosen one claimed with `preferred 1`.

Rules, both ways:
- The Aadhaar number, the OTP and the identifiers are sealed **in the page** under the certificate from `/profile/public/certificate` (RSA/ECB/OAEPWithSHA-1AndMGF1Padding, base64; WebCrypto's `RSA-OAEP` with `SHA-1` on an `spki` import of the key), fetched once an hour. None of them reaches the server, is stored or logged; the audit event for the OTP step carries the last four digits of an Aadhaar at most.
- The X-token and T-token stay in the page's memory, keyed by the flow's `txnId`, for fifteen minutes; they are never sent to the server. The gateway session token is never sent as an X-token, and the page re-reads `abha/session` when the one it holds is within a minute of its expiry or the service answers 401.
- The profile written onto the member: `abha_no` (14 digits), `name`, `gender` (`M` `F` `O` to Male, Female, Other), `dob` (`DD-MM-YYYY`, or day, month and year, to `YYYY-MM-DD`), `mobile` (left blank when the service masks it). A blank field on the form is filled; a typed one is kept.
- A member already on the register under that ABHA is opened for editing, not registered again; the register's unique ABHA refuses a second row anyway ([D5. member](../database/D5-member.md)).

Refused before any call: "An Aadhaar number has 12 digits.", "Ask for the OTP first.", "Enter the OTP that was sent.", "A mobile number has 10 digits.", "An ABHA number has 14 digits.", "Enter the ABHA number, or the mobile it is registered against.", "An ABHA address is 8 to 18 letters, digits, dots or underscores.", "Choose one of the accounts listed.", and on a lapsed login: "The login has lapsed; ask for the OTP again."

A refusal from the service is shown in its words: the `error.code` and `error.message` block, else the field it named invalid.

#### A20Q. REQUEST

The server's two endpoints, behind the session.

| Endpoint | Body | Answers |
|---|---|---|
| `GET abha/session` | | `token` (the ABDM session token for this participant), `expires_at`, `expires_in`, `base_url` (the ABHA service) |
| `POST abha/events` | `action` (one of `enrol_otp_sent`, `enrolled`, `address_set`, `login_otp_sent`, `login_verified`, `login_selected`), `subject` (the ABHA number or the `txnId`), `detail` (a few words) | `recorded`; any other `action` is refused (422), so the page cannot write arbitrary lines into the trail |

The page's ABHA client, which the screens call, exposes the flow as seven functions with these shapes; each makes the service call named in A20E.

| Function | Takes | Answers |
|---|---|---|
| `enrolOtp` | `aadhaar`; `txn_id` to resend | `txn_id`, `message` (the masked mobile the OTP went to) |
| `enrolVerify` | `txn_id`, `otp`, `mobile` (optional) | `txn_id`, `is_new`, `profile`, `message` |
| `suggestions` | `txn_id` | `addresses` |
| `enrolAddress` | `txn_id`, `abha_address` (with or without `@sbx` or `@abdm`) | `abha_no`, `abha_address` |
| `loginOtp` | `abha_no` or `mobile` | `txn_id`, `message`, `hint` (`abha-number` or `mobile`) |
| `loginVerify` | `txn_id`, `otp` | `txn_id`, `hint`, `accounts`; by number also `profile` |
| `loginSelect` | `txn_id`, `abha_no` | `profile` |
| `seal` | a value | the value sealed under the service's certificate, for the face authentication's Aadhaar ([A18. Provider Driver](A18-provider-driver.md)) |

`profile`: `{abha_no, abha_address, name, gender, dob, mobile, status}`. `accounts`: `[{abha_no, name, abha_address, status}]`.

#### A20S. RESPONSE
What the member screen does with it ([S4. Members](../screens/S4-members.md)): "Register with ABHA" runs a verify or create first and opens the registration dialog filled from the profile, so the desk confirms rather than types; the dialog's own "Verify or create an ABHA" fills a dialog already open. The ABHA address is not kept on the member (the member record holds the number); the X-token is not kept beyond the flow.

Data: [D5. member](../database/D5-member.md)

#### A20P. PSEUDOCODE

```
// SERVER: the two doors
GET abha/session:   info = gateway_token(sender)          // the adapter's GET /token for the participant, with expires_at
                    return {token: info.token, expires_at: info.expires_at, expires_in: info.expires_in, base_url: abha_base}
POST abha/events:   if action not in {enrol_otp_sent, enrolled, address_set, login_otp_sent, login_verified, login_selected}: refuse 422
                    audit "abha." + action, entity abha, id subject[:64], detail[:200]

// PAGE: the calls' exact shapes: get(<MCP id>) from the table in A20E; runs in the browser
function session():     cached {token, base_url} from GET abha/session, re-read within a minute of expires_at or after a 401
function certificate(): webcrypto.importKey("spki", der(GET /profile/public/certificate .publicKey), {name: "RSA-OAEP", hash: "SHA-1"})  // cached one hour
function seal(value):   return base64(webcrypto.encrypt({name: "RSA-OAEP"}, certificate(), utf8(value)))
function abha_call(method, path, body, extra):
    headers = {Authorization: "Bearer " + session().token, "REQUEST-ID": uuid(), TIMESTAMP: now_utc_iso_ms()} + extra
    answer = fetch(method, session().base_url + path, body, headers)       // CORS: the service allows the page's origin
    if answer.status >= 300: raise refusal(answer)        // error.code and error.message, else the invalid field
    return answer.body
function audit(action, subject, detail):  POST abha/events {action, subject, detail}, failure ignored

function enrol_otp(aadhaar, txn_id = none):
    d = digits(aadhaar); if len(d) != 12: refuse "An Aadhaar number has 12 digits."
    answer = abha_call(POST, "/enrollment/request/otp", {scope: ["abha-enrol"], loginHint: "aadhaar", loginId: seal(d), otpSystem: "aadhaar"} + (txnId: txn_id if given))
    audit("enrol_otp_sent", answer.txnId, "aadhaar ending " + d[8:]); return {txn_id: answer.txnId, message: answer.message}

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
    answer = abha_call(POST, "/profile/login/verify/user", {ABHANumber: format(digits(abha_no)), txnId: txn_id}, {"T-token": "Bearer " + s.token})
    remember(txn_id, {token: answer.token, x: true}); audit("login_selected", abha_no, "by mobile"); return {txn_id, profile: profile_with(answer.token)}

function profile_with(x_token):  return profile_from(abha_call(GET, "/profile/account", none, {"X-token": "Bearer " + x_token}))
```

#### A20U. USED BY
- Screens: [S4. Members](../screens/S4-members.md)
