# D24. claim_adjudication

#### D24T. TABLE
One row is one decision step taken from the application's adjudicator desk on a case this application raised: one role, one action, one call to the payer's desk. Primary key `id`. Parent table: `claim` (D9), many rows per claim.

#### D24D. DESCRIPTION
A PMJAY decision is taken in the NHCX Payer Service, outside the exchange, so NHCX carries no record of it [PAYER](../references/PAYERS.md#markers). This table is the only trace of who decided what from here, and why. It is a sandbox testing aid (A14, A15) [SANDBOX](../references/PAYERS.md#markers); a production hospital system does not drive the payer's desk.

**Created.** One row per action sent to a payer desk, whether the desk accepted it or not (`success` 0 or 1). Nothing is written for a role lookup alone.

- **Single step.** An action taken by hand at the role currently holding the case.
- **Cycle.** "Approve", "Reject" or "Query" as a decision: for the NHCX Payer Service the role is read before every step and the action for that role is sent, walking the case through the workflow. Every step of one run shares one `cycle_id` (a UUID). The run stops when no role holds the case, the same role comes back twice, an action is refused, a non-approval is taken (after CEX, which can only forward), the last role (or `PPD-Trust` for a pre-authorisation) has acted, or after 8 steps [REF](../references/PAYERS.md#markers).
- **IRDAI payer desk.** One action (`approve`, `reject` or `query`) on the case the payer portal opened; `reject` and `query` need remarks.

`stage` is the leg decided: `preauth` (the D18 row) or `claim` (the D20 row). `case_number` is that leg's `claim_ref` (else the claim number); for the NHCX Payer Service it is the last `/` segment of D18 `preauth_ref` when there is one. `correlation_id` is the leg's own correlation id, never typed in.

Workflow roles of the PMJAY desk, their actions and the `usecase` sent [PAYER](../references/PAYERS.md#markers):

| Role | Actions | usecase |
|---|---|---|
| PPD-Trust | Approve, Reject, Query | PREAUTH |
| CEX-Trust | Forward | CLAIM |
| CPD-Trust | cpdApprove, cpdReject, Pending | CLAIM |
| Medical Audit Committee | Approve, Reject, iQuery | Medical Audit Committee |
| ACO-Trust | Approve, Reject, Pending | CLAIM |
| SHA-Trust | Approve, Reject, Pending | CLAIM |
| Claim Review Committee | Approve, Reject, Pending | Claim Review Committee |

**Updated / deleted.** Rows are never updated. They go by cascade with the claim or when the transactional store is cleared. There is no status column; `success` records the result.

#### D24C. COLUMNS
| Column | Type | Null / default | Meaning |
|---|---|---|---|
| id | INTEGER | primary key | Row id |
| claim_id | INTEGER | NOT NULL | The claim (D9) |
| stage | TEXT | NOT NULL | `preauth` or `claim` |
| case_number | TEXT | null | The case number sent to the desk |
| role | TEXT | null | Role that acted (table above); `Adjudicator` on the IRDAI desk |
| action | TEXT | null | Action as sent (table above); `approve`, `reject` or `query` on the IRDAI desk |
| usecase | TEXT | null | `usecase` sent (table above); the case's stage on the IRDAI desk |
| correlation_id | TEXT | null | The leg's correlation id |
| remarks | TEXT | null | Remarks typed with the action |
| success | INTEGER | NOT NULL, default 0 | 1 when the desk accepted the action |
| http_status | INTEGER | null | HTTP status of the desk's reply |
| response_json | TEXT | null | The full reply as recorded (request, response, error) |
| desk | TEXT | null | Where the action went: `nhcx-payer-service` (the Payer Service called directly), `irdai-payer` (the sandbox payer portal), or `gateway` on rows written when the action was relayed through a separate gateway service. The embedded gateway has no such relay, so new rows do not carry it. Migration also adds it |
| cycle_id | TEXT | null | Shared by every step of one automatic run; null for a single step. Migration also adds it |
| taken_at | TEXT | NOT NULL | When the action was sent |

#### D24K. KEYS AND INDEXES
- Primary key `id` (integer).
- Foreign key `claim_id` references `claim (id)` (D9), `ON DELETE CASCADE`.
- Index `ix_claim_adjudication` on `(claim_id, stage, id DESC)`; decisions are listed per leg, newest first.

#### D24U. USED BY
- APIs: [A15. Adjudicator Process Case](../apis/A15-adjudicator-process-case.md)
- Callbacks: [C1. Callback Door](../callbacks/C1-callback-door.md)
- Database: [D9. claim](D9-claim.md)
