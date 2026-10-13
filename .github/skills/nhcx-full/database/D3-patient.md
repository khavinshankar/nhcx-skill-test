# D3. patient

#### D3T. TABLE
One row is one registered patient; primary key `id`; parent table [D1. organization](D1-organization.md) (`managing_org_id`).

#### D3D. DESCRIPTION
The patient register. A claim is linked to a patient through the admission: the claim's ABHA number is compared digits-only with `abha_number` here, and the patient of the chosen current IPD stay is written to [D9. claim](D9-claim.md) `patient_id`.

Once linked, the claim-side bundles take the patient from this row, falling back to what the payer returned on the claim:
- eligibility check: `given_name` (else the claim's `beneficiary_name`), `family_name`, `gender`, `birth_date`, `mrn` (as `patientRefId`, else `NA`), `district`, `state`, `phone`.
- pre-auth and claim: `name`, `gender`, `birth_date`, `phone`.

`abha_number` and `abha_address` are written by hand on the form, or, better, by the ABHA service through [A19. ABHA Create and Verify (ABDM M1)](../apis/A19-abha-m1.md): a verified or newly created ABHA, with the name, gender, date of birth and mobile the service holds filling what the form left blank. The ABHA number is unique across patients, so a second registration under the same ABHA is refused ("Another patient is already registered with that ABHA number").

Lifecycle:
- Created from the registration form (S14). `name` and `phone` are mandatory ("Name and mobile number are mandatory."). On create the application allocates `mrn` from the `mrn` counter as `MRN` plus five digits (`MRN00001`) [REF](../references/PAYERS.md#markers), stamps `created_at` and `updated_at`, and sets `managing_org_id` to the facility row. `gender` falls back to `unknown`; `country` is always written as `India`.
- Updated from the same form: every form field is overwritten and `updated_at` is stamped. `mrn` and `managing_org_id` do not change.
- No screen deletes a patient or sets `deceased`. Rows are removed only by the "clear transactional data" reset, which deletes every patient row and the counters.

#### D3C. COLUMNS
| column | type | null/default | meaning (and allowed values) |
|---|---|---|---|
| id | INTEGER | primary key | row id |
| mrn | TEXT | NOT NULL, UNIQUE | medical record number, `MRN00001` style; Patient.identifier type MR |
| abha_number | TEXT | null | ABHA number as typed (with or without dashes); matched digits-only against the claim |
| abha_address | TEXT | null | ABHA address |
| name | TEXT | NOT NULL | full name; Patient.name.text |
| given_name | TEXT | null | given name |
| family_name | TEXT | null | family name |
| gender | TEXT | NOT NULL | `male`, `female`, `other`, `unknown` |
| birth_date | TEXT | null | `YYYY-MM-DD` |
| age_years | INTEGER | null | age, captured when the date of birth is unknown |
| phone | TEXT | NOT NULL | mobile number; Patient.telecom |
| email | TEXT | null | email |
| marital_status_code | TEXT | null | code from the `marital_status` terminology kind |
| marital_status_display | TEXT | null | its display |
| blood_group | TEXT | null | value from the `blood_group` terminology kind, for example `B+` |
| address_line | TEXT | null | street address |
| city | TEXT | null | city |
| district | TEXT | null | district; `districtCode` on the eligibility check |
| state | TEXT | null | state; `stateCode` on the eligibility check |
| postal_code | TEXT | null | PIN code |
| country | TEXT | NOT NULL, default `'India'` | country |
| contact_name | TEXT | null | emergency contact name |
| contact_relation | TEXT | null | emergency contact relationship |
| contact_phone | TEXT | null | emergency contact phone |
| managing_org_id | INTEGER | null | the facility row ([D1](D1-organization.md)) set at registration |
| deceased | INTEGER | NOT NULL, default `0` | `1` deceased, `0` not; no screen writes it |
| created_at | TEXT | NOT NULL | ISO timestamp of registration |
| updated_at | TEXT | NOT NULL | ISO timestamp of the last edit |

#### D3K. KEYS AND INDEXES
- Primary key `id` (integer).
- `managing_org_id` references [D1. organization](D1-organization.md) `id`.
- Referenced by [D4. encounter](D4-encounter.md), [D5. condition](D5-condition.md), [D6. observation](D6-observation.md), [D7. allergy](D7-allergy.md) (`patient_id`, NOT NULL) and [D9. claim](D9-claim.md) (`patient_id`, nullable), and by EMR tables outside this spec.
- Unique: `mrn`.
- Indexes: `ix_patient_name (name)`, `ix_patient_phone (phone)`.

#### D3U. USED BY
- Screens: [S4. Claim Creation Form](../screens/S4-claim-creation-form.md), [S13. Patient List](../screens/S13-patient-list.md), [S14. Patient Registration Form](../screens/S14-patient-registration-form.md), [S15. Patient Detail](../screens/S15-patient-detail.md), [S18. Beneficiary Verification](../screens/S18-beneficiary-verification.md)
- APIs: [A18. Biometric Authentication](../apis/A18-biometric-authentication.md), [A19. ABHA Create and Verify (ABDM M1)](../apis/A19-abha-m1.md)
- FHIR: [F15. Patient](../fhir/F15-patient.md)
- Database: [D1. organization](D1-organization.md), [D4. encounter](D4-encounter.md), [D5. condition](D5-condition.md), [D6. observation](D6-observation.md), [D7. allergy](D7-allergy.md), [D9. claim](D9-claim.md), [D30. counter](D30-counter.md), [D31. biometric_auth](D31-biometric-auth.md)
