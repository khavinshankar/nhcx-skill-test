# D28. nhcx_delivery

#### D28T. TABLE
One row is one message the exchange has delivered to this payer, keyed by the message's own identity; primary key `id`. No parent table. The reference implementation names it `payer_nhcx_deliveries` [REF](../references/PAYERS.md#markers).

#### D28D. DESCRIPTION
The receipt behind the callback door ([C1. Callback Door](../callbacks/C1-callback-door.md)). NHCX redelivers: the same message arrives more than once, seconds apart, with a new transaction id each time and the same `x-hcx-api_call_id`. That id is the message's identity, and a message taken in once is not taken in again; otherwise every redelivery would file a claim's documents afresh ([D23. case_document](D23-case-document.md)) or open a second case ([D19. case](D19-case.md)).

**Written** by [C1. Callback Door](../callbacks/C1-callback-door.md) before anything is applied: a plain insert keyed on the api call id (the ledger id from [G8. Receive](../gateway/G8-receive.md) when the message carries none). A duplicate on the key is the answer "seen before", and the door answers `ignored` (the reference answers `duplicate` [REF](../references/PAYERS.md#markers)) without touching the case. The insert runs on its own, outside any transaction, so a refused insert aborts nothing.

The door also reads the audit trail ([D31. audit_log](D31-audit-log.md)) for the transaction: an audit row under `nhcx_txn` with the ledger id means the delivery was already answered, and the same transaction retried by the gateway is a duplicate too.

**Read** by nothing else. `kind` and `txn_id` are bookkeeping for an operator asking what a redelivered id was.

Delete: never by the application; an operator may prune by `seen_at` after the gateway's own retention window ([G9. Ledger](../gateway/G9-ledger.md)) has passed, since nothing older can be redelivered.

#### D28C. COLUMNS
| column | type | null/default | meaning (and allowed values) |
|---|---|---|---|
| id | VARCHAR(96) | primary key | `x-hcx-api_call_id`, else the ledger id, cut to 96 |
| kind | VARCHAR(32) | null | what [C1. Callback Door](../callbacks/C1-callback-door.md) classified the message as |
| txn_id | VARCHAR(96) | null | the ledger id of the first delivery |
| seen_at | TIMESTAMPTZ | NOT NULL, default now | when it was first taken in |

#### D28K. KEYS AND INDEXES
- Primary key `id`.
- Index `idx_nhcx_deliveries_seen` on `seen_at`.

#### D28U. USED BY
- APIs: [A11. Transaction Related](../apis/A11-txn-related.md), [A12. Transaction FHIR](../apis/A12-txn-fhir.md)
- Callbacks: [C1. Callback Door](../callbacks/C1-callback-door.md), [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md)
- Database: [D31. audit_log](D31-audit-log.md)
- Tests: [T18. Redelivery and Duplicates](../tests/T18-redelivery-ignored.md)
