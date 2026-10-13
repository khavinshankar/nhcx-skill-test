# D31. audit_log

#### D31T. TABLE
One row is one line of the trail: who did what to which record, and every message answered on the exchange; primary key `id`, an identity column. No parent table. The reference implementation names it `payer_audit_log` [REF](../references/PAYERS.md#markers).

#### D31D. DESCRIPTION
Money and health information are both the kind of thing you want to answer "who changed this, and when" about. Every write against member, policy, enrolment, case and payment data, and every sign-in attempt, appends a row with the acting account and its address.

**The exchange's receipts.** Every answer this payer sends writes a row under `entity_type` `nhcx_txn` with the inbound ledger id as `entity_id` and the answer's ledger id in the detail: `eligibility.answered`, `eligibility.lapsed`, `eligibility.no_cover`, `eligibility.auth_requirements` ([A1. Eligibility Answer](../apis/A1-eligibility-answer.md)); `insuranceplan.answered`, `insuranceplan.no_plan` ([A2. Insurance Plan Answer](../apis/A2-insurance-plan-answer.md)); `preauth.received`, `preauth.enhanced`, `preauth.resubmitted` ([C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md)); `claim.received` ([C5. Claim Submit](../callbacks/C5-claim-submit.md)); `predetermination.answered` ([A10. Predetermination Quote](../apis/A10-predetermination-quote.md)); `status.answered` ([A8. Status Answer](../apis/A8-status-answer.md)); `task.<code>.answered` ([A9. Task Answer](../apis/A9-task-answer.md)); `paymentnotice.answered` ([A7. Payment Enquiry Answer](../apis/A7-payment-enquiry-answer.md)); `communication.received` ([C9. Communication](../callbacks/C9-communication.md)). Verdicts and notices are written under `case` and `payment`: `preauth.answered`, `claim.answered`, `reprocess.answered` ([A3. Pre-auth Answer](../apis/A3-preauth-answer.md), [A4. Claim Answer](../apis/A4-claim-answer.md), [A9. Task Answer](../apis/A9-task-answer.md)), `query.sent` ([A5. Query Request](../apis/A5-query-request.md)), `payment.noticed` ([A6. Payment Notice](../apis/A6-payment-notice.md)).

The row under `nhcx_txn` is read back by the callback door ([C1. Callback Door](../callbacks/C1-callback-door.md)): an inbound transaction with a receipt was already answered, and the gateway retrying it is a duplicate ([D28. nhcx_delivery](D28-nhcx-delivery.md)).

**Never fails the caller.** A request that succeeded is not reported as failed because the log behind it could not be written; a failure is logged loudly instead.

Delete: never.

#### D31C. COLUMNS
| column | type | null/default | meaning (and allowed values) |
|---|---|---|---|
| id | BIGINT | primary key, identity | row id |
| at | TIMESTAMPTZ | NOT NULL, default now | when |
| user_id | VARCHAR(36) | null | the acting account ([D2. staff](D2-staff.md)); null for the exchange |
| action | VARCHAR(48) | NOT NULL | dotted action name, as above |
| entity_type | VARCHAR(32) | NOT NULL | `member`, `policy`, `subscription`, `case`, `payment`, `nhcx_txn`, `auth` |
| entity_id | VARCHAR(64) | null | the record's id, or the ledger id |
| detail | VARCHAR(500) | null | one line: the sender, correlation id, case and answer transaction |
| ip | VARCHAR(45) | null | the caller's address |

#### D31K. KEYS AND INDEXES
- Primary key `id`.
- Foreign key `user_id` references the account table (`ON DELETE SET NULL`).
- Indexes: `idx_audit_at` on `at`; `idx_audit_entity` on `(entity_type, entity_id, at)`; `idx_audit_user` on `(user_id, at)`.

#### D31U. USED BY
- APIs: [A1. Eligibility Answer](../apis/A1-eligibility-answer.md), [A2. Insurance Plan Answer](../apis/A2-insurance-plan-answer.md), [A3. Pre-auth Answer](../apis/A3-preauth-answer.md), [A4. Claim Answer](../apis/A4-claim-answer.md), [A5. Query Request](../apis/A5-query-request.md), [A6. Payment Notice](../apis/A6-payment-notice.md), [A7. Payment Enquiry Answer](../apis/A7-payment-enquiry-answer.md), [A8. Status Answer](../apis/A8-status-answer.md), [A9. Task Answer](../apis/A9-task-answer.md), [A10. Predetermination Quote](../apis/A10-predetermination-quote.md), [A13. Adjudicate](../apis/A13-adjudicate.md), [A14. Disburse](../apis/A14-disburse.md), [A16. ABHA Policy Link](../apis/A16-abha-policy-link.md), [A19. Sandbox Scenarios](../apis/A19-sandbox-scenarios.md)
- Callbacks: [C1. Callback Door](../callbacks/C1-callback-door.md), [C2. Coverage Eligibility Check](../callbacks/C2-coverage-eligibility-check.md), [C3. Insurance Plan Request](../callbacks/C3-insurance-plan-request.md), [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md), [C5. Claim Submit](../callbacks/C5-claim-submit.md), [C6. Predetermination](../callbacks/C6-predetermination.md), [C7. Task Submit](../callbacks/C7-task-submit.md), [C8. Status Enquiry](../callbacks/C8-status-enquiry.md), [C9. Communication](../callbacks/C9-communication.md), [C10. Payment Enquiry](../callbacks/C10-payment-enquiry.md), [C11. Payment Acknowledgement](../callbacks/C11-payment-acknowledgement.md)
- FHIR: [F2. CoverageEligibilityRequest](../fhir/F2-coverage-eligibility-request.md), [F3. CoverageEligibilityResponse](../fhir/F3-coverage-eligibility-response.md), [F4. Task (InsurancePlan request)](../fhir/F4-task-insuranceplan.md), [F13. PaymentNotice](../fhir/F13-paymentnotice.md)
- Database: [D2. staff](D2-staff.md), [D28. nhcx_delivery](D28-nhcx-delivery.md)
- Tests: [T3. Eligibility Validation and Discovery Answered](../tests/T3-eligibility-answered.md), [T4. Auth-requirements Ruling Answered](../tests/T4-auth-requirements-ruled.md), [T5. Insurance Plan Served](../tests/T5-insurance-plan-served.md)
