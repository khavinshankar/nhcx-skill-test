# D9. abha_link_event

#### D9T. TABLE
One row is one attempt to link or unlink a member's ABHA number to their enrolment at ABDM, kept whatever it did; primary key `id`, an identity column. Parent table [D6. subscription](D6-subscription.md). The reference implementation names it `payer_abha_link_events` [REF](../references/PAYERS.md#markers).

#### D9D. DESCRIPTION
The only record a failed ABHA call leaves. [A16. ABHA Policy Link](../apis/A16-abha-policy-link.md) writes one row per attempt, in the same transaction as whatever it changed on [D6. subscription](D6-subscription.md):

| Outcome | What it means | What changes on [D6. subscription](D6-subscription.md) |
|---|---|---|
| `success` | the participant service acknowledged the link or delink | the link columns move; `abha_link_status` becomes `linked` or `delinked` |
| `failed` | the registry refused it, or the gateway was unreachable | `abha_link_status` `failed` and `abha_request_id`; nothing else |
| `local` | recorded here because no gateway is configured; not a success at ABDM | the number is recorded, `abha_link_status` stays `none` |

`request_id` is the request id the call carried, which ABDM's support desk asks for by name. `response` is the reply verbatim, capped by the client that stores it, for working out why an integration is not working.

The Subscriptions screen ([S5. Subscriptions](../screens/S5-subscriptions.md)) lists the events newest first (`GET subscriptions/:id/abha/events`).

Delete:
- Never; cascades with the enrolment.

#### D9C. COLUMNS
| column | type | null/default | meaning (and allowed values) |
|---|---|---|---|
| id | BIGINT | primary key, identity | row id |
| subscription_id | VARCHAR(24) | NOT NULL | the enrolment ([D6. subscription](D6-subscription.md)) |
| action | VARCHAR(32) | NOT NULL | `link`, `delink` |
| outcome | VARCHAR(32) | NOT NULL | `success`, `failed`, `local` |
| request_id | VARCHAR(64) | null | the request id sent to ABDM |
| http_status | INTEGER | null | what the gateway answered; null when it never answered |
| message | VARCHAR(500) | null | the human line of the result |
| response | TEXT | null | the reply body verbatim |
| user_id | VARCHAR(36) | null | the acting account ([D2. staff](D2-staff.md)) |
| at | TIMESTAMPTZ | NOT NULL, default now | when |

#### D9K. KEYS AND INDEXES
- Primary key `id`.
- Foreign key `subscription_id` references [D6. subscription](D6-subscription.md) `id` (`ON DELETE CASCADE`); `user_id` references the account table (`ON DELETE SET NULL`).
- Checks: `ck_abha_events_action`; `ck_abha_events_outcome`.
- Index `idx_abha_events_subscription` on `(subscription_id, at)`.

#### D9U. USED BY
- Screens: [S5. Subscriptions](../screens/S5-subscriptions.md)
- APIs: [A16. ABHA Policy Link](../apis/A16-abha-policy-link.md)
- Database: [D6. subscription](D6-subscription.md)
