# HIE-CM p3 build

Scaffolds an ABDM p3 integration one journey at a time. It covers reading, approving, denying, enabling, disabling and updating the patient's subscriptions and subscription requests, and the subscription request and notifications on the health locker side.

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

### Subscription request and notifications, HIU side (`p3-subscription-hiu`)

**Act: the calls in this journey, in order**

#### 1. Initiate subscription request (`p3_post_subscription_requests_v3_init`)

```bash
curl --request POST \
  --url https://dev.abdm.gov.in/api/hiecm/subscription-requests/v3/init \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx' \
  --header 'Content-Type: application/json' \
  --data '{
  "subscription": {
    "purpose": {
      "text": "Care Management",
      "code": "CAREMGT",
      "refUri": "https://abc.def.in"
    },
    "patient": {
      "id": "<ABHA_ADDRESS>"
    },
    "hiu": {
      "id": "INDIA_HIU",
      "name": "INDIA HIU",
      "type": "HIU"
    },
    "hips": [
      {
        "id": "INDIA_HIP",
        "name": "INDIA HIP",
        "type": "HIP"
      }
    ],
    "categories": [
      "LINK"
    ],
    "period": {
      "from": "2024-05-09T10:34:00.389Z",
      "to": "2024-05-09T10:34:00.389Z"
    }
  }
}'
```

#### 2. Receive the HIU subscription requests on init (`p3_post_v3_hiu_hiecm_subscription_requests_on_init`)

Inbound to your bridge at `/api/v3/hiu/hiecm/subscription-requests/on-init`. Acknowledge it and continue.

#### 3. Notify subscription requests HIU (`p3_post_v3_hiu_subscription_requests_hiu_notify`)

Inbound to your bridge at `/api/v3/hiu/subscription-requests/hiu/notify`. Acknowledge it and continue.

#### 4. Answer the subscription request notification (`p3_post_subscription_requests_v3_hiu_on_notify`)

```bash
curl --request POST \
  --url https://dev.abdm.gov.in/api/hiecm/subscription-requests/v3/hiu/on-notify \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx' \
  --header 'Content-Type: application/json' \
  --data '{
  "acknowledgement": {
    "status": "OK",
    "subscriptionRequestId": "f29f0e59-8388-4698-9fe6-05db67aeac46"
  },
  "error": {
    "code": "ABDM-1001",
    "message": "No data found"
  },
  "response": {
    "requestId": "f29f0e59-8388-4698-9fe6-05db67aeac46"
  }
}'
```

#### 5. Notify HIU subscription (`p3_post_v3_hiu_subscription_notify`)

Inbound to your bridge at `/api/v3/hiu/subscription/notify`. Acknowledge it and continue.

#### 6. Answer the care context subscription notification (`p3_post_subscription_requests_v3_hiu_care_context_on_notify`)

```bash
curl --request POST \
  --url https://dev.abdm.gov.in/api/hiecm/subscription-requests/v3/hiu/care-context/on-notify \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx' \
  --header 'Content-Type: application/json' \
  --data '{
  "acknowledgement": {
    "status": "OK",
    "eventId": "3c2f0e59-8388-4698-9fe6-05db67aeac46"
  },
  "error": {
    "code": "ABDM-1001",
    "message": "No data found"
  },
  "response": {
    "requestId": "f29f0e59-8388-4698-9fe6-05db67aeac46"
  }
}'
```

**Exit condition (Observe until this is true)**

Each call you made in this journey answered by its callback, with `response.requestId` equal to the `REQUEST-ID` you sent on that call. The 202 on a call is receipt, not the outcome: the outcome is in the callback's body.

- `POST /api/hiecm/subscription-requests/v3/init` is answered by `POST /api/v3/hiu/hiecm/subscription-requests/on-init` on your bridge.

### Subscription approval and management, PHR side (`p3-subscription-phr`)

**Act: the calls in this journey, in order**

#### 1. Approve subscription request (`p3_post_subscription_requests_v3_request_id_approve`)

```bash
curl --request POST \
  --url https://dev.abdm.gov.in/api/hiecm/subscription-requests/v3/{subscriptionRequestId}/approve \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx' \
  --header 'X-AUTH-TOKEN: <TOKEN>' \
  --header 'Content-Type: application/json' \
  --data '{
  "isApplicableForAllHIPs": true,
  "includedSources": [
    {
      "hiTypes": [
        "Prescription",
        "DiagnosticReport",
        "OPConsultation",
        "DischargeSummary",
        "ImmunizationRecord",
        "HealthDocumentRecord",
        "WellnessRecord",
        "Invoice"
      ],
      "purpose": {
        "text": "Care Management",
        "code": "CAREMGT",
        "refUri": "www.abdm.gov.in"
      },
      "categories": [
        "LINK",
        "DATA"
      ],
      "period": {
        "from": "2025-01-09T09:00:00.000Z",
        "to": "2124-12-31T09:00:00.000Z"
      }
    }
  ],
  "excludedSources": []
}'
```

#### 2. Deny subscription request (`p3_post_subscription_requests_v3_request_id_deny`)

```bash
curl --request POST \
  --url https://dev.abdm.gov.in/api/hiecm/subscription-requests/v3/{subscriptionRequestId}/deny \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx' \
  --header 'X-AUTH-TOKEN: <TOKEN>' \
  --header 'Content-Type: application/json' \
  --data '{
  "reason": "Subscription denied."
}'
```

#### 3. Fetch his/her subscription requests details (`p3_get_subscription_requests_v3_requests`)

```bash
curl --request GET \
  --url "https://dev.abdm.gov.in/api/hiecm/subscription-requests/v3/requests?limit=5&offset=5&status=ALL" \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx' \
  --header 'X-AUTH-TOKEN: <TOKEN>'
```

#### 4. Edit the subscription details (`p3_put_subscription_requests_v3_patients_subscription_id`)

```bash
curl --request PUT \
  --url https://dev.abdm.gov.in/api/hiecm/subscription-requests/v3/patients/{subscriptionID} \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx' \
  --header 'X-AUTH-TOKEN: <TOKEN>' \
  --header 'Content-Type: application/json' \
  --data '{
  "hiuId": "INDIA_HIU",
  "subscriptionEditAndApprovalRequest": {
    "isApplicableForAllHIPs": true,
    "includedSources": [
      {
        "hiTypes": [
          "Prescription"
        ],
        "purpose": {
          "text": "Care Management",
          "code": "CAREMGT",
          "refUri": "https://abc.def.in"
        },
        "hip": {
          "id": "INDIA_HIP",
          "name": "INDIA HIP",
          "type": "HIP"
        },
        "categories": [
          "LINK"
        ],
        "period": {
          "from": "2024-05-09T10:34:00.389Z",
          "to": "2024-05-09T10:34:00.389Z"
        },
        "status": "SUCCESS"
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
          "refUri": "https://abc.def.in"
        },
        "hip": {
          "id": "INDIA_HIP",
          "name": "INDIA HIP",
          "type": "HIP"
        },
        "categories": [
          "LINK"
        ],
        "period": {
          "from": "2024-05-09T10:34:00.389Z",
          "to": "2024-05-09T10:34:00.389Z"
        },
        "status": "SUCCESS"
      }
    ]
  }
}'
```

#### 5. Disable the subscription by subscription ID (`p3_post_subscription_requests_v3_disable_subscription_id`)

```bash
curl --request POST \
  --url https://dev.abdm.gov.in/api/hiecm/subscription-requests/v3/disable/{subscriptionID} \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx' \
  --header 'X-AUTH-TOKEN: <TOKEN>'
```

#### 6. Enable the subscription by subscription ID (`p3_post_subscription_requests_v3_enable_subscription_id`)

```bash
curl --request POST \
  --url https://dev.abdm.gov.in/api/hiecm/subscription-requests/v3/enable/{subscriptionID} \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx' \
  --header 'X-AUTH-TOKEN: <TOKEN>'
```

#### 7. Fetch his/her subscription details by subscription REQUEST-ID (`p3_get_subscription_requests_v3_request_request_id`)

```bash
curl --request GET \
  --url https://dev.abdm.gov.in/api/hiecm/subscription-requests/v3/request/{subscriptionRequestId} \
  --header 'Authorization: Bearer <ACCESS_TOKEN_FROM_SESSIONS_CALL>' \
  --header 'REQUEST-ID: 18235d89-cb13-479d-ad71-7a57d5f669a8' \
  --header 'TIMESTAMP: 2022-10-06T15:10:00.587Z' \
  --header 'X-CM-ID: sbx' \
  --header 'X-AUTH-TOKEN: <TOKEN>'
```

#### 8. Fetch his/her subscription details by subscription ID (`p3_get_subscription_requests_v3_subscription_id`)

```bash
curl --request GET \
  --url https://dev.abdm.gov.in/api/hiecm/subscription-requests/v3/{subscriptionID} \
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
  "subscriptionId": "f29f0e59-8388-4698-9fe6-05db67aeac46",
  "purpose": {
    "text": "Care Management",
    "code": "CAREMGT",
    "refUri": "https://abc.def.in"
  },
  "dateCreated": "2021-09-28T12:30:08.573Z",
  "status": "GRANTED",
  "dateGranted": "2021-09-28T12:30:08.573Z",
  "patient": {
    "id": "<ABHA_ADDRESS>"
  },
  "requester": {
    "id": "<ABHA_ADDRESS>",
    "name": "ABDM_HIU",
    "type": "HIU"
  },
  "includedSources": [
    {
      "hip": {
        "id": "INDIA_HIP",
        "name": "INDIA HIP",
        "type": "HIP"
      },
      "categories": [
        "LINK"
      ],
      "hiTypes": [
        "Prescription"
      ],
      "period": {
        "from": "2024-05-09T10:34:00.389Z",
        "to": "2024-05-09T10:34:00.389Z"
      },
      "status": "GRANTED"
    }
  ]
}
```

## Where the detail is

- Every operation, with its body fields and responses: /docs/hiecm/v3/api/p3
- Error codes: /docs/hiecm/v3/api/p3/errors
