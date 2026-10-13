# S8. Line Items Screen

#### S8R. ROUTE
claims/view/:caseid/lines

Breadcrumb: Claims (claims/list, S5) > <case number> (S6)

Sub-pages in this file:
- S8.1 Choose Line Items: claims/view/:caseid/lines/choose
- S8.2 Authorisation Requirements card (shown on the Validate step, S4)

#### S8D. DESCRIPTION
What the pre-authorisation quotes: the procedures being done, the implants the payer approves for them, and the ward or ICU tier the stay runs at. Every line comes from the payer's own package master (S7), priced at the payer's rate. There is no local price list on this path.

Line kinds:

| Value | Label | Chip tone |
|---|---|---|
| `Procedure` | Procedure | info |
| `Implant` | Implant | warning |
| `Stratification` | Ward / ICU tier | neutral |

A ward or ICU tier is not a line of its own. Its rate is inside the amount of the procedure it was quoted through [PAYER](../references/PAYERS.md#markers). So the tables never list a tier as a row: it shows in the "Ward / ICU tier" column of its procedure. A tier whose procedure has been removed hangs off the first remaining procedure; with no procedure at all it shows as its own row.

**Before the plan is ready** (no plan, or status other than `ready`): card "Line items" reading "The pre-authorisation quotes the payer's own packages and rates, so the insurance plan has to be fetched first." with a primary "Go to the insurance plan" button (download icon) to S7.

**With the plan ready**: card "Line items", header action primary "Choose line items" (list icon) to S8.1. Read-only table:

| Column | Content |
|---|---|
| Kind | Kind chip |
| Item | Name, with the code underneath |
| Ward / ICU tier | One chip per tier, `<tier label> · <tier code>`, with `+₹<amount>` beside it; `-` when none |
| Rate | Unit price, `₹` whole rupees |
| Quantity | Quantity, no trailing zeros |
| Amount | `₹` whole rupees |

Under the table, right-aligned: "Total ₹<sum of all line amounts>" (tiers included). Empty state: "Nothing quoted yet. The payer prices this preauth from its own package master - choose the procedure, the implants it approves and the ward tier."

Nothing is sent to NHCX from this tab. Changing the lines after the payer has ruled on them marks the ruling stale on S8.2.

Data: [D16. claim_line](../database/D16-claim-line.md)

Data: [D10. claim_plan](../database/D10-claim-plan.md)

Data: [D11. claim_plan_benefit](../database/D11-claim-plan-benefit.md)

#### S8L. LAYOUT
The arrangement below is the reference implementation's [REF](../references/PAYERS.md#markers): follow the target HMIS's own screen conventions. What is required is in DESCRIPTION and ACTIONS: the fields, options, columns, statuses, messages and actions.


```
|------------------------------------------------------------------|
| [Card] Line items                      [(list) Choose line items]|
|  Kind        | Item           | Ward / ICU tier  | Rate  | Qty | Amount |
|  [Procedure] | Appendicectomy | [ICU · STRAT01]  | ₹20,000 | 1 | ₹25,000 |
|              |   SB039A       |   +₹5,000        |       |     |        |
|  [Implant]   | Mesh 15 X 15   | -                | ₹3,000 | 1  | ₹3,000 |
|              |   IMP001       |                  |       |     |        |
|                                             Total ₹28,000        |
|------------------------------------------------------------------|
```

- Chips and amounts are compact; the table scrolls horizontally inside its card on narrow screens.

#### S8A. ACTIONS
1. Choose line items: open S8.1.
2. Go to the insurance plan (before the plan is ready): open S7.
3. Validate tab: open S4, where S8.2 sends this set for a ruling.
4. Breadcrumb "Claims": S5. Case number: S6.

---

## S8.1 Choose Line Items

#### S8.1R. ROUTE
claims/view/:caseid/lines/choose

Breadcrumb: Claims (S5) > <case number> (S8) > Line items

Page action: "Back to the claim" (undo icon), to S8.

#### S8.1D. DESCRIPTION
The picker. Three blocks, top to bottom: what is on the pre-authorisation, what the payer suggests with it, and the full package master to search. Without a ready plan the page shows only the "Line items" card with "The preauth quotes the payer's own packages and rates, so the insurance plan has to be fetched first." and "Go to the insurance plan" (S7). An unknown case gives a "Claim" not-found page.

**Card 1: "On this preauth"**

| Column | Content |
|---|---|
| Kind | Kind chip |
| Item | Name, code underneath |
| Speciality | Speciality name or `-` |
| Ward / ICU tier | Tier chips as on S8, each with its own red "Remove" button (confirm "Take this tier off the preauth?") |
| Rate | The plan's rate as text. Where the plan prices the line at zero or names no rate, a number input instead (8rem, min 0, step 0.01), since such a package is billed at the hospital's own price [PAYER](../references/PAYERS.md#markers) |
| Quantity | Number input (6rem, min 1, step 1), whole numbers |
| Amount | `₹` whole rupees |
| (action) | Red "Remove" button, confirm "Take this line off the preauth?" |

Below the table "Total ₹<sum>" right-aligned, and a footer with the primary "Update lines" button (save icon). The table and button form one form. Empty state (no form, no button): "Nothing quoted yet, add the procedure being done from the catalogue below."

Update lines rules (red flash on failure, shown verbatim):
- A price is read only for a line whose price is open; everywhere else the plan's rate stands whatever is posted.
- Open price not a number: "Enter a price for <code>."
- Open price below zero: "The price of <code> cannot be negative."
- Quantity with a fraction: "The quantity of <code> must be a whole number."
- Quantity zero, negative or unreadable: "Enter a quantity for <code>."
- An empty quantity keeps the current quantity. Every amount is recomputed as `unit price × quantity`, rounded to two decimals.
- Success flash: "Lines updated."

Remove (line or tier): deletes that line only. Flash "Line removed."

**Card 2: "Suggested by the payer's plan"** (only when there is something to suggest)

Built from the procedures already on the pre-authorisation, from what their plan entries allow, leaving out codes already quoted and each code only once. An accordion with up to two panels:

- "Implants approved for these procedures": columns Code, Implant, Rate, and a primary "Add" button (plus icon) that adds it as an `Implant` line.
- "Ward and ICU tiers": the procedures' `Stratification` tiers. Columns Code, Tier, For (procedure name with its code underneath), Rate, and "Add" that adds it as a `Stratification` line quoted through that procedure.

**Card 3: the package master**

A filter row above the card, a GET form: "Search" (text, at least 18rem, matches code or name as a substring), "Speciality" (blank "All specialities", options `<name> (<count>)`), "Type" (blank "Any type", `Procedure` or `Implant`), and a primary "Search" button. Unlike S7 there is no Clear button.

Card title "<n> in the payer's package master". Columns: Code, Package, Speciality, Type (chip, Procedure info, otherwise warning), Rate, and "Add". A benefit whose kind a pre-authorisation cannot quote (a policy-wide allowance such as an ambulance or room sub-limit) gets no Add button. Every package is listed, with no row limit: paged 100 rows a page with "Previous" and "Next" and "Page <p> of <q>" [REF](../references/PAYERS.md#markers), and the search and filters narrow the whole package master. Empty: "Nothing matches that search."

**Adding a line** posts the kind, the code, and for a tier the parent procedure code. The price is read from the plan at add time, never from the form: a Procedure or Implant takes the benefit's rate, a tier takes the rate its parent procedure lists for it (different procedures price the same ward differently [PAYER](../references/PAYERS.md#markers)). The new line starts at quantity 1. Rules, each shown verbatim as a red flash:
- Kind not one of the three: "That is not something a preauth can quote."
- No code: "Nothing was selected."
- Plan not ready: "Fetch the payer's insurance plan first, the preauth quotes its packages and its rates."
- Tier with an unknown parent: "Pick the procedure this ward tier belongs to."
- Tier the parent does not offer: "That ward tier is not offered for this package."
- Code not in the plan as that kind: "<code> is not a <kind in lower case> in this plan."
- Already quoted: "<code> is already on this preauth."
- Success: "<code> added."

Every action returns to S8.1.

Data: [D16. claim_line](../database/D16-claim-line.md)

Data: [D11. claim_plan_benefit](../database/D11-claim-plan-benefit.md)

#### S8.1L. LAYOUT:

```
|------------------------------------------------------------------|
| Claims > <case number> > Line items        [(undo) Back to the claim]
|------------------------------------------------------------------|
| [Card] On this preauth                                           |
|  Kind | Item | Speciality | Ward / ICU tier | Rate | Qty | Amount|
|  [Procedure] Appendicectomy  General  [ICU · STRAT01] +₹5,000 [Remove]
|               SB039A                      ₹20,000  [1]  ₹25,000 [Remove]
|                                             Total ₹25,000        |
|  ----------------------------------------------------------------|
|                                         [(save) Update lines]    |
|------------------------------------------------------------------|
| [Card] Suggested by the payer's plan                             |
|  > Implants approved for these procedures                        |
|    Code | Implant | Rate | [+ Add]                               |
|  > Ward and ICU tiers                                            |
|    Code | Tier | For | Rate | [+ Add]                            |
|------------------------------------------------------------------|
| Search            Speciality            Type                     |
| [____________]    [All specialities v]  [Any type v]  [Search]   |
| [Card] 975 in the payer's package master                         |
|  Code | Package | Speciality | Type | Rate | [+ Add]             |
|  [Previous]  Page 1 of 10  [Next]                                |
|------------------------------------------------------------------|
```

- The filter fields wrap on narrow screens.
- Add and Remove are extra-small buttons; Remove is the danger style and always confirms.

#### S8.1A ACTIONS:
1. Add (suggested implant, suggested tier, or catalogue row): add the line at the plan's rate and reload S8.1.
2. Edit quantity or open price, then Update lines: recompute amounts and reload S8.1.
3. Remove (line or tier): after the confirm, take it off and reload S8.1.
4. Search / Speciality / Type: filter the catalogue.
5. Back to the claim, or breadcrumb case number: return to S8.
6. Breadcrumb "Claims": S5.

---

## S8.2 Authorisation Requirements

#### S8.2R. ROUTE
Card on claims/view/:caseid/validate (S4, the Validate step). Its action posts and returns to S4.

#### S8.2D. DESCRIPTION
The payer's ruling on the quoted procedure set: whether each line needs authorisation or is excluded, and which documents and forms this particular set needs. A muted line "Payer adapter: <adapter name>" closes the card in every state.

Card title in every state: "Authorisation requirements".

States:

| State | Body | Header action |
|---|---|---|
| Never asked | "The <n> quoted line(s) can go to the payer as a `auth-requirements` check: it rules on each one and names the documents and forms this particular procedure set needs. The check is optional; the pre-authorisation can be sent without it." | primary "Validate procedure set" (shield-check icon) |
| `checking` | "Procedure set sent; awaiting the payer's ruling. Use Refresh to check for it." with Sent at, Transaction, Correlation | "Check again" |
| `error` | The error in the danger colour, or "The exchange failed." | "Check again" |
| `ready` | Ruling (below) | "Check again" |

Ruling statuses: `checking` Awaiting payer (info), `ready` Validated (success), `error` Error (danger).

**Ready state.** Header, three columns: Disposition, Outcome, Checked at. If the lines have changed since the ruling (compared by code, ward tiers and quantities ignored), a warning badge "The line items have changed since this ruling" and "The payer ruled on a different procedure set. Check again so the documents and forms it names are the ones this set needs." sit above the header.

Then an accordion:
1. "Ruling on <n> line(s)": columns Line (name, code underneath), Authorisation (`Required`, `Not required`, or ` - ` when the payer said nothing), Excluded (danger chip `Excluded`, or `No`), Benefit (benefit type code or `-`), Allowed (`₹`). Empty: "The payer ruled on no lines."
2. "Needed for this pre-authorisation (<n>)": requirements the payer marked for the pre-authorisation stage.
3. "Needed later, with the claim (<n>)", only when there are any, with the muted note "The payer marked these for a stage after pre-authorisation, so they are not asked for here."

Requirement tables: columns Kind (chip `Form` info or `Document` warning), Code, What, For (the line code it belongs to), Stage. Empty: "Nothing listed."

**Sending.** Checked before any call (red flash on S4):
- Case not eligible: "Check the policy's eligibility before validating a procedure set against it."
- No lines: "Choose the line items first, this checks the procedure set, so there has to be one."
- Facility setup missing: "Set the facility's HFR ID and NHCX participant code under Settings before checking requirements."

API: [A2. Coverage Eligibility Check](../apis/A2-coverage-eligibility-check.md) (purpose auth-requirements)

A fingerprint of the set sent is kept with the ruling. Asking again clears the previous ruling's lines and requirements. Flash: "Procedure set sent to the payer for validation."

**Waiting.** Each load of the claim screen polls once while the ruling is `checking`. A failed poll changes nothing and the card keeps saying it is awaiting.

Callback: [C3. Authorisation Requirements Ruling](../callbacks/C3-auth-requirements-on-check.md)

API: [A10. Transaction Related](../apis/A10-txn-related.md) (poll)

API: [A11. Transaction Dispatch](../apis/A11-txn-dispatch.md) (poll, dispatch status)

A reply with no ruling is an error: "The payer reply carries no CoverageEligibilityResponse."

The pre-authorisation also asks this check by itself, without waiting, when a set has not been asked about yet, because some payers answer it rarely and the request must not be held up for it [SANDBOX](../references/PAYERS.md#markers).

The forms named here are answered on S9 (and the claim-stage ones on S11), not on this screen.

Data: [D13. claim_auth](../database/D13-claim-auth.md)

Data: [D14. claim_auth_item](../database/D14-claim-auth-item.md)

Data: [D15. claim_auth_requirement](../database/D15-claim-auth-requirement.md)

#### S8.2L. LAYOUT:

```
|------------------------------------------------------------------|
| [Card] Authorisation requirements        [(shield) Check again]  |
|  [! The line items have changed since this ruling]  (when stale) |
|  DISPOSITION        OUTCOME           CHECKED AT                 |
|  > Ruling on 2 line(s)                                           |
|    Line | Authorisation | Excluded | Benefit | Allowed           |
|  > Needed for this pre-authorisation (3)                         |
|    Kind | Code | What | For | Stage                             |
|  > Needed later, with the claim (1)                              |
|  Payer adapter: PMJAY, State Health Agency                         |
|------------------------------------------------------------------|
```

#### S8.2A ACTIONS:
1. Validate procedure set / Check again: send the check and return to S4 with a flash.
2. Refresh (case header, S6): reload and poll for the ruling.
3. Go to the pre-authorisation (the card under this one on S4): open S9.
