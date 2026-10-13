# D24. case_document_file

#### D24T. TABLE
One row is the body of one document ([D23. case_document](D23-case-document.md)) that arrived inline; primary key `document_id`. The reference implementation names it `payer_case_document_files` [REF](../references/PAYERS.md#markers).

#### D24D. DESCRIPTION
Held apart from the document row so a case with forty documents is read far more often than any one of them is opened: the case reads [D23. case_document](D23-case-document.md) alone, and the bytes come out only through `GET cases/:id/documents/:docId/file`, which answers with the content type the document was sent with.

Create:
- Written with the document by [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md), [C5. Claim Submit](../callbacks/C5-claim-submit.md) and [C9. Communication](../callbacks/C9-communication.md) when the attachment carried `data` (base64, decoded on the way in). The content type is the attachment's; when it carried none, `application/pdf`, or `image/jpeg` for an image. A document that arrived as a bare URL has no row here.

Update, delete:
- Never on their own; cascade with the document.

A target that keeps files outside the database (object storage, a file share) replaces this table with a locator on [D23. case_document](D23-case-document.md) and keeps the same route [REF](../references/PAYERS.md#markers).

#### D24C. COLUMNS
| column | type | null/default | meaning (and allowed values) |
|---|---|---|---|
| document_id | VARCHAR(24) | primary key | the document ([D23. case_document](D23-case-document.md)) |
| content_type | VARCHAR(120) | NOT NULL | the MIME type served |
| body | BYTEA | NOT NULL | the bytes |

#### D24K. KEYS AND INDEXES
- Primary key `document_id`.
- Foreign key `document_id` references [D23. case_document](D23-case-document.md) `id` (`ON DELETE CASCADE`).

#### D24U. USED BY
- Screens: [S3. Case Desk](../screens/S3-case-desk.md)
- Callbacks: [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md), [C5. Claim Submit](../callbacks/C5-claim-submit.md), [C9. Communication](../callbacks/C9-communication.md)
- FHIR: [F8. Claim](../fhir/F8-claim.md), [F12. Communication](../fhir/F12-communication.md)
- Database: [D23. case_document](D23-case-document.md)
