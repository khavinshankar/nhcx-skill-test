# S11. Claim Submission Screen

#### S11R. ROUTE
claims/view/:caseid/claim

This is the Claim tab of the Claim Detail shell S6. Its route is `claims/view/:caseid/claim`. Every form posts to its own endpoint and redirects back to this tab with a flash message. A success message shows green. A failure shows red with the error text.

| Endpoint | Purpose |
|---|---|
| `POST claims/:caseid/discharge` | Record how the stay ended |
| `POST claims/:caseid/claim/documents` | Attach files against the discharge summary and the claim-stage codes (multipart) |
| `POST claims/:caseid/documents` with `stage=claim` | Attach any files for the claim (multipart) |
| `POST claims/:caseid/documents/:did/delete` | Remove a document |
| `POST claims/:caseid/forms` with `stage=claim` | Save one claim-stage form's answers (multipart) |
| `POST claims/:caseid/claim` | Send the claim, or a query answer (optional field `reply`) |
| `POST claims/:caseid/status` with `stage=claim` | Ask the payer where the claim stands |
| `POST claims/:caseid/reprocess` | Send a decided claim back for another look |
| `POST claims/:caseid/release` | Ask for the unpaid balance of a partly paid claim |

Breadcrumb: Claims (claims/list, S5) > `<claim number>`

#### S11D. DESCRIPTION
The claim is filed once the patient has left. The tab records the discharge, collects the documents and forms the payer deferred to the claim, and sends the claim. It then shows the payer's verdict, along with the claim's follow-up requests: status, reprocess and balance release.

**Discharge verification** is on the Verification tab, S18: once the admission is discharged that tab turns into the discharge verification ([A18. Biometric Authentication](../apis/A18-biometric-authentication.md), stage Discharge), and the fresh token it takes rides on the claim. The admission's token does not serve the claim, whatever its life. Without one, a payer that requires proof of presence gets the Discharge Consent form answered in the bundle instead.**When the claim can start.** The claim needs a pre-authorisation with status `approved` or `queried`. Until one exists, the tab shows a single card titled "Claim": "A claim goes in against an **approved** pre-authorisation, once the patient has left. Get the pre-authorisation answered on the previous tab first." A `partial` pre-authorisation does not open this tab.

Once open, the tab shows four cards:
1. Discharge
2. Documents for the claim
3. Forms for the claim (only when a form applies)
4. Claim

**Once the claim has been sent (its status is anything but `draft`), the Claim card moves to the top.** The payer's verdict is the first thing to read, and the rest is the record behind it.

**Polling.** Each load of S6 checks the claim while it is `submitting`, and any status, reprocess or release request still `asking`. S6's header shows "Refresh" while anything is awaited.

API: [A10. Transaction Related](../apis/A10-txn-related.md), [A11. Transaction Dispatch](../apis/A11-txn-dispatch.md) (poll)

Callback: [C6. Claim Reply](../callbacks/C6-claim-on-submit.md)

Callback: [C8. Enquiry Reply](../callbacks/C8-enquiry-on-submit.md)

Money shows as `₹12,345`. A missing value shows as `-`.

---

**Discharge card.** One form in a two-column grid:

| Field | Control | Rules / help |
|---|---|---|
| Discharge type (required) | Select, blank "Select": `normal` Normal discharge, `lama` LAMA, `dama` DAMA, `death` Death | "Normal discharge, LAMA, DAMA or death in hospital." |
| Stage (required) | Select, blank "Select": Before Surgery, During Surgery, After Surgery | "Whether that was before, during or after surgery." |
| Discharge date (required) | Date | |
| Surgery date | Date | "Leave blank for a conservative case." |
| Date and time of death | Date and time | "Required when the discharge type is death." |

**LAMA / DAMA rule.** When the type is LAMA or DAMA and the stage is Before Surgery or During Surgery, an amber badge "Claimed as LM100 only" appears [PAYER](../references/PAYERS.md#markers). It reads: "The payer accepts only **LM100** for a LAMA / DAMA case that ended before or during surgery, and disqualifies everything the pre-authorisation approved. The claim below quotes it in their place." The claim then quotes the single procedure `LM100` at the plan's rate, quantity the number of days admitted (admission to discharge, at least 1), in place of every pre-authorised line. The display name falls back to "LAMA / DAMA procedure", and the rate falls back to 0 when the plan has no such package.

"Save discharge" (primary, save icon) is hidden while the claim is `submitting`. The server refuses the save then too. Validation, each shown as a red flash:
- "The claim is with the payer; wait for its answer before changing the discharge."
- "Choose how the patient was discharged."
- "Choose whether that was before, during or after surgery."
- "Enter the discharge date."
- "The discharge date cannot be before the admission date."
- "The surgery date cannot be before the admission date."
- "The discharge date cannot be before the surgery date."
- "Enter the date and time of death." (type Death with no time of death)
- "Enter the time of death as well as the date." (a date with no time)

For any type other than Death, the death time is cleared. Success: "Discharge recorded." Saving opens the claim in `draft` when none exists. An `error` claim goes back to `draft`.

**Documents for the claim card.**

*Requirements form* (posts to `claims/:caseid/claim/documents`). The table has four columns: Code, Document (with the package code as a sub-line), Attached (a link, or "not attached yet"), and Choose a PDF (file input `req_<code>`).
- The first row is always `HDS` Hospital discharge summary.
- The other rows are the documents the payer deferred to the claim:
  - With an auth-requirements ruling, the ruling's requirements that are not due at pre-authorisation.
  - Without one, the package master's documents for the quoted packages that were not already attached at the pre-authorisation stage.

The note beside the "Attach chosen files" button reads "The discharge summary is always wanted; the rest are the requirements the payer's ruling deferred to this stage." When nothing else is listed and no summary is attached, it reads "Only the discharge summary is listed, run the authorisation-requirements check on the pre-authorisation tab to learn what else this payer wants with the claim."

Each code keeps one file, and a new file replaces the old one. The summary is filed under code and category `HDS` with the label "Hospital discharge summary". Other files are filed under their code at the claim stage. Errors: "Choose a PDF for at least one of them." and "That is not a document this claim was asked for." The S9 upload rules also apply: PDF, JPEG, PNG or WebP, at most 10 MB, not empty. A failure part way through adds " (N attached before the failure.)". Success: "N document(s) attached."

*Everything attached for the claim.* A table of the claim-stage documents. Columns: File (opens inline in a new tab), Filed as (label with code sub-line), Size, Uploaded, and a "Remove" button with the confirm "Remove this document from the claim?". Empty text: "Nothing beyond the requirements yet." Below it is the upload row: "Files (PDF or image)" (multiple, required), "Filed as" (the ruling's codes, then the common codes listed on S9, default `CD`), "Label", and "Attach". Hidden field `stage=claim`. Errors: "Choose a PDF or image to attach." plus the upload rules. Success: "N document(s) attached."

**Forms for the claim card.** The payer's questionnaires to answer for the claim leg (the rule is D12's). The card is left out when no form applies. The forms listed are:
- With an auth-requirements ruling, the questionnaires it names for the stage after pre-authorisation.
- The quoted packages' own forms (their standard treatment guideline checklists), on this leg as on the pre-authorisation, whether or not there is a ruling: PMJAY lists an STG requirement per stage on every benefit and its ruling never names the STG [PAYER](../references/PAYERS.md#markers).
- The policy's own forms, offered on this leg whether or not there is a ruling.
- Without a stage-Discharge token on the Verification tab (S18), the scheme's Discharge Consent form, even when nothing lists it; its question is an attachment (the signed declaration), so the desk uploads it here, and the claim is refused PAYR-1363 without it [PAYER](../references/PAYERS.md#markers).

Each form is one accordion item titled `<form title> - <answered>/<total> answered`, and several can be open at once. Inside it, the questions sit in a two-column grid. Each question uses the same typed controls and help text as S9. Every form posts multipart to `claims/:caseid/forms` with hidden `form_url` and `stage=claim`. Its own "Save answers" button sits right-aligned under the grid.

Saving follows the same rules as on S9:
- A blank answer clears the saved answer.
- A chosen file is attached at the claim stage, labelled with the question text.
- A file question left empty keeps its earlier file.

The flash reads "Answers saved.", adding " N file(s) attached." when files went, and the page returns to S11.

Answers are kept once per claim, form and question, and each answer is filed against the leg it was last saved on. The counter and prefilled values on this card show only the answers saved on the claim leg. Saving a policy form here moves that answer to the claim leg.

API: [A5. Claim Submit](../apis/A5-claim-submit.md) (answered forms)

**Claim card.** Status labels:

| Status | Label | Tone |
|---|---|---|
| `draft` | Draft | warning |
| `submitting` | Awaiting payer | info |
| `approved` | Approved | success |
| `partial` | Partially approved | warning |
| `queried` | Query raised | warning |
| `rejected` | Rejected | danger |
| `error` | Error | danger |

States of the card:

1. **Not sent** (not yet started, or `draft`). The card shows what the claim will quote. Table columns: Kind (chip: Procedure info, Implant warning), Item (display with code sub-line), Rate, Quantity, Amount. A bold "Total ₹X" line sits right-aligned under it. With a LAMA / DAMA discharge before or during surgery, the table shows only `LM100`. Empty text: "Nothing to claim, quote the line items on the pre-authorisation tab first." Header action: "Submit claim" (primary, send icon), with the confirm "Send this claim to the payer?".
2. **`submitting`.** The card reads "Claim submitted; awaiting the payer's `on_submit` reply. Use Refresh to check for it, or ask the payer where it stands." Once the payer has acknowledged it (workflow 25, or a `queued` ClaimResponse, C6) it reads "Acknowledged by the payer. The claim is under adjudication." Below it: Sent at, Claimed, Transaction, Correlation. It also shows the Communication pointer (S10) when there is an open query on the claim, the status enquiry rows, and the reprocess rows. Header action: "Ask where it stands" only.
3. **`error`.** The error text in red, or "The exchange failed.". Header action: the send button. A send the exchange refused is sent again as the same kind. An error the payer answered with (`ClaimResponse.error`, a `response.error` reply, a failed Task's reason) is shown line by line with its process notes and an "Open <title> (PDF)" link when the reply carries a `form`. It is shown, never obeyed: nothing is decided and the claim can be sent again.
4. **Decided or queried** (`approved`, `partial`, `rejected`, `queried`):
   - Three stat tiles: "Claimed"; "Approved" (green when `approved`, amber otherwise); "Status" (the label above).
   - Detail list: Disposition; Outcome (`<outcome> · <adjudication>`); Claimed under (the claim number sent); Settled at; Correlation; Sent as (button words of the last send); Our reply; and Submitted / eligible, when the payer gave an eligible amount.
   - The per-item verdict table, as on S9. Columns: Item, Status chip, Eligible, Eligible %, Deducted, The payer's note.
   - "What the payer says", the payer's query as a code block (S10, query note).
   - When `queried`, how to reply (below). Otherwise the Communication pointer, when an open query exists.
   - The status enquiry rows, the reprocess form, and the balance release form.
   - Header actions: "Ask where it stands", plus the send button when one applies. There is no send button while `queried`.

**Send kinds.** A send button appears only when the claim has a send left. Where the payer takes no resubmission, there is no button.

| Where the claim stands | Button label |
|---|---|
| Not sent / `draft` | Submit claim |
| `queried` | Answer the query (N) |
| `approved` / `partial` / `rejected` | Resubmit the claim (16); none for PMJAY [PAYER](../references/PAYERS.md#markers) |
| `error` | the label of the kind that failed |
| `submitting` | refused: "The claim is with the payer; wait for its answer before sending again." |

A decided PMJAY claim goes back only as a reprocess request [PAYER](../references/PAYERS.md#markers). A direct post there is refused with "The payer has decided this claim; it goes back for another look as a reprocess request, not as a claim sent again."

**Replying to a query** (status `queried`). The reply form depends on how the payer raises queries:
- *Query inside the payer's verdict* (`resubmit` mode, PMJAY, see [PAYERS.md](../references/PAYERS.md)) [PAYER](../references/PAYERS.md#markers). An inline form with a required textarea, "Reply to the payer's query". Help text: "Goes to the payer as the claim query detail, with everything attached and answered on this tab since the query." The small primary button "Answer the query (<workflow id>)" (151, or 161 under the sandbox override [SANDBOX](../references/PAYERS.md#markers)) posts to `claims/:caseid/claim` with `reply`. The question being answered is kept, so the card can still show it while the answer is out.
- *Query on a separate communication thread* (`communication` mode). Only the pointer to S10, with the button "Open the Communication tab". The claim is not submitted again.

**Submit validation**, in order, each shown as a red flash:
- The send-kind refusals above.
- On a query answer without text: "Write the reply to the payer's query before answering it."
- "Record how the patient was discharged before claiming."
- "A claim goes in against an approved pre-authorisation."
- "Set the facility's HFR ID and NHCX participant code under Settings before submitting."
- "Link the admitted patient before submitting."
- "Enter the admission date on the preauth draft."
- "Quote at least one ICD-10 diagnosis."
- "Add at least one doctor to the care team."
- "Add at least one line, the procedure being done."

**Submit call.** API: [A5. Claim Submit](../apis/A5-claim-submit.md) (claim, query answer, resubmission)

The claim becomes `submitting`, and the flash reads "Claim submitted to the payer."

**Reading the verdict.** Callback: [C6. Claim Reply](../callbacks/C6-claim-on-submit.md)

**Status enquiry.** "Ask where it stands" behaves as on S9, with `stage=claim`, and is hidden for PMJAY [PAYER](../references/PAYERS.md#markers). Its error when nothing has been sent is "The claim has not been submitted yet." Success: "Status enquiry sent to the payer."

API: [A6. Task Submit](../apis/A6-task-submit.md) (status)

Callback: [C8. Enquiry Reply](../callbacks/C8-enquiry-on-submit.md)

**Enquiry rows.** Each kind of request (status, reprocess, release) shows under its section in a table with three columns: Asked, The payer said, Answered. Newest is first, at most 5 rows.
- `asking`: chip "Asking, use Refresh" (info).
- `error`: chip "Failed" (danger), followed by the error.
- Otherwise, a chip with the answer: approved or reopened green; partial or queried amber; rejected, refused or not-found red; anything else info. The amount and a muted detail follow the chip.

**Reprocess form.** Shown when the claim is `rejected`, `partial` or `approved` and has not been paid in full (paid total below the claimed amount).

| Field | Control |
|---|---|
| Why (required) | Select: `claimrejected` Reprocess request due to claim rejected by payer; `partialpayment` Reprocess request due to partial payment by payer; `rejectiondisputed` Rejection disputed, additional evidence provided. Default `partialpayment` when anything was paid or the claim is `partial`, else `claimrejected` |
| Ask the payer to reprocess the claim | 2-row textarea. Help: "A Task coded reprocess under workflow 36. The payer reopens the claim for a person, and the new verdict arrives on the claim's own thread." [PAYER](../references/PAYERS.md#markers) |
| Evidence to send with it | One checkbox per document on the claim (label or filename, code muted). Help: "Each rides on the Task as a supportingDocument input." Shown only when documents exist |

Button: "Send reprocess request" (primary). The reprocess enquiry rows sit below it. Errors:
- "Only a claim the payer has decided can be sent back for reprocessing."
- "A claim that has been paid in full cannot be reprocessed."
- "Say why the claim should be looked at again."
- "Choose why the claim is being sent back." (a reason the payer's adapter does not allow)
- "That document is not on this claim."
- "Set the facility's HFR ID and NHCX participant code under Settings first."

Success: "Reprocess request sent to the payer."

API: [A6. Task Submit](../apis/A6-task-submit.md) (reprocess)

Callback: [C8. Enquiry Reply](../callbacks/C8-enquiry-on-submit.md)

The row reads `reopened` when the payer accepts, and the claim goes back to `submitting` and waits for the new verdict on its own thread. Otherwise it reads `refused`, with the payer's disposition or description as detail.

**Balance release form.** Shown when the claim is `approved` or `partial`, something has been paid, and a balance is still owed. The balance is the claimed amount minus the paid total.

| Field | Control |
|---|---|
| Balance to release (₹) (required) | Number, step 0.01, min 0.01, max the balance, prefilled with the balance. Help: "₹X paid of ₹Y." |
| Note to the payer | 2-row textarea. Help: "A Task coded release, reason partialpayment, under the arbitration workflow (36). The payer reopens the claim for the balance; the payment notice follows on the claim's own thread." [PAYER](../references/PAYERS.md#markers) |

Button: "Ask for the balance" (primary). The release enquiry rows sit below it. Errors:
- "Say how much of the claim is still owed." (blank, zero, or not a number)
- "Only a decided claim can have its balance asked for."
- "A claim that has been paid in full has no balance."

Success: "Balance release request sent to the payer."

API: [A6. Task Submit](../apis/A6-task-submit.md) (release)

Callback: [C8. Enquiry Reply](../callbacks/C8-enquiry-on-submit.md)

The money itself arrives as a payment notice (S12).

Data: [D9. claim](../database/D9-claim.md)

Data: [D11. claim_plan_benefit](../database/D11-claim-plan-benefit.md)

Data: [D12. claim_plan_form](../database/D12-claim-plan-form.md)

Data: [D15. claim_auth_requirement](../database/D15-claim-auth-requirement.md)

Data: [D16. claim_line](../database/D16-claim-line.md)

Data: [D17. claim_form_answer](../database/D17-claim-form-answer.md)

Data: [D20. claim_submission](../database/D20-claim-submission.md)

Data: [D21. claim_payment](../database/D21-claim-payment.md)

Data: [D23. claim_query](../database/D23-claim-query.md)

Data: [D28. claim_document](../database/D28-claim-document.md)

Data: [D29. claim_enquiry](../database/D29-claim-enquiry.md)

#### S11L. LAYOUT
The arrangement below is the reference implementation's [REF](../references/PAYERS.md#markers): follow the target HMIS's own screen conventions. What is required is in DESCRIPTION and ACTIONS: the fields, options, columns, statuses, messages and actions.


```
|------------------------------------------------------------------|
| Claims > NM-000123                                               |
| <Beneficiary name>   [NM-000123] [Claim: Partially approved]     |
|                      [Paid ₹40,000]                              |
| Next: [Ask for a reprocess]                                      |
|------------------------------------------------------------------|
| ... | Pre-authorisation | Communication | *Claim* | Payments     |
|------------------------------------------------------------------|
| [Card] Claim                             [(?) Ask where it stands]|
|  [Claimed ₹50,000]  [Approved ₹40,000]  [Status Partially appr.] |
|  Disposition  Outcome  Claimed under  Settled at  Correlation ...|
|  Item | Status | Eligible | Eligible % | Deducted | Payer's note |
|  Asked | The payer said | Answered                               |
|  Why [Reprocess request due to partial...v]  Ask the payer [___] |
|  Evidence: [ ] Discharge summary  HDS                            |
|                                        [Send reprocess request]  |
|  Balance to release (₹) [10000.00]   Note to the payer [______]  |
|                                          [Ask for the balance]   |
|------------------------------------------------------------------|
| [Card] Discharge                                                 |
|  Discharge type [v]            Stage [v]                         |
|  Discharge date [date]         Surgery date [date]               |
|  Date and time of death [datetime]                               |
|  [Claimed as LM100 only]  (LAMA / DAMA before or during surgery) |
|                                             [Save discharge]     |
|------------------------------------------------------------------|
| [Card] Documents for the claim                                   |
|  Code | Document | Attached | Choose a PDF                       |
|  HDS  | Hospital discharge summary | not attached yet | [file]   |
|  <note>                                  [Attach chosen files]   |
|  Everything attached for the claim                               |
|  File | Filed as | Size | Uploaded | [Remove]                    |
|  [Files...] [Filed as v] [Label____] [Attach]                    |
|------------------------------------------------------------------|
| [Card] Forms for the claim                                       |
|  > Authentication consent - 0/2 answered                         |
|------------------------------------------------------------------|
```

- Before the claim is sent, the order is Discharge, Documents for the claim, Forms for the claim, Claim. After it is sent, the Claim card comes first, as drawn.
- Stat tiles use two columns on small screens and three on large ones. Detail lists use three columns.
- The discharge and reprocess / release forms use a two-column grid. Their buttons are right-aligned.
- The upload row wraps on narrow screens.
- The Save discharge button disappears while the claim is with the payer.

#### S11A. ACTIONS
1. Save discharge: validate and record the discharge, then reload S11.
2. Attach chosen files: file one document per requirement (the summary under `HDS`), then reload S11.
3. Attach: file any number of claim-stage documents, then reload S11.
4. File links: open the document inline in a new browser tab.
5. Remove: confirm and delete the document. The redirect lands on the Pre-authorisation tab S9, not on S11.
6. Save answers: store one claim-stage form's answers and files, then reload S11.
7. Submit claim / Answer the query / Resubmit the claim: confirm (Submit claim only), validate, send the claim, and reload S11 with the card awaiting the payer.
8. Ask where it stands: send the status Task and reload S11.
9. Send reprocess request: send the reprocess Task and reload S11. The answer appears in the reprocess rows.
10. Ask for the balance: send the release Task and reload S11. The payment follows on S12.
11. Open the Communication tab: go to Communication S10.
12. Refresh (S6 header): reload S11, which polls the claim and every open request.
13. Next buttons (S6 header): go to the tab the case waits on, for example "Record the discharge", "File the claim", "Answer the claim query", "Ask for a reprocess", "Send the claim again", "With the payer; ask where it stands", or "Await the payment notice" (S12).
14. Breadcrumb "Claims": go to the Claim Master S5.
