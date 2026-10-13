# HIE-CM p2 build

Scaffolds an ABDM p2 integration one journey at a time. It covers the PHR profile, linking an ABHA number, switching profiles, and linking, sharing and consent for the patient.

## How this skill runs

Every journey below is an OODA loop, not a recipe: observe the actual state (last response, last error), orient against the step matched below, decide the cheapest next action, act, and return to observe. A step is done only when its exit condition is observed against the sandbox, never because it "should have worked."

Loop limit: 8 passes per step. Hitting the limit is an escalation: state what was observed, what was tried, and which operation page to read, then ask one question.

## Before the first journey, when the codebase already exists

Skip this section only for a system that does not exist yet. Otherwise it runs first, and its exit condition is a written plan, not a call.

### In plain words

Most ABDM integrations are not new systems. They are a hospital management
system, a laboratory system or a clinic application that already has patients,
visits, records, a login, an HTTP client and a way of keeping secrets. Every
ABDM journey has to land somewhere inside that, and a journey built before the
codebase has been read lands in the wrong place: a second HTTP client beside the
first, an ABHA column on the wrong table, a callback route the reverse proxy
never forwards.

So the first loop is not a journey. It is a survey of the system as it is, and
its exit condition is a written plan that names, for every ABDM touchpoint, the
file it will live in. The journeys then build against that plan rather than
against the specification's idea of a fresh codebase.

### Before you start

- The repository, checked out, with permission to read all of it. A survey of
  half a codebase produces a plan for half a system.
- The answers to the deployment interview. The
  code says what the system is. Only the integrator can say what the
  deployment is, and the two together decide which journeys are built at all.
- The practices that hold across every call, which
  the plan has to leave room for.

### What happens

This is one loop with a limit of eight passes over the codebase. Each pass
reads live state only, which here means the files themselves, never a README's
description of them and never an assumption carried from a similar system.

**Observe.** Inventory the system from its manifests and its tree, not from its
documentation. Record file paths for each of these, or record that none exists:

| Find | Where it usually shows | Why ABDM needs it |
|---|---|---|
| Languages and runtime versions | package manifests, lock files, toolchain files | Every generated call has to be idiomatic here |
| Build, run and test commands | manifests, CI configuration, a Makefile | Each journey's exit condition becomes a test that runs the same way |
| The frontend and backend split, and how they talk | the top level tree, an API client in the frontend, route definitions in the backend | The counter screens go in the frontend; every ABDM call goes through the backend |
| The outbound HTTP client the backend already uses | the dependency list, a shared client module | ABDM calls reuse it, or a second one appears and the two drift |
| How secrets and configuration reach the process | environment loading, a vault client, a config file | The client id, the secret and the access token travel the same way |
| The patient model, and the identifier fields it already carries | the schema, the ORM models, the migrations | The ABHA number and address become columns beside the existing identifiers, not a new table |
| The visit, encounter or record model | the same places | A care context maps to one of these, and the plan has to say which |
| Where inbound HTTP is routed and authenticated, and whether the deployment has a public URL | the router, the middleware, the reverse proxy configuration, the deployment manifests | ABDM calls back, and a callback route that nothing forwards is silence nobody notices |
| Existing cryptography helpers | a security or crypto module, the dependency list | The RSA encryption of identifiers reuses them |
| Where errors are shown to a user, and where they are logged | the frontend's error surface, the logging setup | A refused call has to land on the screen the person is looking at, and never log a token |

**Orient.** Map each ABDM touchpoint onto that inventory. Where the map is
exact, write the file path. Where it is not, write two candidates and say what
would decide between them. The common ambiguities: two places that could hold
the patient identifier, an HTTP client in the frontend and none in the backend,
a monorepo with several services and no obvious owner for callbacks.

Then read the interview answers against the inventory. A government integrator
gets the demographic route; a facility with no public URL gets no callback
driven journey until it has one; a desk with a fingerprint reader gets the
biometric method. The route set is the intersection of what the deployment
allows and what the code can host.

**Decide.** Order the journeys. The token comes first because every other call
needs it: the gateway session token, or for M4 the bearer token the registry calls
carry. Then the journey whose exit condition can be observed with
the least new code, usually a profile read for a patient who already holds an
ABHA. Creation and linking come after, because each depends on state the earlier
ones produce. For each journey, name the files it will touch and the test that
proves its exit condition.

**Act.** Write the plan. It is a file in the repository, at the path the
integrator names or at the root as `abdm-integration-plan.md`, and it is the
only output of this loop. Then return to observe once, reading the plan against
the tree, to confirm every path in it exists or is marked as new.

If the limit is reached with questions still open, escalate: name what was
found, name the two candidates that could not be separated, point at this
atom, and ask one question.

### How you know it worked

The plan exists and answers every row of the inventory table with a file path,
or with the words none, add at, followed by a path. No row is blank and no row
says to be decided.

Every ABDM touchpoint in the plan names one file, or names two candidates and
the observation that would choose between them. Every journey in the plan names
the test that proves its exit condition and the command that runs it.

Open the plan beside the tree. Every path it names resolves, or is marked as
new. That is the observation that ends this loop, and the first journey does
not start until it has been made.

### When it goes wrong

- **The plan puts the HTTP client in the frontend.** The survey found the
  frontend's API client and stopped. Every ABDM call carries a secret, so it
  goes through the backend, and the plan has to say which backend module.
- **Two patient tables, and the plan picked one.** Orient produced one
  hypothesis where it needed two. Name both, and name the query that shows
  which one the visit model points at.
- **The plan has a callback route and the deployment has no public URL.** The
  inventory row on inbound routing was answered from the router rather than
  from the deployment. Mark every callback driven journey as blocked on a URL,
  and build the ones that are not.
- **The survey read the README and not the tree.** A README describes the
  system somebody meant to build. The plan is for the one that exists.
- **Eight passes and the plan is still incomplete.** Escalate with the rows
  that are answered, the rows that are not, this atom, and one question about
  the row that blocks the most journeys.

From `shared.concept.survey-an-existing-codebase`.

## Journeys

### PHR profile, update mobile (`p2-update-mobile`)

**Act: the calls in this journey, in order**

#### 1. Request profile OTP (`p2_post_v3_phr_app_login_profile_request_otp`)

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/login/profile/request/otp \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'X-token: Bearer <JWT TOKEN>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'Content-Type: application/json' \
  --data '{
  "scope": [
    "abha-address-profile",
    "mobile-verify"
  ],
  "loginHint": "mobile-number",
  "loginId": "{{encryptedData}}",
  "otpSystem": "abdm"
}'
```

#### 2. Login profile verify (`p2_post_v3_phr_app_login_profile_verify`)

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/login/profile/verify \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'X-token: Bearer <JWT TOKEN>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'Content-Type: application/json' \
  --data '{
  "scope": [
    "abha-address-profile",
    "mobile-verify"
  ],
  "authData": {
    "authMethods": [
      "otp"
    ],
    "otp": {
      "txnId": "37d8d312-35a0-41e7-a6e4-1074eb18a5fa",
      "otpValue": "{{encryptedData}}"
    }
  }
}'
```

**Exit condition (Observe until this is true)**

A 200 whose body matches:

```json
{
  "txnId": "e10ca603-97f5-4cf2-8191-d51ea7db3845",
  "message": "Entered OTP is incorrect. Kindly re-enter valid OTP.",
  "authResult": "failed",
  "users": []
}
```

### PHR profile, update password (`p2-update-password`)

**Act: the calls in this journey, in order**

#### 1. Login profile verify (`p2_post_v3_phr_app_login_profile_verify`)

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/login/profile/verify \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'X-token: Bearer <JWT TOKEN>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'Content-Type: application/json' \
  --data '{
  "scope": [
    "abha-address-profile",
    "password-verify"
  ],
  "authData": {
    "authMethods": [
      "password"
    ],
    "password": {
      "abhaAddress": "<ABHA_ADDRESS>",
      "password": "{{encryptedData}}"
    }
  }
}'
```

**Exit condition (Observe until this is true)**

A 200 whose body matches:

```json
{
  "txnId": "e10ca603-97f5-4cf2-8191-d51ea7db3845",
  "message": "Entered OTP is incorrect. Kindly re-enter valid OTP.",
  "authResult": "failed",
  "users": []
}
```

### Link ABHA number, ABHA OTP (`p2-link-abha-number-abha-otp`)

**Act: the calls in this journey, in order**

#### 1. Request profile OTP (`p2_post_v3_phr_app_login_profile_request_otp`)

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/login/profile/request/otp \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'X-token: Bearer <JWT TOKEN>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'Content-Type: application/json' \
  --data '{
  "scope": [
    "abha-login",
    "mobile-verify"
  ],
  "loginHint": "abha-number",
  "loginId": "<ENCRYPTED_LOGIN_ID>",
  "otpSystem": "abdm"
}'
```

#### 2. Login profile verify (`p2_post_v3_phr_app_login_profile_verify`)

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/login/profile/verify \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'X-token: Bearer <JWT TOKEN>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'Content-Type: application/json' \
  --data '{
  "scope": [
    "abha-login",
    "mobile-verify"
  ],
  "authData": {
    "authMethods": [
      "otp"
    ],
    "otp": {
      "txnId": "37d8d312-35a0-41e7-a6e4-1074eb18a5fa",
      "otpValue": "{{encryptedData}}"
    }
  }
}'
```

#### 3. Link request (`p2_post_v3_phr_app_login_profile_link`)

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/login/profile/link \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'X-token: Bearer <JWT TOKEN>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'Content-Type: application/json' \
  --data '{
  "action": "LINK",
  "transactionId": "37d8d312-35a0-41e7-a6e4-1074eb18a5fa"
}'
```

**Exit condition (Observe until this is true)**

A 200 whose body matches:

```json
{
  "message": "ABHA number is securely linked to ABHA address",
  "authResult": "success"
}
```

### Link ABHA number, Aadhaar OTP (`p2-link-abha-number-aadhaar-otp`)

**Act: the calls in this journey, in order**

#### 1. Request profile OTP (`p2_post_v3_phr_app_login_profile_request_otp`)

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/login/profile/request/otp \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'X-token: Bearer <JWT TOKEN>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'Content-Type: application/json' \
  --data '{
  "scope": [
    "abha-login",
    "aadhaar-verify"
  ],
  "loginHint": "abha-number",
  "loginId": "<ENCRYPTED_LOGIN_ID>",
  "otpSystem": "aadhaar"
}'
```

#### 2. Login profile verify (`p2_post_v3_phr_app_login_profile_verify`)

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/login/profile/verify \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'X-token: Bearer <JWT TOKEN>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'Content-Type: application/json' \
  --data '{
  "scope": [
    "abha-login",
    "aadhaar-verify"
  ],
  "authData": {
    "authMethods": [
      "otp"
    ],
    "otp": {
      "txnId": "37d8d312-35a0-41e7-a6e4-1074eb18a5fa",
      "otpValue": "<ENCRYPTED_OTP_VALUE>"
    }
  }
}'
```

#### 3. Link request (`p2_post_v3_phr_app_login_profile_link`)

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/login/profile/link \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'X-token: Bearer <JWT TOKEN>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'Content-Type: application/json' \
  --data '{
  "action": "LINK",
  "transactionId": "37d8d312-35a0-41e7-a6e4-1074eb18a5fa"
}'
```

**Exit condition (Observe until this is true)**

A 200 whose body matches:

```json
{
  "message": "ABHA number is securely linked to ABHA address",
  "authResult": "success"
}
```

### PHR profile, switch profile (`p2-switch-profile`)

**Act: the calls in this journey, in order**

#### 1. Switch profile (`p2_get_v3_phr_app_login_profile_switch_profile`)

```bash
curl --request GET \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/login/profile/switch-profile \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'X-token: Bearer <JWT TOKEN>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z'
```

#### 2. Verify user switch profile (`p2_post_v3_phr_app_login_profile_verify_switch_profile_user`)

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/login/profile/verify/switch-profile/user \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'T-token: Bearer <JWT TOKEN>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'Content-Type: application/json' \
  --data '{
  "abhaAddress": "<ABHA_ADDRESS>",
  "txnId": "37d8d312-35a0-41e7-a6e4-1074eb18a5fa"
}'
```

**Exit condition (Observe until this is true)**

A 200 whose body matches:

```json
{
  "token": "<JWT TOKEN>",
  "expiresIn": 1800,
  "refreshToken": "<JWT TOKEN>",
  "refreshExpiresIn": 1296000
}
```

### PHR profile, card, QR code and session (`p2-profile`)

**Act: the calls in this journey, in order**

#### 1. Get profile (`p2_get_v3_phr_app_login_profile`)

```bash
curl --request GET \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/login/profile \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'X-token: Bearer <JWT TOKEN>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-AUTH-TOKEN: <X_AUTH_TOKEN>'
```

#### 2. Get QR code (`p2_get_v3_phr_app_login_profile_qrcode`)

```bash
curl --request GET \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/login/profile/qrCode \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'X-token: Bearer <JWT TOKEN>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-AUTH-TOKEN: <X_AUTH_TOKEN>'
```

#### 3. Get PHR card (`p2_get_v3_phr_app_login_profile_phrcard`)

```bash
curl --request GET \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/login/profile/phrCard \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'X-token: Bearer <JWT TOKEN>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-AUTH-TOKEN: <X_AUTH_TOKEN>'
```

#### 4. Update profile (`p2_post_v3_phr_app_login_profile_updateprofile`)

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/login/profile/updateProfile \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'X-token: Bearer <JWT TOKEN>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'Content-Type: application/json' \
  --data '{
  "profilePhoto": "",
  "firstName": "John",
  "middleName": "",
  "lastName": "Doe",
  "dayOfBirth": "<DOB>",
  "monthOfBirth": "<DOB>",
  "yearOfBirth": "<DOB>",
  "gender": "M",
  "email": "<EMAIL>",
  "mobile": "******0903",
  "address": "<ADDRESS>",
  "stateName": "Maharashtra",
  "districtName": "<ADDRESS>",
  "pinCode": "<PINCODE>",
  "stateCode": "27",
  "districtCode": "12"
}'
```

#### 5. Refresh token (`p2_get_v3_phr_app_login_profile_request_token`)

```bash
curl --request GET \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/login/profile/request/token \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'R-token: Bearer <JWT TOKEN>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z'
```

#### 6. Logout (`p2_get_v3_phr_app_login_profile_request_logout`)

```bash
curl --request GET \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/login/profile/request/logout \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'X-token: Bearer <JWT TOKEN>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z'
```

**Exit condition (Observe until this is true)**

A 200 whose body matches:

```json
{
  "message": "You have been logged out",
  "timestamp": "2023-07-27T13:36:28.000Z"
}
```

### Quick OPD Registration (`p2-abdm-hiecm-patient-share-phr`)

**Act: the calls in this journey, in order**

#### 1. OPD token generation (`p2_post_patient_share_v3_share`)

```bash
curl --request POST \
  --url https://dev.abdm.gov.in/api/hiecm/patient-share/v3/share \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx' \
  --header 'X-HIU-ID: HIU_ID' \
  --header 'X-AUTH-TOKEN: Bearer <TOKEN>' \
  --header 'Content-Type: application/json' \
  --data '{
  "intent": "PROFILE_SHARE",
  "metaData": {
    "hipId": "HIP_1",
    "context": "6",
    "hprId": "<EMAIL>",
    "latitude": 20.5937,
    "longitude": 78.9629
  },
  "profile": {
    "patient": {
      "abhaNumber": "<ABHA_NUMBER>",
      "abhaAddress": "<ABHA_ADDRESS>",
      "name": "<NAME>",
      "gender": "M",
      "dayOfBirth": "<DOB>",
      "monthOfBirth": "<DOB>",
      "yearOfBirth": "9999",
      "address": {
        "line": "Address line 1",
        "district": "Coimbatore",
        "state": "Tamil Nadu",
        "pincode": "<PINCODE>"
      },
      "phoneNumber": "<MOBILE_NUMBER>"
    }
  }
}'
```

#### 2. Receive the HIU patient on share (`p2_post_v3_hiu_patient_on_share`)

Inbound to your bridge at `/api/v3/hiu/patient/on-share`. Acknowledge it and continue.

#### 3. OPD Token History (`p2_get_patient_share_v3_profile_gettokendetails`)

```bash
curl --request GET \
  --url "https://dev.abdm.gov.in/api/hiecm/patient-share/v3/profile/getTokenDetails?limit=<LIMIT>" \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx' \
  --header 'X-AUTH-TOKEN: Bearer <TOKEN>'
```

**Exit condition (Observe until this is true)**

Each call you made in this journey answered by its callback, with `response.requestId` equal to the `REQUEST-ID` you sent on that call. The 202 on a call is receipt, not the outcome: the outcome is in the callback's body.

- `POST /api/hiecm/patient-share/v3/share` is answered by `POST /api/v3/hiu/patient/on-share` on your bridge.

Then `GET /api/hiecm/patient-share/v3/profile/getTokenDetails` returns a 200 whose body matches:

```json
[
  {
    "id": 1,
    "patientId": "<ABHA_ADDRESS>",
    "tokenNumber": "1",
    "hipId": "ABDM_HIP",
    "hipName": "Health Information Provider Name",
    "hipAddress": "sample address",
    "expiresIn": 1800,
    "clientId": "ABDM",
    "dateCreated": "2024-09-11T07:31:02.357Z",
    "counterCode": "Counter 1"
  }
]
```

### User initiated linking (`p2-abdm-user-initiated-linking-phr`)

**Act: the calls in this journey, in order**

#### 1. Fetch the list of providers filtered by name (`p2_get_gateway_v3_providers`)

```bash
curl --request GET \
  --url https://dev.abdm.gov.in/api/hiecm/gateway/v3/providers \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx'
```

#### 2. Fetch the record for provider details for requested provider ID (`p2_get_gateway_v3_providers_provider_id`)

```bash
curl --request GET \
  --url https://dev.abdm.gov.in/api/hiecm/gateway/v3/providers/{hip-id} \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx'
```

#### 3. Discover his/her health records (`p2_post_user_initiated_linking_v3_patient_care_context_discover`)

```bash
curl --request POST \
  --url https://dev.abdm.gov.in/api/hiecm/user-initiated-linking/v3/patient/care-context/discover \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx' \
  --header 'X-HIU-ID: IN2810014366' \
  --header 'X-AUTH-TOKEN: <TOKEN>' \
  --header 'Content-Type: application/json' \
  --data '{
  "hip": {
    "id": "cowin_hip_01"
  },
  "unverifiedIdentifiers": [
    {
      "type": "MOBILE",
      "value": "+9198765*****"
    }
  ]
}'
```

#### 4. Receive the discovered care contexts of a patient (`p2_post_v3_hiu_patient_care_context_on_discover`)

Inbound to your bridge at `/api/v3/hiu/patient/care-context/on-discover`. Acknowledge it and continue.

#### 5. Link his/her health records (`p2_post_user_initiated_linking_v3_link_care_context_init`)

```bash
curl --request POST \
  --url https://dev.abdm.gov.in/api/hiecm/user-initiated-linking/v3/link/care-context/init \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx' \
  --header 'X-HIU-ID: IN2810014366' \
  --header 'X-AUTH-TOKEN: <TOKEN>' \
  --header 'Content-Type: application/json' \
  --data '{
  "transactionId": "f901b782-bfdf-4224-9f8d-da2cadc20c0d",
  "patient": [
    {
      "referenceNumber": "<ABHA_ADDRESS>",
      "display": "Test",
      "careContexts": [
        {
          "referenceNumber": "abc123",
          "display": "Sugar Test"
        }
      ],
      "hiType": "OPConsultation",
      "count": 1
    }
  ]
}'
```

#### 6. Receive the initial linking of care contexts for a patient (`p2_post_v3_hiu_patient_care_context_on_init`)

Inbound to your bridge at `/api/v3/hiu/patient/care-context/on-init`. Acknowledge it and continue.

#### 7. Confirm his/her health records (`p2_post_user_initiated_linking_v3_link_care_context_confirm`)

```bash
curl --request POST \
  --url https://dev.abdm.gov.in/api/hiecm/user-initiated-linking/v3/link/care-context/confirm \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx' \
  --header 'X-HIU-ID: IN2810014366' \
  --header 'X-AUTH-TOKEN: <TOKEN>' \
  --header 'Content-Type: application/json' \
  --data '{
  "token": 123456,
  "linkRefNumber": "d353b782-bfdf-4224-9f8d-da2cadc20c0d"
}'
```

#### 8. Receive confirmation of the linked care contexts for a patient (`p2_post_v3_hiu_patient_care_context_on_confirm`)

Inbound to your bridge at `/api/v3/hiu/patient/care-context/on-confirm`. Acknowledge it and continue.

#### 9. Fetch the list of govt programmes (optional) (`p2_get_gateway_v3_govt_programs`)

```bash
curl --request GET \
  --url https://dev.abdm.gov.in/api/hiecm/gateway/v3/govt-programs \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx'
```

**Exit condition (Observe until this is true)**

Each call you made in this journey answered by its callback, with `response.requestId` equal to the `REQUEST-ID` you sent on that call. The 202 on a call is receipt, not the outcome: the outcome is in the callback's body.

- `POST /api/hiecm/user-initiated-linking/v3/patient/care-context/discover` is answered by `POST /api/v3/hiu/patient/care-context/on-discover` on your bridge.
- `POST /api/hiecm/user-initiated-linking/v3/link/care-context/init` is answered by `POST /api/v3/hiu/patient/care-context/on-init` on your bridge.
- `POST /api/hiecm/user-initiated-linking/v3/link/care-context/confirm` is answered by `POST /api/v3/hiu/patient/care-context/on-confirm` on your bridge.

Then `GET /api/hiecm/gateway/v3/govt-programs` returns a 200 whose body matches:

```json
[
  {
    "identifier": {
      "name": "AB - PMJAY",
      "id": "PMJAY"
    },
    "facilityType": [
      "HIP"
    ],
    "isHIP": true
  }
]
```

### Consent manager, HIU and HIP (`p2-consent-manager-hiu-hip`)

**Act: the calls in this journey, in order**

#### 1. Link patient links (`p2_get_hip_v3_link_patient_links`)

```bash
curl --request GET \
  --url "https://dev.abdm.gov.in/api/hiecm/hip/v3/link/patient/links?limit=<LIMIT>" \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx' \
  --header 'X-AUTH-TOKEN: <X_AUTH_TOKEN>'
```

#### 2. Initiate the consent request (`m3_post_consent_v3_request_init`)

```bash
curl --request POST \
  --url https://dev.abdm.gov.in/api/hiecm/consent/v3/request/init \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx' \
  --header 'Content-Type: application/json' \
  --data '{
  "consent": {
    "purpose": {
      "text": "Care Management",
      "code": "CAREMGT",
      "refUri": "www.abc.com"
    },
    "patient": {
      "id": "<ABHA_ADDRESS>"
    },
    "hip": null,
    "hiu": {
      "id": "cowin_hiu_01"
    },
    "careContexts": [
      {
        "patientReference": "batman@tmh",
        "careContextReference": "Episode1"
      }
    ],
    "requester": {
      "name": "<ABHA_ADDRESS>",
      "identifier": {
        "value": "REG1",
        "type": "MH1001",
        "system": "https://www.sample.com"
      }
    },
    "hiTypes": [
      "Prescription"
    ],
    "permission": {
      "accessMode": "VIEW",
      "dateRange": {
        "from": "2021-09-28T12:30:08.573Z",
        "to": "2021-09-28T12:30:08.573Z"
      },
      "dataEraseAt": "2021-09-28T12:30:08.573Z",
      "frequency": {
        "unit": "HOUR",
        "value": 1,
        "repeats": 0
      }
    }
  }
}'
```

#### 3. Get consent request status (`m3_post_consent_v3_request_status`)

```bash
curl --request POST \
  --url https://dev.abdm.gov.in/api/hiecm/consent/v3/request/status \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx' \
  --header 'X-HIU-ID: IN2810014366' \
  --header 'Content-Type: application/json' \
  --data '{
  "consentRequestId": "5f7a535d-a3fd-416b-b069-c97d021fbacd"
}'
```

#### 4. Acknowledge the consent notification (`m2_post_consent_v3_request_hip_on_notify`)

```bash
curl --request POST \
  --url https://dev.abdm.gov.in/api/hiecm/consent/v3/request/hip/on-notify \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx' \
  --header 'Content-Type: application/json' \
  --data '{
  "acknowledgement": {
    "status": "OK",
    "consentId": "e3c74829-3f82-4f94-959e-e10f57bcd57b"
  },
  "response": {
    "requestId": "6f0b4665-a915-4c92-aa36-65afb4a2cd71"
  }
}'
```

#### 5. Acknowledge the consent notification (`m3_post_consent_v3_request_hiu_on_notify`)

```bash
curl --request POST \
  --url https://dev.abdm.gov.in/api/hiecm/consent/v3/request/hiu/on-notify \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx' \
  --header 'Content-Type: application/json' \
  --data '{
  "acknowledgement": [
    {
      "status": "OK",
      "consentId": "e3c74829-3f82-4f94-959e-e10f57bcd57b"
    }
  ],
  "error": {
    "code": "ABDM-1001",
    "message": "unable to connect database"
  },
  "response": {
    "requestId": "6f0b4665-a915-4c92-aa36-65afb4a2cd71"
  }
}'
```

#### 6. Fetch the consent details (`m3_post_consent_v3_fetch`)

```bash
curl --request POST \
  --url https://dev.abdm.gov.in/api/hiecm/consent/v3/fetch \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx' \
  --header 'X-HIU-ID: IN2810014366' \
  --header 'Content-Type: application/json' \
  --data '{
  "consentId": "5f7a535d-a3fd-416b-b069-c97d021fbacd"
}'
```

**Exit condition (Observe until this is true)**

Each call you made in this journey answered by its callback, with `response.requestId` equal to the `REQUEST-ID` you sent on that call. The 202 on a call is receipt, not the outcome: the outcome is in the callback's body.

- `POST /api/hiecm/consent/v3/request/init` is answered by `POST /api/v3/hiu/consent/request/on-init` on your bridge.
- `POST /api/hiecm/consent/v3/request/status` is answered by `POST /api/v3/hiu/consent/request/on-status` on your bridge.
- `POST /api/hiecm/consent/v3/fetch` is answered by `POST /api/v3/hiu/consent/on-fetch` on your bridge.

### Consent manager, fetch and manage consent requests (`p2-consent-management-data-flow-phr`)

**Act: the calls in this journey, in order**

#### 1. Setup an auto-approval policy for given HIU (`p2_post_consent_v3_auto_approve`)

```bash
curl --request POST \
  --url https://dev.abdm.gov.in/api/hiecm/consent/v3/auto/approve \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx' \
  --header 'X-AUTH-TOKEN: <TOKEN>' \
  --header 'Content-Type: application/json' \
  --data '{
  "isApplicableForAllHIPs": false,
  "hiu": {
    "id": "cowin_hiu_01",
    "name": "Cowin",
    "type": "HIU"
  },
  "includedSources": [
    {
      "hiTypes": [
        "Prescription"
      ],
      "purpose": {
        "text": "Care Management",
        "code": "CAREMGT",
        "refUri": "www.abc.com"
      },
      "hip": {
        "id": "cowin_hip_01",
        "name": "Cowin",
        "type": "HIP"
      },
      "period": {
        "from": "2021-09-28T12:30:08.573Z",
        "to": "2021-09-28T12:30:08.573Z"
      }
    }
  ],
  "excludedSources": [
    {
      "hiTypes": [
        "Prescription"
      ],
      "purpose": {
        "text": "Care Management",
        "code": "CAREMGT",
        "refUri": "www.abc.com"
      },
      "hip": {
        "id": "cowin_hip_01",
        "name": "Cowin",
        "type": "HIP"
      },
      "period": {
        "from": "2021-09-28T12:30:08.573Z",
        "to": "2021-09-28T12:30:08.573Z"
      }
    }
  ]
}'
```

#### 2. Disable the auto-approval policy (`p2_post_consent_v3_auto_approve_auto_approval_id_disable`)

```bash
curl --request POST \
  --url https://dev.abdm.gov.in/api/hiecm/consent/v3/auto/approve/{consentId}/disable \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx' \
  --header 'X-AUTH-TOKEN: <TOKEN>'
```

#### 3. Enable the auto-approval policy (`p2_post_consent_v3_auto_approve_auto_approval_id_enable`)

```bash
curl --request POST \
  --url https://dev.abdm.gov.in/api/hiecm/consent/v3/auto/approve/{consentId}/enable \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx' \
  --header 'X-AUTH-TOKEN: <TOKEN>'
```

#### 4. Fetch all the consent request details of a patient (`p2_get_consent_v3_request`)

```bash
curl --request GET \
  --url "https://dev.abdm.gov.in/api/hiecm/consent/v3/request?limit=<LIMIT>" \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx' \
  --header 'X-AUTH-TOKEN: <TOKEN>'
```

#### 5. Get the consent request details by REQUEST-ID (`p2_get_consent_v3_request_request_id`)

```bash
curl --request GET \
  --url https://dev.abdm.gov.in/api/hiecm/consent/v3/request/{consentRequestId} \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx' \
  --header 'X-AUTH-TOKEN: <TOKEN>'
```

#### 6. Approve the consent request raised by HIU from PHR/mobile application (`p2_post_consent_v3_request_request_id_approve`)

```bash
curl --request POST \
  --url https://dev.abdm.gov.in/api/hiecm/consent/v3/request/{consentRequestId}/approve \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx' \
  --header 'X-AUTH-TOKEN: <TOKEN>' \
  --header 'Content-Type: application/json' \
  --data '{
  "consents": [
    {
      "hiTypes": [
        "Prescription"
      ],
      "hip": {
        "id": "ABCD_12345",
        "name": "ABCD Hospital",
        "type": "HIP"
      },
      "careContexts": [
        {
          "patientReference": "batman@tmh",
          "careContextReference": "Episode1"
        }
      ],
      "permission": {
        "dateRange": {
          "from": "2021-09-28T12:30:08.573Z",
          "to": "2021-09-28T12:30:08.573Z"
        },
        "frequency": {
          "unit": "HOUR",
          "value": 1,
          "repeats": 0
        },
        "accessMode": "VIEW",
        "dataEraseAt": "2021-09-28T12:30:08.573Z"
      }
    }
  ]
}'
```

#### 7. Deny the consent request raised by HIU from PHR/mobile application (`p2_post_consent_v3_request_request_id_deny`)

```bash
curl --request POST \
  --url https://dev.abdm.gov.in/api/hiecm/consent/v3/request/{consentRequestId}/deny \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx' \
  --header 'X-AUTH-TOKEN: <TOKEN>' \
  --header 'Content-Type: application/json' \
  --data '{
  "reason": "Not authorized"
}'
```

#### 8. Revoke the granted consent from PHR/mobile application (`p2_post_consent_v3_revoke`)

```bash
curl --request POST \
  --url https://dev.abdm.gov.in/api/hiecm/consent/v3/revoke \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx' \
  --header 'X-AUTH-TOKEN: <TOKEN>' \
  --header 'Content-Type: application/json' \
  --data '{
  "consents": [
    "3fa85f64-5717-4562-b3fc-2c963f66afa6"
  ]
}'
```

#### 9. Request artefact by consent REQUEST-ID (`p2_get_consent_v3_artefact_request_request_id`)

```bash
curl --request GET \
  --url https://dev.abdm.gov.in/api/hiecm/consent/v3/artefact/request/{consentRequestId} \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx' \
  --header 'X-AUTH-TOKEN: <TOKEN>'
```

#### 10. Fetch the consent artefact details associated with the artefact-ID (`p2_get_consent_v3_artefact_artefact_id`)

```bash
curl --request GET \
  --url https://dev.abdm.gov.in/api/hiecm/consent/v3/artefact/{consentId} \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx' \
  --header 'X-AUTH-TOKEN: <TOKEN>'
```

#### 11. Fetch all the consent artefact details of a patient (`p2_get_consent_v3_artefact`)

```bash
curl --request GET \
  --url "https://dev.abdm.gov.in/api/hiecm/consent/v3/artefact?limit=<LIMIT>" \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx' \
  --header 'X-AUTH-TOKEN: <TOKEN>'
```

**Exit condition (Observe until this is true)**

A 200 whose body matches:

```json
{
  "size": 10,
  "limit": 10,
  "offset": 0,
  "consentArtefacts": [
    {
      "status": "GRANTED",
      "consentDetail": {
        "consentId": "e5ec415f-c098-40f6-a0db-faa162fc5295",
        "purpose": {
          "text": "Care Management",
          "code": "CAREMGT",
          "refUri": "www.abc.com"
        },
        "patient": {
          "id": "<ABHA_ADDRESS>"
        },
        "hip": {
          "id": "cowin_hip_01",
          "name": "Cowin",
          "type": "HIP"
        },
        "hiu": {
          "id": "cowin_hiu_01",
          "name": "Cowin",
          "type": "HIU"
        },
        "careContexts": [
          {
            "patientReference": "batman@tmh",
            "careContextReference": "Episode1"
          }
        ],
        "requester": {
          "name": "<ABHA_ADDRESS>",
          "identifier": {
            "value": "REG1",
            "type": "MH1001",
            "system": "https://www.sample.com"
          }
        },
        "createdAt": "2021-09-28T12:30:08.573Z",
        "lastUpdated": "2021-09-28T12:30:08.573Z",
        "schemaVersion": "v3",
        "consentManager": {
          "id": "abdm"
        },
        "hiTypes": [
          "Prescription"
        ],
        "permission": {
          "accessMode": "VIEW",
          "dateRange": {
            "from": "2021-09-28T12:30:08.573Z",
            "to": "2021-09-28T12:30:08.573Z"
          },
          "dataEraseAt": "2021-09-28T12:30:08.573Z",
          "frequency": {
            "unit": "HOUR",
            "value": 1,
            "repeats": 0
          }
        }
      },
      "signature": "e8nY601CYDsC0FKoDjSp+7GeQ2s2R8oZncLCz5ce+pEuDOr5bZV0aaHjwJg4b9S9V+twjt4hbojx3fl7egrt8+0c+lfPTi5/bBUAQXCABTfFmtFU7jn65HlTt8kgkiONx26ZBhJ0wX3xjYI72PPtzYIiT5Q08YtDoILA62KceioV7lwuKssw7wC4ECbBAvRuXT121TmtrPhf+0myJATSnaajS06S6OthrKfZLNTUFf3pFiJzqouSTrjNblOX6DT2+JuO3rom1Szz/03c0HQG+wWASv+PO3J6uRs0UI4JvKmM/4tP+Z+/HPKM15K5U5K+4pqf6czKrbIDpkT/kP8bGg=="
    }
  ]
}
```

## Where the detail is

- Every operation, with its body fields and responses: /docs/hiecm/v3/api/p2
- Error codes: /docs/hiecm/v3/api/p2/errors
