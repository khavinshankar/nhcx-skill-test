# D10. claim_plan

#### D10T. TABLE
One row is the payer's package master (InsurancePlan) for one claim's policy and provider pair; primary key `id`; parent table [D9. claim](D9-claim.md) (one row per claim).

#### D10D. DESCRIPTION
The package master is fetched over NHCX with an InsurancePlan discovery Task (A3, answered on C4). The Task carries only the policy number and the facility's HFR ID. The reply's InsurancePlan is flattened into this row, its packages into [D11. claim_plan_benefit](D11-claim-plan-benefit.md) and its Questionnaires into [D12. claim_plan_form](D12-claim-plan-form.md).

A `ready` plan decides what the rest of the claim uses. The line picker ([D16](D16-claim-line.md)) and line prices come from its benefits, and the package picker uses it in place of the local `claim_package` list. Its documents and forms are the fallback requirement list when there is no auth-requirements ruling ([D13](D13-claim-auth.md)).

Request (S7 "Fetch", or refetch):
- Unless the operator asks to refresh, a master this facility already holds is reused. The source is the newest `ready` row of another claim with the same `policy_code`, `provider_id` and claim `payer_id`, ordered by `fetched_at DESC, id DESC`. All its columns except `id` and `claim_id` are copied onto this claim's row, inserted or overwritten. This claim's benefits and forms are deleted, and the source's are copied. No NHCX call is made.
- Otherwise the request needs the facility's HFR ID and participant code ([D1](D1-organization.md)) and sends A3 with `x-hcx-workflow_id` = `claim_no` [REF](../references/PAYERS.md#markers). Written: `status = 'fetching'`, `txn_id`, `correlation_id`, `requested_at` = now, `policy_code` (the claim's, or null), `provider_id` (HFR ID). Nulled: `fetched_at`, `error_message`, `plan_identifier`, `plan_title`, `plan_type`, `sum_insured`, `policy_documents`, `response_json`. A send that fails writes `status = 'error'` and `error_message`.
- The first request inserts the row. A later one updates it and deletes its benefits in the same transaction; a refetch replaces the master wholesale.

Reply (C4 callback, or polling by `txn_id`):
- A parsed plan writes `plan_identifier`, `plan_title`, `plan_type`, `sum_insured`, `policy_documents`, `fetched_at` = now, `error_message` = null, `response_json`. `status` becomes `ready` when there is at least one benefit, else `empty`. The benefits and forms are deleted and re-inserted in one transaction.
- A reply carrying no InsurancePlan is stored as an empty plan (`status = 'empty'`), with `error_message` ending "The payer has no package master filed under this policy."
- `status = 'error'` with `error_message` on a ProtocolResponse, a protocol error in the ledger, a dispatch status of `dispatch_failed`, `dead` or `failed`, or a ledger 404 ("... Fetch again.").
- A redelivery for a row no longer `fetching` is ignored unless the last send is on record as failed; then the row is revived to `fetching` and the reply applied.

Status values and transitions:
- (none) -> `fetching` (request sent) or `error` (send failed); (none) -> copied status (normally `ready`) on reuse.
- `fetching` -> `ready`, `empty` or `error`.
- `ready`, `empty`, `error` -> `fetching` on a refetch.

Delete: never directly. The row goes with its claim (`ON DELETE CASCADE`) or with the "clear transactional data" reset.

#### D10C. COLUMNS
| column | type | null/default | meaning (and allowed values) |
|---|---|---|---|
| id | INTEGER | primary key | row id; `plan_id` of benefits and forms |
| claim_id | INTEGER | NOT NULL, UNIQUE | the claim ([D9](D9-claim.md)) |
| status | TEXT | NOT NULL, default `'fetching'` | `fetching`, `ready`, `empty`, `error` |
| txn_id | TEXT | null | [G9. Ledger](../gateway/G9-ledger.md) id of the request |
| correlation_id | TEXT | null | ties the request to its on_request |
| requested_at | TEXT | null | ISO timestamp of the request |
| fetched_at | TEXT | null | ISO timestamp the reply was applied |
| error_message | TEXT | null | why the fetch failed, or the note on an empty plan |
| policy_code | TEXT | null | Task.input `policyNumber` sent |
| provider_id | TEXT | null | Task.input `providerId` sent, the facility's HFR ID |
| plan_identifier | TEXT | null | InsurancePlan.identifier[0].value, else InsurancePlan.id |
| plan_title | TEXT | null | InsurancePlan.name |
| plan_type | TEXT | null | display of InsurancePlan.type[0], else of the first plan[].type |
| sum_insured | REAL | null | first plan[].generalCost[].cost.value |
| policy_documents | TEXT | null | JSON list of policy-wide requirements (on the InsurancePlan itself), each `{code, display, category, category_display, form}`; every claim under the policy needs them. Added by migration |
| response_json | TEXT | null | JSON: the full on_request bundle, for audit |

#### D10K. KEYS AND INDEXES
- Primary key `id` (integer).
- `claim_id` references [D9. claim](D9-claim.md) `id`, `ON DELETE CASCADE`.
- Referenced by [D11. claim_plan_benefit](D11-claim-plan-benefit.md) and [D12. claim_plan_form](D12-claim-plan-form.md) (`plan_id`, `ON DELETE CASCADE`).
- Unique: `claim_id` (one package master per claim).
- Index: `ix_claim_plan_corr (correlation_id)`, used to match the reply.

#### D10U. USED BY
- Screens: [S6. Claim Detail](../screens/S6-claim-detail.md), [S7. Insurance Plan](../screens/S7-insurance-plan.md), [S8. Line Items](../screens/S8-line-items.md)
- APIs: [A3. Insurance Plan Request](../apis/A3-insurance-plan-request.md), [A10. Transaction Related](../apis/A10-txn-related.md), [A11. Transaction Dispatch](../apis/A11-txn-dispatch.md), [A13. Transaction List](../apis/A13-txn-list.md), [A17. Claim State](../apis/A17-claim-state.md)
- Callbacks: [C1. Callback Door](../callbacks/C1-callback-door.md), [C4. Insurance Plan Reply](../callbacks/C4-insuranceplan-on-request.md)
- FHIR: [F4. Task (InsurancePlan discovery)](../fhir/F4-task-insuranceplan.md), [F5. InsurancePlan](../fhir/F5-insuranceplan.md)
- Database: [D8. terminology](D8-terminology.md), [D9. claim](D9-claim.md), [D11. claim_plan_benefit](D11-claim-plan-benefit.md), [D12. claim_plan_form](D12-claim-plan-form.md), [D13. claim_auth](D13-claim-auth.md), [D16. claim_line](D16-claim-line.md)
- Tests: [T13. PMJAY Eligibility, Package Master and Ruling](../tests/T13-pmjay-eligibility-and-package-master.md)
