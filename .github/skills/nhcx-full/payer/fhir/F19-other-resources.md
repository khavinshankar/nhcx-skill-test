# F19. Other resources

#### F19R. RESOURCE
The resources a hospital's bundles carry beside the ones with a file of their own: `Procedure` (in the Claim bundles, [F8. Claim](F8-claim.md)), `Location` (in the eligibility request, [F2. CoverageEligibilityRequest](F2-coverage-eligibility-request.md)), and, from builders other than the reference hospital, `Condition` and `Encounter`. No profile is checked. Only the Procedure is read. This payer sends none of them.

#### F19D. DESCRIPTION
**Procedure.** One per `Claim.procedure[]` whose `procedureReference` resolves through the bundle index; an entry that resolves to nothing is skipped. The reference hospital codes every Procedure with the generic SNOMED concept `71388002` "Procedure (procedure)" and names the package in the concept's `text` and on the Claim's `procedureReference.display`; those name it, the concept does not, so the name is the reference display, else the concept text, else the coding display. The package code is then put on the procedure by the item that bills for it: the `productOrService` code of the Claim `item[]` whose `procedureSequence[]` points at the procedure's position, applied when the procedure's own code is empty or the generic concept. A procedure no item bills for keeps its name, cut to 32 characters, as its code, so the column can hold it. The `category` display is kept when there is one. `status` (`preparation` on a pre-authorisation, `completed` on a claim), `performedDateTime` and `subject` are not read: the surgery date comes from the Claim's `PSP` scalar ([F8. Claim](F8-claim.md)).

A LAMA or DAMA claim discharged before or during surgery arrives with one package line `LM100` and one Procedure for it [PAYER](../references/PAYERS.md#markers); it is filed like any other, and the discharge type says what happened.

**Location.** The facility as the place of service, referenced by `CoverageEligibilityRequest.facility`. Not read: the provider Organization ([F17. Organization](F17-organization.md)) already names the facility, and the answer needs nothing more than its registry id and name.

**Condition, Encounter.** A builder that sends diagnoses as `Condition` resources or the stay as an `Encounter` is not the reference hospital's; this payer reads diagnoses from `Claim.diagnosis` ([F8. Claim](F8-claim.md), into [D20. case_diagnosis](../database/D20-case-diagnosis.md)) and the stay from `billablePeriod` and the `supportingInfo` scalars, so both resources are ignored. A bundle carrying only a Condition or an Encounter and no Claim is not a submission ([C1. Callback Door](../callbacks/C1-callback-door.md) classifies it by its focal resource and ignores it).

**DocumentReference, Binary.** Documents ride inline on `Claim.supportingInfo` and `Communication.payload` ([F8. Claim](F8-claim.md), [F12. Communication](F12-communication.md)); a DocumentReference or Binary entry is not read.

#### F19F. FIELDS

| Element read | Stored in | Notes |
|---|---|---|
| `Claim.procedure[].procedureReference.reference` | resolves the Procedure | skipped when unresolved |
| `Claim.procedure[].procedureReference.display` | [D21. case_procedure](../database/D21-case-procedure.md) `name` | first choice for the name |
| `Procedure.code.text` | [D21. case_procedure](../database/D21-case-procedure.md) `name` | when the reference has no display |
| `Procedure.code.coding[0].code`, `.display` | [D21. case_procedure](../database/D21-case-procedure.md) `code` (unless generic), `name` fallback | `71388002` is replaced by the billing item's code |
| `Claim.item[].productOrService.coding[0].code` of the item whose `procedureSequence[]` names this procedure | [D21. case_procedure](../database/D21-case-procedure.md) `code` | the package code |
| `Procedure.category.coding[0].display` (else text) | [D21. case_procedure](../database/D21-case-procedure.md) `category` | |
| position in `Claim.procedure[]` | [D21. case_procedure](../database/D21-case-procedure.md) `position` | |
| `Location`, `Condition`, `Encounter`, `DocumentReference`, `Binary` | nothing | ignored |

The case's `snomed` and `pcs10` columns on [D21. case_procedure](../database/D21-case-procedure.md) are filled only when the hospital's code is one of them; the reference hospital sends neither, and the registry ([D10. procedure_rule](../database/D10-procedure-rule.md)) holds them for the payer's own procedures.

#### F19U. USED BY
- Callbacks: [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md), [C5. Claim Submit](../callbacks/C5-claim-submit.md)
- FHIR: [F8. Claim](F8-claim.md)
- Database: [D21. case_procedure](../database/D21-case-procedure.md)
