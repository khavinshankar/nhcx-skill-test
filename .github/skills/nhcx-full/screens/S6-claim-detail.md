# S6. Claim Detail Screen

#### S6R. ROUTE
claims/view/:caseid (opens the Eligibility tab)
claims/view/:caseid/<tab key> (opens that tab; `?tab=<tab key>` is accepted as an alias)

`:caseid` is the case's stable public id (D9 `external_id`, else the row id), **never the claim number**: an accepted cancellation replaces the claim number (C7), and a route keyed on it breaks at that moment.

Page title: Claim <case number>

Breadcrumb: Claims (claims/list, S5) > <case number>

Companion endpoint: claims/view/:caseid/state (GET, JSON).

#### S6D. DESCRIPTION
The shell for one claim case. It carries a header that says whose case it is and where it stands, a row of next-action buttons that say what the case is waiting for, and a tab bar that walks the episode in the order it happens. Every tab's content is rendered with the page; switching tabs happens in the browser without a reload. An unknown case id shows the standard "Claim" not-found page.

**Correlation id, everywhere.** Wherever a message or a thread of the exchange is on screen (an eligibility check, the ruling, the package master request, the pre-authorisation and claim legs and each reply on them, a payer's query or notification and the reply to it, a payment notice and its acknowledgement), its `x-hcx-correlation_id` is shown beside it, labelled "Correlation id", in full on hover and copied on a click. It is the one id the hospital, the payer, a capture and the exchange's own logs share, so no tab leaves it out.

**Polling on load.** NHCX answers every leg asynchronously. The payer's reply normally arrives by callback ([G8. Receive](../gateway/G8-receive.md) hands it to C1), and each load of this screen is the fallback: before anything is drawn, it reads [G9. Ledger](../gateway/G9-ledger.md) once for every leg that is still out with the payer.

| Leg (tab) | Polled while | Poll failure shows |
|---|---|---|
| Eligibility check (S3) | case status `checking` | muted note "Could not poll the gateway: <error>" on the Eligibility tab |
| Insurance plan fetch (S7) | plan status `fetching` | muted note "Could not poll the gateway: <error>" on the Insurance plan tab |
| Auth-requirements ruling (Validate) | ruling status `checking` | nothing; the card keeps saying it is awaiting |
| Claim submission (S11) | submission status `submitting` | nothing |
| Predetermination quote (S9) | any quote status `asking` | nothing |
| Pre-authorisation (S9) | status `submitting` (polls the reply) or `cancelling` (polls the cancellation) | nothing |
| Status enquiries (S9, S11) | any enquiry status `asking` | nothing |

The page never reloads itself, because that would throw away whatever is being typed on another tab. The operator presses Refresh instead.

**Header.** On the left, the beneficiary name as the heading (the member ID when there is no name yet). On the right, a wrapping row of chips:

1. The case number, info tone.
2. The stage chip "<Stage>: <Sub-stage>" (values and tones in S5). The stage is recomputed on each load.
3. When the payer has messages on the case whose status is not `answered`: "1 query awaiting reply" or "<n> queries awaiting reply", warning tone.
4. When money has settled: "Paid ₹<total>", success tone (thousands separators, no decimals).
5. When any leg is still out with the payer (the same conditions as the poll table): a "Refresh" button with a refresh icon. It reloads this screen on the tab named in the current URL, which runs the polls again.

**Next actions.** Below the header, when the case is waiting on the desk, a muted "Next:" label and small buttons. The first button is primary, the rest secondary. Each one opens this screen on the tab where that action lives. They are worked out from the stage and sub-stage, so only a legal action is offered:

| When | Button label | Opens tab |
|---|---|---|
| Any payer query unanswered or whose reply failed (always first) | Answer the payer (<n>) | Communication (S10) |
| Stage `eligibility`, status `draft`, `error` or `not-eligible` | Check the cover | Eligibility (S3) |
| Stage `eligibility`, eligible, no ready plan | Fetch the package master | Insurance plan (S7) |
| Stage `eligibility`, plan ready, no line items | Quote the treatment | Line items (S8) |
| Stage `eligibility`, line items present, draft not saved (`preauth_saved_at` null) | Save the preauth draft | Pre-authorisation (S4 on S9) |
| Stage `eligibility`, line items present, draft saved | Send the pre-authorisation | Pre-authorisation (S9) |
| Stage `preauth`/`enhancement`, `queried` | Answer the query (payer that takes answers by resubmission) | Pre-authorisation (S9) |
| | Answer the payer's query (payer that takes a Communication, when no query is already listed first) | Communication (S10) |
| Stage `preauth`/`enhancement`, `draft` or `refused` | Send the pre-authorisation | Pre-authorisation (S9) |
| Stage `preauth`/`enhancement`, `rejected` | Send a fresh pre-authorisation | Pre-authorisation (S9) |
| Stage `preauth`/`enhancement`, `approved`/`partial`, lines added since | Send the enhancement (<n> added) | Pre-authorisation (S9) |
| Same, nothing added, no discharge recorded | Record the discharge | Claim (S11) |
| Same, discharge recorded | File the claim | Claim (S11) |
| Stage `preauth`/`enhancement`, `requested`/`answered`/`resubmitted` | With the payer; ask where it stands | Pre-authorisation (S9) |
| Stage `claim`, `queried` | Answer the claim query (resubmission payer), else "Answer the payer's query" | Claim (S11) / Communication (S10) |
| Stage `claim`, `rejected` or `partial` | Ask for a reprocess | Claim (S11) |
| Stage `claim`, `requested`/`answered`/`resubmitted` | With the payer; ask where it stands | Claim (S11) |
| Stage `claim`, `refused`, another send allowed | Send the claim again | Claim (S11) |
| Stage `claim`, `refused`, no send left | Ask for a reprocess | Claim (S11) |
| Stage `claim`, any other sub-stage (approved) | Await the payment notice | Payments (S12) |
| Stage `payment`, a notice not yet acknowledged (or its acknowledgement failed) | Acknowledge the payment notice | Payments (S12) |
| Stage `payment`, all acknowledged | Settled | Payments (S12) |

**Tabs**, in this order. The tab key is the `tab` query value:

| # | Key | Label | Screen |
|---|---|---|---|
| 1 | `eligibility` | Eligibility | S3 |
| 2 | `plan` | Insurance plan | S7 |
| 3 | `lines` | Line items | S8 |
| 4 | `validate` | Validate | S8.2 (auth-requirements ruling on the line items) |
| 5 | `verification` | Verification | S18 (the beneficiary authenticated against their ABHA, at the stage the stay is at) |
| 6 | `preauth` | Pre-authorisation | S4 (link admission, draft form) and S9 (send, verdict, documents, forms) |
| 7 | `communication` | Communication | S10 |
| 8 | `claim` | Claim | S11 |
| 9 | `payments` | Payments | S12 |

Tab rules:
- No `tab`, or an unknown key, opens Eligibility.
- Old key alias: `procedure` opens `plan` (the plan tab's name before line items had their own tab), so old bookmarks still land [REF](../references/PAYERS.md#markers).
- The Pre-authorisation tab is designed to appear once the payer has ruled on the procedure set on Validate (at once for a payer that does not rule), and to stay once a pre-authorisation has been sent. In the current build it is always shown: one scheme's sandbox never answers the ruling [SANDBOX](../references/PAYERS.md#markers), so the tab does not wait, and a ruling that arrives later narrows the documents and forms it asks for. If the tab is hidden and `preauth` is asked for, Validate opens instead.
- The Validate tab reads "Choose the line items on the previous tab first..." until line items exist. After that it holds the ruling card and a card saying the Pre-authorisation tab is open, with a primary "Go to the pre-authorisation" button (arrow icon) to S9.

API: [A17. Claim State](../apis/A17-claim-state.md)

Data: [D9. claim](../database/D9-claim.md)

Data: [D10. claim_plan](../database/D10-claim-plan.md)

Data: [D13. claim_auth](../database/D13-claim-auth.md)

Data: [D18. claim_preauth](../database/D18-claim-preauth.md)

Data: [D19. claim_predetermination](../database/D19-claim-predetermination.md)

Data: [D20. claim_submission](../database/D20-claim-submission.md)

Data: [D21. claim_payment](../database/D21-claim-payment.md)

Data: [D23. claim_query](../database/D23-claim-query.md)

Data: [D29. claim_enquiry](../database/D29-claim-enquiry.md)

#### S6L. LAYOUT
The arrangement below is the reference implementation's [REF](../references/PAYERS.md#markers): follow the target HMIS's own screen conventions. What is required is in DESCRIPTION and ACTIONS: the fields, options, columns, statuses, messages and actions.


```
|------------------------------------------------------------------------------|
| Claims > NM-26-0SE000001                                                     |
|------------------------------------------------------------------------------|
| Asha Devi                      [NM-26-0SE000001] [Pre-authorisation: Requested]|
|                                [1 query awaiting reply] [Paid ₹45,000]        |
|                                [(refresh) Refresh]                           |
| Next: [Answer the payer (1)] [With the payer; ask where it stands]           |
|------------------------------------------------------------------------------|
| Eligibility | Insurance plan | Line items | Validate | Verification |       |
| Pre-authorisation | Communication | Claim | Payments                         |
|------------------------------------------------------------------------------|
|                                                                              |
|  <active tab content: S3, S7, S8, S8.2, S18, S4+S9, S10, S11 or S12>        |
|                                                                              |
|------------------------------------------------------------------------------|
```

- The heading and the chip row sit on one line and wrap on narrow screens; chips wrap among themselves.
- The Refresh button sits among the chips and appears only while something is awaiting the payer.
- The "Next:" row appears only when there is at least one action. Its buttons are small; the first is primary.
- The tab bar underlines the active tab. Panes below are stacks of cards with a consistent vertical gap.

#### S6A. ACTIONS
1. Tab "Eligibility": show S3.
2. Tab "Insurance plan": show S7.
3. Tab "Line items": show S8.
4. Tab "Validate": show the Authorisation Requirements card S8.2, then the way on to the Pre-authorisation tab.
5. Tab "Verification": show S18.
6. Tab "Pre-authorisation": show S4 (admission link and pre-auth draft) above S9 (sending and the payer's verdict).
7. Tab "Communication": show S10.
8. Tab "Claim": show S11.
9. Tab "Payments": show S12.
10. Next-action button: reload this screen on the tab the action names (see the table in S6D).
11. Refresh: reload this screen on the current URL's tab, polling every leg that is out with the payer.
12. Breadcrumb "Claims": go to the Claim Master screen S5.
