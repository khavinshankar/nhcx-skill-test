# D5. condition

#### D5T. TABLE
One row is one chief complaint, diagnosis or medical-history problem of a patient; primary key `id`; parent tables [D3. patient](D3-patient.md) and [D4. encounter](D4-encounter.md) (optional).

#### D5D. DESCRIPTION
The claim reads this table for its diagnoses. When a pre-authorisation draft is saved, the linked admission's rows with `category = 'diagnosis'` and `clinical_status != 'resolved'` (ordered by `id`) replace whatever the form sent. Each is resolved against the `diagnosis` kind of [D8. terminology](D8-terminology.md) by `snomed_code`. If it is found there, the terminology's ICD-10 alt coding is quoted. If it is not found but `icd10_code` is set, the row's own ICD-10 and SNOMED codes are quoted as recorded. The result is written to [D25. claim_diagnosis](D25-claim-diagnosis.md). An admission with no such rows leaves the form's own diagnoses in use.

Lifecycle:
- `chief-complaint` and `diagnosis` rows are written by the OPD and IPD clinical record forms. Each save deletes that encounter's rows of that category and inserts the submitted rows again (replace, not update). A complaint is written with `clinical_status = 'active'`. A diagnosis takes the status chosen on the form (`active`, `recurrence`, `remission`, `resolved`), default `active`. Both get `verification_status = 'confirmed'` and `recorded_at` = now. A coded diagnosis copies SNOMED from the terminology row's `code` / `display` and ICD-10 from its `alt_code` / `alt_display`.
- `medical-history` rows are added from the patient chart (S15 "Add a problem"), attached to an encounter or chart-level (`encounter_id` null), with `clinical_status` one of `active`, `recurrence`, `remission`, `resolved`, `inactive`. A problem needs a coded diagnosis or a description.
- Deleted from the chart only when chart-level: `DELETE ... WHERE id = ? AND patient_id = ? AND encounter_id IS NULL`. Encounter rows go only by the replace-on-save above or by the "clear transactional data" reset.

#### D5C. COLUMNS
| column | type | null/default | meaning (and allowed values) |
|---|---|---|---|
| id | INTEGER | primary key | row id |
| patient_id | INTEGER | NOT NULL | the patient ([D3](D3-patient.md)) |
| encounter_id | INTEGER | null | the visit or admission ([D4](D4-encounter.md)); null for a chart-level problem |
| category | TEXT | NOT NULL | `chief-complaint`, `diagnosis`, `medical-history` |
| clinical_status | TEXT | NOT NULL, default `'active'` | `active`, `recurrence`, `remission`, `resolved`, `inactive` (the last only from the chart) |
| verification_status | TEXT | NOT NULL, default `'confirmed'` | always `confirmed` as written |
| snomed_code | TEXT | null | Condition.code SNOMED CT coding |
| snomed_display | TEXT | null | its display |
| icd10_code | TEXT | null | Condition.code ICD-10 coding; the code the payer reads |
| icd10_display | TEXT | null | its display |
| text | TEXT | NOT NULL | the label shown: coded display, or the typed text |
| onset | TEXT | null | onset date or text |
| severity_code | TEXT | null | severity; no screen writes it |
| severity_display | TEXT | null | its display |
| note | TEXT | null | clinical note (for a diagnosis, the typed text) |
| recorded_at | TEXT | NOT NULL | ISO timestamp written |

#### D5K. KEYS AND INDEXES
- Primary key `id` (integer).
- `patient_id` references [D3. patient](D3-patient.md) `id`.
- `encounter_id` references [D4. encounter](D4-encounter.md) `id`.
- No unique constraints.
- Index: `ix_condition_enc (encounter_id, category)`.

#### D5U. USED BY
- Screens: [S4. Claim Creation Form](../screens/S4-claim-creation-form.md), [S15. Patient Detail](../screens/S15-patient-detail.md)
- Database: [D3. patient](D3-patient.md), [D4. encounter](D4-encounter.md), [D25. claim_diagnosis](D25-claim-diagnosis.md)
