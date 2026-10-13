# D27. case_exchange_message

#### D27T. TABLE
One row is one message exchanged about one case ([D19. case](D19-case.md)) over NHCX, in either direction, with the bundle as it went over the wire; primary key `id`, ordered by `seq`. The reference implementation names it `payer_case_exchange_messages` [REF](../references/PAYERS.md#markers).

#### D27D. DESCRIPTION
The evidence. The timeline ([D26. case_timeline](D26-case-timeline.md)) says what happened in words; this table holds the messages themselves, so an operator can read what the hospital sent and what this payer answered, and a driver or test can read the case's state off it ([A15. Case Exchange Log](../apis/A15-case-exchange.md), `GET cases/:id/exchange`, `.../exchange/:msgId` with the payload). It is the application's own log beside the gateway's ledger ([G9. Ledger](../gateway/G9-ledger.md)): the ledger holds every envelope by transaction, this holds the ones that belong to a case.

**Written** by every callback and every send, after the message has arrived or gone:

| Direction | Kind | Written by |
|---|---|---|
| `in` | `preauth` | [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md), for a new case, an enhancement or a resubmission (the summary says which) |
| `in` | `claim` | [C5. Claim Submit](../callbacks/C5-claim-submit.md) |
| `in` | `communication` | [C9. Communication](../callbacks/C9-communication.md) |
| `in` | `task` | [C7. Task Submit](../callbacks/C7-task-submit.md), [C8. Status Enquiry](../callbacks/C8-status-enquiry.md), [C11. Payment Acknowledgement](../callbacks/C11-payment-acknowledgement.md) |
| `in` | `paymentnotice` | [C10. Payment Enquiry](../callbacks/C10-payment-enquiry.md) |
| `out` | `claimresponse` | [A3. Pre-auth Answer](../apis/A3-preauth-answer.md), [A4. Claim Answer](../apis/A4-claim-answer.md): the acknowledgement and the verdict, one row each; a dropped or delayed answer is recorded with a note and the bundle that was withheld [SANDBOX](../references/PAYERS.md#markers) |
| `out` | `communicationrequest` | [A5. Query Request](../apis/A5-query-request.md) |
| `out` | `task` | [A9. Task Answer](../apis/A9-task-answer.md), the reprocess verdict included; [A8. Status Answer](../apis/A8-status-answer.md) as `status` |
| `out` | `paymentnotice` | [A6. Payment Notice](../apis/A6-payment-notice.md) |
| `out` | `paymentreconciliation` | [A7. Payment Enquiry Answer](../apis/A7-payment-enquiry-answer.md) |

Kinds, exact strings: `preauth`, `claimresponse`, `claim`, `communicationrequest`, `communication`, `paymentnotice`, `paymentreconciliation`, `task`, `status`, `predetermination`; anything else is written as `task`.

**One message, one row.** A redelivery, or a second copy of the application writing to the same database, carries the same transaction id, and two rows for one message read as two exchanges that never happened: a row with the same case, direction, kind and `txn_id` is not written again.

**Never fails the caller.** The message already went over the wire or arrived; losing the application's copy is the lesser failure, so a write error is logged and the id comes back empty.

The answered forms a hospital sent ([F7. QuestionnaireResponse](../fhir/F7-questionnaireresponse.md)) are read back off the `in` rows of kind `preauth` and `claim` ([A15. Case Exchange Log](../apis/A15-case-exchange.md), `GET cases/:id/forms`), which is why the payload is kept whole.

Delete: never; cascade with the case.

#### D27C. COLUMNS
| column | type | null/default | meaning (and allowed values) |
|---|---|---|---|
| id | VARCHAR(24) | primary key | `MSG-<random>` [REF](../references/PAYERS.md#markers) |
| seq | BIGINT | NOT NULL, identity, UNIQUE | insertion order |
| case_id | VARCHAR(24) | NOT NULL | the case ([D19. case](D19-case.md)) |
| direction | VARCHAR(32) | NOT NULL | `in`, `out` |
| kind | VARCHAR(40) | NOT NULL | one of the kinds above |
| correlation_id | VARCHAR(128) | null | the thread the message travelled on |
| txn_id | VARCHAR(128) | null | the ledger id ([G9. Ledger](../gateway/G9-ledger.md)) |
| counterparty | VARCHAR(64) | null | the other participant, `<facility code>` form |
| summary | VARCHAR(1000) | NOT NULL, default `''` | one line for the log, cut to 1000 characters |
| payload | JSONB | null | the bundle as sent or received; left out of a list, present on a read |
| at | TIMESTAMPTZ | NOT NULL, default now | when |

#### D27K. KEYS AND INDEXES
- Primary key `id`. Unique `uq_exchange_messages_seq` on `seq`.
- Foreign key `case_id` references [D19. case](D19-case.md) `id` (`ON DELETE CASCADE`).
- Check `ck_exchange_messages_direction`.
- Indexes: `idx_exchange_messages_case` on `(case_id, seq)`; `idx_exchange_messages_correlation` on `correlation_id`.

#### D27U. USED BY
- Screens: [S3. Case Desk](../screens/S3-case-desk.md), [S11. FHIR Preview](../screens/S11-fhir-preview.md)
- APIs: [A3. Pre-auth Answer](../apis/A3-preauth-answer.md), [A4. Claim Answer](../apis/A4-claim-answer.md), [A5. Query Request](../apis/A5-query-request.md), [A6. Payment Notice](../apis/A6-payment-notice.md), [A7. Payment Enquiry Answer](../apis/A7-payment-enquiry-answer.md), [A8. Status Answer](../apis/A8-status-answer.md), [A9. Task Answer](../apis/A9-task-answer.md), [A12. Transaction FHIR](../apis/A12-txn-fhir.md), [A15. Case Exchange Log](../apis/A15-case-exchange.md), [A19. Sandbox Scenarios](../apis/A19-sandbox-scenarios.md)
- Callbacks: [C1. Callback Door](../callbacks/C1-callback-door.md), [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md), [C5. Claim Submit](../callbacks/C5-claim-submit.md), [C7. Task Submit](../callbacks/C7-task-submit.md), [C8. Status Enquiry](../callbacks/C8-status-enquiry.md), [C9. Communication](../callbacks/C9-communication.md), [C10. Payment Enquiry](../callbacks/C10-payment-enquiry.md), [C11. Payment Acknowledgement](../callbacks/C11-payment-acknowledgement.md)
- FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F7. QuestionnaireResponse](../fhir/F7-questionnaireresponse.md), [F8. Claim](../fhir/F8-claim.md), [F10. Task (claim actions and answers)](../fhir/F10-task-claim-actions.md), [F12. Communication](../fhir/F12-communication.md), [F13. PaymentNotice](../fhir/F13-paymentnotice.md)
- Database: [D19. case](D19-case.md), [D26. case_timeline](D26-case-timeline.md)
