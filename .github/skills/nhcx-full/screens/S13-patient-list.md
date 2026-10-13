# S13. Patient List Screen

> **Existing HMIS screen.** Most HMIS already have this screen. Do not rebuild it: add only what NHCX needs (the fields and actions marked for NHCX below, such as ABHA number and address, HPR id, registration and qualification) to the target's own screen, and record anything else as `found` in discovery.

#### S13R. ROUTE
patients/list

Optional query parameter: `q` (the search term). Example: `patients/list?q=9876`.

Page title: Patient directory. It is the landing screen of the Patients menu.

#### S13D. DESCRIPTION
The hospital's patient directory. The front desk uses it to find a registered patient, open the chart, or start a visit or admission. It is also where a patient is found before an admission is created, and an admission is what a claim is later linked to (S4).

Search:
- One free text box. The term is trimmed and matched as a "contains" match against five fields: full name, MRN, mobile number, ABHA number and ABHA address.
- With no term, the list shows the most recently registered patients.
- Results are ordered newest registration first and capped at 100 rows.
- The search is a GET with the term in the query string, so a result can be bookmarked and a refresh repeats the search.

Table columns, in this order:

| Column | Content |
|---|---|
| Patient | Full name, as a link to the Patient Detail screen S15 |
| MRN | The medical record number, shown as an info chip |
| Age / sex | Gender in title case, a dot, then the age, for example "Female · 47 y". Age comes from the date of birth when present, else from the recorded age in years, else "age unknown" |
| Phone | Mobile number |
| ABHA | ABHA number, or "-" when none is recorded |
| City | City, followed by ", State" when a state is recorded |
| (no header) | Two small buttons: "OPD" and "Admit" |

Card title: "<n> patient(s)", where n is the number of rows shown.

Empty state (no rows): "No patient matches that search."

NHCX use: a "Register with ABHA" button beside the register button runs the ABHA service first ([A19. ABHA Create and Verify (ABDM M1)](../apis/A19-abha-m1.md): verify an existing ABHA by its number or mobile OTP, or create one from an Aadhaar OTP) and opens the registration form S14 filled from the profile; a person already on the register under that ABHA is opened instead. Each row also offers "Link ABHA" (none on file) or "Verify ABHA" (one on file), which writes the verified ABHA number and address onto the row; **"Search insurance policy"**, which opens the policy search [S1. Search Policy](S1-search-policy.md) prefilled with the patient's ABHA number (else the mobile number; the desk may switch to Member ID) and carries the patient through [S2. Select Policy](S2-select-policy.md), so the case that opens is linked to the patient from the start; and **"Claims"**, which opens the claim list [S5. Claim Master](S5-claim-master.md) filtered to the patient's cases. Opening a case for a patient needs no admission yet: the admission is linked later on S4.

The ABHA column matters for claims. When a payer confirms a policy, the claim is linked to a current inpatient stay of a patient whose ABHA number matches the policy's ABHA, compared on digits only (S4). A patient registered without an ABHA number cannot be matched, so the operator can scan this column to see whether the ABHA was captured at registration.

Data: [D3. patient](../database/D3-patient.md)

#### S13L. LAYOUT
The arrangement below is the reference implementation's [REF](../references/PAYERS.md#markers): follow the target HMIS's own screen conventions. What is required is in DESCRIPTION and ACTIONS: the fields, options, columns, statuses, messages and actions.


```
|------------------------------------------------------------------|
| Patient directory                                                |
|------------------------------------------------------------------|
| [Card] 12 patient(s)                                             |
|   [__________________] [Search] [Clear]  [(user+) Register       |
|                                            patient]              |
|------------------------------------------------------------------|
| Patient     | MRN      | Age / sex      | Phone      | ABHA      |
|             |          |                |            |           |
|             | City              |                                |
|------------------------------------------------------------------|
| Asha Devi   | [MRN0012]| Female · 47 y  | 98765xxxxx | 91-70..   |
|             | Shimla, Himachal Pradesh | [OPD] [Admit]           |
| Ravi Kumar  | [MRN0011]| Male · age     | 99887xxxxx | -         |
|             |          |   unknown      |            |           |
|------------------------------------------------------------------|
```

- One card. Its header carries the row count on the left and, in the card actions area, the search form followed by the "Register patient" button.
- The search input is at least 16rem wide. The search form wraps on narrow screens.
- "Search" is the primary style. "Clear" is the secondary style. "Register patient" is the primary style with a user-plus icon.
- The table scrolls horizontally on narrow screens. The last column's "OPD" and "Admit" buttons are extra small.
- When there are no rows, the table is replaced by the empty state line in muted text.

#### S13A. ACTIONS
1. Search: submit the term and reload S13 with the matching patients.
2. Clear: reload S13 with no term, showing the most recent patients.
3. Register patient: go to the Patient Registration Form S14 in create mode.
4. Patient name link: go to the Patient Detail screen S15 for that patient.
5. OPD: open the new OPD visit form with this patient preselected.
6. Admit: open the new IPD admission form with this patient preselected. An admission created here is what the Claim Creation Form S4 later links a claim to.
