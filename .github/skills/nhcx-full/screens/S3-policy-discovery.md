# S3. Policy Discovery Screen

#### S3R. ROUTE
claims/view/:caseid/eligibility

Shown as the first tab, "Eligibility" (tab key `eligibility`), of the Claim Detail screen S6. It is also the tab S6 opens on when no tab is named.

Form posts to: claims/view/:caseid/check (POST), then redirects back to S6.

Breadcrumb (from S6): Claims (claims/list, S5) > <case number>

#### S3D. DESCRIPTION
The coverage eligibility step. It shows who the beneficiary is and which policy the case runs on, sends an eligibility check to the payer, and shows the payer's verdict: whether the policy is in force, the wallet (sum insured, utilised, balance) and whether pre-authorisation is required.

The tab is a stack of up to four cards, in this order:
1. Beneficiary
2. Policy
3. Payer verdict (only once a check has been sent)
4. Coverage eligibility check (hidden while a check is awaiting the payer)

**Beneficiary card.** A photo on the left, then a three-column detail grid. The photo (a URL, a data URI, or bare base64 read as JPEG), 5rem square with rounded corners. With no photo the card shows an initials avatar of the same size. Fields (an empty value shows "-"):

| Label | Value |
|---|---|
| Name | beneficiary name |
| Member ID | member ID |
| ABHA | ABHA number |
| Mobile | mobile number |
| Gender | gender, title-cased |
| Date of birth | date of birth |
| Address | full address |
| Found by | "<identifier label> · <identifier value>" from the S1 search, for example "Member ID · MD5SLS4X5" |

After selection (S2) only member ID, ABHA, mobile and Found by are normally filled. Name, gender, date of birth, address, photo and a corrected ABHA come from the payer's eligibility reply.

**Policy card.** A three-column detail grid:

| Label | Value |
|---|---|
| Policy code | policy code |
| Product | product name (or "-") over the product id, muted |
| Payer | payer name (or "-") over the payer id, muted |
| Plan | plan name |
| Plan period | "<start date> → <end date>" (dates only) |
| Relationship | relationship, title-cased |

**Coverage eligibility check card.** A form with three fields in a three-column grid and a footer with one right-aligned primary button (send icon):

| Field | Control | Default | Notes |
|---|---|---|---|
| Purpose (required) | dropdown | the case's last purpose, else `validation` | options below |
| Policy code | text | the case's policy code | help text "National health plan identifier on the card" |
| Member ID (required) | text, required | the case's member ID | |

Purpose options:

| Value (sent upstream) | Label |
|---|---|
| `validation` | Validation, is the policy in force? |
| `benefits` | Benefits, what does the policy cover for this package? |
| `discovery` | Discovery, find active coverage |

`validation` is used at registration. `benefits` is used before a pre-authorisation or an enhancement. `discovery` is what an indemnity payer answers when the policy is not yet known; a discovery that carries more than one identifier is sent from its own page, [S17. Beneficiary Discovery](S17-beneficiary-discovery.md). A fourth purpose, `auth-requirements`, uses the same exchange but is not offered here: it is sent on the chosen procedure set from the Validate step before pre-authorisation (see S9).

The button reads "Send to payer" while the case is a draft, and "Check again" after any earlier check.

Validation, in this order, before anything is sent. Each failure returns to S6 with the message as a red flash:
- "Choose whether this check is a validation, a benefits check or a discovery."
- "Member ID is required for an eligibility check."
- "Policy code is required for a validation check." or "Policy code is required for a benefits check." (discovery may go without one)
- "Set the facility's HFR ID under Settings before raising claims."
- "Set the facility's NHCX participant code under Settings before raising claims."

API: [A2. Coverage Eligibility Check](../apis/A2-coverage-eligibility-check.md)

After a queued send the case moves to Awaiting payer (`checking`) and any earlier error is cleared. The flash reads "Eligibility request queued to the payer."

If the send fails, the error is flashed red.

**Waiting for the reply (async).** Every load of S6 (and the Refresh button) looks once for the reply while the case is `checking`. A poll failure leaves the case waiting and shows the muted note "Could not poll the gateway: <error>".

Callback: [C2. Coverage Eligibility Verdict](../callbacks/C2-coverage-eligibility-on-check.md)

API: [A10. Transaction Related](../apis/A10-txn-related.md) (poll)

API: [A12. Transaction FHIR](../apis/A12-txn-fhir.md) (poll)

API: [A13. Transaction List](../apis/A13-txn-list.md) (poll, rejection lookup)

API: [A11. Transaction Dispatch](../apis/A11-txn-dispatch.md) (poll, dispatch status)

Data: [D9. claim](../database/D9-claim.md)

**Payer verdict card states.** The card follows the case `status`:

| Status | Status chip | Payer verdict card |
|---|---|---|
| `draft` | Draft (warning) | not shown |
| `checking` | Awaiting payer (info) | waiting text, details and a Send again button; the check form is hidden |
| `eligible` | Eligible (success) | three stat tiles and the verdict details |
| `not-eligible` | Not eligible (danger) | the same, balance tile in danger colour |
| `error` | Error (danger) | the error message in danger colour, or "The exchange failed." |

Waiting text: "Eligibility <purpose> sent to the payer; awaiting the on_check reply. Use Refresh to check for it." (the purpose word, for example "validation", else "check"). Below it the poll note if any, then Sent at, Transaction and Correlation.

Verdict tiles (money shows as "₹" with thousands separators and no decimals, or "-" when not reported):

| Tile | Icon | Tone |
|---|---|---|
| Sum insured | shield-check | default |
| Utilised | trending-down | warning |
| Wallet balance | wallet | success when eligible, danger when not |

Verdict details: Disposition, Outcome, In force ("Yes" or "No"), Pre-authorisation ("Required", "Not required", or "-" when the payer did not say), Checked at, Correlation.

#### S3L. LAYOUT
The arrangement below is the reference implementation's [REF](../references/PAYERS.md#markers): follow the target HMIS's own screen conventions. What is required is in DESCRIPTION and ACTIONS: the fields, options, columns, statuses, messages and actions.


```
|------------------------------------------------------------------|
| [S6 header, next actions and tab bar; Eligibility tab active]    |
|------------------------------------------------------------------|
| [Card] Beneficiary                                               |
|  +------+  NAME            MEMBER ID        ABHA                 |
|  | photo|  Asha Devi       MD5SLS4X5        91703412374240       |
|  | / AD |  MOBILE          GENDER           DATE OF BIRTH        |
|  +------+  -               Female           1984-02-11           |
|            ADDRESS         FOUND BY                              |
|            ...             Member ID · MD5SLS4X5                 |
|------------------------------------------------------------------|
| [Card] Policy                                                    |
|  POLICY CODE     PRODUCT               PAYER                     |
|  PMJAY/HP/S/G    PMJAY for Himachal    Nhcx Pmjay                |
|                  PMJAY/HP/S/G          <payer code>              |
|  PLAN            PLAN PERIOD           RELATIONSHIP              |
|  ...             2026-04-01 → 2027-03-31   Self                  |
|------------------------------------------------------------------|
| [Card] Payer verdict                                             |
|  [Sum insured  ] [Utilised     ] [Wallet balance]                |
|  [₹500,000     ] [₹305,951     ] [₹194,049      ]                |
|  DISPOSITION     OUTCOME          IN FORCE                       |
|  PRE-AUTHORISATION  CHECKED AT    CORRELATION                    |
|------------------------------------------------------------------|
| [Card] Coverage eligibility check                                |
|  Purpose *            Policy code          Member ID *           |
|  [Validation, ... v]  [PMJAY/HP/S/G]       [MD5SLS4X5]           |
|                       National health plan                       |
|                       identifier on the card                     |
|------------------------------------------------------------------|
|                                        [(send) Check again]      |
|------------------------------------------------------------------|

While awaiting the payer (check form hidden):
| [Card] Payer verdict                         [(refresh) Send again]|
|  Eligibility validation sent to the payer; awaiting the on_check |
|  reply. Use Refresh to check for it.                             |
|  Could not poll the gateway: ...   (muted, only on failure)      |
|  SENT AT          TRANSACTION          CORRELATION               |
```

- Detail grids use small uppercase muted labels over the value, three columns from small screens up.
- The stat tiles sit in a grid: one column on phones, two on small screens, three on large.
- The Send again button sits in the Payer verdict card header, secondary style, refresh icon.
- The check form's button sits in the card footer, right-aligned, primary style.

#### S3A. ACTIONS
1. Send to payer / Check again: validate, send the check (A2), set the case to Awaiting payer, and reload S6 on this tab with "Eligibility request queued to the payer." Validation failures reload with the message in red.
2. Send again (only while awaiting the payer): ask "The payer has not replied to the last check yet. Send the same eligibility check again?" and on OK resend with the same purpose (default `validation`), policy code and member ID. The check form is withheld while an exchange is open so two checks on one case cannot be answered out of order; this button is the only way out of a stalled exchange.
3. Refresh (in the S6 header while awaiting): reload S6, which polls once for the on_check reply.
4. After an eligible verdict, the S6 next-action button "Fetch the package master" goes to the Insurance Plan tab S7.
