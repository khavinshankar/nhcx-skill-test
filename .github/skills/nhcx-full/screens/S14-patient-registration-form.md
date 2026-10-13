# S14. Patient Registration Form Screen

> **Existing HMIS screen.** Most HMIS already have this screen. Do not rebuild it: add only what NHCX needs (the fields and actions marked for NHCX below, such as ABHA number and address, HPR id, registration and qualification) to the target's own screen, and record anything else as `found` in discovery.

#### S14R. ROUTE
patients/new (create mode)

patients/edit/:id (edit mode)

Breadcrumb in create mode: Patients (patients/list, S13) > Register

Breadcrumb in edit mode: Patients (S13) > <patient name> (patients/view/:id, S15) > Edit

Page title: "Register patient" in create mode, "Edit <patient name>" in edit mode.

#### S14D. DESCRIPTION
One form registers a new patient or edits an existing one. Both modes show the same fields. In edit mode every field is prefilled from the saved patient.

Fields are grouped into five collapsible sections. All sections can be open at once, and the first one (Identity) starts open.

Identity (two columns):

| Label | Control | Name | Rules |
|---|---|---|---|
| Full name | Text | `name` | Required (marked, and required in the browser) |
| Gender | Dropdown, blank option "Select" | `gender` | Required. Options: Male (`male`), Female (`female`), Other (`other`), Unknown (`unknown`). Saved as `unknown` if nothing arrives |
| Date of birth | Date picker | `birth_date` | Optional. Help text: "Leave blank and fill age if the DOB is unknown." |
| Age (years) | Number, min 0, max 130 | `age_years` | Optional. Used only when there is no date of birth |
| Given name | Text | `given_name` | Optional |
| Family name | Text | `family_name` | Optional |

Contact & ABHA (two columns):

| Label | Control | Name | Rules |
|---|---|---|---|
| Mobile number | Text | `phone` | Required (marked, and required in the browser) |
| Email | Email input | `email` | Optional |
| ABHA number | Text | `abha_number` | Optional. Help text: "Exported as Patient.identifier with type ABHA." |
| ABHA address | Text | `abha_address` | Optional |
| Verify or create an ABHA | Button (secondary) | | Opens the ABHA dialog ([A19. ABHA Create and Verify (ABDM M1)](../apis/A19-abha-m1.md)): verify an existing ABHA by its number or the mobile it is registered against (OTP, with an account chooser when one mobile holds several), or create one from an Aadhaar OTP with the person's consent recorded and an address chosen. On success the ABHA number and address are filled in, and name, gender, date of birth and mobile where the form still has them blank; a typed value is kept. The dialog's description reads: "Verify the person's ABHA with an OTP, or create one from their Aadhaar. What the ABHA service confirms is written onto the file." Opened from S13 "Register with ABHA", the whole form is filled from the profile and its description reads "Filled from ABHA <number>. Confirm the details; a UHID is issued on save." |

Demographics (two columns):

| Label | Control | Name | Options |
|---|---|---|---|
| Marital status | Dropdown, blank option "Not recorded" | `marital_status_code` | Married (`M`), Never Married (`S`), Widowed (`W`), Divorced (`D`), unmarried (`U`). |
| Blood group | Dropdown, blank option "Not recorded" | `blood_group` | A+, A-, B+, B-, AB+, AB-, O+, O- |

Address:

| Label | Control | Name |
|---|---|---|
| Address line | Text, full width | `address_line` |
| City / town | Text | `city` |
| District | Text | `district` |
| State | Text | `state` |
| PIN code | Text | `postal_code` |

Country is not shown. It is always saved as "India".

Emergency contact (three columns):

| Label | Control | Name |
|---|---|---|
| Contact name | Text | `contact_name` |
| Relationship | Text (free text) | `contact_relation` |
| Contact phone | Text | `contact_phone` |

Rules:
- Create: if Full name or Mobile number is empty, the form reloads with the red message "Name and mobile number are mandatory." and nothing is saved.
- Create: on success the system allocates the next MRN, then opens S15 with the green message "Patient registered with MRN <mrn>."
- Edit: the values are saved and S15 opens with "Patient record updated." The MRN never changes.
- Edit of a patient id that does not exist shows "Patient could not be found." with a "Back to dashboard" button.
- There is no format check on mobile number, ABHA number or PIN code.

NHCX use:
- ABHA number is the key that joins a claim to a hospital patient. A confirmed policy is matched to a current inpatient stay whose patient has the same ABHA number, digits only, so "91-7034-1237-4240" and "91703412374240" match (S4). Without it the claim cannot be linked.

API: [A4. Pre-auth Submit](../apis/A4-preauth-submit.md), [A5. Claim Submit](../apis/A5-claim-submit.md)

Data: [D3. patient](../database/D3-patient.md)

#### S14L. LAYOUT
The arrangement below is the reference implementation's [REF](../references/PAYERS.md#markers): follow the target HMIS's own screen conventions. What is required is in DESCRIPTION and ACTIONS: the fields, options, columns, statuses, messages and actions.


```
|------------------------------------------------------------------|
| Patients > Register                                              |
|------------------------------------------------------------------|
| [Card]                                                           |
|  v Identity                                                      |
|    Full name *            Gender *                               |
|    [______________]       [Select          v]                    |
|    Date of birth          Age (years)                            |
|    [dd-mm-yyyy]           [___]                                  |
|    Leave blank and fill age if the DOB is unknown.               |
|    Given name             Family name                            |
|    [______________]       [______________]                       |
|  > Contact & ABHA                                                |
|  > Demographics                                                  |
|  > Address                                                       |
|  > Emergency contact                                             |
|------------------------------------------------------------------|
|  [Cancel]                                  [Register patient]    |
|------------------------------------------------------------------|
```

- One card with no title. The body is an accordion of the five sections in the order above.
- Required fields carry a required marker next to the label.
- The card footer holds "Cancel" (secondary, left) and the submit button (primary, medium, right). The submit label is "Register patient" in create mode and "Save changes" in edit mode.
- Section grids collapse to one column on narrow screens.

#### S14A. ACTIONS
1. Register patient (create mode): validate, create the patient, and go to the Patient Detail screen S15 with the success message.
2. Save changes (edit mode): save and go to S15 for that patient.
3. Cancel: go to the Patient List S13 without saving (in both modes).
4. Breadcrumb "Patients": go to S13. In edit mode, the patient name crumb goes to S15.
5. Expand or collapse a section: show or hide its fields. Values in a collapsed section are still submitted.
6. Verify or create an ABHA: run the ABHA dialog (A19) and fill the form from its profile; the form is not saved until Register patient or Save changes.
7. Under PMJAY, the beneficiary is verified biometrically before registration where the scheme asks for it; the verification lives on the case's Verification tab ([S18. Beneficiary Verification](S18-beneficiary-verification.md), [A18. Biometric Authentication](../apis/A18-biometric-authentication.md), stage Preauth) and is recorded against the patient and read by the sends.
