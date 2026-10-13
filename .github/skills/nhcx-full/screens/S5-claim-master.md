# S5. Claim Master Screen

#### S5R. ROUTE
claims/list?status=<status>[&patient=<id>]

`patient` narrows the list to one patient's cases; the patient master's "Claims" shortcut ([S13. Patient List](S13-patient-list.md), [S15. Patient Detail](S15-patient-detail.md)) opens the list this way, and the card title then reads "<n> claim(s) for <patient name>".

Page title: Claims. This is the landing screen of the Claims section (sidebar item "Claims").

#### S5D. DESCRIPTION
The ledger of every claim case the facility has opened, newest first (by case id, descending). Each row says who the beneficiary is, which policy and payer the case runs on, the wallet balance the payer reported, where the case stands in the scheme's ladder and the result of its eligibility check. It is the entry point for a new claim (S1) and for opening an existing case (S6).

This screen makes no NHCX call. The stage of each case is updated whenever a leg moves (a payer answer lands, a send goes out, a case is opened on S6), so the list is current without anyone opening the case.

A short untitled card above the table explains the flow: an NHCX claim episode starts from the beneficiary's policy; search the insurance registry, pick the policy, then run a coverage eligibility check against the payer. A second sentence notes that JWE encryption and dispatch are handled by the NHCX gateway inside the application ([G6. Encryption](../gateway/G6-encryption.md), [G7. Send](../gateway/G7-send.md)).

Table columns:

| Column header | Content |
|---|---|
| Claim | the case number as a link to S6 |
| Beneficiary | beneficiary name, or "Unknown", over the member ID (muted) |
| Policy | product name, else plan name, else "-", over the policy code (muted) |
| Payer | payer name, or "-" |
| Balance | wallet balance: sum insured minus utilised from the last eligibility verdict, as "₹" with thousands separators and no decimals; "-" when the payer has not reported a wallet |
| Stage | the stage chip (below); empty until the case has a stage |
| Status | the eligibility status chip (below) |
| Opened | the date the case was opened, `YYYY-MM-DD` |

**Status chip and filter.** Status is the result of the coverage eligibility check (S3), not the whole case. Values:

| Value | Chip label | Tone |
|---|---|---|
| `draft` | Draft | warning |
| `checking` | Awaiting payer | info |
| `eligible` | Eligible | success |
| `not-eligible` | Not eligible | danger |
| `error` | Error | danger |

The filter dropdown lists these labels in this order, with a blank first option "All claims". The filter is a GET form, so a filtered list can be bookmarked. An unknown `status` value in the URL is ignored and shows all claims.

**Stage chip.** Where the case stands, as "<Stage>: <Sub-stage>", for example "Pre-authorisation: Approved". The chip's tone comes from the sub-stage.

Stages (the leg the case is on, in the order a case walks them):

| Value | Label |
|---|---|
| `eligibility` | Eligibility |
| `preauth` | Pre-authorisation |
| `enhancement` | Enhancement |
| `claim` | Claim |
| `payment` | Payment |

Sub-stages (what was last done with that leg):

| Value | Label | Tone |
|---|---|---|
| `draft` | Drafted | warning |
| `checking` | Checking | info |
| `eligible` | In force | success |
| `not-eligible` | Not covered | danger |
| `requested` | Requested | info |
| `resubmitted` | Resubmitted | info |
| `answered` | Query answered | info |
| `queried` | Queried | warning |
| `approved` | Approved | success |
| `partial` | Partially approved | warning |
| `rejected` | Rejected | danger |
| `cancelling` | Withdrawing | warning |
| `cancelled` | Withdrawn | danger |
| `refused` | Refused at the door | danger |
| `noticed` | Notice received | info |
| `paid` | Paid | success |

How the pair is worked out (read off the legs, never typed in):
- Any payment notice on the case: `payment`, with `paid` when money has settled, else `noticed`.
- Else a claim that has been sent (not a draft): `claim`, with the claim leg's sub-stage.
- Else a pre-authorisation that has been sent: `preauth`, or `enhancement` when the last send was an enhancement, with that leg's sub-stage.
- Else a saved but unsent pre-authorisation: `preauth` / `draft`.
- Else `eligibility`, with the eligibility status as the sub-stage (`error` shows as `draft`).
- A leg's sub-stage is its own status. A send still in flight reads by what it went out as: `requested` for a first send, `resubmitted` for a resubmission, `answered` for a query response. A leg in error reads `refused`.
- A payer query that is still unanswered turns a leg that is with the payer (`requested`, `answered`, `resubmitted`) into `queried`.

Data: [D9. claim](../database/D9-claim.md)

Data: [D18. claim_preauth](../database/D18-claim-preauth.md)

Data: [D20. claim_submission](../database/D20-claim-submission.md)

Data: [D21. claim_payment](../database/D21-claim-payment.md)

Data: [D23. claim_query](../database/D23-claim-query.md)

**Empty state.** With no rows (none at all, or none matching the filter) the table is replaced by the muted line "No claims yet. Start from a policy search."

#### S5L. LAYOUT
The arrangement below is the reference implementation's [REF](../references/PAYERS.md#markers): follow the target HMIS's own screen conventions. What is required is in DESCRIPTION and ACTIONS: the fields, options, columns, statuses, messages and actions.


```
|------------------------------------------------------------------------------|
| Claims                                                                       |
|------------------------------------------------------------------------------|
| [Card, no title]                                                             |
|  An NHCX claim episode starts from the beneficiary's policy: search the      |
|  insurance registry, pick the policy, then run a coverage eligibility check  |
|  against the payer. ...                                                      |
|------------------------------------------------------------------------------|
|                                                                              |
| [Card] 3 claim(s)          [All claims       v] [Filter]  [(+) New claim]    |
|------------------------------------------------------------------------------|
| Claim       | Beneficiary | Policy       | Payer    | Balance | Stage              | Status   | Opened     |
|-------------|-------------|--------------|----------|---------|--------------------|----------|------------|
| NM-26-0SE.. | Asha Devi   | PMJAY for HP | Nhcx     | ₹194,049| [Pre-authorisation:| [Eligible]| 2026-09-10|
|  (link)     | MD5SLS4X5   | PMJAY/HP/S/G | Pmjay    |         |  Approved]         |          |            |
| NM-26-0SE.. | Unknown     | PMJAY for HP | Nhcx     | -       |                    | [Draft]  | 2026-09-10 |
|             | MD9XK2...   | PMJAY/HP/S/G | Pmjay    |         |                    |          |            |
|------------------------------------------------------------------------------|
```

- The table card title counts the rows shown: "<n> claim(s)".
- The card header's right side holds the filter form (status dropdown and a primary "Filter" button) and then the primary "New claim" button with a plus icon.
- The table scrolls sideways on narrow screens; the header items wrap.
- Chips are small coloured labels. Two-line cells show a main value over a muted line.

#### S5A. ACTIONS
1. New claim: go to the Search Policy screen S1.
2. Claim number link: open the case on the Claim Detail screen S6, which lands on its first tab, Eligibility (S3).
3. Filter: reload this screen with `?status=<value>`, or all claims when "All claims" is chosen.
