# F16. Practitioner

#### F16R. RESOURCE
`Practitioner`, received in a hospital's Claim bundle ([F8. Claim](F8-claim.md)), one per care-team member the Claim points at from `careTeam[].provider`. No profile is checked. The `PractitionerRole` an eligibility request carries as its enterer is not read. This payer sends no Practitioner: its answers name organisations, not people.

#### F16D. DESCRIPTION
The treating team as the hospital declared it. These clinicians work for the provider, not the payer, so the case keeps them as rows of its own ([D22. case_doctor](../database/D22-case-doctor.md)) rather than as references to a doctors table this payer does not have; the HPR id is the only handle that survives the exchange.

**How it is read.** Each `careTeam[]` entry's `provider` reference is followed through the bundle index (by `fullUrl`, else `ResourceType/id`); an entry whose reference resolves to nothing is skipped rather than failing the submission. From the Practitioner: the name (text, else given and family joined) and the first identifier's value as the HPR id, whatever type the hospital gave it (the reference sends the same value twice, typed `HPID` and `HPIN` [REF](../references/PAYERS.md#markers); only the first is read). From its first `qualification[].code`, the display as the qualification (the coding is the HL7 degree table, `MD`, `MS` and so on, so the display is what a person reads). From the `careTeam[]` entry itself, the `role` display (`Primary provider`, `Assisting Provider`). A member with neither name nor identifier is dropped.

**Doctor of record.** The first member kept is the treating doctor of record; the case allows one, and the schema holds that as a unique index ([D22. case_doctor](../database/D22-case-doctor.md)). The order is the Claim's `careTeam` order.

**Specialty.** The `careTeam[].qualification` (a SNOMED specialty) is not read; the specialty column takes the qualification display when the hospital sent nothing else [REF](../references/PAYERS.md#markers). `telecom`, `gender`, `active` and a licence identifier are not read.

#### F16F. FIELDS

| Element read | Stored in | Notes |
|---|---|---|
| `Claim.careTeam[].provider.reference` | resolves the Practitioner | skipped when unresolved |
| `Practitioner.name[0].text`, else `given[]` joined with `family` | [D22. case_doctor](../database/D22-case-doctor.md) `name` | |
| `Practitioner.identifier[0].value` | [D22. case_doctor](../database/D22-case-doctor.md) `hfr_id` | the HPR id, whatever its type; unique per case |
| `Practitioner.qualification[0].code.coding[0].display` (else text) | [D22. case_doctor](../database/D22-case-doctor.md) `qualification`; `specialty` when nothing else names one | |
| `Claim.careTeam[].role.coding[0].display` (else text) | [D22. case_doctor](../database/D22-case-doctor.md) `role` | |
| position in `careTeam[]` | [D22. case_doctor](../database/D22-case-doctor.md) `position`; the first is `is_primary` | one doctor of record per case |

Nothing is written back to the hospital about its practitioners: the verdict ([F9. ClaimResponse](F9-claimresponse.md)) and the Task answers ([F10. Task (claim actions and answers)](F10-task-claim-actions.md)) carry the two Organizations only.

#### F16U. USED BY
- Callbacks: [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md), [C5. Claim Submit](../callbacks/C5-claim-submit.md)
- FHIR: [F8. Claim](F8-claim.md)
- Database: [D22. case_doctor](../database/D22-case-doctor.md)
