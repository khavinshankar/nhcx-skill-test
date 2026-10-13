# S15. Patient Detail Screen

> **Existing HMIS screen.** Most HMIS already have this screen. Do not rebuild it: add only what NHCX needs (the fields and actions marked for NHCX below, such as ABHA number and address, HPR id, registration and qualification) to the target's own screen, and record anything else as `found` in discovery.

#### S15R. ROUTE
patients/view/:id

Optional query parameter: `tab`, one of `overview`, `encounters`, `problems`, `lab`, `billing`. It picks the open tab. Anything else opens Overview.

Breadcrumb: Patients (patients/list, S13) > <patient name>

Page title: the patient's full name.

#### S15D. DESCRIPTION
The patient chart. A header banner identifies the patient, and five tabs hold the record: Overview, Encounters, Problems & allergies, Laboratory and Billing.

A patient id that does not exist shows "Patient could not be found." with a "Back to dashboard" button.

Header banner:
- Avatar, then the full name (a link back to this screen).
- A row of chips: MRN (info), gender in title case, age ("47 y" or "age unknown"), blood group (danger colour, only when recorded), and "ABHA <number>" (success colour, only when recorded).
- The mobile number with a phone icon.
- On the right: "Edit" (pencil icon), "New OPD visit" (primary, stethoscope icon), "Admit" (secondary, bed icon).

Tab 1, Overview:
- A card of label and value pairs in three columns: MRN (chip), ABHA number, ABHA address, Gender, Date of birth, Age, Mobile, Email, Marital status, Blood group, Address (address line, city, district, state and PIN joined by commas, blanks skipped), Emergency contact (name, relationship and phone joined by commas).
- Below it, the Vitals card:
  - Snapshot of the latest set: "Last recorded <when> · <encounter number>", or "· recorded on the chart" when that set is not tied to a visit. Then one tile per vital that has a reading: short name, value, unit, and a flag chip when the value is outside the reference range (High in danger, Low in warning, Normal in success). With no vitals: "No vitals recorded yet."
  - Accordion item "Record a new set of vitals". Open by default only when no vitals exist. Holds one number input (step 0.1) per vital, labelled "<name> (<unit>)" with help text "LOINC <code>" and the reference range as placeholder. The vitals are Body temperature (Cel), Heart rate (/min), Respiratory rate (/min), Systolic blood pressure (mm[Hg]), Diastolic blood pressure (mm[Hg]), Oxygen saturation in Arterial blood by Pulse oximetry (%), Body weight (kg), Body height (cm), Body mass index (kg/m2). Then "Taken at" (date and time, defaults to now), "Attach to encounter" (dropdown of up to the 25 latest encounters as "<number> · <OPD/IPD> · <when>", blank option "Not linked to a visit", defaults to the newest open encounter; help text "Only vitals attached to an encounter enter that encounter's FHIR document."), "Note" (text), and the button "Record vitals" (primary, heart-pulse icon).
  - Accordion item "History - <n> recording(s)": a table with columns Taken at, Encounter (link to the visit, or "-"), then one column per vital. Missing readings show "-". Out of range values carry their flag chip. Empty state: "No vitals recorded yet."

Tab 2, Encounters:
- Card titled "<n> encounter(s)" with actions "New OPD visit" (primary, stethoscope icon) and "Admit" (bed icon).
- Columns: Number (link to the OPD visit or IPD admission), Type (chip: OPD in info, IPD in warning), When, Doctor, Department, Status (colour chip).
- Newest first. Empty state: "No encounters recorded, start an OPD visit or admit the patient."

Tab 3, Problems & allergies:
- Problem list card titled "Problem list - <n> entr(y/ies)".
  - Columns: Problem, ICD-10, SNOMED CT, Type (chip "diagnosis" or "history"), Status, Source (link to the encounter it came from, or "-"), Recorded (date), and a "Remove" button.
  - Shows diagnoses recorded on visits and chart-level medical history. Chart-level entries come first. "Remove" appears only on chart-level history entries, and asks "Remove "<problem>" from the problem list?" before it fires.
  - Empty state: "No problems recorded. Chart-level problems flow into the Medical history section of every document."
  - Accordion item "Add a problem" (open by default only when the list is empty): "Problem (SNOMED CT + ICD-10)" dropdown (options "<display> (<code>)", blank option "Free text only"), "Description" (text), "Clinical status" dropdown (Active, Recurrence, Remission, Resolved, Inactive; default Active), "Onset" (date), "Attach to encounter" (blank option "Chart-level (appears in every document)"), "Note" (text), and the button "Add to problem list" (primary, plus icon).
- Allergies card titled "Allergies - <n> recorded".
  - When any allergy is high risk, a red banner first: "High risk allergy: <names>".
  - Columns: Allergen, SNOMED CT (code, or "text only"), Category, Criticality (chip: "high risk" danger, "low risk" success, "unassessed" warning, or "-"), Reaction, Status, Recorded (date), and a "Remove" button that asks "Remove the recorded allergy to <allergen>?".
  - High risk allergies sort first.
  - Empty state: "No allergies recorded. Entries here populate the Allergies section of the OP consult and discharge summary documents."
  - Accordion item "Add an allergy" (open by default only when the list is empty): "Allergen (SNOMED CT)" dropdown (blank option "Free text only"; help text "AllergyIntolerance.code is mandatory and SNOMED-coded in the NRCES profile."), "Description" (text), "Category" (Medication, Food, Environment, Biologic; blank option "From the allergen"), "Criticality" (Low risk, High risk, Unable to assess; blank option "Not assessed"), "Reaction (SNOMED CT)" (blank option "None"), "Reaction detail" (text), "Noted during encounter" (blank option "Chart-level (appears in every document)"), and the button "Add allergy" (primary, alert icon).

Tab 4, Laboratory:
- Card titled "<n> lab order(s)" with action "Order investigation" (primary, flask icon).
- Columns: Order (link to the lab order), Panel, Ordered, Status. Empty state: "No lab orders for this patient."

Tab 5, Billing:
- Card titled "<n> invoice(s) · ₹ <sum of invoice totals>" with action "Raise invoice" (primary, rupee receipt icon).
- Columns: Invoice (link to the invoice), Type, Date, Amount ("₹ 0.00", right aligned), Status. Empty state: "No invoices raised."

Messages after the POST actions (the screen reloads on the relevant tab):

| Action | Endpoint | Returns to tab | Success | Failure |
|---|---|---|---|---|
| Record vitals | `POST patients/:id/vitals` | Overview | "Recorded <n> vital sign(s)." | "Enter at least one reading." when every reading is blank |
| Add problem | `POST patients/:id/problems` | Problems & allergies | "Problem added." | "a problem needs either a coded diagnosis or a description" |
| Remove problem | `POST patients/:id/problems/:problemid/delete` | Problems & allergies | "Problem removed." | Only chart-level entries can be removed |
| Add allergy | `POST patients/:id/allergies` | Problems & allergies | "Allergy recorded." | "an allergy needs either a coded allergen or a description" |
| Remove allergy | `POST patients/:id/allergies/:allergyid/delete` | Problems & allergies | "Allergy removed." | |

Behaviour worth keeping:
- Blank vital inputs are skipped. Values outside the reference range are flagged High or Low. BMI is derived from weight and height when not entered.
- A new problem is saved as medical history. A coded pick fills the SNOMED and ICD-10 codes and its display wins over the typed description.
- A new allergy takes the typed description, or the allergen's display if none was typed. Category falls back to the allergen's own category. Status is saved as active.

Claims: two actions in the header, beside "Admit": **"Search insurance policy"** opens the policy search [S1. Search Policy](S1-search-policy.md) prefilled with the patient's ABHA number (else the mobile number; the desk may switch to Member ID) and carries the patient through [S2. Select Policy](S2-select-policy.md), so the case opens linked to this patient (the case-opening API already takes `patient`); **"Claims"** opens the claim list [S5. Claim Master](S5-claim-master.md) filtered to this patient's cases. The admission is still linked on the Claim Creation Form S4, and the claim screens (S4, S6) link back here by the patient's name.

NHCX use: the header's ABHA chip is the quickest check that the patient can be matched to a policy. The IPD admissions in the Encounters tab are what a claim links to. The diagnoses recorded on that admission and its consultant become the pre-authorisation's diagnoses and treating doctor, so a diagnosis added to the admission (it shows here with that admission as Source) is what the payer sees.

API: [A4. Pre-auth Submit](../apis/A4-preauth-submit.md), [A5. Claim Submit](../apis/A5-claim-submit.md) (diagnoses, treating doctor)

Data: [D3. patient](../database/D3-patient.md)

Data: [D4. encounter](../database/D4-encounter.md)

Data: [D5. condition](../database/D5-condition.md)

Data: [D6. observation](../database/D6-observation.md)

Data: [D7. allergy](../database/D7-allergy.md)

Data: [D8. terminology](../database/D8-terminology.md)

#### S15L. LAYOUT
The arrangement below is the reference implementation's [REF](../references/PAYERS.md#markers): follow the target HMIS's own screen conventions. What is required is in DESCRIPTION and ACTIONS: the fields, options, columns, statuses, messages and actions.


```
|------------------------------------------------------------------|
| Patients > Asha Devi                                             |
|------------------------------------------------------------------|
| [Card]                                                           |
| (AD) Asha Devi                     [Edit] [New OPD visit] [Admit]|
|      [MRN0012] [Female] [47 y] [B+] [ABHA 91-7034-...]           |
|      (phone) 98765xxxxx                                          |
|------------------------------------------------------------------|
| [Overview] [Encounters] [Problems & allergies] [Laboratory]      |
| [Billing]                                                        |
|------------------------------------------------------------------|
| [Card]                                                           |
|  MRN          ABHA number      ABHA address                      |
|  Gender       Date of birth    Age                               |
|  Mobile       Email            Marital status                    |
|  Blood group  Address          Emergency contact                 |
|------------------------------------------------------------------|
| [Card] Vitals                                                    |
|  Last recorded 12 Sep 10:30 · IPD-0004                           |
|  BODY TEMPERATURE  HEART RATE     RESPIRATORY RATE  SYSTOLIC ... |
|  37.9 Cel [High]   88 /min        18 /min           ...          |
|  > Record a new set of vitals                                    |
|  > History - 3 recording(s)                                      |
|------------------------------------------------------------------|
```

- The header banner is a card above the tabs. Its buttons wrap below the name on narrow screens.
- Tabs sit below the header. Each tab's content is one or two cards.
- The overview grid collapses to fewer columns on narrow screens. Vital tiles run two per row on small screens and four on large.
- Add and record forms live inside accordions under their tables, with the submit button right aligned.
- Remove buttons are extra small, danger style, and confirm in a browser dialog.

#### S15A. ACTIONS
1. Edit: go to the Patient Registration Form S14 in edit mode for this patient.
2. New OPD visit (header or Encounters tab): open the new OPD visit form with this patient preselected.
3. Admit (header or Encounters tab): open the new IPD admission form with this patient preselected. That admission is what S4 links a claim to.
4. Switch tab: show the chosen tab. The open tab can also be set with `?tab=`.
5. Record vitals: post the readings, then reload S15 on the Overview tab with the result message.
6. Add to problem list: post the problem, then reload S15 on the Problems & allergies tab.
7. Remove (problem): confirm, delete the chart-level entry, then reload on the Problems & allergies tab.
8. Add allergy: post the allergy, then reload on the Problems & allergies tab.
9. Remove (allergy): confirm, delete, then reload on the Problems & allergies tab.
10. Encounter number or Source link: open that OPD visit or IPD admission.
11. Order investigation: open the new lab order form for this patient. Order number links open the lab order.
12. Raise invoice: open the new invoice form for this patient. Invoice number links open the invoice.
13. Breadcrumb "Patients": go to the Patient List S13.
