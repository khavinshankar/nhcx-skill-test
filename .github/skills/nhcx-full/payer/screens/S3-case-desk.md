# S3. Case Desk Screen

#### S3R. ROUTE
`/cases/:id`

In the reference the desk is a pane the Cases list S2 swaps in for the selected case (`/cases?id=<case id>`) [REF](../references/PAYERS.md#markers); this skill gives it a route of its own so a case can be linked to. Every action posts to its own endpoint and the whole case comes back; the screen replaces what it shows with the server's copy rather than merging.

| Endpoint | Purpose |
|---|---|
| `GET cases/:id` | The case with its lines, documents, timeline and exchange routing slip |
| `PATCH cases/:id/line-items/:lineId` | One line's decision (S3.1) |
| `POST cases/:id/adjudicate` | Approve, reject or query the case (S3.2) |
| `POST cases/:id/documents` | File a document on the case by hand (S3.3) |
| `GET cases/:id/documents/:docId/file` | The bytes of a document that arrived inline (S3.3) |
| `GET cases/:id/forms` | The questionnaires the hospital answered, per submission |
| `GET cases/:id/exchange`, `GET cases/:id/exchange/:msgId` | The exchange log and one message with its bundle (S3.4) |
| `POST cases/:id/query/resend` | Send the open query again (S3.4) |
| `GET cases/:id/fhir?kind=` | What this payer would send now (S11) |
| `POST cases/:id/enhancement`, `.../cancel`, `.../query-response`, `.../discharge`, `.../claim`, `.../reprocess`, `.../scenario` | The lifecycle stand-ins (S3.6) [SANDBOX](../references/PAYERS.md#markers) |

Breadcrumb: Cases (S2) > `<claim number>`

#### S3D. DESCRIPTION
The one screen where a person decides. A case arrives filed by [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md) (a pre-authorisation), gains its final bill from [C5. Claim Submit](../callbacks/C5-claim-submit.md) (the claim), and every decision taken here goes back to the hospital through [A13. Adjudicate](../apis/A13-adjudicate.md): the verdict as a ClaimResponse ([A3. Pre-auth Answer](../apis/A3-preauth-answer.md) on the pre-authorisation thread, [A4. Claim Answer](../apis/A4-claim-answer.md) on the claim thread, [A9. Task Answer](../apis/A9-task-answer.md) on a reprocess thread), or a query as a CommunicationRequest ([A5. Query Request](../apis/A5-query-request.md)). Nothing is decided by rules: the case waits for a person, and the verdict that goes out is theirs.

**Header.** A "Back" button to S2, the claim number as the title (monospace), "Patient: `<name>` | Hospital: `<name>`", and on the right "Stage: `<stage>`" (settled green, rejected red, otherwise purple) and "| Status: `<adjudication status>`".

**Who may act.** Deciding a line or the case is an adjudicator's or an admin's; finance sees the desk read-only. Once a case reaches `payment`, `settled`, `rejected` or `cancelled` the numbers are fixed and every input is disabled: "This case has moved past adjudication and can no longer be decided" comes back from the server on any attempt [REF](../references/PAYERS.md#markers).

**Dossier cards**, in this order:

1. **Patient Demographics**: name, "`<age>` Yrs (`<gender>`)", "Member ID: `<member id>`"; "Minor Patient" flag and a guardian block ("Guardian: `<name>` (`<relation>`)", "Mobile: `<mobile>`") when the patient is a minor. The patient is this payer's member, not the name the hospital typed ([C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md)).
2. **Facility & Admission Summary**: hospital name and city; Admission date; Discharge (the discharge date, else the expected discharge, else `-`); "Ward: `<ward type>`", "Stay: `<n>` Days", "Type: `<discharge type or Normal Discharge>`".
3. **Treating Doctors & Clinical Team (n)**: Doctor Name & Role, Specialty, Qualification, HFR Registration ID (the practitioner's HPR id as the hospital sent it, [D22. case_doctor](../database/D22-case-doctor.md)). Empty: "No treating doctors listed".
4. **ICD-10 Clinical Diagnoses (n)**: ICD-10 Code, Diagnosis Description, Classification Type (`primary` or `secondary`, at most one primary, [D20. case_diagnosis](../database/D20-case-diagnosis.md)). Empty: "No diagnoses recorded".
5. **Surgical & Clinical Procedures (n)**, only when the case has any: Procedure Code, Procedure Name, Category, SNOMED CT, ICD-10-PCS (PCS10) ([D21. case_procedure](../database/D21-case-procedure.md)).
6. **Questionnaire Answers (n)**: what the hospital answered on the plan's forms ([F7. QuestionnaireResponse](../fhir/F7-questionnaireresponse.md)), per submission that carried any, newest first: "With the Pre-authorisation · received `<time>`" (or "With the Claim"), then each form's title and category ("Treatment guideline" for STG, "Information" for INF) and a two-column table of question and answer, an attachment shown with its title, content type and size. Empty: "The hospital answered no questionnaire on this case. A plan only asks for one on the packages it has a treatment guideline for."
7. **Submitted Proof Documents (n)**: S3.3.
8. **Line-Item Adjudication Workspace**: S3.1 and S3.2.
9. **NHCX Exchange**: S3.4, only for a case that came off the exchange.
10. **Audit Trail & History Log**: S3.5.

##### S3.1 Line items

The itemised bill, and the only place an approved rupee is decided ([D25. case_line_item](../database/D25-case-line-item.md)). Columns: Item Description (with the billed code underneath when the line came off the exchange), Ward / tier (the `Claim.item.modifier` a ward or ICU tier rode in on, shown as its display and code, `-` when none; its rate is already inside the claimed amount), Qty, Unit Cost, Claimed (₹), Approved (₹) as a number input, Decision as a select, and Line Item Remarks / Query as a text input.

Above the table: "Every line starts approved for the full claim, lower the approved figure to make it a partial approval, or switch the line to Query or Reject", and on the right "Approved vs Claimed" with the effective approved total over the claimed total.

**A line nobody has decided reads as approved in full** [REF](../references/PAYERS.md#markers): a `pending` line shows Approve with the claimed amount, so the desk opens with the bill allowed as claimed and the adjudicator works down. Approving the case is what records those lines (S3.2).

Decision select options: Approve, Query, Reject; "Partially Approved" appears, disabled, only on a line that is one. Partial is never picked: it is what an amount below the claim means.

**Committing a line.** Typing is local; the decision is sent when the field is left (blur), never per keystroke. The figure chooses the decision:

| Typed amount | Decision sent |
|---|---|
| equal to the claimed amount | `approved`, amount = claimed |
| 0 | `rejected`, amount 0 |
| between | `partially_approved`, that amount |
| above the claim or below 0 | clamped into range first |

The server reconciles the pair again ([A13. Adjudicate](../apis/A13-adjudicate.md)): `approved` always means the full claimed amount, `rejected` and `queried` mean zero, a partial at or above the claim becomes `approved` and at or below zero becomes `rejected`. Choosing Query with empty remarks is refused on the screen with "Enter what is being queried in the remarks column first." and on the server with "Say what is being queried, so the hospital knows what to send". Remarks alone are committed when they change. A refused commit puts the input back to what the line held.

Each commit appends a timeline event "Line Item Approved" (or Partially Approved, Rejected, Queried) reading "`<description>`, approved ₹x of ₹y claimed." and recomputes the case totals.

API: [A13. Adjudicate](../apis/A13-adjudicate.md)

##### S3.2 Decision

"Master Adjudicator Decision & Remarks": one textarea, then the buttons. What the verdict may be follows the lines beneath it:

| Lines | Allowed |
|---|---|
| any line `queried` | "Raise Dossier Query" and "Reject Case"; the note reads "A line item is under query, the dossier can be put to the hospital or refused, not approved." |
| every line `rejected` | "Reject Case" only; "Every line item was rejected, the dossier can only be rejected." |
| otherwise | "Approve & Advance Stage" (primary) and "Reject Case" (danger) |

Screen refusals before the confirm dialog: "A line item is still under query, raise the query or reject the case.", "Every line item was rejected, this case can only be rejected.", "Please enter query remarks in the Master Adjudicator Decision & Remarks field.", "Please enter rejection reason in the Master Adjudicator Decision & Remarks field." The server repeats the last two as "Record why, so the hospital knows what to do next" and the first two as "A line item is still under query, raise the query or reject the case" and "Every line item was rejected, this case can only be rejected".

**Confirm dialog**, one per action: "Confirm Claim Dossier Approval" with "Are you sure you want to APPROVE this claim dossier for ₹`<effective approved>`?" and the button "Yes, Approve Case"; "Confirm Claim Dossier Rejection" with "Are you sure you want to formally REJECT this claim dossier?" and "Yes, Reject Case"; "Confirm Dossier Query Dispatch" with "Are you sure you want to DISPATCH this dossier query to the provider hospital?" and "Yes, Dispatch Query". Each shows the remarks as typed, or "Case approved by Payer Officer." when empty on an approval.

**What each action does** ([A13. Adjudicate](../apis/A13-adjudicate.md)):

- Approve: every `pending` line becomes `approved` in full, the totals are recomputed, the case moves on (`preauth` to `claim`, `claim` to `payment`) with `adjudication_status = 'approved'`. Approving a claim debits the approved amount from the enrolment's wallet ([D6. subscription](../database/D6-subscription.md), [D8. wallet_entry](../database/D8-wallet-entry.md)); "There is not enough cover left on this policy" refuses it. The verdict goes out: [A3. Pre-auth Answer](../apis/A3-preauth-answer.md) on a pre-authorisation, [A4. Claim Answer](../apis/A4-claim-answer.md) on a claim, [A9. Task Answer](../apis/A9-task-answer.md) on a claim reopened at the hospital's asking. Toast: "Pre-Authorization approved! Advanced to Claim stage." or "Final Claim approved! Transferred to Payment Disbursement queue."
- Reject: stage `rejected`, status `rejected`; the verdict goes out with outcome error. Toast: "Claim dossier rejected".
- Query: the stage stays, status `queried`; a CommunicationRequest goes to the hospital ([A5. Query Request](../apis/A5-query-request.md)) and no ClaimResponse is sent, so the hospital's submission stays open with the question. Toast: "Query successfully raised and dispatched to hospital!"

Timeline events: "Pre-Authorization Approved", "Claim Approved for Disbursement", "Claim Rejected", "Additional Information Requested", each with the remarks.

API: [A3. Pre-auth Answer](../apis/A3-preauth-answer.md)

API: [A4. Claim Answer](../apis/A4-claim-answer.md)

API: [A5. Query Request](../apis/A5-query-request.md)

API: [A9. Task Answer](../apis/A9-task-answer.md)

##### S3.3 Documents

"Submitted Proof Documents (n)". Columns: Document Title, Type Code (the NHCX document code, [D3. document_type](../database/D3-document-type.md)), Stage (`preauth` or `claim`), Uploaded Date & Time, and an "Open" button. A document filed under a code this payer's taxonomy does not carry is filed as `ODN`, other document, with a timeline warning "Attachments Filed as Other" naming the codes ([C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md)). Empty: "No documents attached" with "The hospital has not uploaded any supporting documents yet."

**Open** shows the document in a near full-screen dialog titled with the document's title and "Uploaded at `<time>` | Phase: `<PHASE>`". A document whose bytes the server holds (`has_file`, [D24. case_document_file](../database/D24-case-document-file.md)) is fetched with the session token and shown inline, an image as an image and anything else in a frame, with a "Download (`<size>`)" link. A document that arrived as a bare URL shows "The hospital sent a link rather than the file; it opens on their host." and the link. One recorded by name only shows "This document was recorded by name only, the hospital's message carried no file body and no link (`<url>`)." A fetch failure shows the error in red; while loading, "Loading the document…".

**Filing by hand** (`POST cases/:id/documents`, no button in the reference [REF](../references/PAYERS.md#markers)): title, type code, phase (`preauth` or `claim`), URL and doc type (`image` or `pdf`) are all required: "Enter a document title", "Choose an NHCX document type", "A document needs a URL", "A document belongs to the pre-auth or the claim phase", "A document is an image or a PDF".

Data: [D23. case_document](../database/D23-case-document.md)

Data: [D24. case_document_file](../database/D24-case-document-file.md)

##### S3.4 Exchange log

"NHCX Exchange", with the hospital's participant code beside the title. Shown only for a case that came off the exchange (`exchange` on the case, [D19. case](../database/D19-case.md)).

Threads, one row each with the correlation id (copied on a click) and a chip; a reprocess thread is listed too while one is open ("Reprocess thread", `awaiting verdict`): "Pre-auth thread" (`answered` once the verdict went, else `awaiting verdict`), "Claim thread" (the same), "Query thread" (`awaiting reply`) while a query is open. While the case is `queried` and no query transaction is recorded, an amber line reads "The query has not reached the gateway. Send it so the hospital knows what is missing." and the header button reads "Send query"; otherwise "Resend query". Both post `query/resend` ([A5. Query Request](../apis/A5-query-request.md)) and toast "Query sent to `<hospital code>`".

Messages ([A15. Case Exchange Log](../apis/A15-case-exchange.md)), oldest first, each with a direction arrow (in blue, out green), a label, the time, the summary, and "from `<code>` · `<correlation>` · txn `<id>`" or "to ...":

| Kind | Label |
|---|---|
| `preauth` | Pre-authorisation received |
| `claimresponse` | Verdict sent |
| `claim` | Claim received |
| `communicationrequest` | Query sent |
| `communication` | Reply received |
| `paymentnotice` | Payment notice |
| `paymentreconciliation` | Reconciliation sent |
| `task` | Task |
| `status` | Status enquiry |
| `predetermination` | Predetermination |

Empty: "Nothing has gone over the wire yet." The log re-reads whenever the case changes hands, because a decision just sent a verdict. A message's bundle is opened on S11.

API: [A15. Case Exchange Log](../apis/A15-case-exchange.md)

Data: [D27. case_exchange_message](../database/D27-case-exchange-message.md)

##### S3.5 Timeline

"Audit Trail & History Log": every event on the case in insertion order ([D26. case_timeline](../database/D26-case-timeline.md)), each with a dot coloured by type (success green, error red, warning amber, info blue), the title, the time, the description and "By: `<actor>`". Actors are desk users, the hospital's participant code for what arrived off the exchange, and "Settlement Engine" for the settlement event.

##### S3.6 Lifecycle actions [SANDBOX](../references/PAYERS.md#markers)

Enhancement, cancellation, a query reply, the discharge, the claim and a reprocess are things a hospital does, and in a live deployment they arrive off the exchange ([C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md), [C7. Task Submit](../callbacks/C7-task-submit.md), [C9. Communication](../callbacks/C9-communication.md), [C5. Claim Submit](../callbacks/C5-claim-submit.md)). The reference exposes them on the API so every state a case can reach is reachable without a hospital, for tests and to correct a case whose message was lost [SANDBOX](../references/PAYERS.md#markers). No button on the desk calls them [REF](../references/PAYERS.md#markers); a target that wants them builds forms over these endpoints:

| Endpoint | Body | Refusals |
|---|---|---|
| `POST cases/:id/enhancement` | `reason` (required: "Say why more cover is needed, so the adjudicator can decide"), `line_items` (at least one), `documents` (phase defaults to `preauth`) | closed case: "This case has moved past adjudication and can no longer be decided" |
| `POST cases/:id/cancel` | `reason` ("Say why the pre-authorization is being withdrawn") | the same |
| `POST cases/:id/query-response` | `remarks` ("Say what is being sent in answer"), `documents` | "This case is not under query" |
| `POST cases/:id/discharge` | `discharge_date` ("Enter the discharge date"), `discharge_type` (Normal Discharge, LAMA, Transfer, Deceased, Pending Discharge: "Choose how the admission ended"), `remarks`, optional `line_items` and `documents` (phase `claim`) | |
| `POST cases/:id/claim` | `line_items` (at least one), `remarks`, `documents` | "Record the discharge before submitting the claim, until then the bill is an estimate" |
| `POST cases/:id/reprocess` | `reason` ("Say why the claim is being reopened"); adjudicator or admin only: "Only an adjudicator can reopen a decided claim" | "This case is still open, there is nothing to reopen" |
| `POST cases/:id/scenario` | `scenario`, one of the sandbox presets ([A19. Sandbox Scenarios](../apis/A19-sandbox-scenarios.md)) | "Choose one of the scenarios GET /api/scenarios lists" |

Line items on these carry `description`, `quantity` (above zero), `unit_cost` (not negative) and an optional `claimed_amount`; a missing or zero amount is quantity times unit cost. A claim's lines replace the pre-authorised estimate rather than adding to it. Reopening a claim returns the cover it drew to the wallet.

Data: [D19. case](../database/D19-case.md)

Data: [D20. case_diagnosis](../database/D20-case-diagnosis.md)

Data: [D21. case_procedure](../database/D21-case-procedure.md)

Data: [D22. case_doctor](../database/D22-case-doctor.md)

Data: [D25. case_line_item](../database/D25-case-line-item.md)

Data: [D26. case_timeline](../database/D26-case-timeline.md)

Data: [D27. case_exchange_message](../database/D27-case-exchange-message.md)

#### S3L. LAYOUT
The arrangement below is the reference desk's [REF](../references/PAYERS.md#markers): follow the target payer system's own screen conventions. What is required is in DESCRIPTION and ACTIONS: the cards, the columns, the decision rules, the messages and the actions.

```
|------------------------------------------------------------------|
| [< Back] | CL/26/0SE0000V9                 Stage: preauth        |
|          | Patient: Ramesh Kumar | Hospital: Apollo   | Status:  |
|          |                                              pending  |
|------------------------------------------------------------------|
| [Patient Demographics]          | [Facility & Admission Summary] |
|  Ramesh Kumar  36 Yrs (Male)    |  Apollo (Bengaluru)            |
|  Member ID: MRAJ2004001         |  Admission 2026-08-10          |
|                                 |  Ward | Stay 4 Days | Type     |
|------------------------------------------------------------------|
| [Treating Doctors & Clinical Team (1)]                           |
|  Doctor Name & Role | Specialty | Qualification | HFR ID         |
| [ICD-10 Clinical Diagnoses (1)]                                  |
|  ICD-10 Code | Diagnosis Description | Classification Type       |
| [Questionnaire Answers (5)]                                      |
| [Submitted Proof Documents (3)]                                  |
|  Document Title | Type Code | Stage | Uploaded | [Open]          |
|------------------------------------------------------------------|
| [Line-Item Adjudication Workspace]    Approved vs Claimed        |
|                                       ₹69,000 / ₹69,000          |
|  Item | Ward/tier | Qty | Unit | Claimed | [Approved] | [Decision|
|  v] | [Remarks_____]                                             |
|  Master Adjudicator Decision & Remarks                           |
|  [textarea______________________________________________________]|
|                [Raise Dossier Query] [Reject Case] [Approve &    |
|                                                  Advance Stage]  |
|------------------------------------------------------------------|
| [NHCX Exchange  <facility code>]              [Resend query]     |
|  Pre-auth thread  <correlation>            [awaiting verdict]    |
|  v Pre-authorisation received  2026-08-10 10:14                  |
|    Pre-auth CL/26/... for ₹69,000: 1 line(s)                     |
|------------------------------------------------------------------|
| [Audit Trail & History Log]                                      |
|  o Pre-authorisation Received   2026-08-10 10:14   By: <code>    |
|------------------------------------------------------------------|
```

- The header is a bar above the page body, not a card; the stage and status sit at its right.
- The demographics and admission cards share one row; every other card is full width in the order listed.
- The line-item table scrolls sideways on narrow screens; the approved input is a short number field and the decision a small select, both disabled when the case is closed or the user may not adjudicate.
- The decision block is a bordered panel inside the workspace card; buttons are right-aligned and the guidance note left-aligned.
- Confirm dialogs and the document viewer are modal; the viewer is near full-screen.

#### S3A. ACTIONS
1. Back: return to the Cases list S2.
2. Approved amount: type, then leave the field; the line is committed with the decision the figure implies.
3. Decision select: Approve, Query or Reject the line; Query needs remarks first.
4. Remarks: type, then leave the field; committed on its own when changed.
5. Raise Dossier Query: confirm, then query the case; the CommunicationRequest goes out ([A5. Query Request](../apis/A5-query-request.md)).
6. Reject Case: confirm, then reject; the verdict goes out.
7. Approve & Advance Stage: confirm, then approve; pending lines are recorded in full, the case moves on, a claim approval debits the wallet, and the verdict goes out.
8. Open (document): view the document inline, or follow its link.
9. Send query / Resend query: send the open query again ([A5. Query Request](../apis/A5-query-request.md)).
10. Timeline and exchange log: read only; a message opens on S11.
11. Lifecycle stand-ins (S3.6): forms the target may add over the endpoints listed [SANDBOX](../references/PAYERS.md#markers).
