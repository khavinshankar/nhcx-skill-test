# D20. claim_submission

#### D20T. TABLE
One row is the claim leg of one claim episode: how the stay ended, the last claim send and the payer's verdict on it. Primary key `id`. Parent table: `claim` (D9), one row per claim.

#### D20D. DESCRIPTION
The claim carries everything the pre-authorisation did plus the discharge. It is a separate exchange from the pre-authorisation (D18), with its own thread, and it can go in after a pre-authorisation was queried.

**Created.** The first time the row is needed: saving the discharge or sending the claim on Claim Submission (S11) inserts `{claim_id, status: 'draft'}` if there is no row yet.

**Discharge.** "Save discharge" on S11 writes `discharge_mode`, `discharge_stage`, `discharge_date`, `surgery_date` and `death_date`. It is refused while `status` is `submitting`. Rules: the mode must be `normal`, `lama`, `dama` or `death`; the stage must be `Before Surgery`, `During Surgery` or `After Surgery` [PAYER](../references/PAYERS.md#markers); the discharge date is required and not before the admission date; a surgery date may not be before admission, and the discharge may not be before the surgery; `death` requires a date and time of death (a date alone is refused), and any other mode clears `death_date`. A row in `draft` or `error` goes (back) to `draft`; any other status is kept.

A `lama` or `dama` discharge at `Before Surgery` or `During Surgery` makes the claim quote the single procedure `LM100` instead of the pre-authorised lines (the payer disqualifies the rest) [PAYER](../references/PAYERS.md#markers). That is computed at send time from these two columns.

**Sending.** Allowed only with a discharge recorded and the pre-authorisation (D18) `approved` or `queried`. Each send writes `status` `submitting`, `txn_id`, `correlation_id`, `submitted_at`, `claim_ref` (the current claim number), `requested_amount` (the claim's lines total), `submission_kind`, `workflow_id`, `reply_text`, `request_json`, and clears `settled_at`, `error_message`, `outcome`, `disposition`, `approved_amount`, `eligible_amount`, `submitted_amount`, `items_json` and `response_json`. A query answer also keeps the question in `query_note` (the earlier `query_note`, else the earlier `disposition`).

**Which send it is** (`submission_kind`):

| Current row | Next send | Workflow id (PMJAY adapter; other adapters; see [PAYERS.md](../references/PAYERS.md)) [PAYER](../references/PAYERS.md#markers) |
|---|---|---|
| none or `draft` | `claim` | 15; 15 |
| `queried` | `claim_query_response` (reply text required) | 161 [SANDBOX](../references/PAYERS.md#markers); 151 |
| `rejected`, `partial` or `approved` | `claim_resubmit`, only where the adapter defines a workflow for it; PMJAY defines none and is told to ask for a reprocess instead [PAYER](../references/PAYERS.md#markers) | none; 16 |
| `error` | the same kind as the failed send (`claim_query_response` or `claim_resubmit`), else `claim` | |
| `submitting` | refused: "The claim is with the payer; wait for its answer before sending again." | |

**Statuses** (exact strings): `draft`, `submitting`, `approved`, `partial`, `queried`, `rejected`, `error`.

**The payer's reply** (C6, or polling when the claim is opened) is read exactly as for the pre-authorisation (D18 table) [PAYER](../references/PAYERS.md#markers): outcome `queued` / `acknowledged` or reason `submitted` / `acknowledged` keeps `submitting`; reason `cancelled`, `rejected` or `denied`, or outcome `error`, is `rejected` (the `rejected` and `denied` reasons are a correction to the reference implementation, which read them as `queried`); reason `queried` is `queried`; `partial` with reason `approved` is `partial`; `complete` with reason `approved` or none is `approved`; anything else `queried`. It writes the flattened reply, `api_call_id`, `settled_at` (for a decision), `response_json`, clears `error_message` and copies `correlation_id` into `thread_correlation_id`. A redelivery (same `x-hcx-api_call_id`, or with none, the same outcome and adjudication) is ignored.

**Refusals.** A ProtocolResponse, a peer or protocol error found by polling, a failed dispatch or a failed send sets `status` `error` with the message. A refused `claim_query_response` instead goes back to `queried` with the question restored into `disposition`, so the desk answers again. `correlation_id` is put back to `thread_correlation_id` when there is one. A ledger 404 sets `error`.

**Reprocess and release.** When the payer accepts a reprocess or balance release Task (D29, C8), this row goes back to `submitting` with `settled_at` and `error_message` cleared: the new verdict comes on the claim's own thread.

**Revival.** A row on record as a failed send goes back to `submitting` when the payer answers on its thread.

**Deleted.** Never by the application; by cascade with the claim or when the transactional store is cleared. Every change also recomputes the claim's `stage` and `sub_stage` (D9).

#### D20C. COLUMNS
| Column | Type | Null / default | Meaning |
|---|---|---|---|
| id | INTEGER | primary key | Row id |
| claim_id | INTEGER | NOT NULL, unique | The claim (D9) |
| status | TEXT | NOT NULL, default `draft` | `draft`, `submitting`, `approved`, `partial`, `queried`, `rejected`, `error` |
| discharge_mode | TEXT | null | `normal`, `lama`, `dama`, `death` (sent as `DTH`, `LAMA`, `DAMA`, `DTM`) [PAYER](../references/PAYERS.md#markers) |
| discharge_stage | TEXT | null | `Before Surgery`, `During Surgery`, `After Surgery` |
| discharge_date | TEXT | null | Discharge date or date-time |
| surgery_date | TEXT | null | Surgery date or date-time |
| death_date | TEXT | null | Date and time of death; mode `death` only |
| txn_id | TEXT | null | [G9. Ledger](../gateway/G9-ledger.md) id of the last send |
| correlation_id | TEXT | null | Correlation id of the last send |
| submitted_at | TEXT | null | When the last send went |
| settled_at | TEXT | null | When a decision was applied |
| error_message | TEXT | null | Why the last send failed or was refused |
| claim_ref | TEXT | null | The claim number the claim went under |
| preauth_ref | TEXT | null | `ClaimResponse.preAuthRef` as echoed on the claim's reply. Migration also adds it |
| api_call_id | TEXT | null | `x-hcx-api_call_id` of the last reply applied |
| adjudication | TEXT | null | Claim-level adjudication reason code, lower case |
| query_note | TEXT | null | The payer's query trail; during a query answer, the question being answered |
| outcome | TEXT | null | `ClaimResponse.outcome` |
| disposition | TEXT | null | `ClaimResponse.disposition` |
| approved_amount | REAL | null | `total` category `benefit` |
| eligible_amount | REAL | null | `total` category `eligible` |
| submitted_amount | REAL | null | `total` category `submitted` |
| requested_amount | REAL | null | The claim's lines total when sent |
| items_json | TEXT | null | JSON list, one entry per `ClaimResponse.item` (same shape as D18), including `deductible` and `deduction_reason` |
| submission_kind | TEXT | null | `claim`, `claim_query_response`, `claim_resubmit` |
| workflow_id | TEXT | null | The `x-hcx-workflow_id` the last send carried |
| request_json | TEXT | null | The bundle as sent |
| response_json | TEXT | null | The last reply applied |
| thread_correlation_id | TEXT | null | The correlation id the payer last answered on. Migration only |
| reply_text | TEXT | null | The desk's answer on a query-answer send (the `CQD` entry [PAYER](../references/PAYERS.md#markers)). Migration only |

#### D20K. KEYS AND INDEXES
- Primary key `id` (integer).
- Foreign key `claim_id` references `claim (id)` (D9), `ON DELETE CASCADE`; `claim_id` is UNIQUE.
- Index `ix_claim_submission_corr` on `(correlation_id)`. Payer-initiated messages are also matched on `claim_ref`.

#### D20U. USED BY
- Screens: [S5. Claim Master](../screens/S5-claim-master.md), [S6. Claim Detail](../screens/S6-claim-detail.md), [S11. Claim Submission](../screens/S11-claim-submission.md), [S12. Payments](../screens/S12-payments.md)
- APIs: [A5. Claim Submit](../apis/A5-claim-submit.md), [A10. Transaction Related](../apis/A10-txn-related.md), [A11. Transaction Dispatch](../apis/A11-txn-dispatch.md), [A12. Transaction FHIR](../apis/A12-txn-fhir.md), [A13. Transaction List](../apis/A13-txn-list.md), [A14. Adjudicator User Role](../apis/A14-adjudicator-user-role.md), [A15. Adjudicator Process Case](../apis/A15-adjudicator-process-case.md), [A17. Claim State](../apis/A17-claim-state.md)
- Callbacks: [C1. Callback Door](../callbacks/C1-callback-door.md), [C6. Claim Reply](../callbacks/C6-claim-on-submit.md), [C8. Enquiry Reply](../callbacks/C8-enquiry-on-submit.md), [C9. Payer Communication](../callbacks/C9-communication-request.md), [C10. Payment Notice](../callbacks/C10-paymentnotice-request.md)
- FHIR: [F8. Claim](../fhir/F8-claim.md), [F9. ClaimResponse](../fhir/F9-claimresponse.md), [F10. Task (claim actions)](../fhir/F10-task-claim-actions.md), [F11. CommunicationRequest](../fhir/F11-communicationrequest.md), [F13. PaymentNotice](../fhir/F13-paymentnotice.md), [F19. Other bundle resources](../fhir/F19-other-resources.md)
- Database: [D9. claim](D9-claim.md), [D16. claim_line](D16-claim-line.md), [D21. claim_payment](D21-claim-payment.md), [D23. claim_query](D23-claim-query.md), [D24. claim_adjudication](D24-claim-adjudication.md), [D29. claim_enquiry](D29-claim-enquiry.md)
