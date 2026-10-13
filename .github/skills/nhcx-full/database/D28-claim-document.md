# D28. claim_document

#### D28T. TABLE
One row is one supporting file (PDF or image) attached to a claim for one leg, stored inline with the payer requirement it answers. Primary key `id`. Parent table: `claim` (D9).

#### D28D. DESCRIPTION
**Created.** Every path goes through one insert that checks the file:

- The claim must exist.
- The content type (lower-cased, parameters dropped) must be `application/pdf`, `image/jpeg`, `image/png` or `image/webp`.
- The file must not be empty and must be at most 10 MB (10 * 1024 * 1024 bytes) [REF](../references/PAYERS.md#markers).
- `filename` defaults to `document`; blank `label`, `code` and `category` are stored as null; `stage` defaults to `preauth`; `size` is the byte count; `uploaded_at` is now.

The paths that create rows:

| Path | Screen | code | category | stage | Replaces |
|---|---|---|---|---|---|
| Attach any files under a chosen code | S9 (or S11 with `stage` `claim`) | the code chosen (the payer's, or one of the common codes below) | null | `preauth` or `claim` | nothing |
| Attach against a payer requirement | S9 | the requirement's code | `INV` | `preauth` | every other row on the claim with the same `code` |
| Attach claim-stage requirements | S11 | the requirement's code | `INV` | `claim` | every other row on the claim with the same `code` |
| Discharge summary | S11 | `HDS` | `HDS` | `claim` | every other `HDS` row on the claim |
| File answer to a form question | S9, S11 | null | null | the form's leg | nothing (D17 holds the id) |
| New file on a query reply | S10 | the requirement's or chosen code | null | the queried leg (D23 `stage`) | nothing |

A requirement must be one the payer named for that leg, from the auth-requirements ruling (D15) when there is one, else the package master (D11). The replace step deletes by `claim_id` and `code` only, whatever the stage.

Common codes offered on every upload: `CD` Clinical document (the default), `HDS` Hospital discharge summary, `DIA` Diagnostic and laboratory reports, `RAD` Radiology / scan reports, `PRE` Doctor's prescription notes, `CER` Medical certificate / referral, `EST` Cost estimate, `MB` Medical and pharmacy bills, `INV` Final hospital invoice, `OTR` Operation theatre notes, `ICU` ICU chart, `IMP` Implant invoice and sticker, `POI` Proof of identity, `KYC` KYC / bank proof, `FCF` Filled claim form, `PAU` Pre-authorisation approval letter, `ODN` Other document [PAYER](../references/PAYERS.md#markers).

**Read.**

- A leg's bundle (pre-authorisation, enhancement, query answer, predetermination on `preauth`; claim on `claim`) carries the rows of its own `stage`, except rows used as a form's file answer (those ride inside the QuestionnaireResponse). Each goes with its `code` (else `ODN`), its `category` (else `INV`) [REF](../references/PAYERS.md#markers), its `label` (else `filename`), content type and base64 data.
- On the claim, the discharge summary is the claim-stage row whose code the payer named as a discharge summary, else the newest `HDS` row. It is sent under the `HDS` category and left out of the ordinary attachments.
- Without a ruling, a document required for the claim is no longer asked for when a `preauth` row already carries its code.
- A query reply (D23) and a reprocess request (D29) may attach any rows of the claim, by id.
- Viewing a row serves `data` inline under `content_type`.

**Deleted.** "Remove" on S9 or S11 (the claim-stage documents card) deletes one row and returns to S9. Rows are also replaced as in the table above, removed by cascade with the claim, or cleared with the transactional store. A D17 answer or D23 / D29 id list that pointed at a deleted row is left as it is. There is no status column.

#### D28C. COLUMNS
| Column | Type | Null / default | Meaning |
|---|---|---|---|
| id | INTEGER | primary key | Row id |
| claim_id | INTEGER | NOT NULL | The claim (D9) |
| filename | TEXT | NOT NULL | Uploaded file name (default `document`) |
| content_type | TEXT | NOT NULL | `application/pdf`, `image/jpeg`, `image/png`, `image/webp` |
| label | TEXT | null | Title shown and sent; a requirement's display, a form question's text, `Hospital discharge summary`, or what was typed |
| code | TEXT | null | Payer requirement code it answers (for example `MAND0671` [PAYER](../references/PAYERS.md#markers)), a common code, or `HDS`. Migration also adds it |
| category | TEXT | null | Supporting-info category: `INV`, `HDS`, or null (sent as `INV`). Migration also adds it |
| stage | TEXT | NOT NULL, default `preauth` | Leg it was attached for: `preauth` or `claim`. Migration also adds it |
| size | INTEGER | NOT NULL, default 0 | Size in bytes |
| data | BLOB | NOT NULL | The file |
| uploaded_at | TEXT | NOT NULL | When it was attached |

#### D28K. KEYS AND INDEXES
- Primary key `id` (integer).
- Foreign key `claim_id` references `claim (id)` (D9), `ON DELETE CASCADE`.
- Index `ix_claim_doc` on `(claim_id, id)`.
- Referenced without a foreign key by D17 (`answer` of a file question), D23 (`reply_documents`) and D29 (`document_ids`).

#### D28U. USED BY
- Screens: [S9. Pre-authorisation](../screens/S9-preauthorisation.md), [S10. Communication](../screens/S10-communication.md), [S11. Claim Submission](../screens/S11-claim-submission.md)
- APIs: [A7. Communication Reply](../apis/A7-communication-on-request.md), [A17. Claim State](../apis/A17-claim-state.md), [A18. Biometric Authentication](../apis/A18-biometric-authentication.md)
- FHIR: [F7. QuestionnaireResponse](../fhir/F7-questionnaireresponse.md), [F8. Claim](../fhir/F8-claim.md), [F10. Task (claim actions)](../fhir/F10-task-claim-actions.md), [F12. Communication](../fhir/F12-communication.md)
- Database: [D9. claim](D9-claim.md), [D15. claim_auth_requirement](D15-claim-auth-requirement.md), [D17. claim_form_answer](D17-claim-form-answer.md), [D18. claim_preauth](D18-claim-preauth.md), [D19. claim_predetermination](D19-claim-predetermination.md), [D23. claim_query](D23-claim-query.md), [D29. claim_enquiry](D29-claim-enquiry.md)
