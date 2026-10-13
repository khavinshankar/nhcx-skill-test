# HIE-CM p1 build

Scaffolds an ABDM p1 integration one journey at a time. It covers creating an ABHA address in a PHR app and logging in to it.

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

### PHR certificate and session token (`p1-certificate-and-session`)

**Act: the calls in this journey, in order**

#### 1. Get the PHR certificate (`p1_get_v3_phr_app_login_public_certificate`)

```bash
curl --request GET \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/login/public/certificate \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z'
```

#### 2. Generate access token (`gateway_post_gateway_v3_sessions`)

```bash
curl --request POST \
  --url https://dev.abdm.gov.in/api/hiecm/gateway/v3/sessions \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx' \
  --header 'Content-Type: application/json' \
  --data '{
  "clientId": "SBX_0000",
  "clientSecret": "0******-***-***-***-a****",
  "grantType": "client_credentials"
}'
```

**Exit condition (Observe until this is true)**

A 202 whose body matches:

```json
{
  "accessToken": "<TOKEN>",
  "expiresIn": 1200,
  "refreshExpiresIn": 1800,
  "refreshToken": "<TOKEN>",
  "tokenType": "bearer"
}
```

### Create ABHA number, Aadhaar OTP (`p1-create-abha-number-aadhaar-otp`)

**Act: the calls in this journey, in order**

#### 1. Send Aadhaar OTP for ABHA enrolment (`m1_post_v3_enrollment_request_otp_aadhaar_otp`)

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/enrollment/request/otp \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'Content-Type: application/json' \
  --data '{
  "txnId": "{{txnId}}",
  "scope": [
    "abha-enrol"
  ],
  "loginHint": "aadhaar",
  "loginId": "{{encrypted aadhaar number}}",
  "otpSystem": "aadhaar"
}'
```

#### 2. Create ABHA - verify Aadhaar OTP (`m1_post_v3_enrollment_enrol_byaadhaar_otp`)

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/enrollment/enrol/byAadhaar \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'BENEFIT_NAME: {{Benefit Name}}' \
  --header 'Content-Type: application/json' \
  --data '{
  "authData": {
    "authMethods": [
      "otp"
    ],
    "otp": {
      "txnId": "{{txnId}}",
      "otpValue": "{{encrypted otp}}",
      "mobile": "{{mobile number}}"
    }
  },
  "consent": {
    "code": "abha-enrollment",
    "version": "1.4"
  }
}'
```

#### 3. After ABHA creation - send OTP to verify mobile (optional) (optional) (`m1_post_v3_enrollment_request_otp_mobile_verify_create_ab_1b66bb`)

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/enrollment/request/otp \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'Content-Type: application/json' \
  --data '{
  "txnId": "{{txnId}}",
  "scope": [
    "abha-enrol",
    "mobile-verify"
  ],
  "loginHint": "mobile",
  "loginId": "{{encrypted mobileNumber}}",
  "otpSystem": "abdm"
}'
```

#### 4. After ABHA creation - verify mobile OTP (optional) (optional) (`m1_post_v3_enrollment_auth_byabdm_mobile_verify_create_ab_091285`)

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/enrollment/auth/byAbdm \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'Content-Type: application/json' \
  --data '{
  "scope": [
    "abha-enrol",
    "mobile-verify"
  ],
  "authData": {
    "authMethods": [
      "otp"
    ],
    "otp": {
      "txnId": "{{txnId}}",
      "otpValue": "{{encrypted otp}}"
    }
  }
}'
```

#### 5. Submit the email verification link (`p1_post_v3_profile_account_request_emailverificationlink`)

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/profile/account/request/emailVerificationLink \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-token: Bearer <JWT TOKEN>' \
  --header 'Content-Type: application/json' \
  --data '{
  "scope": [
    "abha-profile",
    "email-link-verify"
  ],
  "loginHint": "email",
  "loginId": "{{encrypted email}}",
  "otpSystem": "abdm"
}'
```

#### 6. After ABHA creation - get ABHA address suggestions (`m1_get_v3_enrollment_enrol_suggestion_create_abha_aadhaar_otp`)

```bash
curl --request GET \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/enrollment/enrol/suggestion \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'TRANSACTION_ID: {{txnId}}' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z'
```

#### 7. After ABHA creation - create ABHA address (`m1_post_v3_enrollment_enrol_abha_address_create_abha_aadhaar_otp`)

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/enrollment/enrol/abha-address \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'Content-Type: application/json' \
  --data '{
  "txnId": "{{txnId}}",
  "abhaAddress": "{{ABHA Address}}",
  "preferred": 1
}'
```

#### 8. Get ABHA profile (`m1_get_v3_profile_account`)

```bash
curl --request GET \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/profile/account \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'X-token: Bearer {{X-token}}' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z'
```

#### 9. Retrieve ABHA card image (`m1_get_v3_profile_account_abha_card`)

```bash
curl --request GET \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/profile/account/abha-card \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'X-token: Bearer {{X-token}}' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z'
```

**Exit condition (Observe until this is true)**

A 200 response. The specification gives no body for it, so read what comes back.

### Create ABHA address, mobile number (`p1-create-abha-address-mobile`)

**Act: the calls in this journey, in order**

#### 1. Request enrolment OTP (`p1_post_v3_phr_app_enrollment_request_otp`)

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/enrollment/request/otp \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'Content-Type: application/json' \
  --data '{
  "scope": [
    "abha-address-enroll",
    "mobile-verify"
  ],
  "loginHint": "mobile-number",
  "loginId": "{{encryptedData}}",
  "otpSystem": "abdm"
}'
```

#### 2. Verify the enrolment OTP (`p1_post_v3_phr_app_enrollment_verify`)

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/enrollment/verify \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'Content-Type: application/json' \
  --data '{
  "scope": [
    "abha-address-enroll",
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

#### 3. Suggest an ABHA address (`p1_post_v3_phr_app_enrollment_suggestion`)

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/enrollment/suggestion \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'Content-Type: application/json' \
  --data '{
  "txnId": "ee10d1c7-e25f-40e0-a3a1-df4c1dda02211",
  "firstName": "John",
  "lastName": "Doe",
  "dayOfBirth": "<DOB>",
  "monthOfBirth": "<DOB>",
  "yearOfBirth": "<DOB>",
  "email": ""
}'
```

#### 4. Check whether the ABHA address exists (`p1_get_v3_phr_app_enrollment_isexists`)

```bash
curl --request GET \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/enrollment/isExists \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z'
```

#### 5. Enrol ABHA address (`p1_post_v3_phr_app_enrollment_enrol`)

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/enrollment/enrol \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'Content-Type: application/json' \
  --data '{
  "txnId": "27d444b7-2a3d-46d8-bf67-e5590b6c46b6",
  "phrDetails": {
    "mobile": "<ENCRYPTED_MOBILE>",
    "firstName": "John",
    "middleName": "",
    "lastName": "Doe",
    "yearOfBirth": "<DOB>",
    "dayOfBirth": "",
    "monthOfBirth": "<DOB>",
    "gender": "M",
    "email": "",
    "profilePhoto": "",
    "address": "<ADDRESS>",
    "stateName": "Maharashtra",
    "stateCode": "27",
    "districtName": "<ADDRESS>",
    "districtCode": "123",
    "pinCode": "<PINCODE>",
    "abhaAddress": "<ABHA_ADDRESS>",
    "password": "<ENCRYPTED_PASSWORD>"
  }
}'
```

**Exit condition (Observe until this is true)**

A 200 whose body matches:

```json
{
  "txnId": "6907ebb5-ff71-47f9-8052-6dd5554df5df",
  "message": "ABHA Address Created Successfully",
  "phrDetails": {
    "firstName": "John",
    "middleName": "",
    "lastName": "Doe",
    "fullName": "John Doe",
    "dayOfBirth": "<DOB>",
    "monthOfBirth": "<DOB>",
    "yearOfBirth": "<DOB>",
    "dateOfBirth": "<DOB>",
    "gender": "M",
    "email": "<EMAIL>",
    "mobile": "******1234",
    "address": "<ADDRESS>",
    "stateName": "Maharashtra",
    "districtName": "<ADDRESS>",
    "pinCode": "<PINCODE>",
    "abhaAddress": [
      "<ABHA_ADDRESS>",
      "<ABHA_ADDRESS>",
      "<ABHA_ADDRESS>"
    ],
    "stateCode": "27",
    "districtCode": "123"
  },
  "tokens": {
    "token": "<JWT TOKEN>",
    "expiresIn": 1800,
    "refreshToken": "<JWT TOKEN>",
    "refreshExpiresIn": 1296000
  }
}
```

### Create ABHA address, ABHA number with ABHA OTP (`p1-create-abha-address-abha-number-abha-otp`)

**Act: the calls in this journey, in order**

#### 1. Request enrolment OTP (`p1_post_v3_phr_app_enrollment_request_otp`)

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/enrollment/request/otp \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'Content-Type: application/json' \
  --data '{
  "scope": [
    "abha-login",
    "mobile-verify"
  ],
  "loginHint": "abha-number",
  "loginId": "{{encryptedData}}",
  "otpSystem": "abdm"
}'
```

#### 2. Verify the enrolment OTP (`p1_post_v3_phr_app_enrollment_verify`)

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/enrollment/verify \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
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

#### 3. Suggest an ABHA address (`p1_post_v3_phr_app_enrollment_suggestion`)

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/enrollment/suggestion \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'Content-Type: application/json' \
  --data '{
  "txnId": "37d8d312-35a0-41e7-a6e4-1074eb18a5fa",
  "firstName": "John",
  "lastName": "Doe",
  "dayOfBirth": "<DOB>",
  "monthOfBirth": "<DOB>",
  "yearOfBirth": "<DOB>",
  "email": ""
}'
```

#### 4. Check whether the ABHA address exists (`p1_get_v3_phr_app_enrollment_isexists`)

```bash
curl --request GET \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/enrollment/isExists \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z'
```

#### 5. Enrol ABHA address (`p1_post_v3_phr_app_enrollment_enrol`)

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/enrollment/enrol \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'Content-Type: application/json' \
  --data '{
  "txnId": "37d8d312-35a0-41e7-a6e4-1074eb18a5fa",
  "phrDetails": {
    "firstName": "John",
    "middleName": "",
    "lastName": "Doe",
    "dayOfBirth": "<DOB>",
    "monthOfBirth": "<DOB>",
    "yearOfBirth": "<DOB>",
    "gender": "M",
    "email": "",
    "mobile": "<ENCRYPTED_MOBILE>",
    "address": "<ADDRESS>",
    "stateName": "Maharashtra",
    "stateCode": "27",
    "districtName": "<ADDRESS>",
    "districtCode": "123",
    "pinCode": "<PINCODE>",
    "abhaAddress": "<ABHA_ADDRESS>",
    "password": "<ENCRYPTED_PASSWORD>"
  }
}'
```

**Exit condition (Observe until this is true)**

A 200 whose body matches:

```json
{
  "txnId": "6907ebb5-ff71-47f9-8052-6dd5554df5df",
  "message": "ABHA Address Created Successfully",
  "phrDetails": {
    "firstName": "John",
    "middleName": "",
    "lastName": "Doe",
    "fullName": "John Doe",
    "dayOfBirth": "<DOB>",
    "monthOfBirth": "<DOB>",
    "yearOfBirth": "<DOB>",
    "dateOfBirth": "<DOB>",
    "gender": "M",
    "email": "<EMAIL>",
    "mobile": "******1234",
    "address": "<ADDRESS>",
    "stateName": "Maharashtra",
    "districtName": "<ADDRESS>",
    "pinCode": "<PINCODE>",
    "abhaAddress": [
      "<ABHA_ADDRESS>",
      "<ABHA_ADDRESS>",
      "<ABHA_ADDRESS>"
    ],
    "stateCode": "27",
    "districtCode": "123"
  },
  "tokens": {
    "token": "<JWT TOKEN>",
    "expiresIn": 1800,
    "refreshToken": "<JWT TOKEN>",
    "refreshExpiresIn": 1296000
  }
}
```

### Create ABHA address, ABHA number with Aadhaar OTP (`p1-create-abha-address-abha-number-aadhaar-otp`)

**Act: the calls in this journey, in order**

#### 1. Request enrolment OTP (`p1_post_v3_phr_app_enrollment_request_otp`)

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/enrollment/request/otp \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'Content-Type: application/json' \
  --data '{
  "scope": [
    "abha-login",
    "aadhaar-verify"
  ],
  "loginHint": "abha-number",
  "loginId": "{{encryptedData}}",
  "otpSystem": "aadhaar"
}'
```

#### 2. Verify the enrolment OTP (`p1_post_v3_phr_app_enrollment_verify`)

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/enrollment/verify \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
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
      "otpValue": "{{encryptedData}}"
    }
  }
}'
```

#### 3. Suggest an ABHA address (`p1_post_v3_phr_app_enrollment_suggestion`)

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/enrollment/suggestion \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'Content-Type: application/json' \
  --data '{
  "txnId": "7f45052a-ac63-48de-92db-c5d8d3d0c92a",
  "firstName": "John",
  "lastName": "Doe",
  "dayOfBirth": "<DOB>",
  "monthOfBirth": "<DOB>",
  "yearOfBirth": "<DOB>",
  "email": ""
}'
```

#### 4. Check whether the ABHA address exists (`p1_get_v3_phr_app_enrollment_isexists`)

```bash
curl --request GET \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/enrollment/isExists \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z'
```

#### 5. Enrol ABHA address (`p1_post_v3_phr_app_enrollment_enrol`)

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/enrollment/enrol \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'Content-Type: application/json' \
  --data '{
  "txnId": "37d8d312-35a0-41e7-a6e4-1074eb18a5fa",
  "phrDetails": {
    "firstName": "John",
    "middleName": "",
    "lastName": "Doe",
    "dayOfBirth": "<DOB>",
    "monthOfBirth": "<DOB>",
    "yearOfBirth": "<DOB>",
    "gender": "M",
    "email": "",
    "mobile": "<ENCRYPTED_MOBILE>",
    "address": "<ADDRESS>",
    "stateName": "Maharashtra",
    "stateCode": "27",
    "districtName": "<ADDRESS>",
    "districtCode": "123",
    "pinCode": "<PINCODE>",
    "abhaAddress": "<ABHA_ADDRESS>",
    "password": "<ENCRYPTED_PASSWORD>"
  }
}'
```

**Exit condition (Observe until this is true)**

A 200 whose body matches:

```json
{
  "txnId": "6907ebb5-ff71-47f9-8052-6dd5554df5df",
  "message": "ABHA Address Created Successfully",
  "phrDetails": {
    "firstName": "John",
    "middleName": "",
    "lastName": "Doe",
    "fullName": "John Doe",
    "dayOfBirth": "<DOB>",
    "monthOfBirth": "<DOB>",
    "yearOfBirth": "<DOB>",
    "dateOfBirth": "<DOB>",
    "gender": "M",
    "email": "<EMAIL>",
    "mobile": "******1234",
    "address": "<ADDRESS>",
    "stateName": "Maharashtra",
    "districtName": "<ADDRESS>",
    "pinCode": "<PINCODE>",
    "abhaAddress": [
      "<ABHA_ADDRESS>",
      "<ABHA_ADDRESS>",
      "<ABHA_ADDRESS>"
    ],
    "stateCode": "27",
    "districtCode": "123"
  },
  "tokens": {
    "token": "<JWT TOKEN>",
    "expiresIn": 1800,
    "refreshToken": "<JWT TOKEN>",
    "refreshExpiresIn": 1296000
  }
}
```

### PHR login, mobile number (`p1-login-mobile`)

**Act: the calls in this journey, in order**

#### 1. Login request OTP (`p1_post_v3_phr_app_login_request_otp`)

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/login/request/otp \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'Content-Type: application/json' \
  --data '{
  "scope": [
    "abha-address-login",
    "mobile-verify"
  ],
  "loginHint": "mobile-number",
  "loginId": "{{encryptedData}}",
  "otpSystem": "abdm"
}'
```

#### 2. Login PHR verify (`p1_post_v3_phr_app_login_verify`)

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/login/verify \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'Content-Type: application/json' \
  --data '{
  "scope": [
    "abha-address-login",
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

#### 3. Verify User, verify user (`p1_post_v3_phr_app_login_verify_user`)

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/login/verify/user \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'T-token: Bearer <JWT TOKEN>' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'Content-Type: application/json' \
  --data '{
  "abhaAddress": "<ABHA_ADDRESS>",
  "txnId": "48bc0a00-1127-459c-b040-8147f4ccc11a"
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

### PHR login, ABHA address with mobile OTP (`p1-login-abha-address-mobile-otp`)

**Act: the calls in this journey, in order**

#### 1. Login request OTP (`p1_post_v3_phr_app_login_request_otp`)

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/login/request/otp \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'Content-Type: application/json' \
  --data '{
  "scope": [
    "abha-address-login",
    "mobile-verify"
  ],
  "loginHint": "abha-address",
  "loginId": "{{encryptedData}}",
  "otpSystem": "abdm"
}'
```

#### 2. Login PHR verify (`p1_post_v3_phr_app_login_verify`)

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/login/verify \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'Content-Type: application/json' \
  --data '{
  "scope": [
    "abha-address-login",
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
  "txnId": "b81a963d-4b97-48b4-9f9f-acf9f13afab7",
  "message": "OTP verified successfully",
  "authResult": "success",
  "users": [
    {
      "abhaAddress": "<ABHA_ADDRESS>",
      "fullName": "John Doe",
      "abhaNumber": "<ABHA_NUMBER>",
      "status": "ACTIVE",
      "kycStatus": "VERIFIED"
    },
    {
      "abhaAddress": "<ABHA_ADDRESS>",
      "fullName": "John Doe",
      "abhaNumber": "<ABHA_NUMBER>",
      "status": "ACTIVE",
      "kycStatus": "PENDING"
    },
    {
      "abhaAddress": "<ABHA_ADDRESS>",
      "fullName": "John Doe",
      "status": "ACTIVE",
      "kycStatus": "PENDING"
    }
  ],
  "tokens": {
    "token": "<JWT TOKEN>",
    "expiresIn": 1800,
    "refreshToken": null,
    "refreshExpiresIn": null
  }
}
```

### PHR login, ABHA number with Aadhaar OTP (`p1-login-abha-number-aadhaar-otp`)

**Act: the calls in this journey, in order**

#### 1. Login request OTP (`p1_post_v3_phr_app_login_request_otp`)

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/login/request/otp \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'Content-Type: application/json' \
  --data '{
  "scope": [
    "abha-login",
    "aadhaar-verify"
  ],
  "loginHint": "abha-number",
  "loginId": "{{encryptedData}}",
  "otpSystem": "aadhaar"
}'
```

#### 2. Login PHR verify (`p1_post_v3_phr_app_login_verify`)

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/login/verify \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
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
      "otpValue": "{{encryptedData}}"
    }
  }
}'
```

#### 3. Verify User, verify user (`p1_post_v3_phr_app_login_verify_user`)

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/login/verify/user \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'T-token: Bearer <JWT TOKEN>' \
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

### PHR login, ABHA number with ABHA OTP (`p1-login-abha-number-abha-otp`)

**Act: the calls in this journey, in order**

#### 1. Login request OTP (`p1_post_v3_phr_app_login_request_otp`)

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/login/request/otp \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'Content-Type: application/json' \
  --data '{
  "scope": [
    "abha-login",
    "mobile-verify"
  ],
  "loginHint": "abha-number",
  "loginId": "{{encryptedData}}",
  "otpSystem": "abdm"
}'
```

#### 2. Login PHR verify (`p1_post_v3_phr_app_login_verify`)

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/login/verify \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
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

#### 3. Verify User, verify user (`p1_post_v3_phr_app_login_verify_user`)

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/login/verify/user \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'T-token: Bearer <JWT TOKEN>' \
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

### PHR login, ABHA address with password (`p1-login-abha-address-password`)

**Act: the calls in this journey, in order**

#### 1. Search auth methods ABHAAddress (`p1_post_v3_phr_app_login_search`)

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/login/search \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'Content-Type: application/json' \
  --data '{
  "abhaAddress": "<ABHA_ADDRESS>"
}'
```

#### 2. Login PHR verify (`p1_post_v3_phr_app_login_verify`)

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/login/verify \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'Content-Type: application/json' \
  --data '{
  "scope": [
    "abha-address-login",
    "password-verify"
  ],
  "authData": {
    "authMethods": [
      "password"
    ],
    "password": {
      "abhaAddress": "<ABHA_ADDRESS>",
      "password": "<ENCRYPTED_PASSWORD>"
    }
  }
}'
```

**Exit condition (Observe until this is true)**

A 200 whose body matches:

```json
{
  "txnId": "b81a963d-4b97-48b4-9f9f-acf9f13afab7",
  "message": "OTP verified successfully",
  "authResult": "success",
  "users": [
    {
      "abhaAddress": "<ABHA_ADDRESS>",
      "fullName": "John Doe",
      "abhaNumber": "<ABHA_NUMBER>",
      "status": "ACTIVE",
      "kycStatus": "VERIFIED"
    },
    {
      "abhaAddress": "<ABHA_ADDRESS>",
      "fullName": "John Doe",
      "abhaNumber": "<ABHA_NUMBER>",
      "status": "ACTIVE",
      "kycStatus": "PENDING"
    },
    {
      "abhaAddress": "<ABHA_ADDRESS>",
      "fullName": "John Doe",
      "status": "ACTIVE",
      "kycStatus": "PENDING"
    }
  ],
  "tokens": {
    "token": "<JWT TOKEN>",
    "expiresIn": 1800,
    "refreshToken": null,
    "refreshExpiresIn": null
  }
}
```

### PHR login, Aadhaar OTP (`p1-login-aadhaar-otp`)

**Act: the calls in this journey, in order**

#### 1. Login request OTP (`p1_post_v3_phr_app_login_request_otp`)

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/login/request/otp \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'Content-Type: application/json' \
  --data '{
  "scope": [
    "abha-login",
    "aadhaar-verify",
    "aadhaar-otp-verify"
  ],
  "loginHint": "aadhaar",
  "loginId": "<ENCRYPTED_LOGIN_ID>",
  "otpSystem": "aadhaar"
}'
```

#### 2. Login PHR verify (`p1_post_v3_phr_app_login_verify`)

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/login/verify \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'Content-Type: application/json' \
  --data '{
  "scope": [
    "abha-login",
    "aadhaar-verify",
    "aadhaar-otp-verify"
  ],
  "authData": {
    "authMethods": [
      "otp"
    ],
    "otp": {
      "txnId": "c51ad4d8-ae92-4509-8fb9-b91dea948492",
      "otpValue": "<ENCRYPTED_OTP_VALUE>"
    }
  }
}'
```

#### 3. Verify User, verify user (`p1_post_v3_phr_app_login_verify_user`)

```bash
curl --request POST \
  --url https://abhasbx.abdm.gov.in/abha/api/v3/phr/app/login/verify/user \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'T-token: Bearer <JWT TOKEN>' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'Content-Type: application/json' \
  --data '{
  "abhaAddress": "<ABHA_ADDRESS>",
  "txnId": "c51ad4d8-ae92-4509-8fb9-b91dea948492"
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

## Where the detail is

- Every operation, with its body fields and responses: /docs/hiecm/v3/api/p1
- Error codes: /docs/hiecm/v3/api/p1/errors
