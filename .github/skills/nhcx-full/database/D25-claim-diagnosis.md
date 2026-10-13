# D25. claim_diagnosis

#### D25T. TABLE
One row is one diagnosis quoted on a claim's pre-authorisation draft, held in both SNOMED and ICD-10. Primary key `id`. Parent table: `claim` (D9).

#### D25D. DESCRIPTION
**Written.** Only by saving the pre-authorisation draft (S4), which needs a linked admission. The save runs in one transaction: every D25, D26 and D27 row of the claim is deleted, then the new sets are inserted with `seq` 1, 2, 3 in order. There is no single-row edit or delete.

Where the diagnoses come from:

1. The linked admission first. Every `condition` (D5) on the claim's encounter (D4) with category `diagnosis` and clinical status other than `resolved` is taken, in id order. A condition whose SNOMED code is in the `diagnosis` terminology (D8) is quoted through that term; one that is not but has an ICD-10 code is quoted as recorded (its SNOMED and ICD-10 codes and displays, the condition text standing in for a missing display).
2. Only when the admission has recorded none are the diagnoses picked on the form used; each must be a `diagnosis` term.

For a term: `snomed_code` and `snomed_display` are the term's code and display; `icd10_code` and `icd10_display` are its secondary coding (`alt_code`, `alt_display`), falling back to the primary code and display. At least one diagnosis is required; with none, the save is refused and the desk is told to record the diagnosis on the admission or pick one on the form, because the payer needs an ICD-10 code.

**Read.** Every pre-authorisation, enhancement, predetermination and claim bundle requires at least one row ("Quote at least one ICD-10 diagnosis.") and sends each row's ICD-10 code and display as a Claim diagnosis, in `seq` order.

**Deleted.** On every draft save (replaced), by cascade with the claim, or when the transactional store is cleared. There is no status column.

#### D25C. COLUMNS
| Column | Type | Null / default | Meaning |
|---|---|---|---|
| id | INTEGER | primary key | Row id |
| claim_id | INTEGER | NOT NULL | The claim (D9) |
| seq | INTEGER | NOT NULL, default 1 | Order on the draft, from 1 |
| snomed_code | TEXT | null | SNOMED CT code (empty string when the admission recorded only ICD-10) |
| snomed_display | TEXT | null | SNOMED CT display |
| icd10_code | TEXT | NOT NULL | ICD-10 code the payer reads |
| icd10_display | TEXT | null | ICD-10 display |

#### D25K. KEYS AND INDEXES
- Primary key `id` (integer).
- Foreign key `claim_id` references `claim (id)` (D9), `ON DELETE CASCADE`.
- Index `ix_claim_dx` on `(claim_id, seq)`.
- The codes are not foreign keys; they are copied from `condition` (D5) or `terminology` (D8).

#### D25U. USED BY
- Screens: [S4. Claim Creation Form](../screens/S4-claim-creation-form.md)
- FHIR: [F8. Claim](../fhir/F8-claim.md)
- Database: [D5. condition](D5-condition.md), [D9. claim](D9-claim.md), [D18. claim_preauth](D18-claim-preauth.md), [D19. claim_predetermination](D19-claim-predetermination.md), [D26. claim_care_team](D26-claim-care-team.md), [D27. claim_item](D27-claim-item.md)
