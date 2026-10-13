# S16. Practitioner Master Screen

> **Existing HMIS screen.** Most HMIS already have this screen. Do not rebuild it: add only what NHCX needs (the fields and actions marked for NHCX below, such as ABHA number and address, HPR id, registration and qualification) to the target's own screen, and record anything else as `found` in discovery.

#### S16R. ROUTE
practitioners/list

Optional query parameter: `edit` (a practitioner id). It loads that practitioner into the form. Example: `practitioners/list?edit=7`.

Breadcrumb: Masters > Doctors & staff

Page title: Doctors & staff.

#### S16D. DESCRIPTION
The master list of the hospital's doctors. Every practitioner that can be picked on a visit, an admission, an invoice or a claim's care team is set up here. Practitioners are never deleted, because their names sit on encounters, prescriptions and reports. They are retired instead, and a retired practitioner drops out of every picker.

List:
- Ordered active first, then by department, then by name. Retired practitioners stay in the list.
- Card title: "<n> practitioner(s)".

| Column | Content |
|---|---|
| Name | Practitioner name |
| Department | Department, or "-" |
| Qualification | Qualification as typed, or "-" |
| Identifier | Identifier type code and number, for example "HPID 71-1234-5678-9012" |
| Specialty | Specialty display, or "-" |
| Fee | Consultation fee as "₹ 500" (no decimals, right aligned) |
| Status | Chip "active" (success) or "retired" (plain) |
| (no header) | "Edit" button, then "Retire" (active rows) or "Reinstate" (retired rows) |

Empty state: "No practitioners configured."

Add and edit form (three columns), under a card titled "Add a practitioner", or "Edit practitioner" when `edit` names a practitioner:

| Label | Control | Name | Rules and options |
|---|---|---|---|
| Name | Text | `name` | Required |
| Department | Dropdown, blank option "Not stated" | `department` | General Medicine, Cardiology, Pediatrics, Orthopedics, Obstetrics & Gynaecology, Dermatology, Emergency, Gastroenterology, Nephrology, General Surgery. |
| Gender | Dropdown, blank option "Not stated" | `gender` | Female, Male, Other |
| Qualification | Text | `qualification_display` | Optional, free text, for example "MBBS, MD (General Medicine)" |
| Identifier type | Dropdown, no blank | `identifier_type_code` | Healthcare Professional ID (HPID) (`HPID`, default), Medical council registration (`MD`), Other identifier (`OIN`). Help text: "Written into Practitioner.identifier.type." |
| Identifier number | Text | `identifier_value` | Required |
| Specialty (SNOMED CT) | Dropdown, blank option "Not stated" | `specialty_code` | The SNOMED service type list, shown as "<display> (<code>)" |
| Consultation fee (₹) | Number, step 1, min 0 | `consultation_fee` | Defaults to 0 |
| Phone | Text | `phone` | Optional |
| Email | Email input | `email` | Optional |

Saving an edit also reinstates a retired practitioner.

FHIR: [F16. Practitioner and PractitionerRole](../fhir/F16-practitioner.md)

Validation (red message at the top of S16, nothing saved):
- Name blank: "a practitioner needs a name"
- Identifier number blank: "a practitioner needs a registration or HPID number"

On success: "Practitioner saved." Retire or Reinstate: "Practitioner updated."

How practitioners are chosen elsewhere:
- Every doctor picker (OPD visit, IPD admission consultant, appointment, billing doctor, and the claim care team) lists only active practitioners, sorted by name, each shown as "<name> - <department>".
- Pre-authorisation care team (on the Claim Creation Form S4): when the linked admission names a consultant, the form shows that doctor as "<name> - treating doctor" with the hint "The consultant on the admission; change it there." and a link to the admission. When the admission names no consultant, it shows the hint "The admission names no consultant yet, set one on the admission, or add the doctor here." and a repeating row of "Doctor" (dropdown, blank option "Select doctor") and "Role" (Admitting physician, Treating doctor, Surgeon, Anaesthetist, Nursing lead; default Treating doctor), with an "Add doctor" button.
- Care team validation messages: "Choose a valid care team role.", "Set the consultant on the admission (or add a doctor here) - the payer needs a treating doctor." at save, and "Add at least one doctor to the care team." at submission. A retired practitioner in the team is skipped.

API: [A4. Pre-auth Submit](../apis/A4-preauth-submit.md), [A5. Claim Submit](../apis/A5-claim-submit.md) (care team)

Data: [D2. practitioner](../database/D2-practitioner.md)

Data: [D8. terminology](../database/D8-terminology.md)

Data: [D26. claim_care_team](../database/D26-claim-care-team.md)

#### S16L. LAYOUT
The arrangement below is the reference implementation's [REF](../references/PAYERS.md#markers): follow the target HMIS's own screen conventions. What is required is in DESCRIPTION and ACTIONS: the fields, options, columns, statuses, messages and actions.


```
|------------------------------------------------------------------|
| Masters > Doctors & staff                                        |
|------------------------------------------------------------------|
| [Card] 8 practitioner(s)                                         |
| Name     | Department | Qualification | Identifier    | Specialty|
|          | Fee   | Status    |                                   |
|------------------------------------------------------------------|
| Dr Mehta | Cardiology | MBBS, MD      | HPID 71-12..  | Cardio.. |
|          | ₹ 800 | [active]  | [Edit] [Retire]                   |
| Dr Rao   | Nephrology | MBBS          | MD KMC-4455   | -        |
|          | ₹ 500 | [retired] | [Edit] [Reinstate]                |
|------------------------------------------------------------------|
| [Card] Add a practitioner                                        |
|  > Practitioner details                                          |
|    Name *            Department         Gender                   |
|    [__________]      [Not stated   v]   [Not stated   v]         |
|    Qualification     Identifier type    Identifier number *      |
|    [__________]      [HPID          v]  [__________]             |
|    Specialty         Consultation fee   Phone                    |
|    [Not stated  v]   [0_____]           [__________]             |
|    Email                                                         |
|    [__________]                                                  |
|                                   [Cancel] [(user+) Add         |
|                                             practitioner]        |
|------------------------------------------------------------------|
```

- Two cards: the list, then the form card below it.
- The form sits inside one accordion item, "Practitioner details". It starts collapsed when adding and open when editing.
- The submit button is primary with a user-plus icon, labelled "Add practitioner" when adding and "Save practitioner" when editing. "Cancel" (secondary) appears only when editing.
- The form grid collapses to one column on narrow screens. The table scrolls horizontally.
- "Edit", "Retire" and "Reinstate" are extra small buttons. Retire and Reinstate post straight away with no confirmation.

#### S16A. ACTIONS
1. Edit: reload S16 with `?edit=<id>`, opening the form prefilled for that practitioner.
2. Add practitioner or Save practitioner: validate, save, and reload S16 with the result message.
3. Cancel (editing only): reload S16 with the form cleared.
4. Retire: mark the practitioner inactive and reload S16. They disappear from every doctor picker, including the claim care team on S4.
5. Reinstate: mark the practitioner active again and reload S16.
6. Breadcrumb "Masters": go to the masters index.
