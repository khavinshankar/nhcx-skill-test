# D18. claim_preauth

#### D18T. TABLE
One row is the pre-authorisation leg of one claim: the last send (first request, query answer, enhancement), the payer's verdict on it and any cancellation. Primary key `id`. Parent table: `claim` (D9), one row per claim.

#### D18D. DESCRIPTION
The draft itself lives on `claim` (D9) and its child tables (D16, D25, D26, D27, D28, D17). This row is the exchange. There is only ever one per claim: every later send, and the cancellation, overwrites it.

**Created.** The first "Send" on Pre-authorisation (S9), allowed only when the claim's eligibility status is `eligible`. The row is inserted with `status` `submitting`. If [G7. Send](../gateway/G7-send.md) reports the send failed after naming the ids it went out under, the row is still written under those ids, marked as a refusal (below), and the error is shown.

**What each send writes.** `status` `submitting`, `txn_id` and `correlation_id` from the [G7. Send](../gateway/G7-send.md) result, `submitted_at` now, `claim_ref` the claim number the bundle went under, `requested_amount` the sum of the lines (D16), `submission_kind`, `workflow_id`, `reply_text`, `request_json`; it clears `settled_at`, `error_message`, `preauth_ref`, `outcome`, `disposition`, `approved_amount`, `eligible_amount`, `submitted_amount`, `items_json` and `response_json`. An enhancement or a query answer then puts the earlier `preauth_ref` back, and keeps `enhancement_no` (an `enhancement` adds 1 to it). **Exception, enhancements.** An `enhancement` or `enhancement_resubmit` send does not clear the approval's columns (`approved_amount`, `eligible_amount`, `submitted_amount`, `outcome`, `adjudication`, `disposition`, `items_json`, `settled_at`): the approval stands until the payer answers, and C5 overwrites them only on an approval (workflow 22). When the enhancement does not get through (the send fails or is refused at the door, A4, or the payer denies it, C5), those columns are therefore still the approval's; a door refusal writes only the failed send's `txn_id`, `correlation_id`, `submitted_at`, `error_message`, `submission_kind`, `workflow_id` and `enhancement_no`, and keeps `request_json` as the last accepted send's bundle. The approved pre-authorisation stands, in the data as on the screen.

**Which send it is** (`submission_kind`, chosen from the current row):

| Current row | Next send | Workflow id (PMJAY adapter, see [PAYERS.md](../references/PAYERS.md)) [PAYER](../references/PAYERS.md#markers) |
|---|---|---|
| none, `cancelled` or `error` | `preauth` | 12 |
| `rejected` | `preauth` (a fresh pre-authorisation) [REF](../references/PAYERS.md#markers) | 12 |
| `queried`, last send an enhancement | `enhancement_resubmit` | 131 |
| `queried`, otherwise | `preauth_query_response` | 19 |
| `approved` / `partial` with lines added since | `enhancement` | 13 |
| `approved` / `partial`, nothing added | refused: "The pre-authorisation is already decided; add a line to ask for an enhancement." | |
| `submitting` / `cancelling` | refused: "The pre-authorisation is with the payer; wait for its answer before sending again." | |

A query answer and an enhancement query answer require the desk's reply text; it is stored in `reply_text` and carried as the `CQD` note [PAYER](../references/PAYERS.md#markers).

**Statuses** (exact strings): `submitting`, `approved`, `partial`, `queried`, `rejected`, `cancelling`, `cancelled`, `error`.

**The payer's reply** (C5, or the poll through A10 to A12 when the case is opened) is read from the ClaimResponse's `outcome` and claim-level `adjudication` reason together [PAYER](../references/PAYERS.md#markers):

| outcome / reason | status |
|---|---|
| outcome `queued` or `acknowledged`, or reason `submitted` or `acknowledged` | `submitting` (not a decision; `settled_at` stays null) |
| reason `cancelled`, `rejected` or `denied` | `rejected` (the `rejected` and `denied` reasons are a correction: the reference implementation read them as `queried`) |
| reason `queried` | `queried` |
| outcome `error` | `rejected` |
| outcome `partial`, reason `approved` | `partial` |
| outcome `partial`, any other reason | `queried` |
| outcome `complete`, reason `approved` or none | `approved` |
| anything else | `queried` |

Applying a reply writes `outcome`, `adjudication`, `disposition`, `preauth_ref` (kept when the reply carries none), the three totals, `items_json`, `query_note`, `api_call_id`, `settled_at` (when it is a decision), `response_json`, clears `error_message`, and copies the current `correlation_id` into `thread_correlation_id`. A reply is applied several times on one thread (acknowledgement, query, decision); one whose `x-hcx-api_call_id` equals `api_call_id` is a redelivery and is ignored. Without an api_call_id, a reply with the same `outcome` and `adjudication` as the row is treated as the same message.

**Refusals.** A ProtocolResponse on the thread, a peer or protocol error found by polling, or a send failure sets `status` `error` with the message, except that a refused `enhancement` or `enhancement_resubmit` goes back to `approved` with the message kept in `error_message` (the approved pre-authorisation stands). Either way `correlation_id` is put back to `thread_correlation_id` when there is one. A ledger that no longer has the transaction (404), or a failed dispatch, sets `error`.

**Revival.** A row on record as a failed send (`error`, or `approved` / `partial` / `queried` with an error message other than a refused cancellation) goes back to `submitting` when the payer answers on its thread, and the answer is then applied.

**Cancellation.** Allowed from `submitting`, `approved`, `partial` or `queried`. It writes `pre_cancel_status` (the status it had), `status` `cancelling`, `cancel_txn_id`, `cancel_correlation_id`, `cancel_requested_at`, `cancel_reason` (a key: `treatmentplanchanged`, `patientrequest`, `financialconstraints`, `alternativetreatment`, `duplicateclaim`, `administrativeerror`, `other`; `other` requires a note), `cancel_note`, and clears `error_message` (`error` when the send failed). The payer's Task reply (C7, or polling) then:

- accepted (Task status none, `completed` or `accepted`, and outcome not `error`): `status` `cancelled`, `settled_at`, `outcome`, `disposition`, `response_json`, and the claim is given a fresh claim number from the counter (D30). The withdrawn number stays here in `claim_ref`.
- refused: `status` back to `pre_cancel_status` (`approved` when none was recorded) with `error_message` "The payer did not accept the cancellation.". The reference implementation always set `approved`, even for a cancel sent from `submitting` or `queried`; restoring the earlier status is a correction. For 15 minutes after that, polling still looks for an acceptance on the thread [REF](../references/PAYERS.md#markers).

- refused at the door (a `ProtocolResponse` on the cancel thread): `status` back to `pre_cancel_status` (`approved` when none was recorded) with `error_message` `<code>: <message>`, so a corrected cancel can be sent from that status; the leg is not left in `error`.

A ClaimResponse adjudicated `cancelled` on the pre-authorisation thread while `cancelling` also sets `cancelled`. Once `cancelled`, every further reply on the thread is ignored.

**Deleted.** Never by the application; by cascade with the claim or when the transactional store is cleared.

Every change goes through a write that also recomputes the claim's `stage` and `sub_stage` (D9).

#### D18C. COLUMNS
| Column | Type | Null / default | Meaning |
|---|---|---|---|
| id | INTEGER | primary key | Row id |
| claim_id | INTEGER | NOT NULL, unique | The claim (D9) |
| status | TEXT | NOT NULL, default `submitting` | `submitting`, `approved`, `partial`, `queried`, `rejected`, `cancelling`, `cancelled`, `error` |
| txn_id | TEXT | null | [G9. Ledger](../gateway/G9-ledger.md) id of the last send |
| correlation_id | TEXT | null | `x-hcx-correlation_id` of the last send; the payer's reply arrives on it |
| submitted_at | TEXT | null | When the last send went (ISO instant, +05:30) |
| settled_at | TEXT | null | When a decision (or cancellation answer) was applied |
| error_message | TEXT | null | Why the last send or cancel failed or was refused |
| claim_ref | TEXT | null | The claim number sent as `Claim.identifier`; keeps a number later retired by a cancellation |
| preauth_ref | TEXT | null | `ClaimResponse.preAuthRef`, the payer's case reference |
| api_call_id | TEXT | null | `x-hcx-api_call_id` of the last reply applied, to ignore redeliveries |
| adjudication | TEXT | null | Claim-level adjudication reason code, lower case (the reason on the entry categorised `status` first) |
| query_note | TEXT | null | The payer's query trail: item adjudication `reason` texts and `processNote` texts, one per line |
| outcome | TEXT | null | `ClaimResponse.outcome`: `complete`, `error`, `partial`, `queued` |
| disposition | TEXT | null | `ClaimResponse.disposition` |
| approved_amount | REAL | null | `total` category `benefit`: granted by this reply |
| eligible_amount | REAL | null | `total` category `eligible`: what the case stands at |
| submitted_amount | REAL | null | `total` category `submitted`, when echoed |
| requested_amount | REAL | null | Sum of the lines (D16) when sent |
| items_json | TEXT | null | JSON list, one entry per `ClaimResponse.item`: `sequence`, `status`, `eligible`, `percent`, `quantity`, `deductible`, `deduction_reason`, `reason`, and `benefit` / `submitted` when present |
| submission_kind | TEXT | null | `preauth`, `preauth_query_response`, `enhancement`, `enhancement_resubmit` (`preauth_resubmit` is recognised when reading but not chosen by the sender [REF](../references/PAYERS.md#markers)) |
| workflow_id | TEXT | null | The `x-hcx-workflow_id` the last send carried |
| request_json | TEXT | null | The bundle as sent |
| response_json | TEXT | null | The last reply bundle applied |
| cancel_txn_id | TEXT | null | Ledger id of the cancel Task |
| cancel_correlation_id | TEXT | null | Correlation id of the cancel Task |
| cancel_requested_at | TEXT | null | When the cancel was sent |
| cancel_reason | TEXT | null | Cancel reason key (listed above) |
| cancel_note | TEXT | null | Free-text justification |
| pre_cancel_status | TEXT | null | The status before the cancel was sent, restored when the payer refuses it. Not in the reference implementation's schema; add it |
| enhancement_no | INTEGER | null | Count of enhancement rounds on this pre-authorisation. Migration only |
| thread_correlation_id | TEXT | null | The correlation id the payer last answered on; restored to `correlation_id` after a refused send. Migration only |
| reply_text | TEXT | null | The desk's answer carried by a query-answer send. Migration only |

#### D18K. KEYS AND INDEXES
- Primary key `id` (integer).
- Foreign key `claim_id` references `claim (id)` (D9), `ON DELETE CASCADE`; `claim_id` is UNIQUE (one leg per claim).
- Index `ix_claim_preauth_corr` on `(correlation_id)`. Inbound messages are also matched on `cancel_correlation_id` (no index) and, for payer-initiated messages, on `claim_ref`.

#### D18U. USED BY
- Screens: [S5. Claim Master](../screens/S5-claim-master.md), [S6. Claim Detail](../screens/S6-claim-detail.md), [S9. Pre-authorisation](../screens/S9-preauthorisation.md)
- APIs: [A4. Pre-auth Submit](../apis/A4-preauth-submit.md), [A6. Task Submit (cancel, status, reprocess, release)](../apis/A6-task-submit.md), [A10. Transaction Related](../apis/A10-txn-related.md), [A11. Transaction Dispatch](../apis/A11-txn-dispatch.md), [A12. Transaction FHIR](../apis/A12-txn-fhir.md), [A13. Transaction List](../apis/A13-txn-list.md), [A14. Adjudicator User Role](../apis/A14-adjudicator-user-role.md), [A15. Adjudicator Process Case](../apis/A15-adjudicator-process-case.md), [A17. Claim State](../apis/A17-claim-state.md)
- Callbacks: [C1. Callback Door](../callbacks/C1-callback-door.md), [C5. Pre-auth Reply](../callbacks/C5-preauth-on-submit.md), [C7. Cancel Reply](../callbacks/C7-cancel-on-submit.md), [C9. Payer Communication](../callbacks/C9-communication-request.md), [C10. Payment Notice](../callbacks/C10-paymentnotice-request.md)
- FHIR: [F8. Claim](../fhir/F8-claim.md), [F9. ClaimResponse](../fhir/F9-claimresponse.md), [F10. Task (claim actions)](../fhir/F10-task-claim-actions.md), [F11. CommunicationRequest](../fhir/F11-communicationrequest.md), [F13. PaymentNotice](../fhir/F13-paymentnotice.md)
- Database: [D9. claim](D9-claim.md), [D16. claim_line](D16-claim-line.md), [D19. claim_predetermination](D19-claim-predetermination.md), [D20. claim_submission](D20-claim-submission.md), [D21. claim_payment](D21-claim-payment.md), [D23. claim_query](D23-claim-query.md), [D24. claim_adjudication](D24-claim-adjudication.md), [D29. claim_enquiry](D29-claim-enquiry.md), [D30. counter](D30-counter.md)
