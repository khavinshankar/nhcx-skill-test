# D3. document_type

#### D3T. TABLE
One row is one document type in the NHCX taxonomy: a code, a name, the desk's filing category and the NDHM supporting-information category the exchange knows it by; primary key `code`. No parent table. The reference implementation names it `payer_document_types` [REF](../references/PAYERS.md#markers).

#### D3D. DESCRIPTION
A reference table rather than a free-text column, so a procedure cannot demand a document no hospital can send ([D11. procedure_rule_doc](D11-procedure-rule-doc.md)) and the code on a case document ([D23. case_document](D23-case-document.md)) always means something. The screen that shows a document and the bundle that names one read the same row, so they cannot drift apart.

Create and update:
- Loaded by the seed at first boot from the NHCX document codes (for example `CD` clinical document, `HDS` discharge summary, `DIA` diagnostics, `RAD` radiology, `PRE` prescription, `MB` medical bills, `INV` invoice, `OTR` operation notes, `ICU` ICU chart, `IMP` implant sticker, `POI` proof of identity, `KYC`, `FCF` filled claim form, `PAU` pre-auth approval letter, `ODN` other document) [REF](../references/PAYERS.md#markers). Upserted by code, so a description is corrected without disturbing the procedures that point at it. The knowledge source lists the current codes.
- The desk reads the whole list through `GET document-types` for the procedure configurator ([S9. Procedure Configurator](../screens/S9-procedure-configurator.md)) and the document filter on the case desk ([S3. Case Desk](../screens/S3-case-desk.md)).

Resolving a hospital's code:
- A document arriving on a Claim ([F8. Claim](../fhir/F8-claim.md)) or a Communication ([F12. Communication](../fhir/F12-communication.md)) is filed under its own code when the table has it, else under the code whose `si_category` matches it, else under `ODN` with the original code named on the case timeline ([D26. case_timeline](D26-case-timeline.md)) ([C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md), [C5. Claim Submit](../callbacks/C5-claim-submit.md), [C9. Communication](../callbacks/C9-communication.md)). Evidence a hospital sent is filed, never dropped.

Delete:
- Never while a procedure rule or a case document points at it (`RESTRICT`).

#### D3C. COLUMNS
| column | type | null/default | meaning (and allowed values) |
|---|---|---|---|
| code | VARCHAR(24) | primary key | the NHCX document code, upper case |
| name | VARCHAR(200) | NOT NULL | what the document is, shown on the desk and as the display in a bundle |
| category | VARCHAR(32) | NOT NULL | the desk's filing shelf: `Identity`, `Clinical`, `Financial`, `Administrative`, `Legal`, `Transport` |
| si_category | VARCHAR(24) | null | the NDHM supporting-information category code the exchange knows this document by |

#### D3K. KEYS AND INDEXES
- Primary key `code`.
- Check `ck_document_types_category`: `category` is one of the six values above.
- Index `idx_document_types_category` on `(category, code)`; index `idx_document_types_si` on `si_category`.
- Referenced by [D11. procedure_rule_doc](D11-procedure-rule-doc.md) `doc_code` and [D23. case_document](D23-case-document.md) `type_code`, both `ON DELETE RESTRICT`.

#### D3U. USED BY
- Screens: [S3. Case Desk](../screens/S3-case-desk.md), [S9. Procedure Configurator](../screens/S9-procedure-configurator.md)
- Callbacks: [C1. Callback Door](../callbacks/C1-callback-door.md), [C5. Claim Submit](../callbacks/C5-claim-submit.md)
- FHIR: [F3. CoverageEligibilityResponse](../fhir/F3-coverage-eligibility-response.md), [F5. InsurancePlan](../fhir/F5-insuranceplan.md), [F6. Questionnaire](../fhir/F6-questionnaire.md), [F8. Claim](../fhir/F8-claim.md), [F12. Communication](../fhir/F12-communication.md)
- Database: [D4. terminology_code](D4-terminology-code.md), [D10. procedure_rule](D10-procedure-rule.md), [D11. procedure_rule_doc](D11-procedure-rule-doc.md), [D23. case_document](D23-case-document.md)
