# S4. Members Screen

#### S4R. ROUTE
`/members`

| Endpoint | Purpose |
|---|---|
| `GET members?search=&limit=&offset=` | The directory |
| `POST members` | Register a member |
| `GET members/:id` | One member |
| `PATCH members/:id` | Edit a member |
| `DELETE members/:id` | Retire a member (soft delete) |

Breadcrumb: Members

#### S4D. DESCRIPTION
A screen most payer systems already have. What NHCX adds is one field and one rule: the member's **ABHA number**, held as fourteen bare digits, which is what a hospital's eligibility check and pre-authorisation carry to find the person ([C2. Coverage Eligibility Check](../callbacks/C2-coverage-eligibility-check.md), [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md), [F2. CoverageEligibilityRequest](../fhir/F2-coverage-eligibility-request.md)); and the member id, which is the `subscriberId` and `MemberId` a hospital quotes. The exchange finds a member by any handle it carries: member id, ABHA number, mobile, or the name; the store matches on all of them ([A1. Eligibility Answer](../apis/A1-eligibility-answer.md)).

**List**, one row per live member. Columns: Member ID (monospace, `MRAJ<yyyy><serial>` in the reference [REF](../references/PAYERS.md#markers)), Full Name (with an avatar initial), Age / Gender / DOB ("`<age>` Yrs (`<gender>`)" and the date underneath), Mobile Number, 14-Digit ABHA ID (the number with a shield icon, or "Not Linked" in italics), Actions (Edit, Delete). The count line reads "`<n>` members found".

**Search** matches name, id, mobile and ABHA number. Empty states: "No members match" with "Nothing matches "`<term>`". Try a name, ID, mobile or ABHA number." and a "Clear search" button; "No members registered" with "Register a policyholder to start building the member registry." and a "Register member" button.

**Register with ABHA**, a second button beside "Register New Member": runs the ABHA service first ([A20. ABHA Create and Verify (ABDM M1)](../apis/A20-abha-m1.md): verify an existing ABHA by its number or the mobile it is registered against, with an OTP and an account chooser when one mobile holds several; or create one from an Aadhaar OTP with the person's consent recorded and an address chosen) and opens the register dialog filled from the profile, sub-title "Filled from ABHA `<number>`. Confirm the details and register." A member already on the register under that ABHA is opened for editing instead, with "`<name>` is already registered as `<id>` with this ABHA".

**Register / edit dialog**, "Register New Policyholder Member" or "Edit Member Details", sub-title "Enter member demographic details and optional 14-digit ABHA Health ID, or verify or create the ABHA with the ABHA service":

| Field | Control | Rule |
|---|---|---|
| Full Legal Name | text, required | "Enter the member's name" |
| Gender | select: Male, Female, Other | "Choose a gender" |
| Date of Birth | date | "Enter a date of birth"; "Use the date picker, the date must be YYYY-MM-DD" |
| Mobile Number | text | "Enter a mobile number"; "Enter a valid mobile number" |
| 14-Digit ABHA ID (Optional) | text | separators are stripped; "An ABHA number is 14 digits" when a partial one is typed; two members cannot share one ([D5. member](../database/D5-member.md)) |
| Verify or create an ABHA | button (secondary) | the ABHA dialog of [A20. ABHA Create and Verify (ABDM M1)](../apis/A20-abha-m1.md); on success the ABHA number is filled in, and name, gender, date of birth and mobile where the dialog still has them blank; a typed value is kept |

The id is issued by the server from the member sequence ([D32. id_sequence](../database/D32-id-sequence.md)). Toasts: "Member `<id>` registered!", "Member `<id>` updated successfully!". Field errors come back per field (`422`, "Some details need correcting") and the first is shown.

**Delete** confirms "Confirm Member Deletion": "Remove `<name>` from the directory? Their claim history is kept, and the deletion is refused if they still hold an active subscription." A member with live cover is refused: "This cannot be removed while other records still refer to it". Removal is soft: the member leaves the directory and their enrolments and cases stay ([D5. member](../database/D5-member.md)).

**Ownership** [SANDBOX](../references/PAYERS.md#markers): in the reference every record carries the client id that made it; another account's members answer 404 and the shared seeded set is read-only ("This is preconfigured, shared with every account, and cannot be changed or removed"). A single-payer deployment has no owners.

API: [A1. Eligibility Answer](../apis/A1-eligibility-answer.md)

API: [A20. ABHA Create and Verify (ABDM M1)](../apis/A20-abha-m1.md)

Callback: [C2. Coverage Eligibility Check](../callbacks/C2-coverage-eligibility-check.md)

Data: [D5. member](../database/D5-member.md)

Data: [D32. id_sequence](../database/D32-id-sequence.md)

#### S4L. LAYOUT
The arrangement below is the reference desk's [REF](../references/PAYERS.md#markers): follow the target payer system's own screen conventions. What is required is in DESCRIPTION and ACTIONS: the ABHA field and its rule, the handles the search matches, the columns and the messages.

```
|------------------------------------------------------------------|
| Members                                  [(+) Register New Member]|
| Register, update, and manage policyholders in the member registry|
|------------------------------------------------------------------|
| [(search) ______________________]           124 members found    |
|------------------------------------------------------------------|
| Member ID     | Full Name    | Age / Gender / DOB | Mobile       |
|               |              |                    | Number       |
| 14-Digit ABHA ID           | Actions                             |
|---------------|--------------|--------------------|--------------|
| MRAJ2004001   | (R) Ramesh   | 36 Yrs (Male)      | +91 98765    |
|               |     Kumar    | 1990-04-10         | 00000        |
| [shield] 91884920194401    | [edit] [delete]                     |
|------------------------------------------------------------------|
| Dialog: Register New Policyholder Member                         |
|  Full Legal Name [__________________________]                    |
|  Gender [Male v]           Date of Birth [1995-04-10]            |
|  Mobile Number [+91 ...]   14-Digit ABHA ID (Optional) [______]  |
|                                   [Cancel] [Register Member]     |
|------------------------------------------------------------------|
```

- One primary action in the header. The search box and the count share one row.
- A table on wide screens, stacked cards with the same fields on small ones.
- The dialog is modal, two columns for the paired fields.

#### S4A. ACTIONS
1. Register New Member: open the dialog empty, save with "Register Member".
2. Edit: open the dialog with the member's values, save with "Save Changes".
3. Delete: confirm, then retire the member; refused while they hold live cover.
4. Search: narrow the list by name, id, mobile or ABHA number; "Clear search" resets it.
5. Register member (empty state): the same as 1.
