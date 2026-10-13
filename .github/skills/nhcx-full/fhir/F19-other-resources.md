# F19. Other bundle resources

#### F19R. RESOURCE
- `Procedure`, profile `https://nrces.in/ndhm/fhir/r4/StructureDefinition/Procedure`: **sent**, one per package, in the claim-side bundles (F8).
- `Location`, no `meta.profile`: **sent**, once, in the eligibility bundle (F2).
- Nothing else. Every other resource the bundles carry has its own file (list at the end).

#### F19D. DESCRIPTION
**Procedure.** One per procedure line of the claim, so the Claim can point at what is being done. The lines (`D16 claim_line`, in order) are first grouped: ward and ICU tiers (kind `Stratification`, or a code starting `STRAT` [PAYER](../references/PAYERS.md#markers)) fold onto the procedure they were quoted through and produce no Procedure; implants produce no Procedure. Every remaining line whose kind is `Procedure` gets one.

- fullUrl `https://nhcx.abdm.gov.in/procedure/<n>`, `id` `<n>`, n from 1 in line order.
- `status` depends on the leg: `preparation` on the pre-authorisation, enhancement, query update and predetermination (treatment not yet done); `completed` on the claim (`use: claim`).
- `code` is always the generic SNOMED concept `71388002` "Procedure (procedure)" [REF](../references/PAYERS.md#markers); the package is named in `code.text`. The package code itself goes on the Claim's `item[].productOrService` (F8), not here.
- `performedDateTime`: on the claim, the surgery date (`D20 claim_submission.surgery_date`) when recorded, else the admission; on every other leg the admission (`D9 claim.admission_date`). Dates are sent as instants: a bare date becomes `T00:00:00+05:30`.
- The Claim refers to each one from `procedure[]` (F8): `id` `Procedure/<n>`, `sequence` n, `type` the plan's procedure type for the package under `https://nhcx.abdm.gov.in/procedure-type` (code lower-cased, display capitalised; `conservative` when the plan does not say), `date` the same instant, `procedureReference` `{reference: <fullUrl>, display: <package display>}`. An item that is a procedure lists its own sequence in `procedureSequence`; any other item lists all of them.

On a LAMA or DAMA claim discharged before or during surgery the claim lines collapse to the single package `LM100`, so the claim carries one Procedure for it [PAYER](../references/PAYERS.md#markers).

**Location.** The facility as the place of service, referenced by `CoverageEligibilityRequest.facility` (F2). Fixed shape: the facility name and a pointer to the provider Organization. Same for every eligibility purpose. It is not sent in claim bundles.

**Not carried.** The claim-side bundles carry no Encounter, Condition, DocumentReference, Binary or Observation. Diagnoses ride on `Claim.diagnosis` (ICD-10 codings, F8); documents ride inline as base64 attachments on `Claim.supportingInfo` (F8) and `Communication.payload` (F12); admission, surgery and discharge dates ride on `Claim.supportingInfo` scalars (F8).

**Received.** Neither Procedure nor Location is read from any payer bundle. The payer's eligibility reply repeats the request's Location; it is ignored.

#### F19F. FIELDS
**Procedure (sent)**

| Element path | Value or source | Cardinality / notes |
|---|---|---|
| `id` | `1`, `2`, ... | |
| `meta.profile[0]` | `.../StructureDefinition/Procedure` | |
| `status` | `preparation` (pre-auth, enhancement, query update, predetermination), `completed` (claim) | |
| `code.coding[0]` | `http://snomed.info/sct` `71388002` "Procedure (procedure)" | constant |
| `code.text` | `D16 claim_line.display` | the package name |
| `subject` | `{reference: "https://nhcx.abdm.gov.in/patient"}` | F15 |
| `performedDateTime` | claim: `D20 claim_submission.surgery_date`, else `D9 claim.admission_date`; other legs: `D9 claim.admission_date`; as an instant | |

Not sent: `performer`, `reasonCode`, `bodySite`, `encounter`, `outcome`, `note`.

**Location (sent)**

| Element path | Value or source | Notes |
|---|---|---|
| `resourceType` | `Location` | fullUrl `https://nhcx.abdm.gov.in/location` |
| `name` | `D1 organization.name` (the default facility), else its HFR id | |
| `managingOrganization` | `{reference: "https://nhcx.abdm.gov.in/provider"}` | F17 |

No `id`, `meta`, `identifier`, `address` or `type`.

#### F19U. USED BY
- APIs: [A2. Coverage Eligibility Check](../apis/A2-coverage-eligibility-check.md), [A4. Pre-auth Submit](../apis/A4-preauth-submit.md), [A5. Claim Submit](../apis/A5-claim-submit.md)
- Callbacks: [C2. Coverage Eligibility Verdict](../callbacks/C2-coverage-eligibility-on-check.md)
- FHIR: [F1. Bundle](F1-bundle.md), [F2. CoverageEligibilityRequest](F2-coverage-eligibility-request.md), [F8. Claim](F8-claim.md)
