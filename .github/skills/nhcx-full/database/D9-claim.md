# D9. claim

#### D9T. TABLE
One row is one claim episode (case) around one selected policy, from eligibility to payment; primary key `id`; parent tables [D3. patient](D3-patient.md) and [D4. encounter](D4-encounter.md), both optional until the admission is linked.

#### D9D. DESCRIPTION
The case row. It holds the policy the operator selected, the coverage eligibility exchange and the payer's verdict flattened from it, the link to the admitted patient, the pre-authorisation draft header, and the case's stage. The legs of the case live in child tables: package master [D10](D10-claim-plan.md), auth-requirements ruling [D13](D13-claim-auth.md), lines [D16](D16-claim-line.md), pre-auth [D18](D18-claim-preauth.md), claim [D20](D20-claim-submission.md), payments [D21](D21-claim-payment.md), queries [D23](D23-claim-query.md) and the others that point here.

Create:
- Written when the operator picks a policy from the search result (S2). The policy must carry a member ID ("That policy has no member ID; a claim cannot be raised without one."). The row starts with `status = 'draft'`, `created_at` = now and a fresh `external_id` (the public id every route uses). When the search was started from the patient master ([S13. Patient List](../screens/S13-patient-list.md), [S15. Patient Detail](../screens/S15-patient-detail.md)) the carried `patient_id` is written too; the admission is still linked later. It copies the search inputs (`search_id_type`, `search_id_value`), the policy fields, `patient_photo` and the raw policy as `policy_json`. `payer_name` is the payer's **registered name on the NHCX participant registry** ([G4. Registry and Certificates](../gateway/G4-registry.md) participant fetch, cached in the application and refreshed when the lookup is retried), looked up by `payer_id` when the case is opened; it is never the search row's `payerName`, a configuration row's `display`, the adapter's name or a configured default name. Configuration rows only choose the adapter ([PAYERS.md](../references/PAYERS.md)). When the registry lookup fails, `payer_name` stays null, the screens show the payer code, and the lookup is tried again the next time the case is opened.
- `claim_no` is allocated from the `claim` counter ([D30](D30-counter.md)) as `NM-<yy>-<mmdd><serial>`, month-and-day in 3 base32 characters and the serial in 6 (alphabet `0-9A-V`), so every number has the same length and sorts by date, then issue order [REF](../references/PAYERS.md#markers). Example: `NM-26-0SE000001`.

Eligibility check (A2):
- Sending sets `status = 'checking'`, `purpose`, `policy_code` (the one entered, else the stored one), `member_id`, `txn_id`, `correlation_id`, `checked_at` = now, `error_message` = null. A send that fails sets `status = 'error'` and `error_message`. The outbound `x-hcx-workflow_id` is `11` by default, or `claim_no` under the `eligibility_workflow_id` setting (A2).
- The verdict (C2 callback, or polling by `txn_id`) writes `inforce`, `outcome`, `disposition`, `auth_required`, `allowed_amount`, `used_amount` and, when the payer returns them, `beneficiary_name`, `patient_gender`, `patient_dob`, `patient_address`, `abha_number`, `patient_photo`, `plan_name`, `plan_period_start`, `plan_period_end`, `relationship`, plus the whole bundle as `response_json`. Values the payer leaves empty are not written. Then `status`: `error` when `outcome = 'error'`, else `eligible` when in force, else `not-eligible`.
- `status = 'error'` with `error_message` also results from a ProtocolResponse on the callback, a protocol error found in the ledger, a [G9. Ledger](../gateway/G9-ledger.md) dispatch status of `dispatch_failed`, `dead` or `failed`, or a G9 ledger that no longer knows the `txn_id` (not found).
- A redelivered verdict for a row that is no longer `checking` is ignored, unless the row's last send is on record as failed (`status = 'error'`). Then the row is revived to `checking`, `error_message` cleared, and the verdict applied.

Status values and transitions (`status`):
- `draft` -> `checking` (check sent) or `error` (send failed).
- `checking` -> `eligible`, `not-eligible` or `error`.
- `error` -> `checking` (payer answered a send reported failed, or the check is sent again).
- `eligible`, `not-eligible`, `error` -> `checking` when the check is sent again ("Check again").

Link the admission (S4):
- Allowed only when `status = 'eligible'` ("Link an admission only after the payer has confirmed the policy is eligible."). The admission must be a current IPD stay of a patient whose ABHA number matches `abha_number`, digits only. Writes `patient_id`, `encounter_id` and, if empty, `admission_date` from the stay's `period_start`.
- Unlink sets `patient_id` and `encounter_id` to null and keeps the draft fields.

Pre-authorisation draft (S4):
- Save requires a linked `encounter_id` ("Link the admitted patient before drafting a pre-authorisation."), an `admission_date`, an `expected_discharge_date` that is empty or not before it, and `case_type` `package` or `nonpackage`. It writes `admission_date`, `expected_discharge_date`, `case_type`, `package_code`, `package_name`, `preauth_total` and `preauth_saved_at` = now, and replaces [D25](D25-claim-diagnosis.md), [D26](D26-claim-care-team.md) and [D27](D27-claim-item.md) in the same transaction.
- `package` with a `ready` package master: `package_code` / `package_name` are the first Procedure line, and `preauth_total` is the lines' total. `package` without one: the package picked from the `claim_package` terminology, and `preauth_total` is its rate. `nonpackage`: package fields null, and `preauth_total` is the sum of the charge items.

Stage (`stage`, `sub_stage`):
- Derived from the legs and stored whenever a leg is written, the verdict lands, the draft is saved or the state endpoint (A17) runs. The stored pair lets the claim list (S5) show and filter it without reading the legs.
- `stage`: `payment` when any payment notice exists; else `claim` when the claim leg exists and is not `draft`; else `enhancement` (last pre-auth send was `enhancement` or `enhancement_resubmit`) or `preauth` when a pre-auth leg exists; else `preauth` with `sub_stage = 'draft'` when `preauth_saved_at` is set; else `eligibility`.
- `sub_stage`: `draft`, `checking`, `eligible`, `not-eligible`, `requested`, `resubmitted`, `answered`, `queried`, `approved`, `partial`, `rejected`, `cancelling`, `cancelled`, `refused`, `noticed`, `paid`. At `eligibility` it is `status`, with `error` read as `draft`. At `payment` it is `paid` when anything has been paid, else `noticed`. On a leg it is the leg's status: a leg still `submitting` reads by its send kind (`requested`, `resubmitted` or `answered`), a leg in `error` reads `refused`, and an open payer query ([D23](D23-claim-query.md) `kind = 'query'`, status `open` or `error`) on a leg in `requested`, `answered` or `resubmitted` reads `queried`.

Other writes:
- An accepted pre-auth cancellation gives the claim a fresh `claim_no` [REF](../references/PAYERS.md#markers). The withdrawn number stays on the pre-auth leg ([D18](D18-claim-preauth.md) `claim_ref`).
- Never deleted by any screen. The "clear transactional data" reset deletes all rows; `ON DELETE CASCADE` on the child tables removes their rows with it.

#### D9C. COLUMNS
| column | type | null/default | meaning (and allowed values) |
|---|---|---|---|
| id | INTEGER | primary key | row id |
| external_id | TEXT | NOT NULL, UNIQUE | a UUID minted when the case is opened; the `:caseid` of every claim route and API. Routes are never keyed on `claim_no`, which C7 replaces on an accepted cancellation. Not in the reference implementation's schema (it routed on `id`); add it, or route on `id` where the HMIS exposes integer ids [REF](../references/PAYERS.md#markers) |
| claim_no | TEXT | NOT NULL, UNIQUE | case number `<prefix>-<yy>-<mmdd><serial>` (prefix a setting, D30); `caseId`, and the plan request's `x-hcx-workflow_id` [REF](../references/PAYERS.md#markers). Replaced by a fresh number when a cancellation is accepted (C7), so never used in a route |
| created_at | TEXT | NOT NULL | ISO timestamp the case was opened |
| status | TEXT | NOT NULL, default `'draft'` | eligibility status: `draft`, `checking`, `eligible`, `not-eligible`, `error` |
| search_id_type | TEXT | null | how the beneficiary was searched: `MemberId`, `MobileNo`, `AbhaNumber` |
| search_id_value | TEXT | null | the value searched |
| member_id | TEXT | NOT NULL | beneficiary / member ID from the selected policy; `pmjayId` [PAYER](../references/PAYERS.md#markers) and `subscriberId` |
| policy_code | TEXT | null | policy / plan identifier, for example `PMJAY/HP/S/G` [PAYER](../references/PAYERS.md#markers); `policyNumber` |
| beneficiary_name | TEXT | null | name from the search, then from the payer's Patient |
| abha_number | TEXT | null | ABHA number from the search, then from the payer's Patient; used to find the admission |
| mobile_number | TEXT | null | mobile number from the search |
| processing_id | TEXT | null | the policy's processing participant code from the policy search (A1); the `x-hcx-recipient_code` of every exchange on the case, falling back to `payer_id` when the registry gave none. Not in the reference implementation's schema, which sent to `payer_id` [REF](../references/PAYERS.md#markers); add it |
| payer_id | TEXT | null | payer participant code, with or without the `@hcx` suffix (for example `<payer code>`); `x-hcx-recipient_code`, and picks the payer adapter (see [PAYERS.md](../references/PAYERS.md)) |
| payer_name | TEXT | null | the payer's registered name from the NHCX participant registry (G4), cached; null until the lookup succeeds, never a guessed or configured name |
| product_id | TEXT | null | insurance product id |
| product_name | TEXT | null | insurance product name |
| policy_json | TEXT | null | JSON: the raw policy row as the search returned it |
| purpose | TEXT | null | last eligibility purpose: `validation`, `benefits`, `discovery` |
| txn_id | TEXT | null | [G9. Ledger](../gateway/G9-ledger.md) id of the outbound check |
| correlation_id | TEXT | null | `x-hcx-correlation_id` tying the check to its on_check |
| checked_at | TEXT | null | ISO timestamp the check was sent |
| error_message | TEXT | null | why the check failed; null otherwise |
| inforce | INTEGER | null | `1` policy in force, `0` not |
| outcome | TEXT | null | CoverageEligibilityResponse.outcome: `complete`, `error`, `partial` |
| disposition | TEXT | null | CoverageEligibilityResponse.disposition |
| auth_required | INTEGER | null | `1` / `0` from the last item's `authorizationRequired` |
| allowed_amount | REAL | null | sum insured: the wallet's `allowedMoney` (what is left) plus `usedMoney` [PAYER](../references/PAYERS.md#markers) |
| used_amount | REAL | null | the wallet's `usedMoney` |
| plan_name | TEXT | null | Coverage.class[0].name |
| plan_period_start | TEXT | null | Coverage.period.start |
| plan_period_end | TEXT | null | Coverage.period.end |
| relationship | TEXT | null | subscriber relationship (`self`, `child` and so on), display else code |
| patient_gender | TEXT | null | gender from the payer's Patient |
| patient_dob | TEXT | null | birth date from the payer's Patient |
| patient_address | TEXT | null | address lines, district, state and postal code joined with ", " |
| patient_photo | TEXT | null | base64 data or URL of the photo, from the search or the payer |
| response_json | TEXT | null | JSON: the full on_check bundle, for audit |
| patient_id | INTEGER | null | linked patient ([D3](D3-patient.md)) |
| encounter_id | INTEGER | null | linked IPD admission ([D4](D4-encounter.md)) |
| admission_date | TEXT | null | `YYYY-MM-DD`; the check's `servicedDate` and the pre-auth period start |
| expected_discharge_date | TEXT | null | provisional discharge, `YYYY-MM-DD`; the pre-auth period end |
| case_type | TEXT | null | `package` or `nonpackage` |
| package_code | TEXT | null | package code when `case_type = 'package'` |
| package_name | TEXT | null | its name |
| preauth_total | REAL | null | package rate, lines' total, or sum of items |
| preauth_saved_at | TEXT | null | ISO timestamp the draft was last saved; set means the case has reached `preauth` / `draft` |
| stage | TEXT | null | `eligibility`, `preauth`, `enhancement`, `claim`, `payment`; migration only |
| sub_stage | TEXT | null | one of the sub-stages listed above; migration only |

#### D9K. KEYS AND INDEXES
- Primary key `id` (integer). Unique: `external_id` (the public id in routes and APIs).
- `patient_id` references [D3. patient](D3-patient.md) `id`, `ON DELETE SET NULL` (the case outlives a merged or removed patient record).
- `encounter_id` references [D4. encounter](D4-encounter.md) `id`, `ON DELETE SET NULL`.
- [D26. claim_care_team](D26-claim-care-team.md) `practitioner_id` references [D2. practitioner](D2-practitioner.md) `id`, `ON DELETE PROTECT`: a practitioner named on a sent care team cannot be deleted, only retired.
- Referenced (`claim_id`, `ON DELETE CASCADE`) by [D10](D10-claim-plan.md), [D13](D13-claim-auth.md), [D16](D16-claim-line.md), [D17](D17-claim-form-answer.md), [D18](D18-claim-preauth.md), [D19](D19-claim-predetermination.md), [D20](D20-claim-submission.md), [D21](D21-claim-payment.md), [D23](D23-claim-query.md), [D24](D24-claim-adjudication.md), [D25](D25-claim-diagnosis.md), [D26](D26-claim-care-team.md), [D27](D27-claim-item.md), [D28](D28-claim-document.md), [D29](D29-claim-enquiry.md). [D10](D10-claim-plan.md), [D13](D13-claim-auth.md), [D18](D18-claim-preauth.md) and [D20](D20-claim-submission.md) allow one row per claim.
- Unique: `claim_no`.
- Index: `ix_claim_status (status, id DESC)`.

#### D9U. USED BY
- Screens: [S2. Select Policy](../screens/S2-select-policy.md), [S3. Policy Discovery](../screens/S3-policy-discovery.md), [S4. Claim Creation Form](../screens/S4-claim-creation-form.md), [S5. Claim Master](../screens/S5-claim-master.md), [S6. Claim Detail](../screens/S6-claim-detail.md), [S9. Pre-authorisation](../screens/S9-preauthorisation.md), [S10. Communication](../screens/S10-communication.md), [S11. Claim Submission](../screens/S11-claim-submission.md), [S12. Payments](../screens/S12-payments.md), [S17. Beneficiary Discovery](../screens/S17-beneficiary-discovery.md)
- APIs: [A1. Policy Search](../apis/A1-policy-search.md), [A2. Coverage Eligibility Check](../apis/A2-coverage-eligibility-check.md), [A4. Pre-auth Submit](../apis/A4-preauth-submit.md), [A5. Claim Submit](../apis/A5-claim-submit.md), [A6. Task Submit (cancel, status, reprocess, release)](../apis/A6-task-submit.md), [A10. Transaction Related](../apis/A10-txn-related.md), [A11. Transaction Dispatch](../apis/A11-txn-dispatch.md), [A13. Transaction List](../apis/A13-txn-list.md), [A14. Adjudicator User Role](../apis/A14-adjudicator-user-role.md), [A15. Adjudicator Process Case](../apis/A15-adjudicator-process-case.md), [A17. Claim State](../apis/A17-claim-state.md), [A18. Biometric Authentication](../apis/A18-biometric-authentication.md)
- Callbacks: [C1. Callback Door](../callbacks/C1-callback-door.md), [C2. Coverage Eligibility Verdict](../callbacks/C2-coverage-eligibility-on-check.md), [C3. Authorisation Requirements Ruling](../callbacks/C3-auth-requirements-on-check.md), [C5. Pre-auth Reply](../callbacks/C5-preauth-on-submit.md), [C6. Claim Reply](../callbacks/C6-claim-on-submit.md), [C7. Cancel Reply](../callbacks/C7-cancel-on-submit.md), [C8. Enquiry Reply](../callbacks/C8-enquiry-on-submit.md), [C9. Payer Communication](../callbacks/C9-communication-request.md), [C10. Payment Notice](../callbacks/C10-paymentnotice-request.md)
- FHIR: [F2. CoverageEligibilityRequest](../fhir/F2-coverage-eligibility-request.md), [F3. CoverageEligibilityResponse](../fhir/F3-coverage-eligibility-response.md), [F4. Task (InsurancePlan discovery)](../fhir/F4-task-insuranceplan.md), [F8. Claim](../fhir/F8-claim.md), [F10. Task (claim actions)](../fhir/F10-task-claim-actions.md), [F11. CommunicationRequest](../fhir/F11-communicationrequest.md), [F12. Communication](../fhir/F12-communication.md), [F13. PaymentNotice](../fhir/F13-paymentnotice.md), [F14. Payment acknowledgement](../fhir/F14-payment-acknowledgement.md), [F15. Patient](../fhir/F15-patient.md), [F17. Organization](../fhir/F17-organization.md), [F18. Coverage](../fhir/F18-coverage.md), [F19. Other bundle resources](../fhir/F19-other-resources.md)
- Database: [D1. organization](D1-organization.md), [D3. patient](D3-patient.md), [D4. encounter](D4-encounter.md), [D10. claim_plan](D10-claim-plan.md), [D13. claim_auth](D13-claim-auth.md), [D16. claim_line](D16-claim-line.md), [D17. claim_form_answer](D17-claim-form-answer.md), [D18. claim_preauth](D18-claim-preauth.md), [D19. claim_predetermination](D19-claim-predetermination.md), [D20. claim_submission](D20-claim-submission.md), [D21. claim_payment](D21-claim-payment.md), [D23. claim_query](D23-claim-query.md), [D24. claim_adjudication](D24-claim-adjudication.md), [D25. claim_diagnosis](D25-claim-diagnosis.md), [D26. claim_care_team](D26-claim-care-team.md), [D27. claim_item](D27-claim-item.md), [D28. claim_document](D28-claim-document.md), [D29. claim_enquiry](D29-claim-enquiry.md), [D30. counter](D30-counter.md), [D31. biometric_auth](D31-biometric-auth.md)
