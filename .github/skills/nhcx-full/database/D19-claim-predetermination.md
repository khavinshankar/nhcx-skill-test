# D19. claim_predetermination

#### D19T. TABLE
One row is one predetermination ask on a claim: the pre-authorisation bundle sent with `use: predetermination` and the payer's non-binding quote. Primary key `id`. Parent table: `claim` (D9), many rows per claim.

#### D19D. DESCRIPTION
A predetermination asks "what would the policy pay for this?" before anything is committed. The payer answers with a ClaimResponse that binds nobody and opens no case, so each ask is its own row rather than a state of the pre-authorisation (D18).

**Created.** "Ask for a quote" on Pre-authorisation (S9). Allowed only when the claim's eligibility status is `eligible` and no earlier ask on the claim is still `asking` ("A quote is already with the payer; wait for its answer before asking again."). The bundle is the pre-authorisation's (lines D16, diagnoses D25, care team D26, the leg's documents D28) under its own anchor. It goes out on the pre-authorisation route with `x-hcx-workflow_id` `12` (see [PAYERS.md](../references/PAYERS.md)) [PAYER](../references/PAYERS.md#markers). The row is inserted with `status` `asking`, `txn_id`, `correlation_id`, `requested_at`, `requested_amount` (the lines total) and `request_json`. When [G7. Send](../gateway/G7-send.md) reports the send failed after naming its ids, the row is inserted with `status` `error` and the message, and the error is shown.

**Statuses** (exact strings): `asking`, `answered`, `error`.

- `asking` to `answered`: a ClaimResponse arrives on the thread, by callback C5 (a pre-authorisation reply whose correlation id no D18 row holds is tried here) or by polling when the claim is opened. Whatever the outcome, the ask is answered: `answered_at`, `outcome`, `adjudication`, `disposition`, `allowed_amount` (the reply's `total` category `benefit`) and `response_json` are written and `error_message` cleared.
- `asking` to `error`: a ProtocolResponse on the thread, a peer or protocol error found by polling, or [G9. Ledger](../gateway/G9-ledger.md) no longer holding the transaction (A10 finds nothing; the message tells the desk to ask again).
- `error` to `asking` to `answered`: an `error` row is revived when the payer answers on its thread anyway.
- An `answered` row ignores further replies.

**Deleted.** Never by the application; by cascade with the claim or when the transactional store is cleared.

#### D19C. COLUMNS
| Column | Type | Null / default | Meaning |
|---|---|---|---|
| id | INTEGER | primary key | Row id |
| claim_id | INTEGER | NOT NULL | The claim (D9) |
| status | TEXT | NOT NULL, default `asking` | `asking`, `answered`, `error` |
| txn_id | TEXT | null | [G9. Ledger](../gateway/G9-ledger.md) id of the ask |
| correlation_id | TEXT | null | Correlation id the answer arrives on |
| requested_at | TEXT | NOT NULL | When the ask was sent |
| answered_at | TEXT | null | When the quote was applied |
| error_message | TEXT | null | Why the ask failed |
| outcome | TEXT | null | `ClaimResponse.outcome`: `complete`, `error`, `partial` |
| adjudication | TEXT | null | Claim-level adjudication reason code, lower case |
| disposition | TEXT | null | `ClaimResponse.disposition` |
| allowed_amount | REAL | null | `total` category `benefit`: what the payer would allow |
| requested_amount | REAL | null | Sum of the lines (D16) when asked |
| request_json | TEXT | null | The bundle as sent |
| response_json | TEXT | null | The reply bundle |

#### D19K. KEYS AND INDEXES
- Primary key `id` (integer).
- Foreign key `claim_id` references `claim (id)` (D9), `ON DELETE CASCADE`.
- Index `ix_claim_predetermination_corr` on `(correlation_id)`.
- Index `ix_claim_predet_claim` on `(claim_id, id)`; asks are listed newest first. (Kept under 30 characters: some ORMs and databases refuse a longer index name; a target with such a limit shortens any other name the same way and records it in mapping.json.)

#### D19U. USED BY
- Screens: [S6. Claim Detail](../screens/S6-claim-detail.md), [S9. Pre-authorisation](../screens/S9-preauthorisation.md)
- APIs: [A4. Pre-auth Submit](../apis/A4-preauth-submit.md), [A10. Transaction Related](../apis/A10-txn-related.md), [A11. Transaction Dispatch](../apis/A11-txn-dispatch.md), [A13. Transaction List](../apis/A13-txn-list.md), [A17. Claim State](../apis/A17-claim-state.md)
- Callbacks: [C1. Callback Door](../callbacks/C1-callback-door.md), [C5. Pre-auth Reply](../callbacks/C5-preauth-on-submit.md)
- FHIR: [F9. ClaimResponse](../fhir/F9-claimresponse.md)
- Database: [D9. claim](D9-claim.md), [D16. claim_line](D16-claim-line.md)
