# D4. encounter

#### D4T. TABLE
One row is one OPD visit or one IPD admission of a patient; primary key `id`; parent tables [D3. patient](D3-patient.md) and [D2. practitioner](D2-practitioner.md).

#### D4D. DESCRIPTION
`kind` separates the OPD visit from the IPD admission. A claim links to an IPD row: the admissions offered for linking are rows with `kind = 'IPD'` and `status <> 'finished'` whose patient's ABHA number matches the claim's, newest `period_start` first. Linking writes this row's id to [D9. claim](D9-claim.md) `encounter_id` and, when the claim has no admission date yet, the first ten characters of `period_start` to `claim.admission_date`. The pre-authorisation then quotes the admission: its `diagnosis` conditions ([D5](D5-condition.md)) become the claim's diagnoses and its `practitioner_id` becomes the treating doctor.

Lifecycle:
- Created by "Admit" (IPD) or "New OPD visit" / checking in an appointment (OPD). `encounter_no` is allocated from the `encounter_IPD` or `encounter_OPD` counter as `IPD-00001` or `OPD-00001` [REF](../references/PAYERS.md#markers). `class_code` defaults to `IMP` for IPD and `AMB` for OPD, and `class_display` is looked up (`AMB` ambulatory, `IMP` inpatient encounter, `EMER` emergency). `type_system` and `service_type_system` default to SNOMED. `created_at` is stamped. Every screen creates it with `status = 'in-progress'` and `period_start` = now.
- IPD admission then occupies a bed, which writes `bed_id`, `ward`, `bed` and `bed_rate`. If the bed cannot be taken the new row is deleted and the admission is refused ("Could not admit: ...").
- Bed transfer rewrites `bed_id`, `ward`, `bed`, `bed_rate`.
- IPD discharge sets `status = 'finished'`, `period_end` and `discharge_ts` to the discharge time, and `discharge_disposition_code` / `_display`, then releases the bed.
- OPD finish sets `status = 'finished'` and `period_end` = now.
- Status transitions written by code: `in-progress` -> `finished`.
- Not deleted by any screen except the failed-admission rollback above. The "clear transactional data" reset deletes all rows.

#### D4C. COLUMNS
| column | type | null/default | meaning (and allowed values) |
|---|---|---|---|
| id | INTEGER | primary key | row id |
| encounter_no | TEXT | NOT NULL, UNIQUE | `IPD-00001` or `OPD-00001` |
| patient_id | INTEGER | NOT NULL | the patient ([D3](D3-patient.md)) |
| kind | TEXT | NOT NULL | `OPD` or `IPD` |
| status | TEXT | NOT NULL | `in-progress` or `finished` as written; schema also lists `planned`, `arrived`, `cancelled` |
| class_code | TEXT | NOT NULL | v3-ActCode: `AMB`, `IMP`, `EMER` |
| class_display | TEXT | NOT NULL | `ambulatory`, `inpatient encounter`, `emergency` |
| type_code | TEXT | null | Encounter.type, SNOMED code from the `encounter_type` terminology kind |
| type_display | TEXT | null | its display |
| type_system | TEXT | null | SNOMED by default |
| service_type_code | TEXT | null | from the `service_type` kind |
| service_type_display | TEXT | null | its display |
| service_type_system | TEXT | null | SNOMED by default |
| priority_code | TEXT | null | from the `priority` kind |
| priority_display | TEXT | null | its display |
| priority_system | TEXT | null | its system |
| practitioner_id | INTEGER | null | consultant ([D2](D2-practitioner.md)); becomes the pre-auth treating doctor |
| department | TEXT | null | department display from the `department` kind |
| period_start | TEXT | NOT NULL | ISO timestamp of admission or visit start; default admission date of a linked claim |
| period_end | TEXT | null | ISO timestamp of discharge or visit end |
| reason_code | TEXT | null | SNOMED code from the `complaint` kind |
| reason_display | TEXT | null | its display |
| admission_type | TEXT | null | IPD only; display from the `admission_type` kind |
| bed_id | INTEGER | null | IPD only; current bed (EMR `bed` table) |
| ward | TEXT | null | IPD only; ward name, copied when the bed is taken |
| bed | TEXT | null | IPD only; bed code, copied when the bed is taken |
| bed_rate | REAL | NOT NULL, default `0` | IPD only; per-day tariff of the current bed |
| discharge_disposition_code | TEXT | null | IPD only; from the `discharge_disposition` kind |
| discharge_disposition_display | TEXT | null | its display |
| discharge_ts | TEXT | null | IPD only; ISO discharge timestamp |
| consultation_fee | REAL | NOT NULL, default `0` | consultation fee (billing only) |
| appointment_slot | TEXT | null | OPD only; appointment slot |
| created_at | TEXT | NOT NULL | ISO timestamp the row was written |

#### D4K. KEYS AND INDEXES
- Primary key `id` (integer).
- `patient_id` references [D3. patient](D3-patient.md) `id`.
- `practitioner_id` references [D2. practitioner](D2-practitioner.md) `id`.
- `bed_id` references the EMR `bed` table (outside this spec).
- Referenced by [D5. condition](D5-condition.md), [D6. observation](D6-observation.md), [D7. allergy](D7-allergy.md) and [D9. claim](D9-claim.md) (`encounter_id`), and by EMR tables outside this spec.
- Unique: `encounter_no`.
- Indexes: `ix_encounter_patient (patient_id, period_start DESC)`, `ix_encounter_kind (kind, status)`.

#### D4U. USED BY
- Screens: [S4. Claim Creation Form](../screens/S4-claim-creation-form.md), [S15. Patient Detail](../screens/S15-patient-detail.md)
- APIs: [A17. Claim State](../apis/A17-claim-state.md)
- Database: [D2. practitioner](D2-practitioner.md), [D3. patient](D3-patient.md), [D5. condition](D5-condition.md), [D6. observation](D6-observation.md), [D7. allergy](D7-allergy.md), [D9. claim](D9-claim.md), [D25. claim_diagnosis](D25-claim-diagnosis.md), [D26. claim_care_team](D26-claim-care-team.md), [D30. counter](D30-counter.md)
