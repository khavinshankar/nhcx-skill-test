# HIE-CM scan-and-pay build

Scaffolds an ABDM scan-and-pay integration one journey at a time. It covers open orders, patient selection and payment status between a facility and a PHR app.

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

### Scan and pay, HIP side (`scan-and-pay-abdm-scan-pay-hip`)

**Act: the calls in this journey, in order**

#### 1. Check the status of reports (`scan-and-pay_post_v3_patient_share_open_order`)

Inbound to your bridge at `/v3/patient/share/open-order`. Acknowledge it and continue.

#### 2. Submit the HIE-CM to send all the open order for patient (`scan-and-pay_post_scan_gateway_v3_patient_on_share_open_order`)

```bash
curl --request POST \
  --url https://dev.abdm.gov.in/api/hiecm/scan-gateway/v3/patient/on-share/open-order \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx' \
  --header 'Content-Type: application/json' \
  --data '{
  "intent": "OPEN_PAYMENT_ORDER",
  "abhaAddress": "<ABHA_ADDRESS>",
  "patientUid": "string",
  "procedures": [
    {
      "category": "OPD consultation",
      "services": [
        {
          "name": "consultation",
          "serviceId": "service-12345",
          "description": "Albumin 24 hrs Urine",
          "amount": 629.12
        }
      ]
    },
    {
      "category": "Laboratory and Diagnostics",
      "services": [
        {
          "name": "Diagnostics",
          "serviceId": "service-12345",
          "description": "Albumin 24 hrs Urine",
          "amount": 629.12
        }
      ]
    },
    {
      "category": "Pharmacy",
      "services": [
        {
          "name": "Pharmacy",
          "serviceId": "service-12345",
          "description": "Albumin 24 hrs Urine",
          "amount": 629.12
        }
      ]
    },
    {
      "category": "Miscellaneous/Other",
      "services": [
        {
          "name": "Miscellaneous",
          "serviceId": "service-12345",
          "description": "Albumin 24 hrs Urine",
          "amount": 629.12
        }
      ]
    }
  ],
  "response": {
    "requestId": "6c3d4e5c-09d1-****-817b-a0c82d130c53"
  }
}'
```

#### 3. Receive the patient selection (`scan-and-pay_post_v3_patient_selection`)

Inbound to your bridge at `/v3/patient/selection`. Acknowledge it and continue.

#### 4. Share payment bundle alone with procedures of the patient (`scan-and-pay_post_scan_gateway_v3_patient_on_selection`)

```bash
curl --request POST \
  --url https://dev.abdm.gov.in/api/hiecm/scan-gateway/v3/patient/on-selection \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx' \
  --header 'Content-Type: application/json' \
  --data '{
  "intent": "PAYMENT_ORDER",
  "openOrderRequestId": "b767614f-153a-4aa3-946f-1622596f0fab",
  "abhaAddress": "<ABHA_ADDRESS>",
  "procedures": [
    {
      "category": "OPD consultation",
      "services": [
        {
          "name": "consultation",
          "serviceId": "service-12345",
          "description": "Albumin 24 hrs Urine",
          "amount": 629.12
        }
      ]
    },
    {
      "category": "Laboratory and Diagnostics",
      "services": [
        {
          "name": "Diagnostics",
          "serviceId": "service-12345",
          "description": "Albumin 24 hrs Urine",
          "amount": 629.12
        }
      ]
    },
    {
      "category": "Pharmacy",
      "services": [
        {
          "name": "Pharmacy",
          "serviceId": "service-12345",
          "description": "Albumin 24 hrs Urine",
          "amount": 629.12
        }
      ]
    }
  ],
  "paymentBundle": {
    "paymentMode": "GATEWAY",
    "paymentUrl": "string",
    "orderNumber": "string",
    "amount": 1250.55,
    "merchantId": "123465",
    "description": "Testing"
  },
  "response": {
    "requestId": "6c3d4e5c-09d1-***-817b-a0c82d130c53"
  }
}'
```

#### 5. Send the payment status to HIU (`scan-and-pay_post_scan_gateway_v3_patient_scan_pay_notify`)

```bash
curl --request POST \
  --url https://dev.abdm.gov.in/api/hiecm/scan-gateway/v3/patient/scan-pay/notify \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx' \
  --header 'X-HIP-ID: IN2810014366' \
  --header 'Content-Type: application/json' \
  --data '{
  "acknowledgement": {
    "status": "SUCCESS/ CANCELED/ PENDING/ FAIL/ REFUND_INITIATED/ REFUND_SUCCESS",
    "abhaAddress": "<username>@sbx",
    "transactionId": "string",
    "orderNumber": "string",
    "openOrderRequestId": "b767614f-153a-4aa3-946f-1622596f0fab",
    "paymentDate": "2025-01-20T07:47:49.102Z",
    "paymentRecipetLink": "PDF URL LINK of RECIPT"
  }
}'
```

#### 6. Receive the patient scan pay on notify (`scan-and-pay_post_v3_patient_scan_pay_on_notify`)

Inbound to your bridge at `/v3/patient/scan-pay/on-notify`. Acknowledge it and continue.

#### 7. Receive the patient scan pay order status (`scan-and-pay_post_v3_patient_scan_pay_order_status`)

Inbound to your bridge at `/v3/patient/scan-pay/order-status`. Acknowledge it and continue.

#### 8. Check the status of reports (`scan-and-pay_post_scan_gateway_v3_patient_scan_pay_on_ord_21f376`)

```bash
curl --request POST \
  --url https://dev.abdm.gov.in/api/hiecm/scan-gateway/v3/patient/scan-pay/on-order-status \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx' \
  --header 'Content-Type: application/json' \
  --data '{
  "acknowledgement": {
    "status": "SUCCESS/ CANCELED/ PENDING/ FAIL/ REFUND_INITIATED/ REFUND_SUCCESS",
    "abhaAddress": "<username>@sbx",
    "transactionId": "string",
    "orderNumber": "string",
    "openOrderRequestId": "Queried Request id",
    "paymentDate": "Transaction Date UTC",
    "paymentRecipetLink": "PDF URL LINK of RECIPT"
  },
  "response": {
    "requestId": "b767614f-153a-***-946f-1622596f0fab"
  }
}'
```

**Exit condition (Observe until this is true)**

Each call you made in this journey answered by its callback, with `response.requestId` equal to the `REQUEST-ID` you sent on that call. The 202 on a call is receipt, not the outcome: the outcome is in the callback's body.

- `POST /api/hiecm/scan-gateway/v3/patient/scan-pay/notify` is answered by `POST /v3/patient/scan-pay/on-notify` on your bridge.

### Scan and pay, PHR side (`scan-and-pay-abdm-hiecm-scan-pay-phr`)

**Act: the calls in this journey, in order**

#### 1. Share patient open order (`scan-and-pay_post_scan_gateway_v3_patient_share_open_order`)

```bash
curl --request POST \
  --url https://dev.abdm.gov.in/api/hiecm/scan-gateway/v3/patient/share/open-order \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx' \
  --header 'X-AUTH-TOKEN: <TOKEN>' \
  --header 'X-HIU-ID: IN2810014366' \
  --header 'Content-Type: application/json' \
  --data '{
  "intent": "OPEN_PAYMENT_ORDER",
  "metaData": {
    "hipId": "HIP_1",
    "counterId": "123-456"
  },
  "profile": {
    "patient": {
      "abhaNumber": "91-7507-xxxx-xxxx",
      "abhaAddress": "<ABHA_ADDRESS>",
      "name": "name",
      "gender": "M",
      "dayOfBirth": "string",
      "monthOfBirth": "string",
      "yearOfBirth": "string",
      "address": {
        "line": "Address line 1",
        "district": "XXXXXXX",
        "state": "XXXXXX",
        "pincode": "XXXXXX"
      },
      "phoneNumber": "987654xxxx"
    }
  }
}'
```

#### 2. Receive the patient on-share (`scan-and-pay_post_v3_patient_on_share_open_order`)

Inbound to your bridge at `/v3/patient/on-share/open-order`. Acknowledge it and continue.

#### 3. Select the all open-order and send to HIP for a payment request detail (`scan-and-pay_post_scan_gateway_v3_patient_selection`)

```bash
curl --request POST \
  --url https://dev.abdm.gov.in/api/hiecm/scan-gateway/v3/patient/selection \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx' \
  --header 'X-AUTH-TOKEN: <TOKEN>' \
  --header 'X-HIU-ID: IN2810014366' \
  --header 'Content-Type: application/json' \
  --data '{
  "intent": "PAYMENT_ORDER",
  "openOrderRequestId": "b767614f-153a-***-946f-1622596f0fab",
  "abhaAddress": "<ABHA_ADDRESS>",
  "procedures": [
    {
      "category": "OPD consultation",
      "services": [
        {
          "name": "consultation",
          "serviceId": "service-12345",
          "description": "Albumin 24 hrs Urine",
          "amount": 629.12
        }
      ]
    },
    {
      "category": "Laboratory and Diagnostics",
      "services": [
        {
          "name": "Diagnostics",
          "serviceId": "service-12345",
          "description": "Albumin 24 hrs Urine",
          "amount": 629.12
        }
      ]
    },
    {
      "category": "Pharmacy",
      "services": [
        {
          "name": "Pharmacy",
          "serviceId": "service-12345",
          "description": "Albumin 24 hrs Urine",
          "amount": 629.12
        }
      ]
    }
  ]
}'
```

#### 4. Receive the patient on selection (`scan-and-pay_post_v3_patient_on_selection`)

Inbound to your bridge at `/v3/patient/on-selection`. Acknowledge it and continue.

#### 5. Notify patient scan pay (`scan-and-pay_post_v3_patient_scan_pay_notify`)

Inbound to your bridge at `/v3/patient/scan-pay/notify`. Acknowledge it and continue.

#### 6. Notify to HIP so that confirm that the HIU received the payment status (`scan-and-pay_post_scan_gateway_v3_patient_scan_pay_on_notify`)

```bash
curl --request POST \
  --url https://dev.abdm.gov.in/api/hiecm/scan-gateway/v3/patient/scan-pay/on-notify \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx' \
  --header 'Content-Type: application/json' \
  --data '{
  "acknowledgement": {
    "status": "SUCCESS/ CANCELED/ PENDING/ FAIL/ REFUND_INITIATED/ REFUND_SUCCESS",
    "abhaAddress": "<username>@sbx",
    "transactionId": "string",
    "orderNumber": "string",
    "openOrderRequestId": "b767614f-153a-4aa3-946f-1622596f0fab",
    "paymentDate": "2025-01-20T07:47:49.102Z",
    "paymentRecipetLink": "PDF URL LINK of RECIPT"
  },
  "response": {
    "requestId": "b767614f-153a-***-946f-1622596f0fab"
  }
}'
```

#### 7. Check the status of reports (`scan-and-pay_post_scan_gateway_v3_patient_scan_pay_order_status`)

```bash
curl --request POST \
  --url https://dev.abdm.gov.in/api/hiecm/scan-gateway/v3/patient/scan-pay/order-status \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx' \
  --header 'X-AUTH-TOKEN: <TOKEN>' \
  --header 'X-HIU-ID: IN2810014366' \
  --header 'Content-Type: application/json' \
  --data '{
  "queryStatus": {
    "orderNumber": "string",
    "abhaAddress": "<ABHA_ADDRESS>",
    "openOrderRequestId": "0d8bd16b-117c-4d07-9916-109fe3a9ab88"
  }
}'
```

#### 8. Receive the patient scan pay on order status (`scan-and-pay_post_v3_patient_scan_pay_on_order_status`)

Inbound to your bridge at `/v3/patient/scan-pay/on-order-status`. Acknowledge it and continue.

**Exit condition (Observe until this is true)**

Each call you made in this journey answered by its callback, with `response.requestId` equal to the `REQUEST-ID` you sent on that call. The 202 on a call is receipt, not the outcome: the outcome is in the callback's body.

- `POST /api/hiecm/scan-gateway/v3/patient/share/open-order` is answered by `POST /v3/patient/on-share/open-order` on your bridge.
- `POST /api/hiecm/scan-gateway/v3/patient/selection` is answered by `POST /v3/patient/on-selection` on your bridge.
- `POST /api/hiecm/scan-gateway/v3/patient/scan-pay/order-status` is answered by `POST /v3/patient/scan-pay/on-order-status` on your bridge.

### Scan and pay details and version update (`scan-and-pay-utility`)

**Act: the calls in this journey, in order**

#### 1. Get the patient scan pay details (`scan-and-pay_get_scan_gateway_v3_patient_scan_pay_details`)

```bash
curl --request GET \
  --url "https://dev.abdm.gov.in/api/hiecm/scan-gateway/v3/patient/scan-pay/details?status=SUCCESS&limit=10&startDate=2024-07-13T07:30:10.186Z&endDate=2025-02-18T08:30:50.189Z&offset=0" \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx' \
  --header 'X-AUTH-TOKEN: <TOKEN>'
```

#### 2. Update version to the serviceId (`scan-and-pay_patch_gateway_v3_scanpay_updateversion`)

```bash
curl --request PATCH \
  --url https://dev.abdm.gov.in/api/hiecm/gateway/v3/scanPay/updateVersion \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx' \
  --header 'Content-Type: application/json' \
  --data '{
  "recordShareEnabled": true,
  "scanPayEnabled": true,
  "scanPayVersion": "v2",
  "serviceId": [
    "****_HIP, ***_HIU"
  ]
}'
```

**Exit condition (Observe until this is true)**

A 200 response. The specification gives no body for it, so read what comes back.

## Where the detail is

- Every operation, with its body fields and responses: /docs/hiecm/v3/api/scan-and-pay
- Error codes: /docs/hiecm/v3/api/scan-and-pay/errors
