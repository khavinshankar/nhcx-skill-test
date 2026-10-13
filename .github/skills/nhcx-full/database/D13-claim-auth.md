# D13. claim_auth

#### D13T. TABLE
One row is the payer's authorisation-requirements ruling on a claim's procedure set; primary key `id`; parent table [D9. claim](D9-claim.md) (one row per claim).

#### D13D. DESCRIPTION
After the lines are chosen, the procedure set is sent as a coverage eligibility check with purpose `auth-requirements` (A2, answered on C3). The check carries the same items the Claim will. The payer answers per line ([D14. claim_auth_item](D14-claim-auth-item.md)): is authorisation required, is the line excluded, what is allowed. It also names the documents and questionnaires the set needs ([D15. claim_auth_requirement](D15-claim-auth-requirement.md)). A `ready` ruling is the source of the required documents and forms for both legs. Without one, the package master ([D10](D10-claim-plan.md)) is used instead.

When it is sent:
- By hand from S8 ("Validate"). This needs `claim.status = 'eligible'` ("Check the policy's eligibility before validating a procedure set against it."). A failed send raises the error.
- Automatically before every pre-auth send (first request, enhancement, query answer). Skipped when the claim is not `eligible`, has no lines, or the payer adapter does not send the check unasked (the operator may still ask any payer from S8). Also skipped when a non-`error` ruling already exists for the same procedure set (`asked_codes` equal to the current set). A failed automatic send is swallowed, and the pre-auth goes out anyway.

Request:
- Written: `status = 'checking'`, `txn_id`, `correlation_id`, `requested_at` = now, `asked_codes` = the current procedure set. Nulled: `settled_at`, `error_message`, `outcome`, `disposition`, `inforce`, `response_json`. A failed send writes `status = 'error'` and `error_message`.
- The first request inserts the row. A later one deletes its items and requirements and updates the row, in one transaction.

Reply (C3 callback, or polling by `txn_id`):
- The last CoverageEligibilityResponse in the bundle is the payer's. Written: `outcome`, `disposition`, `inforce` (from `insurance[0].inforce`), `status = 'ready'`, `settled_at` = now, `error_message` = null, `response_json`. Items and requirements are deleted and re-inserted in the same transaction.
- `status = 'error'` with `error_message` on a ProtocolResponse, a protocol error in the ledger, a dispatch status of `dispatch_failed`, `dead` or `failed`, or a ledger 404 ("... Check again.").
- A coverage reply whose correlation id matches no claim's eligibility check ([D9](D9-claim.md)) is matched here by `correlation_id`.
- A redelivery for a row no longer `checking` is ignored unless the last send is on record as failed; then it is revived to `checking` and applied.

A `ready` ruling is stale when the quoted non-Stratification line codes differ from the ruled item codes. Any change to the procedure set (codes, quantities or tiers) makes `asked_codes` differ, so the ruling is asked again at the next pre-auth send.

Status values and transitions:
- (none) -> `checking` or `error`.
- `checking` -> `ready` or `error`.
- `ready`, `error` -> `checking` on a new request.

Delete: never directly. The row goes with its claim (`ON DELETE CASCADE`) or with the "clear transactional data" reset.

#### D13C. COLUMNS
| column | type | null/default | meaning (and allowed values) |
|---|---|---|---|
| id | INTEGER | primary key | row id; `auth_id` of items and requirements |
| claim_id | INTEGER | NOT NULL, UNIQUE | the claim ([D9](D9-claim.md)) |
| status | TEXT | NOT NULL, default `'checking'` | `checking`, `ready`, `error` |
| txn_id | TEXT | null | [G9. Ledger](../gateway/G9-ledger.md) id of the check |
| correlation_id | TEXT | null | ties the check to its on_check |
| requested_at | TEXT | null | ISO timestamp sent |
| settled_at | TEXT | null | ISO timestamp the ruling was applied |
| error_message | TEXT | null | why the check failed |
| outcome | TEXT | null | CoverageEligibilityResponse.outcome |
| disposition | TEXT | null | CoverageEligibilityResponse.disposition |
| inforce | INTEGER | null | `1` / `0` from `insurance[0].inforce` |
| response_json | TEXT | null | JSON: the full on_check bundle, for audit |
| asked_codes | TEXT | null | the procedure set asked about: sorted `<code>x<quantity>[<tier codes>]` entries joined by `|`. Migration only |

#### D13K. KEYS AND INDEXES
- Primary key `id` (integer).
- `claim_id` references [D9. claim](D9-claim.md) `id`, `ON DELETE CASCADE`.
- Referenced by [D14. claim_auth_item](D14-claim-auth-item.md) and [D15. claim_auth_requirement](D15-claim-auth-requirement.md) (`auth_id`, `ON DELETE CASCADE`).
- Unique: `claim_id`.
- Index: `ix_claim_auth_corr (correlation_id)`.

#### D13U. USED BY
- Screens: [S6. Claim Detail](../screens/S6-claim-detail.md), [S8. Line Items](../screens/S8-line-items.md)
- APIs: [A2. Coverage Eligibility Check](../apis/A2-coverage-eligibility-check.md), [A10. Transaction Related](../apis/A10-txn-related.md), [A11. Transaction Dispatch](../apis/A11-txn-dispatch.md), [A13. Transaction List](../apis/A13-txn-list.md), [A17. Claim State](../apis/A17-claim-state.md)
- Callbacks: [C1. Callback Door](../callbacks/C1-callback-door.md), [C3. Authorisation Requirements Ruling](../callbacks/C3-auth-requirements-on-check.md)
- FHIR: [F3. CoverageEligibilityResponse](../fhir/F3-coverage-eligibility-response.md)
- Database: [D9. claim](D9-claim.md), [D10. claim_plan](D10-claim-plan.md), [D12. claim_plan_form](D12-claim-plan-form.md), [D14. claim_auth_item](D14-claim-auth-item.md), [D15. claim_auth_requirement](D15-claim-auth-requirement.md), [D16. claim_line](D16-claim-line.md)
