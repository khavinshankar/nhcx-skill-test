# S1. Overview Screen

#### S1R. ROUTE
`/`

| Endpoint | Purpose |
|---|---|
| `GET overview` | Every figure and list on the page, counted by the database in one call |

Breadcrumb: none; this is the home of the desk. The sidebar entry is "Overview".

#### S1D. DESCRIPTION
The first screen after sign-in. It answers three questions at a glance: how big is the book (members, enrolments, products), what is waiting on a person (cases pending adjudication), and where the money stands (approved, disbursed, still owed). Everything on it is counted by the server; the screen never sums a page of rows itself, because a page is not the book [REF](../references/PAYERS.md#markers).

**Scope.** The figures are the whole book for a desk account. The reference sandbox narrows them to the participant codes an account works and the records its client id made [SANDBOX](../references/PAYERS.md#markers); a single-payer deployment shows everything.

API: `GET overview` (application; no A spec, the screen reads counts)

**Stat tiles**, four across:

| Tile | Value | Sub-line |
|---|---|---|
| Total Members | `members_total` | "Policyholders & Dependents" |
| Active Subscriptions | `subscriptions_active` | "`<policies_total>` Insurance Policies" |
| Pending Adjudication | `cases_pending` (amber) | "Pre-Auths & Claims in Queue" |
| Total Disbursed | `paid_total` as `₹12,34,567` | "`₹<pending_disbursement>` Pending" |

Money shows as `₹` followed by the amount with Indian grouping; a missing value shows `-`.

**Quick operations**, four buttons in a row: "Add Member" (to S4), "Build Policy" (to S6), "Adjudicate" (to S2), "Disbursement" (to S10). Each carries a one-word sub-label ("Member Register", "Policy Rules", "Line Item Review", "2% TDS & UTR") [REF](../references/PAYERS.md#markers).

**Claim lifecycle stream**, five counters from `cases_by_stage`, always all five, zero when empty:

| Stage | Label | Sub-line |
|---|---|---|
| `preauth` | 1. Pre-Auth | Initial Approval |
| `claim` | 2. Final Claim | Post-Discharge |
| `payment` | 3. Payment | Pending UTR |
| `settled` | 4. Settled | Disbursed |
| `rejected` | 5. Rejected | Non-Payable |

A case whose pre-authorisation was withdrawn is `cancelled` ([D19. case](../database/D19-case.md)) and is not counted in any tile; it is reachable from S2.

**Recent cases**, the four newest from `recent_cases`. Columns: Case & Claim No (the claim number, monospace), Patient & Hospital (name, with a "Minor" flag when the patient is one; hospital and city underneath), Stage & Status (the stage in upper case, coloured: settled green, rejected red, otherwise purple; the adjudication status in brackets), Claimed / Approved (`₹` claimed, then "Appr: ₹" approved), and a "Review Case" button that opens S3 for that case. Empty state: "No cases yet" with "Pre-authorisation and claim dossiers from hospitals will appear here."

**Live refresh.** The page reloads its figures whenever the member, case or payment stores change, so a decision taken on S3 and a payment released on S10 show here without a manual refresh [REF](../references/PAYERS.md#markers).

**One number names a case everywhere.** The claim number (`CL/<yy>/<mmdd><serial>`, [D19. case](../database/D19-case.md)) is what every list shows and what an adjudicator reads out; the row id is a database key and is never quoted [REF](../references/PAYERS.md#markers).

Data: [D5. member](../database/D5-member.md)

Data: [D6. subscription](../database/D6-subscription.md)

Data: [D12. policy](../database/D12-policy.md)

Data: [D19. case](../database/D19-case.md)

Data: [D30. payment](../database/D30-payment.md)

#### S1L. LAYOUT
The arrangement below is the reference desk's [REF](../references/PAYERS.md#markers): follow the target payer system's own screen conventions. What is required is in DESCRIPTION and ACTIONS: the figures, the stage counters, the recent list and the actions.

```
|------------------------------------------------------------------|
| Payer Operations Overview                  [(table) Adjudicate   |
| Sandbox Payer, RCM & Adjudication Dashboard          Claims]     |
|------------------------------------------------------------------|
| [Total Members] [Active Subscriptions] [Pending Adj.] [Disbursed]|
|   1,204            987 / 6 policies      14 (amber)    ₹42,10,000|
|------------------------------------------------------------------|
| Quick Operations Control                                         |
|  [Add Member] [Build Policy] [Adjudicate] [Disbursement]         |
|------------------------------------------------------------------|
| Claim Adjudication Lifecycle Stream                              |
|  [1. Pre-Auth 9] [2. Final Claim 5] [3. Payment 3] [4. Settled   |
|   41] [5. Rejected 2]                                            |
|------------------------------------------------------------------|
| Recent Active Claims Dossiers                       [View All >] |
|  Case & Claim No | Patient & Hospital | Stage & Status |         |
|  Claimed / Approved | [Review Case]                              |
|------------------------------------------------------------------|
```

- Header with the title, a sub-title naming the payer, and one primary action "Adjudicate Claims" that opens S2.
- Stat tiles in a four-column grid (two on small screens, one on phones).
- The quick operations and the lifecycle stream are cards with a titled header line and a grid of buttons or counters.
- The recent cases table collapses to stacked cards on small screens, each with the same fields and the "Review Case" button.

#### S1A. ACTIONS
1. Adjudicate Claims: open the Cases list S2.
2. Add Member: open Members S4.
3. Build Policy: open Policies S6.
4. Adjudicate: open Cases S2.
5. Disbursement: open Payments S10.
6. View All: open Cases S2.
7. Review Case: open the case desk S3 for that case (`/cases/:id`).
8. Sidebar: Overview, Cases, Members, Subscriptions, Policies, Procedures, FHIR Preview, Payments; the Organisation screen S12 is reached by its route [REF](../references/PAYERS.md#markers).
