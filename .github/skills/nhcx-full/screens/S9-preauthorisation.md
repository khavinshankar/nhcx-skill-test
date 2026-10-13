# S9. Pre-authorisation Screen

#### S9R. ROUTE
claims/view/:caseid/preauth

The Pre-authorisation tab of the Claim Detail shell S6 (route `claims/view/:caseid/preauth`). Every form on the tab posts to its own endpoint and redirects back to this tab with a flash message: green on success, red with the error text on failure.

| Endpoint | Purpose |
|---|---|
| `POST claims/:caseid/link` | Link the admitted patient (field `encounter_id`) |
| `POST claims/:caseid/unlink` | Detach the admission |
| `POST claims/:caseid/preauth` | Save the pre-authorisation draft (S4) |
| `POST claims/:caseid/forms` | Save one payer form's answers (multipart) |
| `POST claims/:caseid/documents/required` | Attach files against the payer's named document codes (multipart) |
| `POST claims/:caseid/documents` | Attach any files under a chosen code (multipart) |
| `GET claims/:caseid/documents/:did` | View a document inline |
| `POST claims/:caseid/documents/:did/delete` | Remove a document |
| `POST claims/:caseid/predetermination` | Ask the payer for a quote |
| `POST claims/:caseid/submit` | Send the pre-authorisation, an enhancement or a query answer (optional field `reply`) |
| `POST claims/:caseid/cancel` | Ask the payer to cancel (fields `reason`, `note`) |
| `POST claims/:caseid/status` | Ask the payer where the leg stands (field `stage=preauth`) |

Breadcrumb: Claims (claims/list, S5) > `<claim number>`

#### S9D. DESCRIPTION
The pre-authorisation dossier for one case, and the card that sends it and shows what the payer said.

**When the tab appears.** The tab sits between Validate and Communication in S6 and is always present. It does not wait for the payer's auth-requirements ruling: the package master already lists the documents and forms, and the ruling only narrows them when it arrives. PMJAY's sandbox rarely answers that check, so waiting on it would block the case [SANDBOX](../references/PAYERS.md#markers).

**What the pane shows depends on the case:**

1. No admission linked and the claim's eligibility status is not `eligible`: one card titled "Pre-authorisation" reading "The pre-authorisation opens once the payer has confirmed the policy is **eligible**. Run the coverage eligibility check on the Eligibility tab first."
2. No admission linked and eligible: only the card "Link the admitted patient", which matches current IPD stays by ABHA number. It is specified on S4.
3. Admission linked: a stack of cards in this order:
   1. Linked admission (S4)
   2. Pre-authorisation draft (S4)
   3. Forms the payer requires
   4. Supporting documents
   5. Predetermination
   6. Pre-authorisation

   **Once a pre-authorisation has been sent, the Pre-authorisation card moves to the top**, because the payer's answer is the first thing to read.

**Polling.** The page never reloads itself, because a reload would lose whatever is being typed on another tab. Instead, each load of S6 checks every exchange still open: the pre-authorisation while `submitting`, the cancel Task while `cancelling`, any predetermination `asking`, and any status enquiry `asking`. A failed check never breaks the page. While anything is awaited, S6's header shows a "Refresh" button that reloads the same tab.

API: [A10. Transaction Related](../apis/A10-txn-related.md), [A11. Transaction Dispatch](../apis/A11-txn-dispatch.md) (poll)

Callback: [C5. Pre-auth Reply](../callbacks/C5-preauth-on-submit.md)

Callback: [C7. Cancel Reply](../callbacks/C7-cancel-on-submit.md)

Callback: [C8. Enquiry Reply](../callbacks/C8-enquiry-on-submit.md)

---

**Linked admission, and the Pre-authorisation draft.** Both are specified on S4: the admission summary with its "Unlink" action, and the stay, diagnoses, treating doctor and case/estimate form saved with "Save preauth draft". This screen hosts them and does not describe them again.

**Forms the payer requires.** The payer's questionnaires for this procedure set, each shown as a form to answer. The card is left out when no form applies, and it needs the insurance plan (package master, S7) to have been fetched. The forms listed are:
- With the payer's auth-requirements ruling in: the questionnaires the ruling names for the pre-authorisation.
- In both cases: every questionnaire the package master attaches to the quoted packages, such as each package's treatment-guideline (STG) form. The ruling adds to these, it does not replace them, and the same package forms are offered again on the claim leg (S11) [PAYER](../references/PAYERS.md#markers).
- In both cases: the policy's own forms, added when not already listed. The same policy forms are offered again on the claim leg (S11).
- Without a stage-Preauth token on the Verification tab (S18): the scheme's Authentication Consent form, even when nothing lists it. Its question is an attachment (the signed declaration), so the desk uploads it here; the pre-authorisation is refused PAYR-1256 without it [PAYER](../references/PAYERS.md#markers).

Each form is one accordion item titled `<form title> - <answered>/<total> answered`. Several items can be open at once. Inside each item, the questions sit in a two-column grid. Each field is labelled with the question text, or with its question id when the question has no text. Each question renders by its declared answer type:

| Type | Control |
|---|---|
| `attachment` | File input (PDF or image); the attached file shows as a link with "attached" |
| `choice`, or any question with options | Select with blank "-", preselecting the payer's initial answer |
| `boolean` | Select Yes / No |
| `text` | Textarea |
| `date`, `dateTime`, `time`, `integer`, `decimal`, `quantity`, `url` | Matching HTML input type |
| anything else | Text input |

The help text under each field is the answer type ("File", "Choice", "Date & time", "Date", "Time", "Text", "Long text", "Yes / no", "Number", "Link"). An unknown type shows the payer's own spelling. A required question has the required marker on its label, but neither the browser nor the server enforces it.

Each form has its own "Save answers" button (primary, save icon), right-aligned under the grid. Every form posts as multipart to `claims/:caseid/forms` with hidden `form_url` and `stage=preauth`. Inputs are named `qa_<question id>`. How the post is handled:
- Each answer is kept per form and question, filed against the leg it was saved on.
- A blank answer clears the saved answer.
- A chosen file is attached to the claim as a document at the preauth stage, labelled with the question text. The answer points to that document.
- A file question left without a new file is ignored, so the file already given stays attached.
- The upload errors listed under Supporting documents apply.

The flash reads "Answers saved.", with " N file(s) attached." added when files went up, and the page returns to S9.

API: [A4. Pre-auth Submit](../apis/A4-preauth-submit.md) (answered forms)

**Supporting documents card.**

*Documents the payer named.* This block appears only when there are any. With a ruling, they are the ruling's document requirements due at pre-authorisation. Without one, they are every document the package master names for the quoted packages (codes other than `STG` [PAYER](../references/PAYERS.md#markers)). Table columns: Code, Document (display, with the package code as a sub-line), Attached (link to the file, or "not attached yet"), Choose a PDF (a file input named `req_<code>`). Under the table: "Named by the payer's authorisation-requirements ruling for this procedure set. Re-choosing a file replaces what is attached for that code." and the button "Attach chosen files". Only one file is kept per code; a new one replaces the old. Fields left empty are skipped. Errors: "Choose a PDF for at least one of them." and "That is not a document this pre-authorisation was asked for."

*Everything attached.* Table columns: File (opens inline in a new tab), Filed as (label, with the code as a sub-line), Type (PDF, JPEG image, PNG image, WebP image), Size ("x.x MB", or whole KB with a 1 KB minimum), Uploaded, and a "Remove" button that confirms "Remove this document from the claim?" and flashes "Document removed." Empty text: "No documents attached yet. The payer expects the admission note and the beneficiary's ID as a minimum." [PAYER](../references/PAYERS.md#markers)

*Upload row.* "Files (PDF or image)" (multiple, required), "Filed as", "Label", and the button "Attach". The "Filed as" select lists the codes the ruling named first, then the common codes below [PAYER](../references/PAYERS.md#markers). Each option reads as the code, a dash, and the label. `CD` is selected by default.

| Code | Label |
|---|---|
| CD | Clinical document (case sheet, notes) |
| HDS | Hospital discharge summary |
| DIA | Diagnostic & laboratory reports |
| RAD | Radiology / scan reports |
| PRE | Doctor's prescription notes |
| CER | Medical certificate / referral |
| EST | Cost estimate |
| MB | Medical & pharmacy bills |
| INV | Final hospital invoice |
| OTR | Operation theatre notes |
| ICU | ICU chart |
| IMP | Implant invoice & sticker |
| POI | Proof of identity |
| KYC | KYC / bank proof |
| FCF | Filled claim form |
| PAU | Pre-authorisation approval letter |
| ODN | Other document |

Upload rules for both forms: allowed types are PDF, JPEG, PNG and WebP; a file may be at most 10 MB [REF](../references/PAYERS.md#markers); empty files are refused. The messages are "Choose a PDF or image to attach.", "Only JPEG image, PDF, PNG image, WebP image files can be attached.", "That file is empty." and "A document may be at most 10 MB." A failure part way through reports how many had already gone up, for example " (2 of 3 attached before the failure.)". Success: "N document(s) attached." Documents are filed at stage `preauth`.

**Predetermination card.** This asks the payer to price the dossier without committing anyone.

| State | Body | Header action |
|---|---|---|
| Never asked | "The same bundle can go first as a `predetermination`: the payer prices it at once and answers with what the policy would allow and what it would cut. It binds nobody and opens no case." | "Ask for a quote" (no confirm) |
| `asking` | "Sent; awaiting the payer's quote. Use Refresh to check for it." then Sent at, Requested, Transaction, Correlation | none |
| `error` | The error message in red, or "The exchange failed." | "Ask again" |
| `answered` | Two stat tiles, "Requested" and "Would be allowed" (green when outcome is `complete`, amber otherwise); then Outcome (`<outcome> · <adjudication>`), Disposition, Quoted at, Quotes asked; then the muted line "A quote binds nobody: the pre-authorisation below is what commits the payer." | "Ask again" |

"Ask again" confirms "Send the dossier to the payer as a predetermination?". Errors: "Ask for a quote only after the payer has confirmed the policy is eligible." and "A quote is already with the payer; wait for its answer before asking again.". The dossier checks listed under Submit also apply. Success: "Predetermination sent to the payer."

API: [A4. Pre-auth Submit](../apis/A4-preauth-submit.md) (predetermination)

---

**Pre-authorisation card (the submit card).** Money shows as `₹12,345` and missing values as `-`. Status labels:

| Status | Label | Tone |
|---|---|---|
| `submitting` | Awaiting payer | info |
| `approved` | Approved | success |
| `partial` | Partially approved | warning |
| `queried` | Query raised | warning |
| `rejected` | Rejected | danger |
| `cancelling` | Cancelling | warning |
| `cancelled` | Cancelled | danger |
| `error` | Error | danger |

States of the card:

1. **Not sent.** "Everything above goes to the payer as one FHIR Claim bundle: the beneficiary, the admission, the diagnoses, the care team, the N quoted line(s) at ₹X, the attached documents and the answered forms." Header action: "Submit to payer" (primary, no confirm). **Until the S4 draft has been saved** (D9 `preauth_saved_at` null) the button is disabled with the help text "Save the preauth draft first", and a direct post is refused with the same words: the draft is what writes the diagnoses, care team and lines, so sending before it is saved met A4's "Quote at least one ICD-10 diagnosis." with a misleading cause.
2. **`submitting`.** "Submitted; awaiting the payer's `on_submit` reply. Use Refresh to check for it, or ask the payer where it stands." Once the payer has acknowledged the send (workflow 20, or a `queued` ClaimResponse, C5) the line reads "Acknowledged by the payer. The pre-authorisation is under adjudication." and the acknowledgement's workflow id is shown beside it. Then Sent at, Requested, Transaction, Correlation; the Communication pointer (S10) when the payer has an open query on this leg; the status enquiry rows; and the cancel form. Header action: "Ask where it stands" only. There is no send button while the pre-authorisation is with the payer.
3. **`cancelling`.** "Cancellation sent to the payer; awaiting its answer to the Task. Use Refresh to check for it." Then Reason (in words), Note, Sent at, Transaction, Correlation.
4. **`cancelled`.** "The payer accepted the cancellation; this pre-authorisation is withdrawn." If the claim number was retired, it adds: "The payer holds **`<old number>`** against the withdrawn pre-authorisation, so the episode carries on as **`<new number>`**, anything sent under the old number would be a duplicate of a cancelled case." Then Reason, Note, Withdrawn under, Pre-auth reference, Cancelled at, Disposition. Header action: "Submit to payer" with the confirm "Send this pre-authorisation to the payer?" (a fresh pre-authorisation).
5. **`error`.** The error text in red, or "The exchange failed.". Header action: the send button, labelled for the kind of send that failed. An error the payer answered with (`ClaimResponse.error`, a `response.error` reply, a failed Task's reason) is shown here line by line with its process notes, and an "Open <title> (PDF)" link when the reply carries a `form`. It is shown, never obeyed: nothing is decided, nothing else on the case is blocked, and the send can be made again.
6. **Decided or queried** (`approved`, `partial`, `rejected`, `queried`):
   - Three stat tiles: "Requested"; "Approved" (green when `approved`, amber otherwise); "Pre-auth reference".
   - Detail list: Status, Disposition, Outcome (`<outcome> · <adjudication>`, because the outcome alone does not say what happened), Settled at, Correlation, Enhancements (round count or `-`), Sent as (the button words of the last send, such as "Answer the query (19)" [PAYER](../references/PAYERS.md#markers)), Our reply, and Case stands at (the eligible amount, when the payer gave one).
   - "What the payer said", when the reply carries any: its `ClaimResponse.error` entries in the danger colour, its process notes, and an "Open <title> (PDF)" link for a `form` attachment, opened in a new tab.
   - The per-item verdict table, when the payer ruled per item. Columns: Item (sequence), Status (a chip: approved green, queried amber, rejected red, pending info), Eligible, Eligible %, Deducted (amount plus the deduction reason, muted), and The payer's note (with `|` shown as ` · `, cut to 240 characters).
   - The enhancement block (below).
   - "What the payer says": the payer's query text as a code block (see S10, query note).
   - How to reply (below), the status enquiry rows, and the cancel form.
   - Header actions: "Ask where it stands", plus a send button. With lines added since the decision, the button is "Submit enhancement (₹X, workflow 13)" [PAYER](../references/PAYERS.md#markers). On `rejected` it is "Submit to payer", which starts a fresh pre-authorisation. There is no send button on `approved` or `partial` with nothing added, and none on `queried`.

**Send kinds.**

| Where the pre-auth stands | Button label |
|---|---|
| Not sent, `cancelled`, `error`, `rejected` | Submit to payer |
| `queried` | Answer the query (19) [PAYER](../references/PAYERS.md#markers) |
| `approved` / `partial` with lines added | Submit enhancement (₹X, workflow 13) [PAYER](../references/PAYERS.md#markers) |
| `queried` after an enhancement | Answer the enhancement query (131) [PAYER](../references/PAYERS.md#markers) |
| `approved` / `partial`, nothing added | refused: "The pre-authorisation is already decided; add a line to ask for an enhancement." |
| `submitting` / `cancelling` | refused: "The pre-authorisation is with the payer; wait for its answer before sending again." |

**Submit validation**, in order, each shown as a red flash:
- "Save the preauth draft first" (first send only, `preauth_saved_at` null)
- "Submit a preauth only after the payer has confirmed the policy is eligible."
- The send-kind refusals above.
- On a query answer with no reply text: "Write the reply to the payer's query before answering it."
- "Set the facility's HFR ID and NHCX participant code under Settings before submitting."
- "Link the admitted patient before submitting."
- "Enter the admission date on the preauth draft."
- "Quote at least one ICD-10 diagnosis."
- "Add at least one doctor to the care team."
- "Add at least one line, the procedure being done."

**Submit call.** API: [A2. Coverage Eligibility Check](../apis/A2-coverage-eligibility-check.md) (auth-requirements, when not yet ruled)

API: [A4. Pre-auth Submit](../apis/A4-preauth-submit.md) (pre-authorisation, enhancement, query answer)

The leg becomes `submitting` and the flash reads "Pre-authorisation submitted to the payer." On failure the error flashes.

**Reading the reply.** Callback: [C5. Pre-auth Reply](../callbacks/C5-preauth-on-submit.md)

**Enhancement.** After an `approved` or `partial` decision, any line whose code was not in the last bundle sent counts as added. The card shows an amber badge "Enhancement pending: N new line(s), ₹X". Below it is a list of each added line with quantity and amount, and the muted line "Added since the payer decided. Sending the enhancement asks for these against the same pre-authorisation." The button confirms "Send the added lines to the payer as an enhancement of this pre-authorisation?". It keeps the pre-auth reference and counts the round in Enhancements.

**Replying to a query** (status `queried`). The reply depends on how the payer asks:
- *Payer queries inside its reply* (PMJAY, query mode `resubmit`, see [PAYERS.md](../references/PAYERS.md)) [PAYER](../references/PAYERS.md#markers): an inline form with the required textarea "Reply to the payer's query". Its help text is "Goes to the payer as the claim query detail, with everything attached and answered on this tab since the query." The small primary button, labelled with the send kind, posts to `claims/:caseid/submit` with `reply`.
- *Payer asks on a separate communication thread* (query mode `communication`): no resubmit form. The Communication pointer reads "`<payer name>` asks for more by CommunicationRequest and takes the answer as a Communication on that thread. A question from it arrives on the Communication tab; this leg is not submitted again to answer it." with the button "Open the Communication tab" (S10).

**Cancel form.** Shown while the status is `submitting`, `approved`, `partial` or `queried`. Not shown after a rejection, and never twice. It is a single row:
- "Cancel because" select, blank "Select a reason":

| Value | Label |
|---|---|
| `treatmentplanchanged` | Treatment plan changed during hospitalization |
| `patientrequest` | Patient requested cancellation |
| `financialconstraints` | Financial constraints |
| `alternativetreatment` | Alternative treatment chosen |
| `duplicateclaim` | Duplicate claim / preauth |
| `administrativeerror` | Administrative error |
| `other` | Other reason |

- "Note" text input, at least 18rem wide.
- Danger button "Cancel pre-authorisation". The browser confirms "Ask the payer to cancel this pre-authorisation?".

Errors: "There is no pre-authorisation to cancel.", "A pre-authorisation that is `<status label, lower case>` cannot be cancelled.", "Choose why the pre-authorisation is being cancelled.", and, when the reason is Other with no note, "Describe the reason, with “Other reason” the note is the only thing the payer can read." Success: "Cancellation sent to the payer."

API: [A6. Task Submit](../apis/A6-task-submit.md) (cancel)

Callback: [C7. Cancel Reply](../callbacks/C7-cancel-on-submit.md)

The leg goes to `cancelling`. On acceptance the status becomes `cancelled`, **the claim number is retired, and the case continues under a freshly minted number** [REF](../references/PAYERS.md#markers). The old number stays on the pre-auth as "Withdrawn under". On refusal the status returns to `approved` with "The payer did not accept the cancellation." recorded.

**Status enquiry ("Ask where it stands").** The button is shown only for payers that answer a status Task. PMJAY does not (see [PAYERS.md](../references/PAYERS.md)) [PAYER](../references/PAYERS.md#markers), so the button is hidden, and a direct post fails with "`<payer name>` answers no status enquiry over NHCX; read where the case stands on its own desk, and the verdict arrives on this thread." Other errors: "No pre-authorisation has been sent yet." Success: "Status enquiry sent to the payer."

API: [A6. Task Submit](../apis/A6-task-submit.md) (status)

Callback: [C8. Enquiry Reply](../callbacks/C8-enquiry-on-submit.md)

Answers show in a table under the card, newest first, at most 5. Columns are Asked, The payer said, and Answered:
- `asking`: chip "Asking, use Refresh" (info).
- `error`: chip "Failed" (danger) followed by the error.
- Otherwise a chip with the answer: approved or reopened green; partial or queried amber; rejected, refused or not-found red; anything else info. The chip is followed by the amount and a muted detail (stage, outcome, total approved, total paid).

Reprocess and balance release apply to the claim, not the pre-authorisation. They are on S11.

Data: [D9. claim](../database/D9-claim.md)

Data: [D11. claim_plan_benefit](../database/D11-claim-plan-benefit.md)

Data: [D12. claim_plan_form](../database/D12-claim-plan-form.md)

Data: [D15. claim_auth_requirement](../database/D15-claim-auth-requirement.md)

Data: [D16. claim_line](../database/D16-claim-line.md)

Data: [D17. claim_form_answer](../database/D17-claim-form-answer.md)

Data: [D18. claim_preauth](../database/D18-claim-preauth.md)

Data: [D19. claim_predetermination](../database/D19-claim-predetermination.md)

Data: [D23. claim_query](../database/D23-claim-query.md)

Data: [D28. claim_document](../database/D28-claim-document.md)

Data: [D29. claim_enquiry](../database/D29-claim-enquiry.md)

Data: [D30. counter](../database/D30-counter.md)

#### S9L. LAYOUT
The arrangement below is the reference implementation's [REF](../references/PAYERS.md#markers): follow the target HMIS's own screen conventions. What is required is in DESCRIPTION and ACTIONS: the fields, options, columns, statuses, messages and actions.


```
|------------------------------------------------------------------|
| Claims > NM-000123                                               |
| <Beneficiary name>     [NM-000123] [Pre-authorisation: Approved] |
|                        [1 query awaiting reply] [Refresh]        |
| Next: [Send the enhancement (1 added)]                           |
|------------------------------------------------------------------|
| Eligibility | Insurance plan | Line items | Validate |           |
| *Pre-authorisation* | Communication | Claim | Payments           |
|------------------------------------------------------------------|
| [Card] Pre-authorisation     [(?) Ask where it stands] [(>) Submit|
|                                        enhancement (₹X, wf 13)]  |
|  [Requested ₹X]   [Approved ₹Y]   [Pre-auth reference ABC123]    |
|  Status  Disposition  Outcome  Settled at  Correlation ...       |
|  Item | Status | Eligible | Eligible % | Deducted | Payer's note |
|  [Enhancement pending: 1 new line(s), ₹Z]                        |
|  What the payer says: [code block]                               |
|  Asked | The payer said | Answered                               |
|  Cancel because [Select v]  Note [_______]  [Cancel pre-auth]    |
|------------------------------------------------------------------|
| [Card] Linked admission                              [Unlink]    |
|  Patient  MRN  Admission  Ward / bed  Admitted  Consultant       |
|------------------------------------------------------------------|
| [Card] Pre-authorisation draft  (S4)                             |
|------------------------------------------------------------------|
| [Card] Forms the payer requires                                  |
|  > Treatment guideline - 3/5 answered                            |
|------------------------------------------------------------------|
| [Card] Supporting documents                                      |
|  Code | Document | Attached | Choose a PDF      [Attach chosen]  |
|  File | Filed as | Type | Size | Uploaded | [Remove]             |
|  [Files...] [Filed as v] [Label____] [Attach]                    |
|------------------------------------------------------------------|
| [Card] Predetermination                          [Ask again]     |
|  [Requested ₹X]  [Would be allowed ₹Y]                           |
|------------------------------------------------------------------|
```

- Before anything is sent, the Pre-authorisation card sits last. Once a pre-authorisation exists it moves to the top, as drawn.
- Stat tiles sit in a grid: two columns on small screens, three on large (two for the predetermination).
- Detail lists are three columns (two on the predetermination quote).
- Header actions sit in the card header, right-aligned. Send buttons are primary with a send icon. The cancel button is the danger style.
- The cancel form, the upload row and the "Filed as" field are single wrapping rows with labelled fields aligned to the button.
- Card order when nothing is linked: a single card, either "Pre-authorisation" (not eligible) or "Link the admitted patient".

#### S9A. ACTIONS
1. Link / Unlink / Register patient / New admission and the admission links: see S4. Each reloads S9.
2. Save preauth draft: see S4. Reloads S9.
3. Save answers: store one form's answers and files, then reload S9.
4. Attach chosen files: attach one file per payer code and reload S9.
5. Attach: attach any number of files under the chosen code and label, then reload S9.
6. File link: open the document inline in a new browser tab.
7. Remove: confirm and delete the document, then reload S9.
8. Ask for a quote / Ask again: send the predetermination and reload S9 with the card awaiting.
9. Submit to payer / Submit enhancement / Answer the query: validate, send the pre-authorisation bundle and reload S9 with the card awaiting the payer.
10. Cancel pre-authorisation: confirm, send the cancel Task and reload S9 in `cancelling`.
11. Ask where it stands: send the status Task and reload S9. The answer appears in the enquiry rows.
12. Open the Communication tab: go to Communication S10.
13. Refresh (S6 header): reload S9, which polls every exchange still open.
14. Next buttons (S6 header): go to the tab the case is waiting on, for example "Send the pre-authorisation", "Answer the query", "Send a fresh pre-authorisation", "Send the enhancement (N added)", "With the payer; ask where it stands", "Record the discharge" or "File the claim" (S11).
15. Breadcrumb "Claims": go to the Claim Master S5.
