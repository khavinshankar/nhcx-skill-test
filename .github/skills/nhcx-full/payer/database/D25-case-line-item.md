# D25. case_line_item

#### D25T. TABLE
One row is one line of the bill on one case ([D19. case](D19-case.md)): what was billed, what is claimed, what is approved, and the decision on it; primary key `id`. The reference implementation names it `payer_case_line_items` [REF](../references/PAYERS.md#markers).

#### D25D. DESCRIPTION
The itemised bill, and the only place an approved rupee is decided. The case's totals ([D19. case](D19-case.md) `total_claimed`, `total_approved`) are sums over these rows, recomputed inside every transaction that touches one.

**What a line holds from the wire.** `code` is the `productOrService` the line was billed under ([F8. Claim](../fhir/F8-claim.md) `item[]`): a package code, a SNOMED concept, an implant code; it is what a ClaimResponse ([F9. ClaimResponse](../fhir/F9-claimresponse.md)) and a query ([F11. CommunicationRequest](../fhir/F11-communicationrequest.md)) name the line by. `modifier_code` and `modifier_display` are the ward or ICU tier the line was billed under (`Claim.item.modifier`), which the scheme prices over the package rate [PAYER](../references/PAYERS.md#markers); it arrives as a modifier with its rate already inside the item's `net`, not as a line of its own, and the desk shows it as a column ([S3. Case Desk](../screens/S3-case-desk.md)). `claimed_amount` is the item's `net`, else quantity times unit cost. `enhancement_no` is the round the line arrived in: zero for the original submission, one and up for each enhancement.

**Created:**
- With the case by [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md) ([C5. Claim Submit](../callbacks/C5-claim-submit.md) for a direct claim): every `Claim.item[]` as `pending` with `approved_amount` 0, in order. A short random `LI-` id [REF](../references/PAYERS.md#markers).
- By an enhancement ([C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md)): the lines the case does not already hold, matched on code, description and amount (the reference's enhancement repeats the original lines beside the new ones), appended after the existing ones with `enhancement_no` = the new round.
- By a claim ([C5. Claim Submit](../callbacks/C5-claim-submit.md)) or a discharge with a final bill ([S3. Case Desk](../screens/S3-case-desk.md)) [SANDBOX](../references/PAYERS.md#markers): the whole bill is deleted and replaced, because the final bill is the whole of what is claimed and adding it to the estimate would claim both.

**Decided** by [A13. Adjudicate](../apis/A13-adjudicate.md) (`PATCH cases/:id/line-items/:lineId`), only while the case is open (`stage` `preauth` or `claim`, else "the case is closed"). The status and the amount have to agree, and the write derives the amount from the status so the adjudicator gets the decision they meant rather than a constraint error:

| Status | `approved_amount` |
|---|---|
| `approved` | the claimed amount |
| `rejected` | 0 |
| `partially_approved` | the amount given; 0 or less becomes `rejected`, the claimed amount or more becomes `approved` |
| `pending`, `queried` | 0 |

`query_remarks` is kept only on a `queried` line. Each decision appends a timeline event ([D26. case_timeline](D26-case-timeline.md)) "Line Item Approved", "Partially Approved", "Rejected" or "Queried" with the amounts.

**Moved by the case:** approving the case ([A13. Adjudicate](../apis/A13-adjudicate.md)) approves every `pending` line in full first, and is refused while any line is `queried` or when every line is `rejected`; a query reply ([C9. Communication](../callbacks/C9-communication.md), [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md) resubmission) puts every `queried` line back to `pending` and clears `query_remarks`; a reprocess ([C7. Task Submit](../callbacks/C7-task-submit.md)) puts every line back to `pending` with `approved_amount` 0 and remarks cleared.

**Read into the wire:** each row is one `ClaimResponse.item[]` ([F9. ClaimResponse](../fhir/F9-claimresponse.md)) with its `itemSequence`, an `eligible` adjudication of `approved_amount`, a status adjudication from `status`, and `remarks` or `query_remarks` as the reason; and one payload of a query ([F11. CommunicationRequest](../fhir/F11-communicationrequest.md)) when queried.

Delete: never on their own; by replacement of the bill, or cascade with the case.

#### D25C. COLUMNS
| column | type | null/default | meaning (and allowed values) |
|---|---|---|---|
| id | VARCHAR(24) | primary key | `LI-<random>` [REF](../references/PAYERS.md#markers); the `:lineId` of the decision route |
| case_id | VARCHAR(24) | NOT NULL | the case ([D19. case](D19-case.md)) |
| description | VARCHAR(300) | NOT NULL | the item's display or text |
| code | VARCHAR(64) | null | `productOrService` code as billed |
| modifier_code | VARCHAR(64) | null | the ward or ICU tier modifier [PAYER](../references/PAYERS.md#markers) |
| modifier_display | VARCHAR(200) | null | its display |
| quantity | NUMERIC(10,2) | NOT NULL, default 1 | positive |
| unit_cost | NUMERIC(14,2) | NOT NULL | non-negative |
| claimed_amount | NUMERIC(14,2) | NOT NULL | the item's net; non-negative |
| approved_amount | NUMERIC(14,2) | NOT NULL, default 0 | between 0 and `claimed_amount`, agreeing with `status` |
| status | VARCHAR(32) | NOT NULL, default `'pending'` | `pending`, `approved`, `partially_approved`, `rejected`, `queried` |
| remarks | VARCHAR(500) | NOT NULL, default `''` | the adjudicator's note on the decision |
| query_remarks | VARCHAR(500) | null | what was asked; only on a `queried` line |
| position | INTEGER | NOT NULL, default 0 | order on the bill |
| enhancement_no | INTEGER | NOT NULL, default 0 | the round the line arrived in |

#### D25K. KEYS AND INDEXES
- Primary key `id`.
- Foreign key `case_id` references [D19. case](D19-case.md) `id` (`ON DELETE CASCADE`).
- Checks: `ck_line_items_status`; `ck_line_items_amounts` (`quantity > 0`, `unit_cost >= 0`, `claimed_amount >= 0`, `0 <= approved_amount <= claimed_amount`); `ck_line_items_decision` (`rejected` has 0, `approved` has the claimed amount, `partially_approved` strictly between, `pending` and `queried` unconstrained); `ck_line_items_query` (`query_remarks` null unless `queried`).
- Indexes: `idx_line_items_case` on `(case_id, position)`; `idx_line_items_status` on `(case_id, status)`; `idx_line_items_enhancement` on `(case_id, enhancement_no)`.

#### D25U. USED BY
- Screens: [S2. Cases](../screens/S2-cases.md), [S3. Case Desk](../screens/S3-case-desk.md)
- APIs: [A3. Pre-auth Answer](../apis/A3-preauth-answer.md), [A4. Claim Answer](../apis/A4-claim-answer.md), [A5. Query Request](../apis/A5-query-request.md), [A13. Adjudicate](../apis/A13-adjudicate.md)
- Callbacks: [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md), [C5. Claim Submit](../callbacks/C5-claim-submit.md), [C7. Task Submit](../callbacks/C7-task-submit.md), [C9. Communication](../callbacks/C9-communication.md)
- FHIR: [F8. Claim](../fhir/F8-claim.md), [F9. ClaimResponse](../fhir/F9-claimresponse.md), [F11. CommunicationRequest](../fhir/F11-communicationrequest.md), [F12. Communication](../fhir/F12-communication.md)
- Database: [D19. case](D19-case.md)
