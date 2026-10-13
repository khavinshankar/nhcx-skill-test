# D8. terminology

#### D8T. TABLE
One row is one concept in one code list (a picker), for example one ICD-10/SNOMED diagnosis, one department or one payer adapter mapping; primary key `id`; no parent table.

#### D8D. DESCRIPTION
Every picker in the application reads this table by `kind`, ordered by `sort_order, display`. A single concept is looked up by `kind` and `code`. Records that use a concept copy its code and display onto themselves, so later edits or deletes here never rewrite history.

Kinds the claim flow reads:
- `diagnosis`: SNOMED CT concept in `code` / `display`, with the ICD-10 code in `alt_code` / `alt_display`. The pre-auth quotes the ICD-10 (`alt_code`, else `code`).
- `claim_package`: local HBP package list used only when the payer's package master ([D10](D10-claim-plan.md)) is not `ready`; `extra` is the package rate in rupees [PAYER](../references/PAYERS.md#markers).
- `charge`: charge master for a non-package case; `extra` is `price|invoice type code`, and the price is the unit price of a [D27. claim_item](D27-claim-item.md).
- `payer_adapter`: maps a payer's NHCX participant code (`code`, for example `<payer code>`) to the adapter key in `extra` (`pmjay`, `kyrocare` or `generic`, see [PAYERS.md](../references/PAYERS.md)). The claim's `payer_id` is matched on its numeric part, so `<n>`, `<n>@hcx` and `<n>@HCX` reach the same row. A payer with no row falls back to `generic`.
- `department`, `service_type`: practitioner department and specialty ([D2](D2-practitioner.md)).
- `vital`: the vitals written to [D6](D6-observation.md), with `unit`, `ref_low`, `ref_high`.
- `allergen`, `reaction`: allergies ([D7](D7-allergy.md)); an allergen's `extra` is its default category.
- `complaint`, `encounter_type`, `priority`, `admission_type`, `discharge_disposition`, `marital_status`, `blood_group`: encounter and patient pickers.

The full set of kinds, by group: Clinical (`complaint`, `diagnosis`, `procedure`, `procedure_category`, `procedure_outcome`, `allergen`, `reaction`); Medication (`medicine`, `route`, `method`, `dose_instruction`); Diagnostics (`vital`, `lab_panel`, `lab_analyte`, `specimen`); Dialysis (`dialysis_modality`, `vascular_access`, `dialyser`, `anticoagulant`, `dialysis_complication`); Wellness (`wellness_vital`, `wellness_body`, `wellness_activity`, `wellness_assessment`, `wellness_women`, `wellness_lifestyle`, `lifestyle_smoking`, `lifestyle_alcohol`, `lifestyle_yesno`, `wellness_mental`, `wellness_wellbeing`); Administrative (`charge`, `claim_package`, `payer_adapter`, `department`, `ward`, `encounter_type`, `service_type`, `priority`, `admission_type`, `discharge_disposition`, `marital_status`, `blood_group`).

Lifecycle:
- Seeded at start-up with `INSERT OR IGNORE`, so reseeding never duplicates or overwrites a row.
- Added from the clinical codes master. `code` and `display` are required ("a concept needs both a code and a display name"), and a code already in the kind is refused ("<code> already exists in this set"). `system` defaults to a local code system URL ending in `/<kind>`. `sort_order` defaults to the kind's highest `sort_order` plus 1.
- Updated from the same master; `display` must not be blank ("a concept needs a display name").
- Deleted from the same master. Deleting only takes the concept out of the picker.
- A master table: it survives the "clear transactional data" reset.

#### D8C. COLUMNS
| column | type | null/default | meaning (and allowed values) |
|---|---|---|---|
| id | INTEGER | primary key | row id |
| kind | TEXT | NOT NULL | the code list, one of the kinds listed above |
| system | TEXT | NOT NULL | code system URL (SNOMED, LOINC, ICD-10, or a local system) |
| code | TEXT | NOT NULL | the code |
| display | TEXT | NOT NULL | the display name |
| alt_system | TEXT | null | optional secondary coding system, for example ICD-10 next to SNOMED for a diagnosis |
| alt_code | TEXT | null | secondary code (the ICD-10 code of a diagnosis) |
| alt_display | TEXT | null | secondary display |
| unit | TEXT | null | unit for measurable concepts (vitals, analytes) |
| ref_low | REAL | null | reference range low |
| ref_high | REAL | null | reference range high |
| extra | TEXT | null | kind-specific data: `claim_package` rate; `charge` `price|type`; `payer_adapter` adapter key; `ward` per-day tariff; `lab_panel` `category|analyte codes|price`; `medicine` presentation; `allergen` default category; `wellness_lifestyle` the kind holding its answers |
| sort_order | INTEGER | NOT NULL, default `100` | display order inside the kind |

#### D8K. KEYS AND INDEXES
- Primary key `id` (integer).
- No foreign keys in or out. Other tables copy `code` and `display`; nothing references `id`.
- Unique `ux_terminology` on `(kind, system, code)`. The master screen also refuses a duplicate `code` inside a `kind`, whatever the system.
- Index: `ix_terminology_kind (kind, sort_order)`.

#### D8U. USED BY
- Screens: [S4. Claim Creation Form](../screens/S4-claim-creation-form.md), [S15. Patient Detail](../screens/S15-patient-detail.md), [S16. Practitioner Master](../screens/S16-practitioner-master.md)
- Database: [D1. organization](D1-organization.md), [D2. practitioner](D2-practitioner.md), [D5. condition](D5-condition.md), [D6. observation](D6-observation.md), [D7. allergy](D7-allergy.md), [D25. claim_diagnosis](D25-claim-diagnosis.md), [D27. claim_item](D27-claim-item.md)
- Tests: [T1. Test Configuration](../tests/T1-test-configuration.md)
