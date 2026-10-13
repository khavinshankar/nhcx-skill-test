# D21. case_procedure

#### D21T. TABLE
One row is one procedure on one case ([D19. case](D19-case.md)), as the hospital coded it; primary key `(case_id, code)`. The reference implementation names it `payer_case_procedures` [REF](../references/PAYERS.md#markers).

#### D21D. DESCRIPTION
What the hospital says it did or intends to do, read from the Procedure resources and the package items of the Claim bundle ([F8. Claim](../fhir/F8-claim.md), [F19. Other resources](../fhir/F19-other-resources.md)): the code, the name, and the category and clinical codings when sent. It is the hospital's statement, kept beside the registry's own procedure ([D10. procedure_rule](D10-procedure-rule.md)) rather than joined to it: a hospital may bill a package this payer has never heard of, and the adjudicator has to see that it did.

The predetermination rules ([A10. Predetermination Quote](../apis/A10-predetermination-quote.md)) and the desk ([S3. Case Desk](../screens/S3-case-desk.md)) match `code` against the member's product ([D13. policy_procedure](D13-policy-procedure.md)) to say whether the procedure is covered and at what rate.

Create:
- Written with the case by [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md) ([C5. Claim Submit](../callbacks/C5-claim-submit.md) for a direct claim), in the order sent, or from the desk's own case form [SANDBOX](../references/PAYERS.md#markers). Cascade with the case; never edited on their own.

#### D21C. COLUMNS
| column | type | null/default | meaning (and allowed values) |
|---|---|---|---|
| case_id | VARCHAR(24) | primary key part | the case ([D19. case](D19-case.md)) |
| code | VARCHAR(32) | primary key part | the procedure or package code as sent |
| name | VARCHAR(200) | NOT NULL | its display |
| category | VARCHAR(64) | null | the item's category code, when sent |
| snomed | VARCHAR(32) | null | SNOMED CT concept, when sent |
| pcs10 | VARCHAR(32) | null | ICD-10-PCS code, when sent |
| position | INTEGER | NOT NULL, default 0 | order as sent |

#### D21K. KEYS AND INDEXES
- Primary key `(case_id, code)`.
- Foreign key `case_id` references [D19. case](D19-case.md) `id` (`ON DELETE CASCADE`).
- Index `idx_case_procedures_order` on `(case_id, position)`.

#### D21U. USED BY
- Screens: [S3. Case Desk](../screens/S3-case-desk.md)
- Callbacks: [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md)
- FHIR: [F8. Claim](../fhir/F8-claim.md), [F11. CommunicationRequest](../fhir/F11-communicationrequest.md), [F19. Other resources](../fhir/F19-other-resources.md)
- Database: [D19. case](D19-case.md)
