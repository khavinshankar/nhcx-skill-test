# F15. Patient

#### F15R. RESOURCE
- `resourceType`: `Patient`
- Profile in `meta.profile`: `https://nrces.in/ndhm/fhir/r4/StructureDefinition/Patient`
- Direction: **sent** at `https://nhcx.abdm.gov.in/patient` in every claim-side bundle and in the eligibility bundle. **Received**: the payer's own Patient in the eligibility reply, read back onto the claim.

#### F15D. DESCRIPTION
The beneficiary. Three variants are sent, all at fullUrl `https://nhcx.abdm.gov.in/patient` and all referenced from the other entries by that url:

| Variant | Bundle | Built from | Content |
|---|---|---|---|
| Claim-bundle Patient | pre-auth, predetermination, enhancement, query update (F8 via A4), claim (F8 via A5) | the admitted patient, with the claim row as fallback | identifiers, name, phone, gender, birth date; `id` `1` |
| Communication-reply Patient | reply to a query (F12 via A7) | lifted unchanged from the queried leg's sent bundle; when no leg went out, built as the claim-bundle Patient from the **claim row only** | as above |
| Eligibility Patient | CoverageEligibilityRequest bundle (F2 via A2) | the member id alone | two identifiers, nothing else; no `id` |

**Identifiers.** The member id goes twice: typed `PMJAY` and typed `MB` [PAYER](../references/PAYERS.md#markers). On the claim-bundle Patient the ABHA number sits between them when the claim has one. No `system` on any of them. The facility MRN, the ABHA address and the patient's own `D3 patient.abha_number` are not sent.

**Fallbacks.** The claim-bundle Patient takes each demographic from the admitted patient (`D3 patient`, the one the claim is linked to through `D9 claim.patient_id` when the admission is linked; linking requires a current IPD stay of a patient whose ABHA number matches the claim's, digits only, so a linked claim always has an ABHA to send) and falls back to the claim row. The claim row's values come from the policy search (A1: name, ABHA number, mobile number) and are overwritten by the payer's Patient when an eligibility reply arrives (C2: name, gender, birth date, ABHA, address, photo). A pre-auth or claim cannot be built without a linked admission ("Link the admitted patient before submitting."), so in those bundles the admitted patient normally supplies name, gender and phone, which the patient table requires.

**Eligibility Patient.** Demographics are deliberately not sent: they are the payer's to return. The builder takes the identifiers only, so A2 need not read the linked patient at all (a check runs before any patient is linked); a name, gender, birth date, phone, MRN, district or state handed to it is ignored.

#### F15F. FIELDS
**Claim-bundle Patient (sent)**

| Element path | Value or source | Cardinality / notes |
|---|---|---|
| `id` | `1` | |
| `meta.profile[0]` | `.../StructureDefinition/Patient` | |
| `identifier[0].type` | `PMJAY` "Pradhan Mantri Jan Aarogya Yojana (PMJAY) ID" under `https://nrces.in/ndhm/fhir/r4/CodeSystem/ndhm-identifier-type-code` | always, also for non-PMJAY payers [PAYER](../references/PAYERS.md#markers) |
| `identifier[0].value` | `D9 claim.member_id` | required on the claim |
| `identifier[1].type` | `ABHA` "Ayushman Bharat Health Account (ABHA) ID" under `ndhm-identifier-type-code` | only when `D9 claim.abha_number` is set |
| `identifier[1].value` | `D9 claim.abha_number`, trimmed | |
| `identifier[last].type` | `MB` "Member Number" under `http://terminology.hl7.org/CodeSystem/v2-0203` | always |
| `identifier[last].value` | `D9 claim.member_id` | |
| `name[0].text` | `D3 patient.name`, else `D9 claim.beneficiary_name` | always present, empty text if both are empty |
| `telecom[0]` | `{system: "phone", value: D3 patient.phone, else D9 claim.mobile_number}` | only when a phone is known |
| `gender` | `D3 patient.gender`, else `D9 claim.patient_gender`, lower-cased | only when known |
| `birthDate` | `D3 patient.birth_date`, else `D9 claim.patient_dob` | only when known |

Not sent: `address`, `photo`, `given`/`family` names, MRN, ABHA address, `active`, `deceased`.

**Eligibility Patient (sent)**

| Element path | Value or source |
|---|---|
| `meta.profile[0]` | `.../StructureDefinition/Patient` |
| `identifier[0]` | type `PMJAY` (as above), value the member id entered on the check form (A2) |
| `identifier[1]` | type `MB` (as above), value the same member id |
| `identifier[]` typed `ABHA` | the ABHA number searched on, only on a discovery that also gives a member id (A2) |
| `identifier[]` typed `ADN` "Adhaar number" under `ndhm-identifier-type-code` | the Aadhaar number given as additional information on a discovery (A2), 12 digits; absent otherwise |
| `telecom[0]` | `{system: "phone", value: <mobile>}`, the mobile given as additional information on a discovery; absent otherwise |

**Payer's Patient (received, eligibility reply)**. The reply repeats the request's Patient and appends the payer's; the **last** Patient in the bundle is read onto `D9 claim`:

| Element path | Stored in |
|---|---|
| `name[0].text`, else `given` joined with spaces, else `family` | `beneficiary_name` |
| `gender` | `patient_gender` |
| `birthDate` | `patient_dob` |
| `address[0].line[]`, `.district`, `.state`, `.postalCode` | `patient_address`, joined with `, ` |
| `identifier[]` whose first type coding code is `ABHA` | `abha_number` |
| `photo[0].data`, else `photo[0].url` | `patient_photo` |

Empty values are not written. Patients in ClaimResponse, Task, communication and payment bundles are not read.

#### F15U. USED BY
- Screens: [S17. Beneficiary Discovery](../screens/S17-beneficiary-discovery.md)
- APIs: [A2. Coverage Eligibility Check](../apis/A2-coverage-eligibility-check.md), [A4. Pre-auth Submit](../apis/A4-preauth-submit.md), [A5. Claim Submit](../apis/A5-claim-submit.md), [A7. Communication Reply](../apis/A7-communication-on-request.md)
- Callbacks: [C2. Coverage Eligibility Verdict](../callbacks/C2-coverage-eligibility-on-check.md), [C3. Authorisation Requirements Ruling](../callbacks/C3-auth-requirements-on-check.md), [C5. Pre-auth Reply](../callbacks/C5-preauth-on-submit.md), [C6. Claim Reply](../callbacks/C6-claim-on-submit.md), [C7. Cancel Reply](../callbacks/C7-cancel-on-submit.md), [C8. Enquiry Reply](../callbacks/C8-enquiry-on-submit.md), [C9. Payer Communication](../callbacks/C9-communication-request.md)
- FHIR: [F2. CoverageEligibilityRequest](F2-coverage-eligibility-request.md), [F7. QuestionnaireResponse](F7-questionnaireresponse.md), [F8. Claim](F8-claim.md), [F12. Communication](F12-communication.md), [F18. Coverage](F18-coverage.md), [F19. Other bundle resources](F19-other-resources.md)
