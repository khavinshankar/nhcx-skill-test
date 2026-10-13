# S7. Insurance Plan Screen

#### S7R. ROUTE
claims/view/:caseid/plan

Breadcrumb: Claims (claims/list, S5) > <case number> (S6)

Sub-pages in this file:
- S7.1 Package Detail: claims/view/:caseid/plan/:benefitid
- S7.2 Plan Forms: claims/view/:caseid/plan/forms
- S7.3 Form Detail: claims/view/:caseid/plan/forms/:formid

#### S7D. DESCRIPTION
The payer's package master for this policy and this facility: every empanelled speciality, the packages under it, their rates, the tiers paid on top, their claim conditions, the documents they need and the questionnaires the payer ships with them. Line Items (S8) quotes only from this master, so it has to be fetched before a pre-authorisation can be priced.

Intro text on the card: "The payer's **package master** for this policy and this facility: every empanelled speciality, the packages under it and their rates. The app asks for it with an InsurancePlan discovery Task - a lookup that carries no clinical content, only the policy code and the facility's HFR ID - and the payer answers asynchronously, exactly like the eligibility check."

**Fetching.** "Fetch insurance plan" (first time) or "Fetch again" (refresh). Before any call:
- The facility must have an HFR ID: "Set the facility's HFR ID under Settings before fetching a package master."
- The facility must have an NHCX participant code: "Set the facility's NHCX participant code under Settings before fetching a package master."

Reuse before asking: on the first fetch (not on "Fetch again"), if another case already holds a `ready` master for the same payer, the same policy code and the same facility HFR ID, the newest one is copied onto this case and no request goes out. Flash: "Using the package master already held for this policy - Fetch again asks the payer for a new one." A master belongs to the facility and the policy, not to one case, and a full PMJAY master is tens of megabytes [SANDBOX](../references/PAYERS.md#markers).

API: [A3. Insurance Plan Request](../apis/A3-insurance-plan-request.md)

With neither a policy code nor an HFR ID the request is refused: "A plan request needs a policy code or the facility's HFR ID." Flash: "Insurance plan requested from the payer." A refetch clears the case's packages before the new answer lands, so a stale package cannot survive it.

**Waiting for the answer.** There is no timer: every load of the claim screen polls once while the plan is `fetching`. A failure of the poll itself shows as a muted line "Could not poll the gateway: <error>" on the waiting card.

Callback: [C4. Insurance Plan Reply](../callbacks/C4-insuranceplan-on-request.md)

API: [A10. Transaction Related](../apis/A10-txn-related.md) (poll)

API: [A11. Transaction Dispatch](../apis/A11-txn-dispatch.md) (poll, dispatch status)

The case header shows a "Refresh" button while any exchange is outstanding (S6); pressing it reloads and polls.

Plan statuses:

| Status | Label | Chip tone |
|---|---|---|
| `fetching` | Awaiting payer | info |
| `ready` | Ready | success |
| `empty` | No plan returned | warning |
| `error` | Error | danger |

A reply that carries no InsurancePlan at all (only the payer's Organization) settles as `empty` with the F5 message "The payer reply carries no InsurancePlan. The payer has no package master filed under this policy." shown on the card, as C4 and D10 say; it is a legitimate answer, not an error. A reply with a plan but zero packages is `empty` too. Only a `ProtocolResponse` or a transport failure is `error`.

Data: [D10. claim_plan](../database/D10-claim-plan.md)

Data: [D11. claim_plan_benefit](../database/D11-claim-plan-benefit.md)

Data: [D12. claim_plan_form](../database/D12-claim-plan-form.md)

**What the tab shows per state:**

- No plan yet: card "Insurance plan" with the intro and a primary "Fetch insurance plan" button (download icon).
- `fetching`: card "Insurance plan" with the intro, then "Discovery Task sent to the payer; awaiting the on_request reply. Use Refresh to check for it.", the poll note if any, and Sent at, Transaction, Correlation. Header action "Fetch again" (refresh icon) with the confirm "The payer has not returned the plan yet. Send the discovery Task again?"
- `error`: card "Insurance plan" with the error in the danger colour (or "The exchange failed.") and the "Fetch again" button.
- `empty`: the summary card, then a card reading "The payer returned no plan for this policy and facility. That is a legitimate answer, not a transport failure - it means no coverage matches this policy-provider pair, so the pre-authorisation falls back to the local HBP package master."
- `ready`: the summary card, the filter row and the packages table.

Summary card "Insurance plan", three columns: Plan, Plan identifier, Plan type, Overall sum insured (`₹` whole rupees), Asked with (policy code and HFR ID, comma separated), Fetched at, Correlation. Header actions: "All forms" (clipboard-list icon, only when the plan carries questionnaires, goes to S7.2) and "Fetch again" (refresh icon, primary) with the confirm "Fetch the insurance plan again? The packages stored for this claim are replaced by whatever the payer returns."

**Filter row** (its own row above the table, a GET form so the result can be bookmarked):

| Field | Control | Behaviour |
|---|---|---|
| Search | text, at least 18rem | Substring match on the package code or name, any case |
| Speciality | select, blank "All specialities" | Options are the plan's specialities as `<name> (<package count>)`, sorted by name |
| Type | select, blank "Any type" | `Procedure`, `Implant` |

A primary "Search" button (search icon). "Clear" (x icon) appears when any filter is set and resets all three.

**Packages table.** Card title "<n> package(s)" where n is the filtered count. Rows keep the payer's order. Columns:

| Column | Content |
|---|---|
| Code | Package code |
| Package | Package name, or the code |
| Speciality | Speciality name, or code, or `-` |
| Type | Chip: `Procedure` info, anything else (`Implant`) warning, `-` if none |
| (action) | "View" small secondary button, opens S7.1 in a modal |

Every package is listed: there is no row limit, whatever the size of the plan. A large plan is paged, 100 rows a page with "Previous" and "Next" and "Page <p> of <q>" under the table [REF](../references/PAYERS.md#markers), and search and filters narrow it across all its packages, not just the page shown. Empty state: "Nothing matches that search."

Cell helpers available for a denser table (defined but not in the default column set): a rate cell showing the package rate with "+<k> tier(s), up to ₹<max>" underneath; a conditions cell with up to three chips (key conditions first, in the order GovtReserved, Standalone, IsDayCare, ApprovalNotRequired, ImplantApplicable, StratificationAllowed, ProcedureType [PAYER](../references/PAYERS.md#markers); a true flag shows just its name, others `<name>: <value>`) and "+<k> more"; and a documents cell "<n> required" with the first document's name underneath.

#### S7L. LAYOUT
The arrangement below is the reference implementation's [REF](../references/PAYERS.md#markers): follow the target HMIS's own screen conventions. What is required is in DESCRIPTION and ACTIONS: the fields, options, columns, statuses, messages and actions.


```
|------------------------------------------------------------------|
| [Card] Insurance plan               [All forms] [(o) Fetch again]|
|  PLAN               PLAN IDENTIFIER      PLAN TYPE               |
|  OVERALL SUM INSURED  ASKED WITH         FETCHED AT              |
|  CORRELATION                                                     |
|------------------------------------------------------------------|
| Search              Speciality          Type                     |
| [______________]    [All specialities v] [Any type v] [Search] [x Clear]
|------------------------------------------------------------------|
| [Card] 975 package(s)                                            |
|  Code     | Package              | Speciality | Type       |     |
|  SB039A   | Appendicectomy       | General    | [Procedure]| View|
|  ...                                                             |
|  [Previous]  Page 1 of 10  [Next]                                |
|------------------------------------------------------------------|
```

- The filter fields sit side by side and wrap on narrow screens.
- "View" opens one shared modal filled on demand (the master can run to a thousand packages, so there is not one dialog per row). The modal shows "Loading…", then the package body; it has a "Close" button in its footer. If the fragment fails to load, the browser goes to the full S7.1 page instead. With scripts off, "View" is a plain link to S7.1.

#### S7A. ACTIONS
1. Fetch insurance plan: reuse a held master or send the discovery Task, then return to this tab with a flash.
2. Fetch again: after the confirm, always ask the payer; the case's packages are replaced by the answer.
3. Refresh (case header, S6): reload and poll once for the `on_request` reply.
4. Search / change Speciality / change Type: filter the table.
5. Clear: remove all filters.
6. View (on a row): open S7.1 in the modal.
7. All forms: open S7.2.
8. Line Items tab: go to S8 once the plan is `ready`.
9. Breadcrumb "Claims": S5. Case number: S6.

---

## S7.1 Package Detail

#### S7.1R. ROUTE
claims/view/:caseid/plan/:benefitid

Breadcrumb: Claims (S5) > <case number> (S7) > <package code>

#### S7.1D. DESCRIPTION
Everything the payer published about one package. It serves both as the modal body on S7 (fragment mode, with the package name as a heading) and as a full page with the package name as the card title. A package id that does not belong to this case gives a "Package" not-found page.

Header, three columns: Code, Type, Speciality, Package rate (`₹`), Currency, Requirement, Plan.

Below it, an accordion (several sections open at once). For a Procedure:

1. "Implants allowed (<n>)": columns Code, Implant, Rate (the rate quoted for this package), and a "View" button that opens the implant's own entry, or "not in this plan" when the implant has no entry. Empty: "No implant is approved for this package." Under the table, chips for `ImplantApplicable`, `MultipleImplantsAllowed` and `MaximumImplantsAllowed` when the payer set them, as `<name>: <value>` [PAYER](../references/PAYERS.md#markers).
2. "Ward & ICU tiers (<n>)": every non-implant tier. Columns Tier (label with code underneath), Kind (for example `Stratification`), Rate. Empty: "No ward or ICU tier is payable over the package rate."

For an Implant, instead of those two:

1. "Allowed with (<n>)": the packages that list this implant. Columns Code, Package, Speciality, "View". Every such package is listed, with no row limit, paged as the package list is. Empty: "No package in this plan lists this implant."

Then for both:

- "Claim conditions (<n>)": columns Condition, Value (`Yes` for a true flag). Empty: "The payer published no conditions for this package."
- "Documents required (<n>)": columns Code, Document, Category, Form (the questionnaire title, "form not sent" when the document names a form the plan did not include, `-` when none). Empty: "No documents are listed as mandatory here."
- "Forms to complete (<n>)", only when the documents name questionnaires the plan carries: an inner accordion, one panel per form titled "<form title> (<question count>)", each a read-only table as in S7.3.

Data: [D11. claim_plan_benefit](../database/D11-claim-plan-benefit.md)

Data: [D12. claim_plan_form](../database/D12-claim-plan-form.md)

#### S7.1L. LAYOUT:

```
|------------------------------------------------------------------|
| Appendicectomy                                                   |
|  CODE        TYPE          SPECIALITY                            |
|  PACKAGE RATE  CURRENCY    REQUIREMENT                           |
|  PLAN                                                            |
|  > Implants allowed (0)                                          |
|  > Ward & ICU tiers (3)                                          |
|  > Claim conditions (7)                                          |
|  > Documents required (4)                                        |
|  > Forms to complete (1)                                         |
|                                                    [Close]       |
|------------------------------------------------------------------|
```

#### S7.1A ACTIONS:
1. View (implant or package row): load that entry into the same modal, or open its page.
2. Close: close the modal and stay on S7.
3. Breadcrumb case number (full page): back to S7.

---

## S7.2 Plan Forms

#### S7.2R. ROUTE
claims/view/:caseid/plan/forms

Breadcrumb: Claims (S5) > <case number> (S7) > Forms

#### S7.2D. DESCRIPTION
Every questionnaire the payer shipped with the plan, searchable. Reached from "All forms" on S7. With no plan on the case, an "Insurance plan" not-found page.

Card title "<n> form(s)". Header action is a search form: "Search" text field (at least 16rem, parameter kept in the URL) and a primary "Search" button. The search matches the form title or form id as a substring.

Columns:

| Column | Content |
|---|---|
| Form | Title, with the form id underneath |
| Kind | Chip `STG` (warning) for a url under `/stgquestionnaire/`, a standard treatment guideline checklist [PAYER](../references/PAYERS.md#markers); otherwise `Policy` (info) |
| Questions | Number of questions, nested ones included |
| (action) | "View", opens S7.3 in the modal |

Sorted by title. Every form is listed, with no row limit, paged the same way as the packages. Empty: "Nothing matches that search."

Data: [D12. claim_plan_form](../database/D12-claim-plan-form.md)

#### S7.2L. LAYOUT:

```
|------------------------------------------------------------------|
| Claims > <case number> > Forms                                   |
|------------------------------------------------------------------|
| [Card] 991 form(s)              Search [__________] [(search)Search]
|  Form                 | Kind     | Questions |                   |
|  Consent form         | [Policy] | 12        | View              |
|  frm-123                                                         |
|------------------------------------------------------------------|
```

#### S7.2A ACTIONS:
1. Search: filter the forms list.
2. View: open S7.3 in the modal.
3. Breadcrumb case number: back to S7.

---

## S7.3 Form Detail

#### S7.3R. ROUTE
claims/view/:caseid/plan/forms/:formid

Breadcrumb: Claims (S5) > Forms (S7.2) > <form id>

#### S7.3D. DESCRIPTION
One questionnaire, read-only, as the modal body (with the title as a heading) or a full page (title as card title). A form id that does not belong to this case gives a "Form" not-found page. Answering happens on S9 and S11, not here.

Columns:

| Column | Content |
|---|---|
| Question | Question text (or the question id), indented by its nesting depth; a red `*` when required |
| Answer type | Label for the answer type, see below |
| Options | One info chip per answer option, or `-` |

Answer type labels: `attachment` File, `choice` Choice, `datetime` Date & time, `date` Date, `time` Time, `string` Text, `text` Long text, `boolean` Yes / no, `integer` / `decimal` / `quantity` Number, `url` Link. Any other type shows as sent.

Empty: "This form carries no questions."

Data: [D12. claim_plan_form](../database/D12-claim-plan-form.md)

#### S7.3L. LAYOUT:

```
|------------------------------------------------------------------|
| Consent form                                                     |
|  Question                    | Answer type | Options             |
|  Was consent obtained? *     | Yes / no    | -                   |
|    Date of consent           | Date        | -                   |
|  Type of anaesthesia         | Choice      | [GA] [SA] [LA]      |
|                                                    [Close]       |
|------------------------------------------------------------------|
```

#### S7.3A ACTIONS:
1. Close: close the modal.
2. Breadcrumb "Forms": back to S7.2.
