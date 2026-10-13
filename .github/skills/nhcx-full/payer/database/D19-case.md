# D19. case

#### D19T. TABLE
One row is one claim dossier (case) around one enrolment, from the pre-authorisation that opened it to its settlement; primary key `id`, with `claim_no` as the number everyone quotes. Parent tables [D6. subscription](D6-subscription.md), [D5. member](D5-member.md) and, for a dependant, [D7. subscription_family_member](D7-subscription-family-member.md). The reference implementation names it `payer_cases` [REF](../references/PAYERS.md#markers).

#### D19D. DESCRIPTION
The case row. It holds who the patient is (snapshotted rather than joined: under a family floater the patient is often a dependant, and a claim must keep saying who it was for after the family list is edited), where they were treated, the admission, the running totals over the bill ([D25. case_line_item](D25-case-line-item.md)) and the payments ([D30. payment](D30-payment.md)), the decision, and the routing slips of every thread the case has with the exchange. Its children hold the diagnoses ([D20. case_diagnosis](D20-case-diagnosis.md)), procedures ([D21. case_procedure](D21-case-procedure.md)), doctors ([D22. case_doctor](D22-case-doctor.md)), documents ([D23. case_document](D23-case-document.md)), lines ([D25. case_line_item](D25-case-line-item.md)), timeline ([D26. case_timeline](D26-case-timeline.md)) and messages ([D27. case_exchange_message](D27-case-exchange-message.md)).

**Numbering.** `id` is `CASE-<serial>` from the `case` counter, four digits [REF](../references/PAYERS.md#markers); it is a database key. `claim_no` is `CL/<yy>/<mmdd><serial>`, the month-and-day in three base32 characters and the serial in six over the sortable `0-9A-V` alphabet (`CL/26/0SE0000V9` is the 1001st claim, dated 10 September), from the `claim` counter ([D32. id_sequence](D32-id-sequence.md)) and dated from the admission [REF](../references/PAYERS.md#markers). It is the number every screen shows and the `preAuthRef` every ClaimResponse ([F9. ClaimResponse](../fhir/F9-claimresponse.md)) carries. The hospital's own number (`Claim.identifier` typed `CLN`) is kept apart as `nhcx_claim_ref`.

**Created:**
- By [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md) from a pre-authorisation Claim ([F8. Claim](../fhir/F8-claim.md)): the enrolment found by the handles the Claim carries (in force first, else the most recent cover, so a lapsed policy is filed and refused with the reason rather than dead-lettered), the member's own name, gender and age on the admission date, the hospital, the admission, diagnoses, team, lines and documents as sent, and the routing slip (`nhcx_correlation_id`, `nhcx_sender_code`, `nhcx_recipient_code`, `nhcx_claim_ref`). `stage` `preauth`, `adjudication_status` `pending`. A Claim naming no enrolment is refused permanently ("No enrolment matches the patient on this pre-authorisation").
- By [C5. Claim Submit](../callbacks/C5-claim-submit.md) from a Claim with no pre-authorisation on file: `stage` `claim`, with the discharge date the Claim carries (required for a direct claim) and the claim leg's slip (`nhcx_claim_correlation_id`, `nhcx_claim_submission_ref`).
- By hand from the desk ([S3. Case Desk](../screens/S3-case-desk.md), `POST cases`) with no routing slip, which is what "nothing is waiting for an answer" means [SANDBOX](../references/PAYERS.md#markers).
- A redelivery finds its case by `nhcx_correlation_id` (unique) or `nhcx_claim_correlation_id` (unique) and opens no second one; two deliveries racing lose to the unique index ("That claim already exists").

**Stage and decision.** `stage`: `preauth`, `claim`, `payment`, `settled`, `rejected`, `cancelled`. `adjudication_status`: `pending`, `approved`, `rejected`, `queried`, `cancelled`. A case is open for decision while `stage` is `preauth` or `claim`; once money is in flight the numbers are fixed. A decision is a verdict and a time together, or neither (`ck_cases_adjudicated`).

| From | Write | Stage after | Status after |
|---|---|---|---|
| [A13. Adjudicate](../apis/A13-adjudicate.md) approve at `preauth` | pending lines approved in full, totals recomputed | `claim` | `approved` |
| [A13. Adjudicate](../apis/A13-adjudicate.md) approve at `claim` | as above, then the wallet ([D6. subscription](D6-subscription.md), [D8. wallet_entry](D8-wallet-entry.md)) debited by `total_approved`; refused when short ("Insufficient wallet balance"), when a line is still `queried`, or when every line is rejected | `payment` | `approved` |
| [A13. Adjudicate](../apis/A13-adjudicate.md) reject | | `rejected` | `rejected` |
| [A13. Adjudicate](../apis/A13-adjudicate.md) query | the case stays where it is; [A5. Query Request](../apis/A5-query-request.md) goes out | unchanged | `queried` |
| [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md) enhancement (lines added) | new lines pending, `enhancement_count` up one, the pre-auth slip reopened (`nhcx_correlation_id` replaced, `nhcx_answer_txn_id` cleared, `claim` back to `preauth` when no claim is filed) | `preauth` | `pending` |
| [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md) resubmission or [C9. Communication](../callbacks/C9-communication.md) reply on a `queried` case | queried lines back to pending, documents filed, `nhcx_query_correlation_id` cleared | unchanged | `pending` |
| [C5. Claim Submit](../callbacks/C5-claim-submit.md) claim on a pre-authorised case | the bill replaced by the final one, discharge recorded when the case had none, the claim slip written | `claim` | `pending` |
| [C7. Task Submit](../callbacks/C7-task-submit.md) cancel, or the desk's cancel | | `cancelled` | `cancelled` |
| [C7. Task Submit](../callbacks/C7-task-submit.md) reprocess or release on a decided, unpaid claim (or the desk's reprocess) | every line back to pending, the wallet credited when the case was at `payment`, `reprocess_count` up one, `nhcx_claim_answer_txn_id` cleared, the reprocess slip written | `claim` | `pending` |
| [A14. Disburse](../apis/A14-disburse.md) a payment completes | `total_paid` up by the amount; `settled` when nothing approved is left | `settled` when paid in full | unchanged |

A reprocess of a paid case is refused (that is a recovery, not a reprocess); of an open case, refused ("only a decided case can be reprocessed").

**The routing slips** (the exchange origin; all null on a case entered by hand):

| Columns | Written by | Read by |
|---|---|---|
| `nhcx_correlation_id`, `nhcx_sender_code`, `nhcx_recipient_code`, `nhcx_claim_ref` | [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md) on filing; `nhcx_correlation_id` and `nhcx_claim_ref` replaced by an enhancement or resubmission | [A3. Pre-auth Answer](../apis/A3-preauth-answer.md): the verdict goes back on `nhcx_correlation_id` to `nhcx_sender_code`; `nhcx_recipient_code` decides which payer code the case belongs to and which accounts see it |
| `nhcx_answer_txn_id` | [A3. Pre-auth Answer](../apis/A3-preauth-answer.md) when the pre-auth verdict goes out; cleared by an enhancement | [A3. Pre-auth Answer](../apis/A3-preauth-answer.md): set means the thread is answered and a second verdict is not sent |
| `nhcx_claim_correlation_id`, `nhcx_claim_submission_ref` | [C5. Claim Submit](../callbacks/C5-claim-submit.md) on filing | [A4. Claim Answer](../apis/A4-claim-answer.md): the claim verdict's thread and the number it names |
| `nhcx_claim_answer_txn_id` | [A4. Claim Answer](../apis/A4-claim-answer.md) or the reprocess answer; cleared by a reprocess | [A4. Claim Answer](../apis/A4-claim-answer.md): set means answered |
| `nhcx_query_correlation_id`, `nhcx_query_txn_id` | [A5. Query Request](../apis/A5-query-request.md) when the CommunicationRequest goes out (the gateway mints the id); cleared when the reply is filed | [C9. Communication](../callbacks/C9-communication.md): the hospital's Communication is matched on it first |
| `nhcx_reprocess_correlation_id`, `nhcx_reprocess_claim_ref` (migration 0002) | [C7. Task Submit](../callbacks/C7-task-submit.md) when a reprocess or release Task is taken in | [A9. Task Answer](../apis/A9-task-answer.md): the decision of a reopened claim goes back on this thread as a completed Task, because the claim's own thread was completed by the verdict being disputed and the exchange refuses a second answer on it; both cleared when it goes |

`scenario` pins a sandbox preset on the case, overriding what the member id implies ([A19. Sandbox Scenarios](../apis/A19-sandbox-scenarios.md)) [SANDBOX](../references/PAYERS.md#markers).

**Totals.** `total_claimed` and `total_approved` are recomputed from [D25. case_line_item](D25-case-line-item.md) inside every transaction that changes a line; `total_paid` inside the one that completes a payment. The checks hold `total_approved <= total_claimed` and `total_paid <= total_approved`.

**Deleted:** never by the application. The sandbox's clear-data removes a sign-up account's cases with their children by cascade [SANDBOX](../references/PAYERS.md#markers).

#### D19C. COLUMNS
| column | type | null/default | meaning (and allowed values) |
|---|---|---|---|
| id | VARCHAR(24) | primary key | `CASE-<serial>` [REF](../references/PAYERS.md#markers); the `:id` of the case desk |
| claim_no | VARCHAR(32) | NOT NULL, UNIQUE | `CL/<yy>/<mmdd><serial>` [REF](../references/PAYERS.md#markers); `preAuthRef` on every verdict |
| stage | VARCHAR(32) | NOT NULL, default `'preauth'` | `preauth`, `claim`, `payment`, `settled`, `rejected`, `cancelled` |
| subscription_id | VARCHAR(24) | NOT NULL | the enrolment ([D6. subscription](D6-subscription.md)) |
| member_id | CITEXT | NOT NULL | the member ([D5. member](D5-member.md)) |
| family_member_id | VARCHAR(24) | null | the dependant ([D7. subscription_family_member](D7-subscription-family-member.md)) when the patient is not the policyholder |
| patient_name | VARCHAR(160) | NOT NULL | the member's name, not the hospital's spelling |
| patient_age | INTEGER | NOT NULL | age on the admission date |
| patient_gender | VARCHAR(32) | NOT NULL | `Male`, `Female`, `Other` |
| is_minor | BOOLEAN | NOT NULL, default false | a minor is admitted with a named guardian |
| attendee_name | VARCHAR(160) | null | the guardian; required when `is_minor`, forbidden otherwise |
| attendee_relation | VARCHAR(40) | null | required with the guardian |
| attendee_mobile | VARCHAR(24) | null | |
| attendee_govt_id | VARCHAR(64) | null | |
| hospital_name | VARCHAR(200) | NOT NULL | from the provider Organization ([F17. Organization](../fhir/F17-organization.md)) |
| hospital_hfr_id | VARCHAR(64) | NOT NULL | the facility's HFR id |
| hospital_city | VARCHAR(80) | NOT NULL | |
| ward_type | VARCHAR(80) | NOT NULL | the ward or room class |
| admitted_on | DATE | NOT NULL | admission date; today when the Claim carried none |
| expected_discharge | DATE | null | as the pre-authorisation stated it |
| discharge_date | DATE | null | recorded by the claim or the desk; not before `admitted_on` |
| discharge_type | VARCHAR(32) | null | `Normal Discharge`, `LAMA`, `Transfer`, `Deceased`, `Pending Discharge` |
| urgency | VARCHAR(32) | NOT NULL, default `'Elective'` | `Emergency`, `Urgent`, `Elective` |
| enhancement_count | INTEGER | NOT NULL, default 0 | rounds the hospital came back for more |
| reprocess_count | INTEGER | NOT NULL, default 0 | times a decided claim was reopened |
| nhcx_correlation_id | VARCHAR(128) | null, UNIQUE | the pre-auth thread |
| nhcx_sender_code | CITEXT, at most 64 | null | the hospital's participant code |
| nhcx_recipient_code | CITEXT, at most 64 | null | this payer's code the case was addressed to |
| nhcx_claim_ref | CITEXT, at most 128 | null | the hospital's own claim number on the pre-authorisation |
| nhcx_answer_txn_id | VARCHAR(128) | null | the ledger id ([G9. Ledger](../gateway/G9-ledger.md)) the pre-auth verdict went out as |
| nhcx_claim_correlation_id | VARCHAR(128) | null, UNIQUE | the claim thread |
| nhcx_claim_submission_ref | CITEXT, at most 128 | null | the hospital's number on the claim |
| nhcx_claim_answer_txn_id | VARCHAR(128) | null | the ledger id the claim verdict went out as |
| nhcx_query_correlation_id | VARCHAR(128) | null | the open query's thread |
| nhcx_query_txn_id | VARCHAR(128) | null | the ledger id the query went out as |
| nhcx_reprocess_correlation_id | VARCHAR(128) | null | the open reprocess Task's thread (migration 0002) |
| nhcx_reprocess_claim_ref | VARCHAR(64) | null | the claim number the reprocess asked about (migration 0002) |
| scenario | VARCHAR(40) | null | a pinned sandbox preset, upper case [SANDBOX](../references/PAYERS.md#markers) |
| total_claimed | NUMERIC(14,2) | NOT NULL, default 0 | sum of [D25. case_line_item](D25-case-line-item.md) `claimed_amount` |
| total_approved | NUMERIC(14,2) | NOT NULL, default 0 | sum of [D25. case_line_item](D25-case-line-item.md) `approved_amount` |
| total_paid | NUMERIC(14,2) | NOT NULL, default 0 | sum of completed [D30. payment](D30-payment.md) amounts |
| adjudication_status | VARCHAR(32) | NOT NULL, default `'pending'` | `pending`, `approved`, `rejected`, `queried`, `cancelled` |
| adjudication_remarks | VARCHAR(2000) | NOT NULL, default `''` | the decision's remarks; `ClaimResponse.disposition` |
| adjudicated_by | VARCHAR(36) | null | the deciding account ([D2. staff](D2-staff.md)) |
| adjudicated_at | TIMESTAMPTZ | null | null exactly when `pending` |
| created_at | TIMESTAMPTZ | NOT NULL, default now | |
| updated_at | TIMESTAMPTZ | NOT NULL, default now | bumped by trigger |

#### D19K. KEYS AND INDEXES
- Primary key `id`. Unique `uq_cases_claim_no` on `claim_no`.
- Foreign keys: `subscription_id` references [D6. subscription](D6-subscription.md), `member_id` references [D5. member](D5-member.md), `family_member_id` references [D7. subscription_family_member](D7-subscription-family-member.md), all `ON DELETE RESTRICT`; `adjudicated_by` references the account table (`ON DELETE SET NULL`).
- Checks: `ck_cases_stage`; `ck_cases_patient_gender`; `ck_cases_discharge_type`; `ck_cases_urgency`; `ck_cases_adjudication_status`; `ck_cases_attendee` (a minor has a guardian name and relation, a non-minor has no guardian name); `ck_cases_discharge_order` (`discharge_date >= admitted_on`); `ck_cases_totals` (all non-negative, `total_approved <= total_claimed`, `total_paid <= total_approved`); `ck_cases_adjudicated` (`pending` with no time, else a time); `ck_cases_nhcx_codes_len`.
- Unique indexes `uq_cases_nhcx_correlation` on `nhcx_correlation_id` and `uq_cases_nhcx_claim_correlation` on `nhcx_claim_correlation_id`: one case per submission.
- Indexes: `idx_cases_stage` on `(stage, created_at)`; `idx_cases_subscription`; `idx_cases_member`; `idx_cases_hospital` on `hospital_name`; `idx_cases_adjudication` on `(adjudication_status, stage)`; `idx_cases_nhcx_query_correlation`; `idx_cases_nhcx_claim_ref`; `idx_cases_nhcx_claim_submission_ref`; `idx_cases_recipient` on `nhcx_recipient_code`.
- Referenced (`case_id`, `ON DELETE CASCADE`) by [D20. case_diagnosis](D20-case-diagnosis.md), [D21. case_procedure](D21-case-procedure.md), [D22. case_doctor](D22-case-doctor.md), [D23. case_document](D23-case-document.md), [D25. case_line_item](D25-case-line-item.md), [D26. case_timeline](D26-case-timeline.md), [D27. case_exchange_message](D27-case-exchange-message.md); by [D30. payment](D30-payment.md) `case_id` with `ON DELETE RESTRICT`.

#### D19U. USED BY
- Screens: [S1. Overview](../screens/S1-overview.md), [S2. Cases](../screens/S2-cases.md), [S3. Case Desk](../screens/S3-case-desk.md), [S10. Payments](../screens/S10-payments.md)
- APIs: [A3. Pre-auth Answer](../apis/A3-preauth-answer.md), [A4. Claim Answer](../apis/A4-claim-answer.md), [A5. Query Request](../apis/A5-query-request.md), [A6. Payment Notice](../apis/A6-payment-notice.md), [A7. Payment Enquiry Answer](../apis/A7-payment-enquiry-answer.md), [A8. Status Answer](../apis/A8-status-answer.md), [A9. Task Answer](../apis/A9-task-answer.md), [A10. Predetermination Quote](../apis/A10-predetermination-quote.md), [A11. Transaction Related](../apis/A11-txn-related.md), [A13. Adjudicate](../apis/A13-adjudicate.md), [A14. Disburse](../apis/A14-disburse.md), [A15. Case Exchange Log](../apis/A15-case-exchange.md), [A17. Participant Lookup](../apis/A17-participant-lookup.md), [A19. Sandbox Scenarios](../apis/A19-sandbox-scenarios.md)
- Callbacks: [C1. Callback Door](../callbacks/C1-callback-door.md), [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md), [C5. Claim Submit](../callbacks/C5-claim-submit.md), [C7. Task Submit](../callbacks/C7-task-submit.md), [C8. Status Enquiry](../callbacks/C8-status-enquiry.md), [C9. Communication](../callbacks/C9-communication.md), [C11. Payment Acknowledgement](../callbacks/C11-payment-acknowledgement.md)
- FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F2. CoverageEligibilityRequest](../fhir/F2-coverage-eligibility-request.md), [F7. QuestionnaireResponse](../fhir/F7-questionnaireresponse.md), [F8. Claim](../fhir/F8-claim.md), [F9. ClaimResponse](../fhir/F9-claimresponse.md), [F10. Task (claim actions and answers)](../fhir/F10-task-claim-actions.md), [F11. CommunicationRequest](../fhir/F11-communicationrequest.md), [F12. Communication](../fhir/F12-communication.md), [F13. PaymentNotice](../fhir/F13-paymentnotice.md), [F14. PaymentReconciliation](../fhir/F14-paymentreconciliation.md), [F15. Patient](../fhir/F15-patient.md), [F17. Organization](../fhir/F17-organization.md), [F18. Coverage](../fhir/F18-coverage.md)
- Database: [D2. staff](D2-staff.md), [D5. member](D5-member.md), [D6. subscription](D6-subscription.md), [D7. subscription_family_member](D7-subscription-family-member.md), [D20. case_diagnosis](D20-case-diagnosis.md), [D21. case_procedure](D21-case-procedure.md), [D22. case_doctor](D22-case-doctor.md), [D23. case_document](D23-case-document.md), [D25. case_line_item](D25-case-line-item.md), [D26. case_timeline](D26-case-timeline.md), [D27. case_exchange_message](D27-case-exchange-message.md), [D28. nhcx_delivery](D28-nhcx-delivery.md), [D30. payment](D30-payment.md), [D32. id_sequence](D32-id-sequence.md)
- Tests: [T6. Pre-auth Received and Approved](../tests/T6-preauth-approved.md), [T8. Pre-auth Queried and Answered](../tests/T8-preauth-queried.md), [T9. Enhancement Received and Approved](../tests/T9-enhancement-approved.md), [T10. Pre-auth Cancelled](../tests/T10-preauth-cancelled.md), [T12. Claim Received and Approved](../tests/T12-claim-approved.md), [T13. LAMA and Death Claims](../tests/T13-claim-lama-death.md), [T14. Reprocess and Balance Release](../tests/T14-reprocess-and-release.md), [T18. Redelivery and Duplicates](../tests/T18-redelivery-ignored.md)
