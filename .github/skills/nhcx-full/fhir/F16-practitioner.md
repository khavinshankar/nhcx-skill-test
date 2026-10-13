# F16. Practitioner and PractitionerRole

#### F16R. RESOURCE
- `Practitioner`, profile `https://nrces.in/ndhm/fhir/r4/StructureDefinition/Practitioner`: **sent**, one per care-team doctor, in the claim-side bundles (F8) and carried again in a communication reply (F12).
- `PractitionerRole`, profile `https://nrces.in/ndhm/fhir/r4/StructureDefinition/PractitionerRole`: **sent**, once, as the enterer of the eligibility request (F2).
- Neither is read when received.

#### F16D. DESCRIPTION
**Practitioner (the care team).** The treating team saved on the pre-auth draft (`D26 claim_care_team`, in `seq` order) joined to the doctor's record (`D2 practitioner`). A team member whose practitioner row no longer exists is skipped. At least one member is required: "Add at least one doctor to the care team."

- First member: fullUrl `https://nhcx.abdm.gov.in/practitioner`, `id` `1`. Second and later: `https://nhcx.abdm.gov.in/practitioner/<n>`, `id` `<n>`.
- The Claim names each one on `careTeam[]` (F8): `sequence` n, `provider` the fullUrl, `role` `primary` "Primary provider" for the first and `assist` "Assisting Provider" for the rest (under `http://terminology.hl7.org/CodeSystem/claimcareteamrole`; the role saved on `D26 claim_care_team.role` is not used), and `qualification` the specialty: SNOMED `D2 practitioner.specialty_code` with `specialty_display`, else `{text: specialty_display}`, else none.
- Every Claim `item` lists every care-team sequence in `careTeamSequence`.

**HPR id.** One value, `D2 practitioner.identifier_value`, goes out twice: typed `HPID` under the NHCX system, and typed `HPIN` under the Healthcare Professionals Registry system `https://hpr.abdm.gov.in`. PMJAY's payer service looks the practitioner up by the `HPIN` one (PAYR-1083 without it) [PAYER](../references/PAYERS.md#markers). The value is sent whatever `D2 practitioner.identifier_type_code` says it is (HPID or a registration number). When it is empty, the practitioner's row id is sent instead [REF](../references/PAYERS.md#markers).

**Degree coding (HL7 v2-0360).** The qualification goes out as a coding under `http://terminology.hl7.org/CodeSystem/v2-0360`, whose display must be the table's own wording, so the practitioner's qualification as written (`D2 practitioner.qualification_display`) is read for the highest degree it names. `D2 practitioner.qualification_code` and `qualification_system` are not used. The text is upper-cased and split on spaces, commas, brackets, `/` and `;`; leading and trailing dots are stripped from each part. Then, first match wins (this mapping is [REF](../references/PAYERS.md#markers)):

| Condition | Code | Display |
|---|---|---|
| a part `BSC` and `NURS` anywhere in the text | `RN` | Registered Nurse |
| a part `PHD` | `PHD` | Doctor of Philosophy |
| a part `MS` or `MCH` | `MS` | Master of Science |
| a part `DO` | `DO` | Doctor of Osteopathy |
| a part `BDS` or `MDS` | `DDS` | Doctor of Dental Surgery |
| a part `RN` or `GNM` | `RN` | Registered Nurse |
| anything else, or empty | `MD` | Doctor of Medicine |

So `MBBS, MD (General Medicine)` is `MD`, `MBBS, MS (Ortho)` is `MS`, and `M.S.` (an inner dot survives) is `MD`. Because the default always yields a coding, every sent Practitioner carries a `qualification`.

**Licence.** The builder adds a licence identifier (type `MD` "Medical License number") only when given a licence number; the claim builder never passes one, so it is not sent.

**PractitionerRole (eligibility enterer).** A fixed resource at `https://nhcx.abdm.gov.in/practitioner-role`, referenced by `CoverageEligibilityRequest.enterer`: SNOMED `307988006` "Medical technician" [REF](../references/PAYERS.md#markers). It names no Practitioner and no Organization. Same for every purpose (discovery, validation, benefits, auth-requirements).

#### F16F. FIELDS
**Practitioner (sent)**

| Element path | Value or source | Cardinality / notes |
|---|---|---|
| `id` | `1`, `2`, ... in care-team order | |
| `meta.profile[0]` | `.../StructureDefinition/Practitioner` | |
| `identifier[0].type` | `HPID` "Healthcare Professional ID (HPID)" under `https://nrces.in/ndhm/fhir/r4/CodeSystem/ndhm-identifier-type-code` | always |
| `identifier[0].system` | `https://nhcx.abdm.gov.in` | |
| `identifier[0].value` | `D2 practitioner.identifier_value`, else `D2 practitioner.id` | |
| `identifier[1]` (licence) | type `MD` "Medical License number" (v2-0203), system `https://nhcx.abdm.gov.in` | never sent by the claim builder (no licence number is passed) |
| `identifier[last].type` | `HPIN` "Health Practitioner ID issued by NDHM" under `ndhm-identifier-type-code` | always |
| `identifier[last].system` | `https://hpr.abdm.gov.in` | |
| `identifier[last].value` | same value as the HPID | |
| `name[0].text` | `D2 practitioner.name` | always |
| `qualification[0].code.coding[0]` | system `http://terminology.hl7.org/CodeSystem/v2-0360`, code and display from the degree table above, read off `D2 practitioner.qualification_display` | always |

Not sent: `gender`, `telecom`, `prefix`, `active`, specialty (the specialty rides on `Claim.careTeam.qualification`).

**PractitionerRole (sent)**

| Element path | Value or source |
|---|---|
| `meta.profile[0]` | `.../StructureDefinition/PractitionerRole` |
| `code[0].coding[0]` | system `http://snomed.info/sct`, code `307988006`, display `Medical technician` |

No `id`, `practitioner`, `organization` or `specialty`.

#### F16U. USED BY
- Screens: [S16. Practitioner Master](../screens/S16-practitioner-master.md)
- APIs: [A2. Coverage Eligibility Check](../apis/A2-coverage-eligibility-check.md), [A4. Pre-auth Submit](../apis/A4-preauth-submit.md), [A5. Claim Submit](../apis/A5-claim-submit.md), [A7. Communication Reply](../apis/A7-communication-on-request.md)
- Callbacks: [C2. Coverage Eligibility Verdict](../callbacks/C2-coverage-eligibility-on-check.md), [C9. Payer Communication](../callbacks/C9-communication-request.md)
- FHIR: [F2. CoverageEligibilityRequest](F2-coverage-eligibility-request.md), [F8. Claim](F8-claim.md)
