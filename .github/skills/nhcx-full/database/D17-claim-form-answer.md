# D17. claim_form_answer

#### D17T. TABLE
One row is the answer to one question of one payer form (questionnaire) on one claim. Primary key `id`. Parent table: `claim` (D9); the form itself is a `claim_plan_form` row (D12) matched by `form_url`, not by a foreign key.

#### D17D. DESCRIPTION
The payer's forms arrive with its insurance plan (D12). The forms a leg must carry are listed on Pre-authorisation (S9) and Claim Submission (S11); saving one form posts all its answers at once.

**Created and updated.** Each posted answer is trimmed, then looked up by `(claim_id, form_url, link_id)`:

- no row yet and a non-blank answer: a row is inserted with the leg it was saved for in `stage`;
- a row exists and the answer is non-blank: `answer` and `stage` are overwritten;
- the answer is blank: the existing row is deleted (a blank answer clears the question).

A file question is answered by uploading the file: it is stored as a supporting document (D28) at the same leg's stage, labelled with the question's text, and the answer holds that document's id as text. A file field posted empty is left out of the save, so re-saving a form without touching its file question keeps the file attached.

`stage` is `preauth` or `claim` (anything else is saved as `preauth`). The unique index does not include `stage`, so one question holds one answer per claim: saving the same form on the other leg overwrites the answer and moves the row to that leg. When the answers are read for a leg, a row with no `stage` counts as `preauth`.

**Deleted.** By a blank answer, by cascade when the claim is deleted, or when the transactional store is cleared.

**How the answers are read.** When a pre-authorisation, an enhancement, a query answer or a claim is built, each required form of that leg that has at least one answer becomes one QuestionnaireResponse. Each answer is converted by the question's declared type: `attachment` to `valueAttachment` (the stored document's bytes), `date` / `datetime` / `instant` to `valueDateTime`, `time` to `valueTime`, `boolean` to `valueBoolean` (`yes`, `true` or `1` is true), `integer` to `valueInteger`, `decimal` / `quantity` to `valueDecimal` (falling back to `valueString` when not a number), anything else to `valueString`. Documents given as file answers are left out of the leg's separate attachments, because they ride inside the QuestionnaireResponse.

There is no status column.

#### D17C. COLUMNS
| Column | Type | Null / default | Meaning |
|---|---|---|---|
| id | INTEGER | primary key | Row id |
| claim_id | INTEGER | NOT NULL | The claim (D9) |
| form_url | TEXT | NOT NULL | The form's `Questionnaire.url` (D12 `url`) |
| link_id | TEXT | NOT NULL | The question's `linkId` |
| answer | TEXT | null | The answer as typed or chosen; for a file question, the D28 document id as text |
| stage | TEXT | null | Leg the answer was last saved for: `preauth` or `claim`. Null is read as `preauth`. Added by migration |

#### D17K. KEYS AND INDEXES
- Primary key `id` (integer).
- Foreign key `claim_id` references `claim (id)` (D9), `ON DELETE CASCADE`.
- Unique index `ux_claim_form_answer` on `(claim_id, form_url, link_id)`. It does not include `stage`.

#### D17U. USED BY
- Screens: [S9. Pre-authorisation](../screens/S9-preauthorisation.md), [S11. Claim Submission](../screens/S11-claim-submission.md)
- FHIR: [F6. Questionnaire](../fhir/F6-questionnaire.md), [F7. QuestionnaireResponse](../fhir/F7-questionnaireresponse.md)
- Database: [D9. claim](D9-claim.md), [D12. claim_plan_form](D12-claim-plan-form.md), [D18. claim_preauth](D18-claim-preauth.md), [D28. claim_document](D28-claim-document.md)
