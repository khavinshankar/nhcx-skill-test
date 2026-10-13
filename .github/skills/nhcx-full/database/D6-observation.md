# D6. observation

#### D6T. TABLE
One row is one measured or coded finding (a vital sign reading, a lab analyte, a wellness or dialysis reading); primary key `id`; parent tables [D3. patient](D3-patient.md) and [D4. encounter](D4-encounter.md) (optional), plus EMR tables outside this spec (`lab_order`, `dialysis_session`, `wellness_record`).

#### D6D. DESCRIPTION
In the screens this spec covers, the table holds vitals. It is not sent in any NHCX bundle; the claim flow does not read it.

Lifecycle:
- Vitals are recorded from the patient chart (S15 "Record vitals") and from the OPD and IPD clinical record forms. One row is written per vital with a numeric value; blanks and non-numbers are skipped, and only codes in the `vital` kind of [D8. terminology](D8-terminology.md) are accepted. When weight and height are both given, BMI (`39156-5`) is derived and stored as a row too. Each row gets `category = 'vital-signs'`, `status = 'final'`, the LOINC code and display from the terminology row, SNOMED from its alt coding, `value_unit`, `ref_low` / `ref_high` from the terminology row, `interpretation`, `effective_ts` (the "Taken at" time, else now) and `sort_order` (the reading's position in the set).
- `interpretation` is `L` below `ref_low`, `H` above `ref_high`, `N` in range, null when there is no range.
- From the chart, `encounter_id` is the chosen encounter or null ("Not linked to a visit"); only rows with an encounter enter that encounter's FHIR document.
- The OPD and IPD clinical record save deletes that encounter's `vital-signs` rows and writes the set again.
- Lab orders write one row per analyte with `category = 'laboratory'`, `status = 'registered'`, then `preliminary` or `final` when results are saved.
- Wellness records and the dialysis flowsheet write their own rows (wellness section names as `category`; dialysis `phase` `pre` or `post`) and replace them on save.
- The foreign keys to `lab_order`, `dialysis_session` and `wellness_record` cascade, so deleting one of those parents deletes its rows here.
- Rows are otherwise removed only by the "clear transactional data" reset.

#### D6C. COLUMNS
| column | type | null/default | meaning (and allowed values) |
|---|---|---|---|
| id | INTEGER | primary key | row id |
| patient_id | INTEGER | NOT NULL | the patient ([D3](D3-patient.md)) |
| encounter_id | INTEGER | null | the visit or admission ([D4](D4-encounter.md)); null for chart-only vitals |
| lab_order_id | INTEGER | null | lab order the analyte belongs to (EMR `lab_order`) |
| dialysis_session_id | INTEGER | null | dialysis session (EMR `dialysis_session`); added by migration on older databases |
| phase | TEXT | null | dialysis vitals only: `pre` or `post`; added by migration |
| wellness_record_id | INTEGER | null | wellness record (EMR `wellness_record`); added by migration |
| value_system | TEXT | null | coded value system (valueCodeableConcept); added by migration |
| value_code | TEXT | null | coded value code; added by migration |
| value_display | TEXT | null | coded value display; added by migration |
| code_text | TEXT | null | Observation.code.text for a concept with no LOINC or SNOMED code; added by migration |
| category | TEXT | NOT NULL | `vital-signs`, `laboratory`, or a wellness section (`body-measurement`, `physical-activity`, `general-assessment`, `women-health`, `lifestyle`, `other`) |
| status | TEXT | NOT NULL, default `'final'` | `final` for vitals; `registered`, `preliminary`, `final` for lab analytes |
| loinc_code | TEXT | null | Observation.code LOINC coding |
| loinc_display | TEXT | null | its display |
| snomed_code | TEXT | null | Observation.code SNOMED coding |
| snomed_display | TEXT | null | its display |
| value_quantity | REAL | null | numeric value |
| value_unit | TEXT | null | UCUM unit, for example `Cel`, `/min`, `mm[Hg]`, `%`, `kg`, `cm`, `kg/m2` |
| value_string | TEXT | null | text value |
| ref_low | REAL | null | reference range low |
| ref_high | REAL | null | reference range high |
| interpretation | TEXT | null | `N`, `H`, `L` (schema also lists `A`) |
| body_site_code | TEXT | null | body site code |
| body_site_display | TEXT | null | its display |
| note | TEXT | null | note entered with the set |
| effective_ts | TEXT | NOT NULL | ISO timestamp the reading was taken |
| sort_order | INTEGER | NOT NULL, default `100` | order inside a set |

#### D6K. KEYS AND INDEXES
- Primary key `id` (integer).
- `patient_id` references [D3. patient](D3-patient.md) `id`.
- `encounter_id` references [D4. encounter](D4-encounter.md) `id`.
- `lab_order_id`, `dialysis_session_id`, `wellness_record_id` reference EMR tables outside this spec, each `ON DELETE CASCADE`.
- No unique constraints.
- Indexes: `ix_obs_enc (encounter_id, category)`, `ix_obs_lab (lab_order_id)`.

#### D6U. USED BY
- Screens: [S15. Patient Detail](../screens/S15-patient-detail.md)
- Database: [D3. patient](D3-patient.md), [D4. encounter](D4-encounter.md), [D8. terminology](D8-terminology.md)
