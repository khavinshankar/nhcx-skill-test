# D7. allergy

#### D7T. TABLE
One row is one allergy or intolerance of a patient; primary key `id`; parent tables [D3. patient](D3-patient.md) and [D4. encounter](D4-encounter.md) (optional).

#### D7D. DESCRIPTION
Recorded on the patient chart (S15, Problems & allergies tab). It is not sent in any NHCX bundle; the claim flow does not read it.

Lifecycle:
- Created from the chart. AllergyIntolerance.code is required, so a row needs a coded allergen (the `allergen` kind of [D8. terminology](D8-terminology.md)) or a typed description; with neither the save fails with "an allergy needs either a coded allergen or a description". `text` is the typed description, else the allergen's display. `category` is the chosen category, else the allergen's default (the terminology row's `extra`). `reaction` is the typed reaction, else the display of the chosen `reaction` concept. `clinical_status` is always written as `active` and `recorded_at` as now.
- Never updated.
- Deleted from the chart ("Allergy removed."), matched on `id` and `patient_id`. Otherwise removed only by the "clear transactional data" reset.

#### D7C. COLUMNS
| column | type | null/default | meaning (and allowed values) |
|---|---|---|---|
| id | INTEGER | primary key | row id |
| patient_id | INTEGER | NOT NULL | the patient ([D3](D3-patient.md)) |
| encounter_id | INTEGER | null | the encounter it was recorded in ([D4](D4-encounter.md)), or null |
| snomed_code | TEXT | null | SNOMED code of the allergen |
| snomed_display | TEXT | null | its display |
| text | TEXT | NOT NULL | allergen label |
| category | TEXT | null | `food`, `medication`, `environment` |
| criticality | TEXT | null | `low`, `high`, `unable-to-assess` |
| clinical_status | TEXT | NOT NULL, default `'active'` | always `active` as written |
| reaction | TEXT | null | reaction manifestation text |
| recorded_at | TEXT | NOT NULL | ISO timestamp written |

#### D7K. KEYS AND INDEXES
- Primary key `id` (integer).
- `patient_id` references [D3. patient](D3-patient.md) `id`.
- `encounter_id` references [D4. encounter](D4-encounter.md) `id`.
- No unique constraints or indexes beyond the primary key.

#### D7U. USED BY
- Screens: [S15. Patient Detail](../screens/S15-patient-detail.md)
- Database: [D3. patient](D3-patient.md), [D4. encounter](D4-encounter.md), [D8. terminology](D8-terminology.md)
