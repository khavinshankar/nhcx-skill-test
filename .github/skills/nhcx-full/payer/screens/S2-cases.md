# S2. Cases Screen

#### S2R. ROUTE
`/cases`

| Endpoint | Purpose |
|---|---|
| `GET cases?stage=&search=&awaiting_payment=true&limit=&offset=` | The case list; collections answer `{"items": [...], "total": n}` |

Selecting a case opens the case desk S3, in the reference as `/cases?id=<case id>` on the same route [REF](../references/PAYERS.md#markers); this skill gives it the route `/cases/:id`.

Breadcrumb: Cases

#### S2D. DESCRIPTION
The list of every case this payer holds, whichever way it arrived: filed by a hospital over the exchange ([C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md), [C5. Claim Submit](../callbacks/C5-claim-submit.md)) or raised by hand on the desk (S3.6). One case is one episode from pre-authorisation to settlement; the pre-authorisation and the claim that follows it are two legs of the same case, not two rows ([D19. case](../database/D19-case.md)).

**Who sees what.** An account that works particular participant codes sees only the cases addressed to those codes (`exchange.recipient_code`); a case addressed elsewhere answers 404 to it, the same as one that does not exist. An account that lists no participants sees every case [SANDBOX](../references/PAYERS.md#markers). A single-payer deployment shows every case.

**Stage filter tabs**, with a count in brackets on each:

| Tab | Value | Label |
|---|---|---|
| all | (none) | All Cases |
| `preauth` | preauth | Pre-Auth Stage |
| `claim` | claim | Final Claims |
| `payment` | payment | Payment Queue |
| `settled` | settled | Settled Cases |
| `rejected` | rejected | Rejected Cases |

`cancelled` cases (a pre-authorisation the hospital withdrew, [C7. Task Submit](../callbacks/C7-task-submit.md)) appear under All Cases only [REF](../references/PAYERS.md#markers).

**Urgency filter**, a select: All Urgency Levels, Emergency, Urgent, Elective. The reference filters on the discharge type by mistake [REF](../references/PAYERS.md#markers); the required behaviour is a filter on the case's `urgency`.

**Search**, one text box. The server matches the claim number, the case id, the patient name, the hospital name and city, and a diagnosis code or description (`?search=`); the reference also filters the loaded page in the browser [REF](../references/PAYERS.md#markers).

**Awaiting payment.** `?awaiting_payment=true` narrows to approved cases with money still outstanding (`total_paid < total_approved`); this is the disbursement queue S10 reads, not a tab here.

**Case cards**, one per case:

- The claim number (monospace) with the correlation id of the thread the case arrived on under it (the claim's once there is one, the pre-authorisation's until then; copied on a click), and on the right the stage label (Pre-Auth Stage, Final Claim, Payment Queue, or the stage word) coloured settled green, rejected red, otherwise purple, with the adjudication status under it.
- The patient's name with a "Minor" flag when `patient.is_minor`, then "`<age>` Yrs (`<gender>`) | Member: `<member id>`".
- The hospital name and city, then "Admission: `<date>` | Stay: `<n>` Days (`<discharge type or Normal Discharge>`)".
- "Claimed / Approved": `₹` claimed, and the approved amount in brackets, green.
- An "Adjudicate" button that opens S3.

Adjudication statuses shown: `pending`, `approved`, `rejected`, `queried`, `cancelled` ([D19. case](../database/D19-case.md)).

Empty state: "No cases match" with "No dossier matches the current stage, urgency or search filters." and a "Clear filters" button.

**Live refresh.** The list repaints from the server's latest copy whenever a case changes (a decision on S3, a message off the exchange), the way the reference's case store publishes changes [REF](../references/PAYERS.md#markers).

API: [A13. Adjudicate](../apis/A13-adjudicate.md)

Callback: [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md)

Callback: [C5. Claim Submit](../callbacks/C5-claim-submit.md)

Data: [D19. case](../database/D19-case.md)

Data: [D25. case_line_item](../database/D25-case-line-item.md)

#### S2L. LAYOUT
The arrangement below is the reference desk's [REF](../references/PAYERS.md#markers): follow the target payer system's own screen conventions. What is required is in DESCRIPTION and ACTIONS: the filters, the fields on each row, the statuses and the actions.

```
|------------------------------------------------------------------|
| Cases                                                            |
| Adjudicate hospital pre-authorization and final claim dossiers   |
|------------------------------------------------------------------|
| [All Cases (58)] [Pre-Auth Stage (9)] [Final Claims (5)]         |
| [Payment Queue (3)] [Settled Cases (39)] [Rejected Cases (2)]    |
|                                          [All Urgency Levels v]  |
|------------------------------------------------------------------|
| [(search) ______________________________________________________]|
|------------------------------------------------------------------|
| +----------------------+ +----------------------+ +--------------+|
| | CL/26/0SE0000V9      | | CL/26/0SE0000VA      | |              ||
| |        PRE-AUTH STAGE| |        FINAL CLAIM   | |   ...        ||
| |               pending| |              approved| |              ||
| | (o) Ramesh Kumar     | | (o) Sita Devi  Minor | |              ||
| | 36 Yrs (Male) |      | |                      | |              ||
| | Member: MRAJ2004001  | |                      | |              ||
| | [] Apollo (Bengaluru)| |                      | |              ||
| | Admission: 2026-08-10| |                      | |              ||
| | Claimed / Approved   | |                      | |              ||
| | ₹69,000 (₹0)         | |                      | |              ||
| |        [Adjudicate]  | |        [Adjudicate]  | |              ||
| +----------------------+ +----------------------+ +--------------+|
|------------------------------------------------------------------|
```

- Filter tabs are pill buttons; the active one is filled. The urgency select sits at the right of the same row.
- Cards are in a three-column grid (two on medium, one on small screens), each with a divider between the header, the patient, the hospital and the money block.
- The "Adjudicate" button is outlined, small, with a table icon.

#### S2A. ACTIONS
1. Stage tab: filter the list to that stage; All Cases removes the stage filter. The counts on the tabs are for the whole list, not the search.
2. Urgency: filter to Emergency, Urgent or Elective.
3. Search: narrow the list as typed; the server search is by claim number, case id, patient, hospital or diagnosis.
4. Clear filters: reset the stage, the urgency and the search.
5. Adjudicate: open the case desk S3 for that case.
6. Back from S3 returns here with the filters as they were.
