# HIE-CM record-share build

Scaffolds an ABDM record-share integration one journey at a time. It covers a patient sharing chosen records with an HIU from a PHR app after scanning its QR code.

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

### Record share, PHR app side (`record-share-phr`)

**Act: the calls in this journey, in order**

#### 1. Share a patient's records with the HIU whose QR code was scanned (`record-share_post_patient_record_v3_share`)

```bash
curl --request POST \
  --url https://dev.abdm.gov.in/api/hiecm/patient-record/v3/share \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-HIU-ID: HIU_ID' \
  --header 'X-CM-ID: sbx' \
  --header 'X-AUTH-TOKEN: Bearer <USER_TOKEN>' \
  --header 'Content-Type: application/json' \
  --data '{
  "metaData": {
    "hiuId": "MANISH_HIU",
    "counterId": "IN081010313"
  },
  "profile": {
    "patient": {
      "abhaNumber": null,
      "abhaAddress": "abhaAddress@sbx",
      "name": "String",
      "gender": "M",
      "dayOfBirth": "18",
      "monthOfBirth": "10",
      "yearOfBirth": "1991",
      "address": {
        "line": "String",
        "district": "String",
        "state": "String",
        "pincode": "XXXXXX"
      },
      "phoneNumber": "989141XXXX"
    }
  },
  "sharedRecordCount": 2,
  "consent": {
    "careContexts": [
      {
        "patientReference": "manishk1991@sbx",
        "careContextReference": "10004-20200001768-1"
      },
      {
        "patientReference": "manishk1991@sbx",
        "careContextReference": "10004-20200001768-2"
      }
    ],
    "permission": {
      "accessMode": "VIEW"
    },
    "dataEraseAt": "2025-10-11T08:58:09.738Z"
  }
}'
```

#### 2. Receive the HIU's data push URL and encryption key, as the PHR app (`record-share_post_v3_patient_record_on_share`)

Inbound to your bridge at `/api/v3/patient-record/on-share`. Acknowledge it and continue.

#### 3. Push the encrypted records to the HIU's data push URL, as the PHR app (`record-share_post_health_information_transfer`)

Outbound from your app. POST the encrypted records to the `dataPushUrl` the HIU sent in the on-share of step 2. The call goes straight to the HIU, not through the gateway. The HIU answers 202.

#### 4. Notify patient record (`record-share_post_patient_record_v3_notify`)

```bash
curl --request POST \
  --url https://dev.abdm.gov.in/api/hiecm/patient-record/v3/notify \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-HIU-ID: HIU_ID' \
  --header 'X-CM-ID: sbx' \
  --header 'Content-Type: application/json' \
  --data '{
  "notification": {
    "transactionId": "a0e7bed4-ef98-4ea8-9077-f4a6192bfe2b",
    "doneAt": "2026-03-19T08:01:11.090Z",
    "statusNotification": {
      "sessionStatus": "TRANSFERRED",
      "statusResponses": [
        {
          "careContextReference": "COC497647c1-0627-48fa-8131-0dddc1b3e0b4",
          "hiStatus": "DELIVERED",
          "description": "Data sent successfully"
        },
        {
          "careContextReference": "COC497647c1-0627-48fa-8131-0dddc1b3e0b5",
          "hiStatus": "DELIVERED",
          "description": "Data sent successfully"
        }
      ]
    }
  }
}'
```

#### 5. Receive the other side's transfer status (`record-share_post_v3_patient_record_on_notify`)

Inbound to your bridge at `/api/v3/patient-record/on-notify`. Acknowledge it and continue.

#### 6. List the record sharing history of the signed in user (`record-share_get_patient_record_v3_audit_history`)

```bash
curl --request GET \
  --url https://dev.abdm.gov.in/api/hiecm/patient-record/v3/audit-history \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx' \
  --header 'X-AUTH-TOKEN: Bearer <USER_TOKEN>'
```

**Exit condition (Observe until this is true)**

Each call you made in this journey answered by its callback, with `response.requestId` equal to the `REQUEST-ID` you sent on that call. The 202 on a call is receipt, not the outcome: the outcome is in the callback's body.

- `POST /api/hiecm/patient-record/v3/share` is answered by `POST /api/v3/patient-record/share` on your bridge.
- `POST /api/hiecm/patient-record/v3/notify` is answered by `POST /api/v3/patient-record/on-notify` on your bridge.

Then `GET /api/hiecm/patient-record/v3/audit-history` returns a 200 whose body matches:

```json
[
  {
    "requestId": "ed9f451d-9e07-484d-ab68-9972d6529d68",
    "abhaAddress": "manishk1991@sbx",
    "senderFacilityId": "MANISH_PHR_TEST",
    "senderFacilityName": "MANISH-PHR-TEST",
    "receiverFacilityId": "MANISH_HIU",
    "receiverFacilityName": "MANISH_HIU",
    "counterCode": "f4cd0d8e-25ec-465f-993c-01c91a56e0e4",
    "transactionId": "f413b202-16b6-4d4a-9900-5cdcfb8baa50",
    "status": "RECORD_SHARE_REQUESTED",
    "sharedRecordCount": 2,
    "consent": {
      "accessMode": "VIEW",
      "dataEraseAt": "2026-10-12T08:58:09.738Z",
      "careContexts": [
        {
          "patientReference": "manikandanb87@sbx",
          "careContextReference": "COC497647c1-0627-48fa-8131-0dddc1b3e0b4"
        },
        {
          "patientReference": "manikandanb87@sbx",
          "careContextReference": "COC497647c1-0627-48fa-8131-0dddc1b3e0b5"
        }
      ]
    },
    "dateCreated": "2025-12-08T12:04:53.594Z",
    "dateModified": "2025-12-08T12:04:53.594Z"
  }
]
```

### Record share, HIU side (`record-share-hiu`)

**Act: the calls in this journey, in order**

#### 1. Receive a patient's share request, as the HIU (`record-share_post_v3_patient_record_share`)

Inbound to your bridge at `/api/v3/patient-record/share`. Acknowledge it and continue.

#### 2. Submit the reply to a share request with the data push URL and the encryption key (`record-share_post_patient_record_v3_on_share`)

```bash
curl --request POST \
  --url https://dev.abdm.gov.in/api/hiecm/patient-record/v3/on-share \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-HIU-ID: HIU_ID' \
  --header 'X-CM-ID: sbx' \
  --header 'Content-Type: application/json' \
  --data '{
  "hiRequest": {
    "transactionId": "18235d89-cb13-479d-ad71-7a57d5f669a8",
    "dataPushUrl": "https://webhook.site/a2477c41-2185-47eb-835a/health-information/transfer",
    "keyMaterial": {
      "cryptoAlg": "ECDH.",
      "curve": "curve25519",
      "dhPublicKey": {
        "expiry": "2022-12-28T13:18:20.742Z",
        "parameters": "Ephemeral public key.",
        "keyValue": "BFN7KTdOT0jIAExG2A8Jg+01wMPWxptiGqwHRVvtiVEsUq2FR7P2UdqZxJyPJSeR6muai21iQhasNxnhh8I5M+g="
      },
      "nonce": "28236d89-cb13-479d-ad71-7a57d5f669a9"
    }
  },
  "response": {
    "requestId": "efd6964f-6893-4b66-9e4e-28afc164126b"
  }
}'
```

#### 3. Receive the encrypted records at the data push URL, as the HIU (`record-share_post_health_information_transfer`)

Inbound to your bridge at `/health-information/transfer`. Acknowledge it and continue.

#### 4. Receive the other side's transfer status (`record-share_post_v3_patient_record_on_notify`)

Inbound to your bridge at `/api/v3/patient-record/on-notify`. Acknowledge it and continue.

#### 5. Notify patient record (`record-share_post_patient_record_v3_notify`)

```bash
curl --request POST \
  --url https://dev.abdm.gov.in/api/hiecm/patient-record/v3/notify \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-HIU-ID: HIU_ID' \
  --header 'X-CM-ID: sbx' \
  --header 'Content-Type: application/json' \
  --data '{
  "notification": {
    "transactionId": "3acbbb52-6de0-441f-b452-3c9488462b25",
    "doneAt": "2023-01-24T06:35:44.167Z",
    "statusNotification": {
      "sessionStatus": "RECEIVED",
      "statusResponses": [
        {
          "careContextReference": "10004-20200001768-1",
          "hiStatus": "VALID",
          "description": "Data received successfully"
        },
        {
          "careContextReference": "10004-20200001768-2",
          "hiStatus": "ERRORED",
          "description": "Data could not be decrypted"
        }
      ]
    }
  }
}'
```

**Exit condition (Observe until this is true)**

Each call you made in this journey answered by its callback, with `response.requestId` equal to the `REQUEST-ID` you sent on that call. The 202 on a call is receipt, not the outcome: the outcome is in the callback's body.

- `POST /api/hiecm/patient-record/v3/on-share` is answered by `POST /api/v3/patient-record/on-share` on your bridge.
- `POST /api/hiecm/patient-record/v3/on-share` is answered by `POST /health-information/transfer` on your bridge.
- `POST /api/hiecm/patient-record/v3/notify` is answered by `POST /api/v3/patient-record/on-notify` on your bridge.

## Where the detail is

- Every operation, with its body fields and responses: /docs/hiecm/v3/api/record-share
- Error codes: /docs/hiecm/v3/api/record-share/errors
