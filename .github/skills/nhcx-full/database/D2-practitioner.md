# D2. practitioner

#### D2T. TABLE
One row is one doctor or staff member of the facility; primary key `id`; no parent table.

#### D2D. DESCRIPTION
The practitioner master. The claim flow reads it for the treating team: the consultant on the admission ([D4. encounter](D4-encounter.md) `practitioner_id`) becomes the treating doctor of the pre-authorisation, and each care-team member ([D26. claim_care_team](D26-claim-care-team.md)) is sent as a Practitioner with `identifier_value` as the HPR id, `qualification_display` as the degree, and `specialty_code` / `specialty_display` as the specialty.

Lifecycle:
- Created by seeding and from the practitioner master screen (S16). Save refuses a blank `name` ("a practitioner needs a name") or a blank `identifier_value` ("a practitioner needs a registration or HPID number").
- The screen always writes `prefix = 'Dr'`, `qualification_code = 'BS'`, `qualification_system` = HL7 v2-0203, `identifier_system = 'https://doctor.abdm.gov.in'`, `role_code = '158965000'`, `role_display = 'Medical practitioner'` and `active = 1` [REF](../references/PAYERS.md#markers). `specialty_*` comes from the `service_type` kind and `department` from the `department` kind of [D8. terminology](D8-terminology.md).
- Updated by the same form (saving an edit also sets `active = 1`).
- Retired or reinstated by toggling `active` (`1` active, `0` retired). Never deleted, because the name is on encounters, prescriptions and reports. It is a master table and survives the "clear transactional data" reset.
- Only `active = 1` rows are accepted onto a pre-auth care team.

#### D2C. COLUMNS
| column | type | null/default | meaning (and allowed values) |
|---|---|---|---|
| id | INTEGER | primary key | row id; also the Practitioner resource id in the bundle |
| name | TEXT | NOT NULL | full name; Practitioner.name.text |
| prefix | TEXT | null | name prefix; the screen writes `Dr` |
| gender | TEXT | null | `male`, `female`, `other`, `unknown` |
| identifier_type_system | TEXT | NOT NULL | NDHM identifier type code system when the type is `HPID`, else HL7 v2-0203 |
| identifier_type_code | TEXT | NOT NULL | `HPID`, `MD` (medical licence number) or `OIN` (other); defaults to `HPID` |
| identifier_type_display | TEXT | NOT NULL | "Healthcare Professional ID (HPID)", "Medical License number" or "Other identifier" |
| identifier_system | TEXT | NOT NULL | `https://doctor.abdm.gov.in` |
| identifier_value | TEXT | NOT NULL | HPR id or registration number; sent as the practitioner's HPR id |
| qualification_code | TEXT | null | `BS` from the screen |
| qualification_display | TEXT | null | degrees as written, for example "MBBS, MD (General Medicine)"; the bundle derives the v2-0360 degree coding from it |
| qualification_system | TEXT | null | HL7 v2-0203 |
| role_code | TEXT | null | PractitionerRole.code, SNOMED; `158965000` |
| role_display | TEXT | null | `Medical practitioner` |
| specialty_code | TEXT | null | PractitionerRole.specialty, SNOMED code from the `service_type` terminology kind |
| specialty_display | TEXT | null | display of the specialty |
| department | TEXT | null | department display from the `department` terminology kind |
| phone | TEXT | null | phone |
| email | TEXT | null | email |
| consultation_fee | REAL | NOT NULL, default `0` | OPD fee (billing only) |
| active | INTEGER | NOT NULL, default `1` | `1` active, `0` retired |

#### D2K. KEYS AND INDEXES
- Primary key `id` (integer).
- No foreign keys out.
- Referenced by [D4. encounter](D4-encounter.md) `practitioner_id` and [D26. claim_care_team](D26-claim-care-team.md) `practitioner_id`, and by EMR tables outside this spec (prescriptions, procedures, notes, labs, invoices, appointments).
- No unique constraints or indexes beyond the primary key.

#### D2U. USED BY
- Screens: [S4. Claim Creation Form](../screens/S4-claim-creation-form.md), [S16. Practitioner Master](../screens/S16-practitioner-master.md)
- FHIR: [F8. Claim](../fhir/F8-claim.md), [F16. Practitioner and PractitionerRole](../fhir/F16-practitioner.md)
- Database: [D4. encounter](D4-encounter.md), [D8. terminology](D8-terminology.md), [D9. claim](D9-claim.md), [D26. claim_care_team](D26-claim-care-team.md)
- Tests: [T1. Test Configuration](../tests/T1-test-configuration.md)
