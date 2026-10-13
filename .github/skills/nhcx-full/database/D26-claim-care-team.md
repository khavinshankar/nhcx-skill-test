# D26. claim_care_team

#### D26T. TABLE
One row is one doctor on the treating team quoted on a claim's pre-authorisation draft, with the role they play. Primary key `id`. Parent tables: `claim` (D9) and `practitioner` (D2).

#### D26D. DESCRIPTION
**Written.** Only by saving the pre-authorisation draft (S4), in the same transaction that replaces the claim's D25 and D27 rows: every D26 row of the claim is deleted, then the new team is inserted with `seq` 1, 2, 3 in order. There is no single-row edit or delete.

Where the team comes from:

1. The linked admission first. When the claim's encounter (D4) names a consultant (`encounter.practitioner_id`), the team is that one doctor with role `treating`, and the form's rows are ignored.
2. Only when the admission names none are the doctors picked on the form used. A row whose doctor is not an active practitioner (D2 `active = 1`) is skipped. A row with no role gets `treating`; a role outside the list below is refused ("Choose a valid care team role.").

At least one doctor is required; with none the save is refused and the desk is told to set the consultant on the admission or add a doctor on the form.

Roles (`role`, exact keys and their labels): `admitting` Admitting physician, `treating` Treating doctor, `surgeon` Surgeon, `anaesthetist` Anaesthetist, `nurse` Nursing lead.

**Read.** Every pre-authorisation, enhancement, predetermination and claim bundle requires at least one row ("Add at least one doctor to the care team.") and sends a Practitioner for each row whose practitioner still exists, built from D2: id, name, HPR id (`identifier_value`), qualification (as an HL7 v2-0360 degree coding) and specialty. The rows are read joined to D2 for the doctor's name.

**Deleted.** On every draft save (replaced), by cascade with the claim, or when the transactional store is cleared. A practitioner referenced here cannot be deleted while the row exists (the foreign key has no cascade); practitioners are deactivated rather than deleted. There is no status column.

#### D26C. COLUMNS
| Column | Type | Null / default | Meaning |
|---|---|---|---|
| id | INTEGER | primary key | Row id |
| claim_id | INTEGER | NOT NULL | The claim (D9) |
| seq | INTEGER | NOT NULL, default 1 | Order on the draft, from 1 |
| practitioner_id | INTEGER | NOT NULL | The doctor (D2) |
| role | TEXT | NOT NULL | `admitting`, `treating`, `surgeon`, `anaesthetist`, `nurse` |

#### D26K. KEYS AND INDEXES
- Primary key `id` (integer).
- Foreign key `claim_id` references `claim (id)` (D9), `ON DELETE CASCADE`.
- Foreign key `practitioner_id` references `practitioner (id)` (D2), `ON DELETE PROTECT` (a practitioner named on a sent care team is retired, never deleted; the reference implementation set no action [REF](../references/PAYERS.md#markers)).
- Index `ix_claim_team` on `(claim_id, seq)`.

#### D26U. USED BY
- Screens: [S4. Claim Creation Form](../screens/S4-claim-creation-form.md), [S16. Practitioner Master](../screens/S16-practitioner-master.md)
- FHIR: [F8. Claim](../fhir/F8-claim.md), [F16. Practitioner and PractitionerRole](../fhir/F16-practitioner.md)
- Database: [D2. practitioner](D2-practitioner.md), [D9. claim](D9-claim.md), [D18. claim_preauth](D18-claim-preauth.md), [D19. claim_predetermination](D19-claim-predetermination.md), [D25. claim_diagnosis](D25-claim-diagnosis.md), [D27. claim_item](D27-claim-item.md)
