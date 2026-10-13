# D23. claim_query

#### D23T. TABLE
One row is one message the payer started on a claim over the communication route: a query for the desk to answer, a notification to acknowledge, or a note to read. Primary key `id`. Parent table: `claim` (D9), many rows per claim.

#### D23D. DESCRIPTION
A payer asks for more in one of two ways, set per payer by its adapter's query mode. A `resubmit` payer (PMJAY, see [PAYERS.md](../references/PAYERS.md)) queries inside the ClaimResponse [PAYER](../references/PAYERS.md#markers); that query lives on the leg (D18 or D20 `query_note`) and is answered by sending the leg again. It never creates a row here. A `communication` payer (generic NHCX, IRDAI payers) sends a CommunicationRequest on a thread of its own, and that is a row here.

**Created.** By the communication callback (C9):

- **Bundle with a CommunicationRequest.** A redelivery (its correlation id already on a row) is ignored. The claim is found by the references on `about`, `basedOn` and `identifier` (claim number, then an old leg `claim_ref`), then by a `request_id` already held, then by the message's correlation id, then by `x-hcx-workflow_id` matched against the `correlation_id` of D20 (leg `claim`) or D18 (leg `preauth`). No claim found: `unmatched`, nothing stored. `stage` is the leg the workflow id named, else `claim` when the claim leg has been sent (D20 not `draft`), else `preauth`.
  - `kind` is decided by the sender's adapter (else the claim's): a `resubmit` payer's request is always a `notification`. Otherwise the Task's `intent` decides (`proposal` is a `notification`, `order` is a `query`); with no intent, a reason code of `additionalinfo`, `questionnaire`, `query` or none is a `query`, any other reason a `notification` [REF](../references/PAYERS.md#markers).
  - The row is inserted with `status` `open`. A `query` recomputes the claim's stage (an open query on a leg still with the payer puts the case into `queried`). A `notification` is acknowledged at once.
- **Bundle with a bare Communication.** Stored as `kind` `note`, `status` `noted`. It is matched like a request. A note whose Communication id is already held as a note on the same claim is ignored. The message's correlation id is stored only if no other row already holds it, otherwise null.

**Statuses** (exact strings), by kind:

| kind | statuses | transitions |
|---|---|---|
| `query` | `open`, `answered`, `error` | `open` or `error` to `answered` when the reply is sent (A7); to `error` when the send fails |
| `notification` | `open`, `acknowledged`, `error` | `open` to `acknowledged` at once on arrival; to `error` if that send fails; `error` to `acknowledged` when re-sent from S10 |
| `note` | `noted` | none |

**Answering a query** (Communication tab, S10). Text or at least one document is required. New files chosen on the reply are first stored as supporting documents (D28) at this row's `stage`. The reply goes back to `sender_code` (else the claim's payer) on this row's `correlation_id`, with this row's `workflow_id` (else the queried leg's correlation id, else the claim number [REF](../references/PAYERS.md#markers)). Success writes `status` `answered`, `reply_text`, `reply_documents`, `reply_txn_id`, `reply_correlation_id`, `answered_at`, `reply_json`, clears `error_message`, and recomputes the claim stage. Failure writes `status` `error`, `error_message`, `reply_text`, `reply_documents` and, when named, `reply_txn_id` / `reply_correlation_id`. Only `kind` `query` can be answered.

**Acknowledging a notification.** The request bundle is sent back with its Task set to `completed`. Success writes `status` `acknowledged`, `reply_txn_id`, `reply_correlation_id`, `acknowledged_at`, `reply_json`, clears `error_message`. Only `kind` `notification` can be acknowledged.

A query counts as waiting on the desk while `kind` is `query` and `status` is `open` or `error`.

**Deleted.** Never by the application; by cascade with the claim or when the transactional store is cleared.

#### D23C. COLUMNS
| Column | Type | Null / default | Meaning |
|---|---|---|---|
| id | INTEGER | primary key | Row id |
| claim_id | INTEGER | NOT NULL | The claim (D9) |
| stage | TEXT | NOT NULL, default `preauth` | Leg asked about: `preauth` or `claim` |
| correlation_id | TEXT | null, unique | The request's own thread; the reply goes back on it |
| request_id | TEXT | null | `CommunicationRequest.id` (note: `Communication.id`) |
| claim_ref | TEXT | null | The first reference the message named without a `/` (the payer's own number first) |
| sender_code | TEXT | null | `x-hcx-sender_code`; the reply goes back to it |
| workflow_id | TEXT | null | `x-hcx-workflow_id`: the queried submission's thread |
| received_at | TEXT | NOT NULL | When it arrived |
| status | TEXT | NOT NULL, default `open` | See the table above |
| kind | TEXT | NOT NULL, default `query` | `query`, `notification`, `note`. Migration also adds it |
| reason_code | TEXT | null | `Task.reasonCode`, lower case; `claimArbitartion` is stored as `claimarbitration`. Known values: `tatquery`, `grievance`, `walletupdate`, `policychange`, `additionalinfo`, `claimarbitration`, `questionnaire`, `query` [PAYER](../references/PAYERS.md#markers) |
| remarks | TEXT | null | The questions joined by new lines |
| questions | TEXT | null | JSON list: each `payload[].contentString`; else each `reasonCode[].text`; else the Task description (note: payload strings, attachment titles, note texts) |
| request_json | TEXT | null | The bundle as received |
| reply_text | TEXT | null | The desk's answer |
| reply_documents | TEXT | null | JSON list of D28 ids sent with the answer |
| reply_txn_id | TEXT | null | Ledger id of the reply or acknowledgement |
| reply_correlation_id | TEXT | null | Correlation id the reply went out under |
| answered_at | TEXT | null | When the answer went |
| acknowledged_at | TEXT | null | When the acknowledgement went. Migration also adds it |
| error_message | TEXT | null | Why the reply or acknowledgement failed |
| reply_json | TEXT | null | The reply or acknowledgement bundle as sent |

#### D23K. KEYS AND INDEXES
- Primary key `id` (integer).
- Foreign key `claim_id` references `claim (id)` (D9), `ON DELETE CASCADE`.
- Index `ix_claim_query` on `(claim_id, id DESC)`; messages are listed newest first.
- Unique index `ux_claim_query_corr` on `(correlation_id)`. SQLite allows several nulls, which is why a note on a thread already held stores null.

#### D23U. USED BY
- Screens: [S5. Claim Master](../screens/S5-claim-master.md), [S6. Claim Detail](../screens/S6-claim-detail.md), [S9. Pre-authorisation](../screens/S9-preauthorisation.md), [S10. Communication](../screens/S10-communication.md), [S11. Claim Submission](../screens/S11-claim-submission.md)
- APIs: [A7. Communication Reply](../apis/A7-communication-on-request.md), [A17. Claim State](../apis/A17-claim-state.md)
- Callbacks: [C1. Callback Door](../callbacks/C1-callback-door.md), [C9. Payer Communication](../callbacks/C9-communication-request.md)
- FHIR: [F11. CommunicationRequest](../fhir/F11-communicationrequest.md), [F12. Communication](../fhir/F12-communication.md)
- Database: [D9. claim](D9-claim.md), [D28. claim_document](D28-claim-document.md)
