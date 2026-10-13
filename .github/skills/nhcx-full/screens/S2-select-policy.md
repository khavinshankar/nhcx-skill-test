# S2. Select Policy Screen

#### S2R. ROUTE
claims/search/results?id_type=<type>&id_value=<value>[&patient=<id>]

Breadcrumb: Claims (claims/list, S5) > Policy search

Select posts to: claims (POST), then redirects to claims/view/:caseid (S6).

#### S2D. DESCRIPTION
The second step of a new claim. It lists every policy the Beneficiary Identification System (BIS) returned for the identifier searched on S1, and lets the operator pick one. Picking a policy opens a new claim (a case) around it and lands on the Claim Detail screen S6.

The search card from S1 stays at the top of this screen, pre-filled with the identifier type and value, so the operator can correct the identifier and search again without going back. The results card sits below it.

API: [A1. Policy Search](../apis/A1-policy-search.md)

Results table columns:

| Column header | Main line | Muted sub-line |
|---|---|---|
| Beneficiary | `name`, or "Unknown" | `member_id`, or "-" |
| Product / policy | `product_name`, or "-" | `policy_code`, else `product_id` |
| Payer | the payer's registered name from the participant registry (`payer_name`, G4, cached), else the code | `payer_id` |
| ABHA | `abha_number`, or "-" | |
| Mobile | `mobile_number`, or "-" | |
| (blank header) | Select button | |

The sandbox returns no beneficiary name at this stage, so the Beneficiary column normally reads "Unknown" over the member ID [SANDBOX](../references/PAYERS.md#markers). The name, gender, date of birth, address and ABHA arrive later with the payer's eligibility reply (S3).

The card title counts the rows: "1 policy found", or "N policies found" for any other count (including "0 policies found").

Select sends the whole normalised policy back to the server as a JSON string, with the search identifier:

```
POST claims
id_type=MemberId
id_value=<the searched value>
patient=<patient id, when the search was started from the patient master>
policy={"member_id": "MD5SLS4X5", "name": null, "policy_code": "PMJAY/HP/S/G",
        "payer_id": "<payer code>", "payer_name": "<registry name, or null>",
        "product_id": "PMJAY/HP/S/G", "product_name": "PMJAY for Himachal",
        "abha_number": "91703412374240", "mobile_number": "", "photo": null,
        "raw": { ...the BIS row... }}
```

Opening the claim makes no NHCX call. It saves a new draft claim (status Draft) around the chosen policy and the search identifier (shown on S3 as "Found by"), with D9 `patient_id` set when a `patient` was carried from the patient master ([S13. Patient List](S13-patient-list.md), [S15. Patient Detail](S15-patient-detail.md)); the admission is still linked on S4. The case number takes the form `NM-<yy>-<mmdd><serial>`, month-day and serial in base32, so numbers sort by date and then issue order [REF](../references/PAYERS.md#markers). The payer name is the registry's (G4), looked up by the payer id and cached; it never falls back to a configured label, the adapter's name or a default name, and a payer whose lookup failed is shown by its code.

Data: [D9. claim](../database/D9-claim.md)

Data: [D30. counter](../database/D30-counter.md)

Rules:
- A policy without a member ID cannot open a claim. The server refuses with "That policy has no member ID; a claim cannot be raised without one." and returns to the search screen with that message as a red flash.
- An unreadable `policy` field is treated as an empty policy, which fails the same member ID rule.
- Selecting the same policy twice opens two separate claims. There is no duplicate check at this step.
- On success the flash reads "Claim <number> opened."

#### S2L. LAYOUT
The arrangement below is the reference implementation's [REF](../references/PAYERS.md#markers): follow the target HMIS's own screen conventions. What is required is in DESCRIPTION and ACTIONS: the fields, options, columns, statuses, messages and actions.


```
|------------------------------------------------------------------|
| Claims > Policy search                                           |
|------------------------------------------------------------------|
| [Card] Search the beneficiary's policy                           |
|  Identifier type      Identifier value                           |
|  [Member ID      v]   [MD5SLS4X5_________]   [(search) Search    |
|                                                         policies]|
|------------------------------------------------------------------|
|                                                                  |
| [Card] 1 policy found                                            |
|------------------------------------------------------------------|
| Beneficiary | Product / policy   | Payer       | ABHA    | Mobile |  |
|-------------|--------------------|-------------|---------|--------|--|
| Unknown     | PMJAY for Himachal | Nhcx Pmjay  | 9170... | -      |[(+) Select]
| MD5SLS4X5   | PMJAY/HP/S/G       | <payer code>|         |        |  |
|------------------------------------------------------------------|

Empty result:
| [Card] 0 policies found                                          |
|  No policy matches that identifier.   (muted text, no table)     |

Search failed:
| [Card, no title]                                                 |
|  <error message in danger colour>                                |
```

- The search card is the S1 card, pre-filled.
- The results card sits below it with a gap. It holds a single scrollable table (it scrolls sideways on narrow screens).
- Two-line cells show the main value over a smaller muted line.
- Each row ends with an extra-small primary "Select" button with a circle-plus icon. The column has no header.
- When there are no rows the table is replaced by the muted line "No policy matches that identifier."
- When the lookup failed the results card is replaced by an untitled card holding the error in the danger colour.

#### S2A. ACTIONS
1. Select: post the chosen policy with the search identifier, open a draft claim, and go to the Claim Detail screen S6 (it opens on the Eligibility tab, S3) with the flash "Claim <number> opened." If the policy has no member ID, stay on S1 with the red flash "That policy has no member ID; a claim cannot be raised without one."
2. Search policies: run the S1 search again with the edited type or value and refresh this list.
3. Breadcrumb "Claims": go to the Claim Master screen S5.
