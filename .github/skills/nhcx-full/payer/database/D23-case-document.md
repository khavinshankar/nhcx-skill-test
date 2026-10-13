# D23. case_document

#### D23T. TABLE
One row is one document on one case ([D19. case](D19-case.md)): what it is filed as, which phase it belongs to, and where its bytes are; primary key `id`. Parent tables [D19. case](D19-case.md) and [D3. document_type](D3-document-type.md). The reference implementation names it `payer_case_documents` [REF](../references/PAYERS.md#markers).

#### D23D. DESCRIPTION
The evidence. Documents arrive on a pre-authorisation or claim ([F8. Claim](../fhir/F8-claim.md) `supportingInfo` attachments, [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md), [C5. Claim Submit](../callbacks/C5-claim-submit.md)), on a query reply ([F12. Communication](../fhir/F12-communication.md) attachments, [C9. Communication](../callbacks/C9-communication.md)), on a resubmission, or from the desk ([S3. Case Desk](../screens/S3-case-desk.md), `POST cases/:id/documents`). Each is filed under a code from [D3. document_type](D3-document-type.md): the hospital's own code when the taxonomy has it, else the code whose NDHM category matches, else `ODN` with the original code named on the timeline ([D26. case_timeline](D26-case-timeline.md)). A document under an unknown code is filed, not dropped.

**Taken in once.** The exchange redelivers, and a second copy of the application sharing the database files the same message again. A document already on the case under the same code, title and size is that document, not a second one, and is not filed twice.

**Where the bytes are.** A document that arrived inline (`valueAttachment.data`, `contentAttachment.data`) has its bytes in [D24. case_document_file](D24-case-document-file.md) and is served by `GET cases/:id/documents/:docId/file` as the content type it was sent with; one that arrived as a bare `url` has no row there, the URL is all there is, and the file route answers 404. The case lists each document with `has_file`.

`phase` is `preauth` or `claim`: the leg the document belongs to. A query reply's documents are filed at the phase the case is in.

Update, delete:
- Never on their own. Cascade with the case. A document type in use cannot be removed from [D3. document_type](D3-document-type.md).

#### D23C. COLUMNS
| column | type | null/default | meaning (and allowed values) |
|---|---|---|---|
| id | VARCHAR(24) | primary key | `DOC-<random>` [REF](../references/PAYERS.md#markers) |
| case_id | VARCHAR(24) | NOT NULL | the case ([D19. case](D19-case.md)) |
| title | VARCHAR(200) | NOT NULL | the attachment's title, or the form question it answered |
| type_code | VARCHAR(24) | NOT NULL | the document type ([D3. document_type](D3-document-type.md)) it is filed as |
| phase | VARCHAR(32) | NOT NULL | `preauth`, `claim` |
| url | VARCHAR(1000) | NOT NULL | the attachment's URL as sent, or a `urn:nhcx:...` locator minted for an inline document [REF](../references/PAYERS.md#markers) |
| doc_type | VARCHAR(32) | NOT NULL | `image`, `pdf`, from the content type |
| file_size | VARCHAR(24) | null | human-readable size of an inline document |
| uploaded_at | TIMESTAMPTZ | NOT NULL, default now | the attachment's creation time when sent, else when filed |

#### D23K. KEYS AND INDEXES
- Primary key `id`.
- Foreign keys: `case_id` references [D19. case](D19-case.md) `id` (`ON DELETE CASCADE`); `type_code` references [D3. document_type](D3-document-type.md) `code` (`ON DELETE RESTRICT`).
- Checks: `ck_case_documents_phase`; `ck_case_documents_doc_type`.
- Indexes: `idx_case_documents_case` on `(case_id, phase, uploaded_at)`; `idx_case_documents_type` on `type_code`.
- Referenced by [D24. case_document_file](D24-case-document-file.md) `document_id` (`ON DELETE CASCADE`).

#### D23U. USED BY
- Screens: [S3. Case Desk](../screens/S3-case-desk.md)
- Callbacks: [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md), [C5. Claim Submit](../callbacks/C5-claim-submit.md), [C9. Communication](../callbacks/C9-communication.md)
- FHIR: [F7. QuestionnaireResponse](../fhir/F7-questionnaireresponse.md), [F8. Claim](../fhir/F8-claim.md), [F12. Communication](../fhir/F12-communication.md)
- Database: [D3. document_type](D3-document-type.md), [D19. case](D19-case.md), [D24. case_document_file](D24-case-document-file.md), [D28. nhcx_delivery](D28-nhcx-delivery.md)
