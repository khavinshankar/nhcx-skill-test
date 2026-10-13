# D26. case_timeline

#### D26T. TABLE
One row is one event on one case's trail: who did what, in order; primary key `id`, ordered by `seq`. Parent table [D19. case](D19-case.md). The reference implementation names it `payer_case_timeline` [REF](../references/PAYERS.md#markers).

#### D26D. DESCRIPTION
The audit trail shown on the case desk ([S3. Case Desk](../screens/S3-case-desk.md)) in words; the exchange log ([D27. case_exchange_message](D27-case-exchange-message.md)) is the evidence beside it. Two events written in one transaction land in the same millisecond, and `at` alone would leave them to sort at random, so `seq` is the insertion order and is what the timeline is ordered by.

Written inside the transaction of the change it describes, one event per change, with the actor's name (the desk account, or the hospital's name or participant code for a message off the exchange) and a tone. The events, with their titles [REF](../references/PAYERS.md#markers):

| Change | Title | Tone |
|---|---|---|
| a case opened by [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md) | Pre-Authorization Claim Created | info |
| a direct claim opened by [C5. Claim Submit](../callbacks/C5-claim-submit.md) | Claim Filed Directly | info |
| attachments filed under `ODN` because their codes are unknown ([C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md), [C5. Claim Submit](../callbacks/C5-claim-submit.md), [C9. Communication](../callbacks/C9-communication.md)) | Attachments Filed as Other | warning |
| a line decided ([A13. Adjudicate](../apis/A13-adjudicate.md)) | Line Item Approved, Partially Approved, Rejected or Queried | success, warning, error, warning |
| the case approved ([A13. Adjudicate](../apis/A13-adjudicate.md)) | Pre-Authorization Approved, or Claim Approved for Disbursement | success |
| rejected | Claim Rejected | error |
| queried | Additional Information Requested | warning |
| an enhancement ([C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md)) | Enhancement `<n>` Requested | warning |
| withdrawn ([C7. Task Submit](../callbacks/C7-task-submit.md) cancel) | Pre-Authorization Withdrawn | warning |
| a query answered ([C9. Communication](../callbacks/C9-communication.md), [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md) resubmission) | Query Answered | info |
| the discharge recorded | Patient Discharged | info |
| the claim filed ([C5. Claim Submit](../callbacks/C5-claim-submit.md)) | Claim Submitted | info |
| reopened ([C7. Task Submit](../callbacks/C7-task-submit.md) reprocess or release) | Claim Reopened for Reprocessing (round `<n>`) | warning |
| a payment raised, completed, failed ([A14. Disburse](../apis/A14-disburse.md)) | Disbursement Initiated, Disbursement Completed (UTR: `<utr>`), Disbursement Failed | info, success, error |
| paid in full | Case Fully Settled, by "Settlement Engine" | success |

Delete: never; cascade with the case.

#### D26C. COLUMNS
| column | type | null/default | meaning (and allowed values) |
|---|---|---|---|
| id | VARCHAR(24) | primary key | `TL-<random>` [REF](../references/PAYERS.md#markers) |
| seq | BIGINT | NOT NULL, identity, UNIQUE | insertion order |
| case_id | VARCHAR(24) | NOT NULL | the case ([D19. case](D19-case.md)) |
| title | VARCHAR(200) | NOT NULL | the event, from the table above |
| description | VARCHAR(1000) | NOT NULL, default `''` | the detail: remarks, amounts, counts |
| actor | VARCHAR(160) | NOT NULL | who: a desk account's name, the hospital, or the engine |
| type | VARCHAR(32) | NOT NULL, default `'info'` | `info`, `success`, `warning`, `error` |
| at | TIMESTAMPTZ | NOT NULL, default now | when; the event's own stamp when it carried one |

#### D26K. KEYS AND INDEXES
- Primary key `id`. Unique `uq_timeline_seq` on `seq`.
- Foreign key `case_id` references [D19. case](D19-case.md) `id` (`ON DELETE CASCADE`).
- Check `ck_timeline_type`.
- Index `idx_timeline_case` on `(case_id, seq)`.

#### D26U. USED BY
- Screens: [S3. Case Desk](../screens/S3-case-desk.md)
- APIs: [A5. Query Request](../apis/A5-query-request.md), [A11. Transaction Related](../apis/A11-txn-related.md), [A13. Adjudicate](../apis/A13-adjudicate.md), [A14. Disburse](../apis/A14-disburse.md), [A15. Case Exchange Log](../apis/A15-case-exchange.md)
- Callbacks: [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md), [C5. Claim Submit](../callbacks/C5-claim-submit.md), [C7. Task Submit](../callbacks/C7-task-submit.md), [C9. Communication](../callbacks/C9-communication.md), [C11. Payment Acknowledgement](../callbacks/C11-payment-acknowledgement.md)
- FHIR: [F8. Claim](../fhir/F8-claim.md), [F10. Task (claim actions and answers)](../fhir/F10-task-claim-actions.md), [F12. Communication](../fhir/F12-communication.md)
- Database: [D3. document_type](D3-document-type.md), [D19. case](D19-case.md), [D23. case_document](D23-case-document.md), [D25. case_line_item](D25-case-line-item.md), [D27. case_exchange_message](D27-case-exchange-message.md)
