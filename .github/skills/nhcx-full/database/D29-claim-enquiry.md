# D29. claim_enquiry

#### D29T. TABLE
One row is one small Task exchange a claim starts beside its main legs: a status enquiry, a reprocess request or a balance release request. Primary key `id`. Parent table: `claim` (D9), many rows per claim.

#### D29D. DESCRIPTION
Each ask is its own Task on `task/submit` with its own correlation id, so each is its own row.

**Created.** One row per ask, inserted with `status` `asking`, `kind`, `stage`, `txn_id`, `correlation_id`, `requested_at`, `reason` and `request_json`. When [G7. Send](../gateway/G7-send.md) reports the send failed after naming its ids, the row is inserted with `status` `error` and the message. The three kinds:

| kind | Where | Allowed when | stage | Workflow id | Extra columns |
|---|---|---|---|---|---|
| `status` | S9 (pre-authorisation card) or S11 (claim card) | the leg has been sent (D18 exists; D20 not `draft`) and the payer's adapter answers status enquiries [PAYER](../references/PAYERS.md#markers) | `preauth` or `claim` | the leg's own `correlation_id`, else `13` [REF](../references/PAYERS.md#markers) | none |
| `reprocess` | S11 | D20 is `rejected`, `partial` or `approved` and the claim is not paid in full (D21 paid total below D20 `requested_amount`) | `claim` | adapter's `reprocess` (see [PAYERS.md](../references/PAYERS.md)) [PAYER](../references/PAYERS.md#markers) | `reason` (required text), `reason_code`, `document_ids` |
| `release` | S11 | D20 is `approved` or `partial` and not paid in full; the amount must be above 0 | `claim` | adapter's `release` (see [PAYERS.md](../references/PAYERS.md)) [PAYER](../references/PAYERS.md#markers) | `reason` (the optional note) |

`reason_code` must be one the adapter allows: `claimrejected` (the default), `partialpayment`, `rejectiondisputed` [PAYER](../references/PAYERS.md#markers). The reprocess Task carries the chosen D28 documents; `document_ids` records their ids. `reason_code` and `document_ids` are written by an update right after the insert.

**Statuses** (exact strings): `asking`, `answered`, `error`.

- `asking` to `answered`: a Task reply arrives on the thread, by callback C8 (a `status` or `task` message on a correlation id held here is routed here before anything else) or by polling when the claim is opened. It writes `answered_at`, `response_json`, `answer`, `detail`, and clears `error_message`.
  - `status`: `answer` is `entity_status` from the `x-hcx-status_response` header, else the Task's `claimStatus` output, else `not-found` when the Task is `rejected`, else `unknown`. `detail` is the Task description plus the header's `stage`, `outcome`, `total_approved` and `total_paid`.
  - `reprocess` and `release`: `answer` is `reopened` when the Task status is `completed`, `accepted` or `in-progress`, otherwise `refused`; `detail` is the reply's disposition or the Task description. When reopened, the claim leg (D20) goes back to `submitting` to wait for the new verdict on its own thread.
- `asking` to `error`: a ProtocolResponse on the thread, a peer, protocol or own dispatch error found by polling, or a ledger 404 (the message tells the desk to ask again).
- `error` to `asking` to `answered`: an `error` row is revived when the payer answers on its thread anyway.
- An `answered` row ignores further replies.

`amount` exists in the schema but no code path writes it; the release amount travels only in `request_json`.

**Deleted.** Never by the application; by cascade with the claim or when the transactional store is cleared.

#### D29C. COLUMNS
| Column | Type | Null / default | Meaning |
|---|---|---|---|
| id | INTEGER | primary key | Row id |
| claim_id | INTEGER | NOT NULL | The claim (D9) |
| kind | TEXT | NOT NULL | `status`, `reprocess`, `release` |
| stage | TEXT | null | `preauth` or `claim` (always `claim` for reprocess and release) |
| txn_id | TEXT | null | [G9. Ledger](../gateway/G9-ledger.md) id of the Task |
| correlation_id | TEXT | null | Correlation id the answer arrives on |
| requested_at | TEXT | NOT NULL | When the Task was sent |
| status | TEXT | NOT NULL, default `asking` | `asking`, `answered`, `error` |
| answer | TEXT | null | Status: entity status, claim status, `not-found` or `unknown`. Reprocess and release: `reopened` or `refused` |
| detail | TEXT | null | What the payer said, in words |
| amount | REAL | null | An amount the answer carried; not written by the current code |
| reason | TEXT | null | Reprocess: why it was asked for. Release: the note |
| reason_code | TEXT | null | Reprocess only: `claimrejected`, `partialpayment`, `rejectiondisputed`. Migration also adds it |
| document_ids | TEXT | null | Reprocess only: JSON list of D28 ids sent with it. Migration also adds it |
| error_message | TEXT | null | Why the ask failed |
| request_json | TEXT | null | The Task bundle as sent |
| response_json | TEXT | null | The reply bundle |
| answered_at | TEXT | null | When the answer was applied |

#### D29K. KEYS AND INDEXES
- Primary key `id` (integer).
- Foreign key `claim_id` references `claim (id)` (D9), `ON DELETE CASCADE`.
- Index `ix_claim_enquiry_corr` on `(correlation_id)`.
- Index `ix_claim_enquiry_claim` on `(claim_id, id)`; asks are listed newest first, filtered by `kind` and `stage`.

#### D29U. USED BY
- Screens: [S6. Claim Detail](../screens/S6-claim-detail.md), [S9. Pre-authorisation](../screens/S9-preauthorisation.md), [S11. Claim Submission](../screens/S11-claim-submission.md)
- APIs: [A6. Task Submit (cancel, status, reprocess, release)](../apis/A6-task-submit.md), [A10. Transaction Related](../apis/A10-txn-related.md), [A11. Transaction Dispatch](../apis/A11-txn-dispatch.md), [A13. Transaction List](../apis/A13-txn-list.md), [A17. Claim State](../apis/A17-claim-state.md)
- Callbacks: [C1. Callback Door](../callbacks/C1-callback-door.md), [C8. Enquiry Reply](../callbacks/C8-enquiry-on-submit.md)
- FHIR: [F10. Task (claim actions)](../fhir/F10-task-claim-actions.md)
- Database: [D9. claim](D9-claim.md), [D20. claim_submission](D20-claim-submission.md), [D28. claim_document](D28-claim-document.md)
