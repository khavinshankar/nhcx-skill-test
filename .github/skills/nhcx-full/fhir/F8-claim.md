# F8. Claim

#### F8R. RESOURCE
`Claim`, profile `https://nrces.in/ndhm/fhir/r4/StructureDefinition/Claim`, the anchor (`entry[0]`) of a bundle with profile `https://nrces.in/ndhm/fhir/r4/StructureDefinition/ClaimBundle` (F1). Direction: sent.

#### F8D. DESCRIPTION
One Claim document serves every leg of the episode: pre-authorisation, enhancement, predetermination, claim, and the answer to a payer query on any of them. What differs between legs is the anchor, `use`, the Procedure status, the discharge information, `preAuthRef`, the query answer and which documents and forms ride.

**Bundle entries**, in this order (F1):

| # | `fullUrl` | Resource | `id` | Spec |
|---|---|---|---|---|
| 1 | the anchor (table below) | Claim | the claim number | this file |
| 2 | `https://nhcx.abdm.gov.in/patient` | Patient | `1` | F15 |
| 3 | `.../provider` | Organization, facility | `1` | F17 |
| 4 | `.../payer` | Organization, payer | `2` | F17 |
| 5 | `.../coverage` | Coverage | `1` | F18 |
| 6 | `.../practitioner`, then `.../practitioner/2`, ... | Practitioner, one per care-team member | `1`, `2`, ... | F16 |
| 7 | `.../procedure/1`, `.../procedure/2`, ... | Procedure, one per procedure item | `1`, `2`, ... | F19 |
| 8 | `.../questionnaireresponse/1`, ... | QuestionnaireResponse, one per answered form | `1`, `2`, ... | F7 |

Every resource and every Claim list element carries an `id`, because PMJAY's payer service reads them by id and refuses an item without one (PAYR-1027 "invalid item id") [PAYER](../references/PAYERS.md#markers).

**Variants.**

| Send kind (A4, A5) | `use` | Anchor | Bundle `id` | Procedure status (F19) | Adds |
|---|---|---|---|---|---|
| Pre-authorisation | `preauthorization` | `/preauth/request` | `preauth-request-generic` | `preparation` | |
| Enhancement | `preauthorization` | `/preauth/enhancement` | `preauth-enhancement-request-generic` | `preparation` | every quoted line, old and new |
| Pre-authorisation query answer, enhancement query answer | `preauthorization` | `/preauth/queryupdate` | `preauth-queryupdate-request-generic` | `preparation` | `NMI` / `CQD` answer |
| Predetermination | `predetermination` | `/predetermination/request` | `predetermination-request-generic` | `preparation` | no QuestionnaireResponse |
| Claim, claim resubmit | `claim` | `/claim/request` | `claim-request-generic` | `completed` | discharge, `preAuthRef` |
| Claim query answer | `claim` | `/claim/queryupdate` | `claim-queryupdate-request-generic` | `completed` | discharge, `preAuthRef`, `NMI` / `CQD` answer |

The workflow id (`x-hcx-workflow_id`) is what tells the payer which round it is (A4, A5; values in [PAYERS.md](../references/PAYERS.md)) [PAYER](../references/PAYERS.md#markers). An enhancement goes under the same claim number, with no `related` link.

**Lines to items.** The quoted lines are D16 `claim_line`, read in `kind`, `seq` order (so implants come before procedures). One `item` per procedure or implant line. A ward or ICU tier (a `Stratification` line) is **not** an item: it rides as a `modifier` on the item of the procedure whose code is the tier's `parent_code`, else the first procedure, and that item's `net` carries the procedure and its tiers together [PAYER](../references/PAYERS.md#markers). A tier with no procedure at all becomes an item of its own. `unitPrice` is `net / quantity`, so FHIR's arithmetic holds.

`factor` is the multiple-procedure rule, where the payer's adapter has one (see [PAYERS.md](../references/PAYERS.md)): procedure items ranked by their own line amount (tiers not counted), the costliest at 1, the second at 0.5, the rest at 0.25 [PAYER](../references/PAYERS.md#markers). Implant items carry no factor. Generic payers get no `factor`.

**Claim leg differences.**
- The lines are the claim's lines. A LAMA or DAMA discharge at stage "Before Surgery" or "During Surgery" collapses them to one procedure line `LM100` (display and rate from the plan's `LM100` package, else "LAMA / DAMA procedure" at 0; category from the plan, else from the first quoted line), because the payer disqualifies every other item (PAYR-1362) [PAYER](../references/PAYERS.md#markers). Its `quantity` is the number of days admitted, admission date to discharge date, at least 1 (the knowledge source's `nhcx.fhir.claim-request`: "Set its quantity to the number of days admitted"), with `unitPrice` the plan's `LM100` rate and `net` rate times days [PAYER](../references/PAYERS.md#markers). Open: the knowledge source reads as a per-day rate; confirm it with the payer before go-live.
- `billablePeriod.end` is the discharge date (else the admission date).
- `insurance[0].preAuthRef` is the payer's pre-authorisation reference.
- Documents are those filed at the claim stage. The discharge summary goes as the `HDS` entry: the claim-stage document whose code is a required claim document with "discharge summary" in its display, else the latest document coded `HDS`. It goes under that document's own code (for example PMJAY's `MAND0006` [PAYER](../references/PAYERS.md#markers)).
- Discharge scalars follow the documents (table in F8F).

**Supporting information order.** Numbered from 1 in this order: documents; the discharge summary (claim); `ADDD`; `EDT`; `PSP` (claim, when a surgery date is given); `DSDE` (claim); `DTM` (claim, death only); `DIS` (claim); `CQD` (query answers); one pointer per QuestionnaireResponse (F7). Documents given as a form answer are not listed here: they ride inside the QuestionnaireResponse.

**Refusals before sending** are listed in A4 and A5 (eligible policy, linked admission, admission date, at least one diagnosis, care-team member and line; a query answer needs reply text; a claim needs a discharge mode and an approved or queried pre-authorisation).

**Read back.** The last pre-authorisation bundle sent (D18 `claim_preauth.request_json`) is read again to find which lines are new: every `item[].productOrService` code and every `modifier` code in it counts as sent. A line whose code is not there makes an enhancement due.

#### F8F. FIELDS
Claim header:

| Element | Value or source | Card / notes |
|---|---|---|
| `resourceType` | `Claim` | |
| `id` | D9 `claim.claim_no` | 1..1 |
| `meta.profile[0]` | `https://nrces.in/ndhm/fhir/r4/StructureDefinition/Claim` | |
| `identifier[0].type` | `https://nrces.in/ndhm/fhir/r4/CodeSystem/ndhm-identifier-type-code` `CLN` "Claim number" | |
| `identifier[0].system` | `https://nhcx.abdm.gov.in` | |
| `identifier[0].value` | D9 `claim.claim_no` | |
| `status` | `active` | |
| `type` | `http://snomed.info/sct` `737481003` "Inpatient care management (procedure)" | every leg [REF](../references/PAYERS.md#markers) |
| `use` | `preauthorization`, `predetermination` or `claim` (variants table) | |
| `patient.reference` | `https://nhcx.abdm.gov.in/patient` (F15) | |
| `billablePeriod.start` | D9 `claim.admission_date` as an instant (`+05:30`) | |
| `billablePeriod.end` | pre-authorisation: D9 `claim.expected_discharge_date`, else the admission date; claim: D20 `claim_submission.discharge_date`, else the admission date | instant |
| `created` | now, `+05:30` | also the QuestionnaireResponse `authored` |
| `insurer.reference` | `https://nhcx.abdm.gov.in/payer` (F17) | |
| `provider.reference` | `https://nhcx.abdm.gov.in/provider` (F17) | |
| `priority` | `http://terminology.hl7.org/CodeSystem/processpriority` `normal` "Normal" | the builder also knows `stat` "Immediate" and `deferred` "Deferred"; no caller sets them |
| `insurance[0]` | `{sequence: 1, focal: true, coverage: {reference: "https://nhcx.abdm.gov.in/coverage"}}` (F18) | |
| `insurance[0].preAuthRef[0]` | D18 `claim_preauth.preauth_ref` | claim leg only, when present |
| `total.value` | pre-authorisation and predetermination: sum of D16 `claim_line.amount` (tiers included); claim: sum of the claim's lines (after any LAMA/DAMA collapse); rounded to 2 decimals, whole numbers as integers | |
| `total.currency` | `INR` | |

`careTeam[]`, one per D26 `claim_care_team` row in `seq` order (the D2 practitioner it names):

| Element | Value or source | Notes |
|---|---|---|
| `sequence` | 1, 2, ... | |
| `provider.reference` | `https://nhcx.abdm.gov.in/practitioner` for the first, `.../practitioner/<n>` after (F16) | |
| `role` | `http://terminology.hl7.org/CodeSystem/claimcareteamrole` `primary` "Primary provider" for the first; `assist` "Assisting Provider" for the rest | D26 `role` is not used |
| `qualification` | `http://snomed.info/sct` D2 `practitioner.specialty_code` / `specialty_display` | when a code is set; else `{text: specialty_display}` when a display is set; else absent |

`diagnosis[]`, one per D25 `claim_diagnosis` row in `seq` order (at least one):

| Element | Value or source |
|---|---|
| `sequence` | 1, 2, ... |
| `diagnosisCodeableConcept` | `http://hl7.org/fhir/sid/icd-10` D25 `icd10_code` / `icd10_display` |
| `type[0]` | `http://terminology.hl7.org/CodeSystem/ex-diagnosistype` `admitting` "Admitting Diagnosis" |
| `onAdmission` | `http://terminology.hl7.org/CodeSystem/ex-diagnosis-on-admission` `yes` "Yes" |

D25 `snomed_code` is not sent.

`procedure[]`, one per procedure item, numbered in item order:

| Element | Value or source | Notes |
|---|---|---|
| `id` | `Procedure/<n>` | |
| `sequence` | n | |
| `type[0]` | `https://nhcx.abdm.gov.in/procedure-type`, code = the package's `ProcedureType` condition in D11 `claim_plan_benefit.conditions` lower-cased, else `conservative`; display = the code capitalised | for example `surgical` "Surgical", `medical` "Medical" |
| `date` | claim leg: D20 `claim_submission.surgery_date` as an instant, else the admission instant; other legs: the admission instant | also the Procedure's `performedDateTime` (F19) |
| `procedureReference` | `{reference: "https://nhcx.abdm.gov.in/procedure/<n>", display: D16 claim_line.display}` | |

`item[]`, one per procedure or implant line:

| Element | Value or source | Notes |
|---|---|---|
| `id` | `Item/<n>` | |
| `sequence` | n | |
| `productOrService` | `https://nrces.in/ndhm/fhir/r4/CodeSystem/ndhm-procedure-code` D16 `claim_line.code` / `display` | |
| `servicedPeriod` | `{start, end}` = the dates (`YYYY-MM-DD`) of `billablePeriod` | |
| `quantity.value` | D16 `claim_line.quantity`, else 1 | whole number when whole |
| `unitPrice` | `{value: net / quantity, currency: "INR"}` | 2 decimals |
| `net` | `{value: line amount + each riding tier's amount, currency: "INR"}` | line amount is D16 `claim_line.amount`, else `quantity x unit_price` |
| `category` | `https://nrces.in/ndhm/fhir/r4/CodeSystem/ndhm-benefit-category` D16 `category_code` / `category_display` | when a category code is set |
| `modifier[]` | per riding tier: D16 `code` / `display`, **no system** [REF](../references/PAYERS.md#markers) | when tiers ride on it |
| `programCode[0]` | `https://nrces.in/ndhm/fhir/r4/CodeSystem/ndhm-program-code` `AB-PMJAY` "Ayushman Bharat Pradhan Mantri Jan Arogya Yojana (AB-PMJAY)" | PMJAY adapter only [PAYER](../references/PAYERS.md#markers) |
| `factor` | 1, 0.5 or 0.25 by rank | procedure items, adapters with the rule [PAYER](../references/PAYERS.md#markers) |
| `careTeamSequence` | every `careTeam.sequence` | |
| `diagnosisSequence` | every `diagnosis.sequence` | |
| `procedureSequence` | the item's own procedure sequence; an implant item lists every procedure sequence | |
| `informationSequence` | every `supportingInfo.sequence` | |

`supportingInfo[]`, each with `id` `SupportingInformation/<n>` and `sequence` n. Categories are under `https://nrces.in/ndhm/fhir/r4/CodeSystem/ndhm-supportinginfo-category`. Document codes are under `https://nhcx.abdm.gov.in/document-code`. Scalar codes are under `https://nrces.in/ndhm/fhir/r4/CodeSystem/ndhm-supportinginfo-code`.

| Entry | `category` | `code` | Value | When |
|---|---|---|---|---|
| Document | D28 `claim_document.category`, else `INV`; display "Document Type - Investigation" (`INV`), "Hospital discharge summary" (`HDS`), "Other" (`OTH`), "Other document" (`ODN`), none for other codes | D28 `code`, else `ODN`; display D28 `label`, else `filename` | `valueAttachment {contentType: D28 content_type (else application/pdf), data: base64 of D28 data, title: label}` | each D28 row of the leg's stage (`preauth` for pre-authorisation, enhancement, predetermination; `claim` for the claim), minus files given as form answers; on the claim, minus `HDS` documents and the summary |
| Discharge summary | `HDS` "Hospital discharge summary" | the summary document's code, else `HDS`; display its label, else "Hospital discharge summary" | `valueAttachment` as above | claim, when a summary with content exists |
| Admission | `ONS` "Period, start or end dates of aspects of the Condition. (e.g. admission, discharge etc)" | `ADDD` "Admission date -Discharge date" | `valueString`: admission instant | always |
| Encounter | `OTH` "Other" | `EDT` "EncounterDateTime" | `valueString`: admission instant | always |
| Surgery | `ONS` | `PSP` "PatientSurgeryPerformed(startdatetime-enddatetime)" | `valueString`: D20 `surgery_date` instant | claim, when given |
| End of stay | `ONS` | `DSDE` "Discharge start-discharge end time" | `valueString`: D20 `death_date` instant, else `discharge_date` instant | claim, when either is given |
| Death | `ONS` | `DTM` "DischargetoMortuary" | `valueString`: D20 `death_date` instant | claim, death only |
| How the stay ended | `DIS` "Discharge status and discharge to location detail" | by D20 `discharge_mode`: `normal` `DTH` "DischargeToHome (Discharge disposition status)"; `lama` `LAMA` "Left against medical advice"; `dama` `DAMA` "Discharged against medical advice"; `death` `DTM` "Death" | `valueString`: D20 `discharge_stage` ("Before Surgery", "During Surgery", "After Surgery"), else "Discharged to home" / "Left against medical advice" / "Discharged against medical advice" / "Died in hospital" | claim |
| Query answer | `NMI` "Claim query detail" | `CQD` "Claim query detail" | `valueString`: the desk's reply (required; kept in D18 / D20 `reply_text`) | `/queryupdate` anchors |
| Answered form | `INF` "Information" or `STG` "Standard Treatment Guidelines" | `ODN` "Other document" or `STG` "Standard Treatment Guidelines" | `valueReference` to the QuestionnaireResponse (F7) | per answered form, not on a predetermination |

#### F8U. USED BY
- APIs: [A4. Pre-auth Submit](../apis/A4-preauth-submit.md), [A5. Claim Submit](../apis/A5-claim-submit.md), [A7. Communication Reply](../apis/A7-communication-on-request.md), [A17. Claim State](../apis/A17-claim-state.md)
- FHIR: [F1. Bundle](F1-bundle.md), [F5. InsurancePlan](F5-insuranceplan.md), [F6. Questionnaire](F6-questionnaire.md), [F7. QuestionnaireResponse](F7-questionnaireresponse.md), [F9. ClaimResponse](F9-claimresponse.md), [F12. Communication](F12-communication.md), [F15. Patient](F15-patient.md), [F16. Practitioner and PractitionerRole](F16-practitioner.md), [F17. Organization](F17-organization.md), [F18. Coverage](F18-coverage.md), [F19. Other bundle resources](F19-other-resources.md)
