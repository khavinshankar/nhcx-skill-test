# S10. Communication Screen

#### S10R. ROUTE
claims/view/:caseid/communication

This is the Communication tab of the Claim Detail shell S6. Its route is `claims/view/:caseid/communication`.

| Endpoint | Purpose |
|---|---|
| `POST claims/:caseid/queries/:qid/reply` | Answer one payer query (multipart) |
| `POST claims/:caseid/queries/:qid/acknowledge` | Send a notification's acknowledgement again |

Breadcrumb: Claims (claims/list, S5) > `<claim number>`

#### S10D. DESCRIPTION
Everything the payer has said on this case outside a verdict, on both legs, and the way to answer it. The messages are its questions (queries), its notifications, and its notes. Each is one row, newest first. The tab shows two cards: one for the pre-authorisation leg and one for the claim leg. Both are titled "Payer queries". A card appears only when its leg has at least one message.

**Two ways a payer asks for more.** Each payer's adapter has a query mode:

| | `resubmit` (PMJAY, see [PAYERS.md](../references/PAYERS.md)) [PAYER](../references/PAYERS.md#markers) | `communication` (IRDAI payers, generic NHCX) |
|---|---|---|
| How the question arrives | Inside the payer's verdict on the leg's own thread, with status `queried` | A separate payer message, on a new thread the payer starts |
| How it is answered | The leg is submitted again with the reply, from S9 or S11 | A reply, from this tab |
| What a separate payer message from this payer is | Always a notification | A query or a notification |

**Empty state.** When the payer has sent nothing yet, a single card titled "Communication" reads "Nothing from the payer yet. `<adapter name>` asks for more ..." and then one of two endings:
- `communication` mode: "as a `CommunicationRequest` on a thread of its own, answered here with a `Communication` on that thread. Its notifications (a turnaround time query, a grievance, a wallet or policy change) are acknowledged the moment they land and kept here."
- `resubmit` mode: "inside the `ClaimResponse`, answered by submitting the leg again, with what was missing, from the Pre-authorisation or Claim tab. What it sends as a `CommunicationRequest` is a notification, acknowledged the moment it lands and kept here."

Both endings continue: "Questions, answers and notes on both the pre-authorisation and the claim collect here."

**Message kinds and statuses.**

| Status | Chip | Tone |
|---|---|---|
| `open` | Awaiting our reply | warning |
| `answered` | Answered | success |
| `acknowledged` | Acknowledged | success |
| `noted` | Noted | info |
| `error` | Reply failed | danger |

Reason codes are shown in words: `tatquery` Turnaround time query, `grievance` Grievance, `walletupdate` Wallet or benefit update, `policychange` Policy change, `additionalinfo` Additional information request, `claimarbitration` Claim arbitration intimation (the misspelling `claimArbitartion` is accepted), `questionnaire` Questionnaire, `query` Query [PAYER](../references/PAYERS.md#markers). An unknown code is shown as the payer spelled it.

Each message is one accordion item (several can be open at once):

**1. Open query** (kind `query`, status `open` or `error`). Title: "Query raised `<date>` - awaiting our reply".
- A four-column detail list: Received, From (sender participant code), About (the payer's claim number), Status chip.
- "What the payer asked": a bullet list, one line per thing asked. When the payer asked nothing specific, it shows "The payer asked for more without saying what."
- When a reply failed, a red line with the error followed by "Nothing reached the payer, send it again."
- The reply form, multipart:
  - "Reply": a 4-row textarea named `text`, prefilled with the last reply attempted.
  - "Send documents already on the claim": one checkbox per document on the claim (`document_ids`). Each shows the label or filename, then its code (or `-`) and stage, muted. Help: "Each ticked file rides on the reply as a contentAttachment under its own code." Shown only when the claim holds documents.
  - "Documents the payer named": shown when the payer's ruling (or package master) named documents for this leg. A table of Code, Document (with package code sub-line) and Choose a PDF (file input `req_<code>`). Help: "Each file is filed and sent under the payer's own code, so the reply quotes it back."
  - "Attach anything else": "Add files (PDF or image)" (multiple), "Filed as" (the same code list as S9, default `CD`), and "Label". Help: "Any number of files. They are kept on the claim as well as sent, choose the payer's code where it named one."
  - The primary button "Send reply to payer".

**2. Answered query.** Title: "Query answered `<date>`". The same detail list, then "What the payer asked", "Our reply" (a code block, or `-`), "Attached" (links to each file that went, shown when any did), and Sent at, Transaction, Thread (the reply's correlation id).

**3. Notification** (kind `notification`). Title: "`<reason in words>` `<date>`, acknowledged" or "..., not yet acknowledged".
- A five-column detail list: Received, From, About, Reason, and Status. The Status chip reads "Acknowledged" (success), "Acknowledgement failed" (danger) or "Awaiting acknowledgement" (warning).
- "What the payer says": the lines, or "The payer sent no text with it.".
- A muted line: "A notification is kept on the case and acknowledged to the payer; the case's status is not changed by it and nothing here is answered."
- Once acknowledged: Acknowledged at, Transaction, Thread.
- Otherwise: the red error, if any, followed by "The payer has not heard that it was seen; send it again.", and the primary button "Send the acknowledgement".

**4. Note** (a plain message from the payer). Title: "Note from the payer `<date>`". A detail list of Received, From, About, and Status chip "Noted" (info). Then "What the payer says" and the muted line "A note from the payer is kept on the case and read; nothing goes back and nothing is held up by it." A note has no action.

**Answering a query.** The server checks, in order, each error returned as a red flash:
- "That query is not on this claim."
- "That message is not a question: a notification is acknowledged and a note is read, neither takes an answer."
- New files are filed on the claim first, at the queried leg's stage. Files chosen against a named code carry that code. General files share the chosen code and label. The upload errors from S9 apply ("Only JPEG image, PDF, PNG image, WebP image files can be attached.", "That file is empty.", "A document may be at most 10 MB."). One bad file refuses the whole reply before anything is sent.
- "Set the facility's HFR ID and NHCX participant code under Settings before answering a query."
- "Write a reply or attach a document, an empty answer tells the payer nothing."
- "One of the chosen documents is not on this claim."

API: [A7. Communication Reply](../apis/A7-communication-on-request.md) (reply)

On success the query becomes `answered` and shows the reply, the documents sent, and the reply's transaction and thread. The flash reads "Reply sent to the payer." and adds " Sent with N document(s) from the claim and M new document(s)." when files went. On failure the query becomes `error` with the message, the text is kept for the next try, and the error flashes. After a reply the case's stage is recomputed, so it is no longer `queried`. The leg itself waits for the payer's next verdict on its own thread (S9 or S11).

**Acknowledging a notification.** A notification is acknowledged automatically the moment it lands. The button on this tab is only for re-sending after a failure. Errors: "That message is not on this claim." and "Only a notification is acknowledged; a query is answered from the communication tab." Success: "Acknowledgement sent to the payer."

API: [A7. Communication Reply](../apis/A7-communication-on-request.md) (acknowledgement)

**Query note on the leg cards** (shown on S9 and S11, not on this tab). On a queried leg, the leg's card shows "What the payer says" as a code block. It holds the verdict's disposition, which is where PMJAY writes its query [PAYER](../references/PAYERS.md#markers), followed by the item-level query trail when that differs.

**Communication pointer on the leg cards** (S9 and S11). The pointer shows on a leg's card when that leg has an unanswered query. It also shows, for a `communication`-mode payer, whenever the leg stands `queried`.
- With open queries: "The payer has asked N question(s) on this leg by CommunicationRequest. The answer goes back as a Communication on the request's own thread, with the documents it asked for, from the Communication tab."
- Queried, with no open request yet: "`<payer name>` asks for more by CommunicationRequest and takes the answer as a Communication on that thread. A question from it arrives on the Communication tab; this leg is not submitted again to answer it."
- Button: "Open the Communication tab" (primary, message icon).

**Header signals in S6.** Open queries (kind `query`, status `open` or `error`) show in S6's header as an amber chip, "1 query awaiting reply" or "N queries awaiting reply". They also put "Answer the payer (N)" first in the Next buttons. An open query on a leg that is with the payer puts the case's stage into `queried`. A notification or a note never does.

---

Callback: [C9. Payer Communication](../callbacks/C9-communication-request.md)

Data: [D9. claim](../database/D9-claim.md)

Data: [D15. claim_auth_requirement](../database/D15-claim-auth-requirement.md)

Data: [D23. claim_query](../database/D23-claim-query.md)

Data: [D28. claim_document](../database/D28-claim-document.md)

#### S10L. LAYOUT
The arrangement below is the reference implementation's [REF](../references/PAYERS.md#markers): follow the target HMIS's own screen conventions. What is required is in DESCRIPTION and ACTIONS: the fields, options, columns, statuses, messages and actions.


```
|------------------------------------------------------------------|
| Claims > NM-000123                                               |
| <Beneficiary name>  [NM-000123] [Claim: Queried]                 |
|                     [1 query awaiting reply]                     |
| Next: [Answer the payer (1)]                                     |
|------------------------------------------------------------------|
| ... | Pre-authorisation | *Communication* | Claim | Payments     |
|------------------------------------------------------------------|
| [Card] Payer queries                        (pre-authorisation)  |
|  v Query answered 2026-09-12                                     |
|     Received  From  About  Status [Answered]                     |
|     What the payer asked: * ...                                  |
|     Our reply: [code block]   Attached: * file.pdf               |
|     Sent at  Transaction  Thread                                 |
|  > Turnaround time query 2026-09-10, acknowledged                |
|------------------------------------------------------------------|
| [Card] Payer queries                        (claim)              |
|  v Query raised 2026-09-18 - awaiting our reply                  |
|     Received  From  About  Status [Awaiting our reply]           |
|     What the payer asked: * Discharge summary is illegible       |
|     Reply [______________________________________]               |
|     Send documents already on the claim                          |
|       [ ] Case sheet  CD · preauth                               |
|     Documents the payer named                                    |
|       Code | Document | Choose a PDF                             |
|     Attach anything else                                         |
|       [Files...] [Filed as v] [Label____]                        |
|                                      [(>) Send reply to payer]   |
|  > Note from the payer 2026-09-19                                |
|------------------------------------------------------------------|
```

- The pre-authorisation leg's card comes first, then the claim leg's. Both are titled "Payer queries", and a card is left out when its leg has no messages.
- Inside a card, each message is an accordion item. Several can be open at once, and the newest is first.
- Detail lists use four columns for queries and notes, and five for notifications.
- The reply form is full width. The send button is right-aligned and primary with a send icon.
- The upload row in "Attach anything else" wraps on narrow screens.

#### S10A. ACTIONS
1. Send reply to payer: file any new files, send the reply on the request's thread, and reload S10. The query shows as answered, or as "Reply failed" with the error.
2. Send the acknowledgement: re-send a notification's acknowledgement and reload S10.
3. Attached file links: open the document inline in a new browser tab.
4. Open the Communication tab (on the S9 or S11 cards): come here.
5. Answer the payer (N) (S6 header Next button): come here.
6. Refresh (S6 header, while anything is awaited): reload S6 on this tab. New payer messages arrive pushed through the callback door, so a reload shows them.
7. Breadcrumb "Claims": go to the Claim Master S5.
