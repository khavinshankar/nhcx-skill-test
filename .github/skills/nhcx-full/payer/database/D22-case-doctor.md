# D22. case_doctor

#### D22T. TABLE
One row is one member of the treating team on one case ([D19. case](D19-case.md)), as the hospital declared it; primary key `id`. The reference implementation names it `payer_case_doctors` [REF](../references/PAYERS.md#markers).

#### D22D. DESCRIPTION
The care team is not a foreign key to a doctors table: these clinicians work for the provider, not the payer, and the registry id is the only handle that survives the exchange. Each row keeps the name, the practitioner's registry id (the HPR id from the Practitioner ([F16. Practitioner](../fhir/F16-practitioner.md)); the reference column is named `hfr_id` [REF](../references/PAYERS.md#markers)), specialty, qualification and role. The first on the list is the treating doctor of record (`is_primary`), and one case has one such doctor.

Create:
- Written with the case by [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md) ([C5. Claim Submit](../callbacks/C5-claim-submit.md) for a direct claim) from `Claim.careTeam[]` and the Practitioner resources, in the order sent, the first marked primary; or from the desk's own case form [SANDBOX](../references/PAYERS.md#markers). A short random `DR-` id [REF](../references/PAYERS.md#markers). The same practitioner twice on one case is refused (`uq_case_doctors_hfr`).

Update, delete:
- Never on their own. Cascade with the case. The desk ([S3. Case Desk](../screens/S3-case-desk.md)) shows the team; the ClaimResponse ([F9. ClaimResponse](../fhir/F9-claimresponse.md)) does not echo it.

#### D22C. COLUMNS
| column | type | null/default | meaning (and allowed values) |
|---|---|---|---|
| id | VARCHAR(24) | primary key | `DR-<random>` [REF](../references/PAYERS.md#markers) |
| case_id | VARCHAR(24) | NOT NULL | the case ([D19. case](D19-case.md)) |
| name | VARCHAR(160) | NOT NULL | the practitioner's name |
| hfr_id | VARCHAR(64) | NOT NULL | the practitioner's registry id (HPR id) as sent |
| specialty | VARCHAR(96) | NOT NULL | specialty |
| qualification | VARCHAR(160) | NOT NULL | degree or qualification |
| role | VARCHAR(96) | null | the care-team role as sent |
| is_primary | BOOLEAN | NOT NULL, default false | the treating doctor of record |
| position | INTEGER | NOT NULL, default 0 | order as sent |

#### D22K. KEYS AND INDEXES
- Primary key `id`.
- Unique `uq_case_doctors_hfr` on `(case_id, hfr_id)`.
- Foreign key `case_id` references [D19. case](D19-case.md) `id` (`ON DELETE CASCADE`).
- Unique index `uq_case_doctors_primary` on `case_id` where `is_primary`.
- Index `idx_case_doctors_order` on `(case_id, position)`.

#### D22U. USED BY
- Screens: [S3. Case Desk](../screens/S3-case-desk.md)
- Callbacks: [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md)
- FHIR: [F8. Claim](../fhir/F8-claim.md), [F11. CommunicationRequest](../fhir/F11-communicationrequest.md), [F16. Practitioner](../fhir/F16-practitioner.md)
- Database: [D19. case](D19-case.md)
