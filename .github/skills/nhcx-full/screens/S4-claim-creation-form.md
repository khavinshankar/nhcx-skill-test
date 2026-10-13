# S4. Claim Creation Form Screen

#### S4R. ROUTE
claims/view/:caseid/validate (the Validate step)
claims/view/:caseid/preauth (the admission link and the draft)

This is the step of a case that turns a validated procedure set into a pre-authorisation draft. It always works on one case opened from S2, so it carries that case's id. It is not a page of its own: it is the Validate tab of the Claim Detail shell together with the "Link the admitted patient", "Linked admission" and "Pre-authorisation draft" cards that open the Pre-authorisation tab (S9).

Breadcrumb: Claims (claims/list, S5) > <case number> (S6)

#### S4D. DESCRIPTION
The screen does three things, in order:

1. Validate. It shows whether the procedure set chosen on Line Items (S8) has been sent to the payer for an authorisation ruling, and hands over to the pre-authorisation once it has.
2. Link. It attaches the case to the patient's current IPD admission, matched on ABHA number.
3. Draft. It captures the pre-authorisation draft: the stay dates, the ICD-10 diagnoses, the treating team and the case type with its estimate. Saving it keeps the draft in the application. Nothing goes to NHCX from this screen; the draft is sent from S9.

**Validate block**

- With no line items on the case, the only card is "Validate", reading: "Choose the line items on the previous tab first. This tab then sends that procedure set to the payer, which rules on each line and names the documents and forms the pre-authorisation needs."
- With line items, the first card is "Authorisation requirements" (the payer's ruling on the procedure set, described in full in S8, section S8.2).
- Below it, a card reading "The procedure set is validated; the **Pre-authorisation** tab is open. Fill in the dossier there and send it." with a primary button "Go to the pre-authorisation" (arrow-right icon).
- The pre-authorisation opens without waiting for the ruling. Some payers (the PMJAY sandbox among them) never answer the procedure-set check, so the draft is not blocked on it [SANDBOX](../references/PAYERS.md#markers). When the ruling does arrive it narrows the documents and forms S9 asks for.

**Verification** is the tab before this one, S18: the beneficiary authenticated against their ABHA ([A18. Biometric Authentication](../apis/A18-biometric-authentication.md)), whose token the pre-authorisation carries. Optional for any payer, required by PMJAY, and never a blocker here: without a token the consent questionnaire stands in for a payer that requires one.

**Link block**

Which card shows depends on the case:

| Case state | Card shown |
|---|---|
| Eligibility status is not `eligible` and no admission is linked | "Pre-authorisation": "The pre-authorisation opens once the payer has confirmed the policy is **eligible**. Run the coverage eligibility check on the Eligibility tab first." |
| Eligible, but the policy carries no ABHA number | "Link the admitted patient": "This policy carries no ABHA number, so it cannot be matched to an admission. Re-run the eligibility check - the payer's reply usually carries the beneficiary's ABHA." |
| Eligible with an ABHA number, not yet linked | "Link the admitted patient" with the matching admissions table |
| Linked | "Linked admission" summary, then the draft form |

Matching admissions are the current (not yet finished) IPD stays of patients whose ABHA number equals the policy's ABHA number, compared on digits only (the payer writes `91-7034-...`, the front desk may store it without dashes). Newest admission first.

The intro line reads: "The policy is eligible for **<beneficiary name or member id>** (ABHA <abha>). Link the claim to their current IPD stay to start the pre-authorisation."

Matching admissions table columns: Patient (link to S15), MRN, Admission (encounter number, link to the admission), Ward / bed (`ward / bed`, or just the ward), Admitted (date and time), Doctor, and a primary "Link" button (link icon).

Empty state: "No current IPD admission matches this ABHA number. Register the patient with this ABHA and admit them first." followed by two buttons, "Register patient" (user-plus icon, S14) and "New admission" (hospital icon).

Link rules, checked on the server (errors show as a red flash on the Pre-authorisation tab):
- Case must be eligible: "Link an admission only after the payer has confirmed the policy is eligible."
- The chosen stay must still be in the match list: "That admission is not a current IPD stay of a patient with this claim's ABHA number."
- On success the case is linked to the patient and the admission, and the admission date defaults to the stay's start date when the case has none yet. Flash: "Admission linked to the claim."

Linked admission card fields (three columns): Patient (link to S15), MRN, Admission (link), Ward / bed (`ward / bed`, dashes when missing), Admitted, Consultant. Header action "Unlink" (unlink icon) asks "Detach this claim from the admission? The preauth draft is kept." and then detaches the patient and admission from the case, keeping the draft. Flash: "Admission unlinked."

**Draft block: "Pre-authorisation draft"**

A single form in a card. When a draft has been saved before, a three-column summary sits above the sections: Last saved (date and time), Case (`Package (HBP rate)` or `Non-package (itemised)`), Estimated amount (`₹` with two decimals, or `-`).

The form is an accordion of four sections, several open at once:

1. **Stay**, two columns:

| Field | Control | Rule |
|---|---|---|
| Admission date | date input, required | Defaults from the linked admission |
| Provisional discharge date | date input, optional | Must not be before the admission date |

2. **Diagnoses (ICD-10)**
   - If the linked admission already records diagnoses that are not resolved, they are listed read-only as `<ICD-10 code> - <ICD-10 display>` with the hint "Recorded on the admission; change it there." ("there" links to the admission). Those diagnoses are what is saved; the form does not ask again.
   - Otherwise the hint reads "The admission has no diagnosis recorded yet - add it on the admission, or pick one here for now." followed by repeating rows. Each row has one select, "Diagnosis (ICD-10)" (24rem), blank option "Select diagnosis". Options come from the diagnosis terminology and are labelled `<ICD-10 code> - <ICD-10 display>` (falling back to the base code and display). Each row has a red trash button to remove it, and "Add diagnosis" adds a row.

3. **Treating doctor**
   - If the admission names a consultant, it shows "<doctor name> - treating doctor" with the hint "The consultant on the admission; change it there." That consultant is saved with role `treating`.
   - Otherwise the hint reads "The admission names no consultant yet, set one on the admission, or add the doctor here." followed by repeating rows with:
     - "Doctor" select (18rem), blank "Select doctor", options are active practitioners as `<name> - <department>`, sorted by name.
     - "Role" select (12rem), default `treating`, options:

| Value | Label |
|---|---|
| `admitting` | Admitting physician |
| `treating` | Treating doctor |
| `surgeon` | Surgeon |
| `anaesthetist` | Anaesthetist |
| `nurse` | Nursing lead |

   "Add doctor" adds a row; each row has a trash button.

4. **Case and estimate**. Two radio buttons, "Package (HBP rate)" (`package`, the default) and "Non-package (itemised)" (`nonpackage`) [PAYER](../references/PAYERS.md#markers). Switching shows one of two boxes without a reload:
   - Package box, when the payer's insurance plan (S7) is fetched and ready: a read-only table of the quoted lines with columns Kind (chip: Procedure info, Implant warning, "Ward / ICU tier"), Item (display with code underneath), Ward / ICU tier (tier chips `<label> · <code>` with `+₹<amount>`), Rate, Quantity, Amount, then "Total ₹<sum>" right-aligned, and a primary "Choose line items" button (list icon) that goes to the S8 picker. Empty text: "Nothing quoted yet, choose the procedure being done, the implants the payer approves for it and the ward tier."
   - Package box, when no plan is ready: one "Package" select, blank "Select package", options from the local HBP package master as `<display> - ₹<rate>`, with help text "The rate is fixed by the local HBP master. Fetch the payer's insurance plan to quote against its own packages instead."
   - Non-package box: label "Items" with help text "Prices are fixed by the charge master; you choose the quantity." then repeating rows of "Item (fixed price)" select (20rem, blank "Select item", options `<display> - ₹<price>` from the charge master) and "Quantity" number input (8rem, min 0.5, any step). "Add item" adds a row.

Footer: primary "Save preauth draft" button (save icon).

**Save rules** (checked on the server in this order, each message shown verbatim as a red flash, and the operator returns to the same tab):

- No admission linked: "Link the admitted patient before drafting a pre-authorisation."
- Admission date empty: "Enter the admission date."
- Discharge before admission: "The provisional discharge date cannot be before the admission date."
- No usable diagnosis: "Record the diagnosis on the admission (or pick one here) - the payer needs an ICD-10 code."
- Unknown role: "Choose a valid care team role."
- No active doctor: "Set the consultant on the admission (or add a doctor here) - the payer needs a treating doctor."
- Case type missing or unknown: "Choose whether this is a package or a non-package case."
- Package case with a ready plan and no Procedure line: "Quote at least one procedure for this package case - use “Choose line items”."
- Package case without a plan and no package chosen: "Select the package for this case."
- Non-package item with a quantity of zero or less: `Enter a quantity for "<item display>".`
- Non-package case with no items: "Add at least one item to a non-package case."

Pricing is never taken from the form. A package case with a ready plan takes the first Procedure line as the package and the sum of the quoted lines as the estimate. A local package takes its master rate. A non-package case re-reads each item's price from the charge master and prices each item at `price × quantity`, rounded to two decimals, with their sum as the estimate. Saving replaces the previously saved diagnoses, team and items. Flash on success: "Pre-authorisation draft saved."

Data: [D9. claim](../database/D9-claim.md)

Data: [D3. patient](../database/D3-patient.md)

Data: [D4. encounter](../database/D4-encounter.md)

Data: [D5. condition](../database/D5-condition.md)

Data: [D2. practitioner](../database/D2-practitioner.md)

Data: [D8. terminology](../database/D8-terminology.md)

Data: [D16. claim_line](../database/D16-claim-line.md)

Data: [D25. claim_diagnosis](../database/D25-claim-diagnosis.md)

Data: [D26. claim_care_team](../database/D26-claim-care-team.md)

Data: [D27. claim_item](../database/D27-claim-item.md)

#### S4L. LAYOUT
The arrangement below is the reference implementation's [REF](../references/PAYERS.md#markers): follow the target HMIS's own screen conventions. What is required is in DESCRIPTION and ACTIONS: the fields, options, columns, statuses, messages and actions.


```
|------------------------------------------------------------------|
| Claims > <case number>                                           |
|------------------------------------------------------------------|
| [Card] Authorisation requirements          [Validate procedure   |
|  (see S8.2)                                  set / Check again]  |
|------------------------------------------------------------------|
| [Card] The procedure set is validated; the Pre-authorisation     |
|  tab is open. ...          [(->) Go to the pre-authorisation]    |
|------------------------------------------------------------------|
| [Card] Linked admission                              [Unlink]    |
|  PATIENT        MRN            ADMISSION                         |
|  Ravi Kumar     MRN-0042       IPD-0007                          |
|  WARD / BED     ADMITTED       CONSULTANT                        |
|  Gen / 12       2026-09-20     Dr Rao                            |
|------------------------------------------------------------------|
| [Card] Pre-authorisation draft                                   |
|  LAST SAVED     CASE                 ESTIMATED AMOUNT            |
|  v Stay                                                          |
|    Admission date *     Provisional discharge date               |
|    [dd-mm-yyyy]         [dd-mm-yyyy]                             |
|  v Diagnoses (ICD-10)                                            |
|    - K35.8 - Acute appendicitis                                  |
|    Recorded on the admission; change it there.                   |
|  v Treating doctor                                               |
|    Dr Rao - treating doctor                                      |
|  v Case and estimate                                             |
|    (o) Package (HBP rate)   ( ) Non-package (itemised)           |
|    Kind | Item | Ward / ICU tier | Rate | Quantity | Amount      |
|                                           Total ₹25,000          |
|                                    [(list) Choose line items]    |
|  ----------------------------------------------------------------|
|                                   [(save) Save preauth draft]    |
|------------------------------------------------------------------|
```

Before linking, the Linked admission card and the draft card are replaced by:

```
|------------------------------------------------------------------|
| [Card] Link the admitted patient                                 |
|  The policy is eligible for <name> (ABHA <abha>). Link ...       |
|  Patient | MRN | Admission | Ward / bed | Admitted | Doctor | [Link]
|  (empty: No current IPD admission matches this ABHA number...)   |
|  [Register patient]  [New admission]      (only when empty)      |
|------------------------------------------------------------------|
```

- Cards stack vertically with even spacing.
- The draft sections are an accordion that allows several sections open at once.
- Repeating rows (diagnoses, doctors, items) are bordered boxes with the fields inline and a red trash icon button at the end; they wrap on narrow screens. The Add button under each list is a small secondary button with a plus icon.
- The case type switch is client-side: only the chosen box is visible, but both are in the form.
- Summary values show `-` when empty.

#### S4A. ACTIONS
1. Go to the pre-authorisation: open the Pre-authorisation screen S9.
2. Validate procedure set / Check again: send the procedure set for an authorisation ruling (see S8, section S8.2) and return here.
3. Link (on an admission row): attach the case to that admission and show the Linked admission card and the draft form.
4. Patient name link: open Patient Detail S15.
5. Register patient: open Patient Registration Form S14.
6. New admission: open the admission form of the hospital's IPD module (outside this screen map).
7. Unlink: after the confirm, detach the admission; the draft is kept.
8. Add diagnosis / Add doctor / Add item: add an empty row; the trash button removes a row. Empty rows are ignored on save.
9. Switch case type: toggle between the package box and the items box.
10. Choose line items: open the line item picker, S8 section S8.1.
11. Save preauth draft: validate and store the draft, then return to this screen with a green or red flash. Sending it to the payer happens on S9.
12. Breadcrumb "Claims": go to Claim Master S5. Case number: go to Claim Detail S6.
