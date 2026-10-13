# D20. case_diagnosis

#### D20T. TABLE
One row is one diagnosis on one case ([D19. case](D19-case.md)); primary key `(case_id, code)`. The reference implementation names it `payer_case_diagnoses` [REF](../references/PAYERS.md#markers).

#### D20D. DESCRIPTION
The diagnoses as the hospital declared them: the ICD-10 code, its description and whether it is the primary or a secondary diagnosis. "At most one primary diagnosis per case" is carried as a partial unique index, because it is the rule the whole adjudication hangs off.

Create:
- Written with the case by [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md) from `Claim.diagnosis[]` ([F8. Claim](../fhir/F8-claim.md)): the code and display of the coding, the type from `diagnosis.type` (`principal` read as `primary`, anything else `secondary`), in the order sent; or from the desk's own case form ([S3. Case Desk](../screens/S3-case-desk.md)) [SANDBOX](../references/PAYERS.md#markers). A second primary is refused by the index.

Update, delete:
- Never on their own; the desk shows them ([S3. Case Desk](../screens/S3-case-desk.md)) and the ClaimResponse ([F9. ClaimResponse](../fhir/F9-claimresponse.md)) does not echo them. Cascade with the case.

#### D20C. COLUMNS
| column | type | null/default | meaning (and allowed values) |
|---|---|---|---|
| case_id | VARCHAR(24) | primary key part | the case ([D19. case](D19-case.md)) |
| code | VARCHAR(16) | primary key part | the ICD-10 code |
| description | VARCHAR(300) | NOT NULL | the coding's display |
| type | VARCHAR(32) | NOT NULL | `primary`, `secondary` |
| position | INTEGER | NOT NULL, default 0 | order as sent |

#### D20K. KEYS AND INDEXES
- Primary key `(case_id, code)`.
- Foreign key `case_id` references [D19. case](D19-case.md) `id` (`ON DELETE CASCADE`).
- Check `ck_diagnoses_type`.
- Unique index `uq_diagnoses_primary` on `case_id` where `type = 'primary'`.
- Indexes: `idx_diagnoses_order` on `(case_id, position)`; `idx_diagnoses_code` on `code`.

#### D20U. USED BY
- Screens: [S3. Case Desk](../screens/S3-case-desk.md)
- Callbacks: [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md)
- FHIR: [F8. Claim](../fhir/F8-claim.md), [F11. CommunicationRequest](../fhir/F11-communicationrequest.md), [F19. Other resources](../fhir/F19-other-resources.md)
- Database: [D19. case](D19-case.md)
