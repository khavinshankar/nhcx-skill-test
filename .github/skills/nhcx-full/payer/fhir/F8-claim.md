# F8. Claim

#### F8R. RESOURCE
`Claim`, received as the anchor of a hospital's Claim bundle ([F1. Bundle](F1-bundle.md)) on `v1/preauth/submit` (`use` `preauthorization` or `predetermination`) and `v1/claim/submit` (`use` `claim`). No profile is checked. Read by [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md) (a pre-authorisation, an enhancement, a query resubmission), [C5. Claim Submit](../callbacks/C5-claim-submit.md) (the final bill) and [C6. Predetermination](../callbacks/C6-predetermination.md) (a predetermination). The bundle is indexed by `fullUrl` and by `ResourceType/id` first and walked afterwards: a reference that resolves to nothing leaves its field blank rather than failing the parse. A pre-authorisation that names its patient but loses its hospital is still one an adjudicator can work on, and refusing the whole submission would dead-letter it at the gateway.

#### F8D. DESCRIPTION
One document serves every leg the hospital sends: pre-authorisation, enhancement, query resubmission, predetermination, claim and claim query answer. The parser flattens it into one submission shape; what the case does with it depends on `use` and on what the submission names.

**Which Claim.** The first `Claim` in the bundle whose `use` is `preauthorization` (or the older `preauth`, read as the same), `claim` or `predetermination`. A bundle with none is not a submission ([C1. Callback Door](../callbacks/C1-callback-door.md) classifies it as something else, or ignores it).

| `use` | Callback | Becomes |
|---|---|---|
| `preauthorization` | [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md) | a new case ([D19. case](../database/D19-case.md)), or an enhancement or a query resubmission on the case it comes back to |
| `claim` | [C5. Claim Submit](../callbacks/C5-claim-submit.md) | the final bill on the pre-authorised case, or a case opened by a direct claim |
| `predetermination` | [C6. Predetermination](../callbacks/C6-predetermination.md) | a quote ([D29. predetermination_quote](../database/D29-predetermination-quote.md)), no case |

**The person.** The Claim's `patient` is followed to the Patient ([F15. Patient](F15-patient.md)) and read for exactly the handles an eligibility question is read for ([F2. CoverageEligibilityRequest](F2-coverage-eligibility-request.md)): the enrolment is found by the same means, so a hospital that can find cover for a patient can submit for them. `gender` and `birthDate` are read as well, which an enquiry has no use for and a case does. The patient on the case is this payer's member ([D5. member](../database/D5-member.md)), not the name the hospital typed: the enrolment is the record of who they are.

**The hospital.** The Claim's `provider` is followed to the Organization ([F17. Organization](F17-organization.md)): `name` and the first identifier as the HFR id. The `insurer` is not read.

**Cover and dates.** The first `insurance[]` whose `coverage` resolves gives the policy code (the Coverage's first identifier, unless `UNDEFINED`) and, from the Coverage `period`, the admission and expected discharge ([F18. Coverage](F18-coverage.md)). `billablePeriod.start` overrides the admission; its `end` is the discharge date on a claim only. Then the `supportingInfo` scalars override both, because the period is the cover, which a hospital may send as the policy year, and the admission entry is the admission:

| `supportingInfo` category | code | Read as |
|---|---|---|
| `ADMD`, any code | | admission date |
| `SURD`, any code | | surgery date |
| `DSCHD`, any code | | discharge date |
| `ONS` or `OTH` | `ADDD`, `EDT` | admission date |
| `ONS` or `OTH` | `PSP` | surgery date |
| `ONS` or `OTH` | `DSDE` | discharge date |
| `ONS` or `OTH` | `DTM` | discharge date; discharge type `Deceased` when none was read |
| `ONS`, any other code | | discharge date; `Deceased` when no type was read (an older bundle carried the death alone) |
| `DIS` | the discharge mode | discharge type: `DTH` or `NORMAL` "Normal Discharge"; `LAMA` or `DAMA` "LAMA"; `DTM`, `DEATH`, `DECEASED` "Deceased"; `TRANSFER`, `TRF` "Transfer"; anything else blank |

Every `valueString` is trimmed to its calendar date. A pre-authorisation with no admission date is filed on the day it arrived [REF](../references/PAYERS.md#markers).

**Priority.** `priority` `stat` or `asap` is `Emergency`, `urgent` is `Urgent`, anything else `Elective`.

**The prior it comes back to.** A resubmission names the pre-authorisation it enhances or answers in one of three places, tried in order: `related[]` (the `reference.value`, else the last segment of `claim.reference`, else `claim.display`), `insurance[].preAuthRef[0]`, an identifier typed `PAR`. The reference hospital sends an enhancement as the whole pre-authorisation again under the same claim number with no `related` link ([REF](../references/PAYERS.md#markers)); then the claim number itself finds the case, as long as that case is past its first filing ([C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md)). Lines already on the case are matched on code, description and claimed amount; only the rest are added.

**Diagnoses.** One per `diagnosis[]` with a code; the first is `primary`, the rest `secondary`, because the scheme types them all "Preliminary diagnosis", which says when a diagnosis was made rather than which of them the case is about, and at most one row per case may be primary ([D20. case_diagnosis](../database/D20-case-diagnosis.md)).

**Care team.** One doctor per `careTeam[]` whose `provider` resolves to a Practitioner ([F16. Practitioner](F16-practitioner.md)): name, first identifier as the HPR id, first qualification's display, and the `role` display. A team member with neither name nor id is dropped.

**Procedures.** One per `procedure[]` whose `procedureReference` resolves ([F19. Other resources](F19-other-resources.md)). The reference codes every Procedure with the generic SNOMED concept `71388002` and names the package in the concept's `text` and on the reference's `display`; those name it, the concept does not. The package code is then put on the procedure from the item whose `procedureSequence` points at it, and a procedure no item bills for keeps its name, cut to 32 characters, as its code so the column can hold it.

**Items.** One line ([D25. case_line_item](../database/D25-case-line-item.md)) per `item[]` with a `productOrService` display or code. `quantity` defaults to 1; `net` defaults to `unitPrice` times quantity, and `unitPrice` to `net` over quantity, so both are always known. A ward or ICU tier rides as the first `modifier` on the item with the package's own rate already inside `net`; it is kept beside the line as its modifier, never as a line of its own. `factor`, `careTeamSequence`, `diagnosisSequence` and `informationSequence` are not read.

**Documents.** Every `supportingInfo` with a `valueAttachment` is one document ([D23. case_document](../database/D23-case-document.md)). The title is the attachment's, else the code's display, else the code, else the category, else "Attachment". `contentType` starting `image/` is an image, anything else a PDF. Inline `data` is decoded (standard and URL-safe base64, padded or not, whitespace folded in) and kept ([D24. case_document_file](../database/D24-case-document-file.md)), because a document nobody can open is not a document an adjudicator can decide against; the url defaults to `urn:nhcx:claim/<claim number>/supportingInfo/<sequence>`. An attachment with neither url nor data is dropped. The document code is the supportingInfo `code` upper-cased, unless it starts with `(` (the scheme puts a discharge mode in brackets there, which is not a document type [PAYER](../references/PAYERS.md#markers)), else the category. A code this payer's taxonomy does not carry ([D3. document_type](../database/D3-document-type.md), by code or by its NDHM category) is filed as `ODN`, other document, and the timeline says so. The phase is `preauth` on a pre-authorisation and `claim` on a claim.

**Query note.** The `supportingInfo` coded `CQD` carries the hospital's words on a resubmission answering a query (workflow 19, 121, 131, 151 or 161 [PAYER](../references/PAYERS.md#markers)); its `valueString` becomes the reply filed on the case.

**Forms.** Every QuestionnaireResponse the Claim points at from `supportingInfo[].valueReference` is read as [F7. QuestionnaireResponse](F7-questionnaireresponse.md).

**Total.** `total.value` as quoted; the case totals are recomputed from the lines, so the quoted total is shown, never trusted.

#### F8F. FIELDS

| Element read | Stored in | Notes |
|---|---|---|
| `use` | decides the callback | `preauth` read as `preauthorization` |
| `identifier[0].value` | [D19. case](../database/D19-case.md) `nhcx_claim_ref` (pre-auth), `nhcx_claim_submission_ref` (claim); [D29. predetermination_quote](../database/D29-predetermination-quote.md) `claim_ref` | the hospital's own claim number, and what its support desk asks about |
| `related[].reference.value`, else `related[].claim.reference` last segment, else `.display`; `insurance[].preAuthRef[0]`; identifier typed `PAR` | the prior looked up ([C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md), [C5. Claim Submit](../callbacks/C5-claim-submit.md)) | first found wins |
| `total.value` | the exchange message summary ([D27. case_exchange_message](../database/D27-case-exchange-message.md)); [D29. predetermination_quote](../database/D29-predetermination-quote.md) `total_claimed` | case totals come from the lines |
| `priority.coding[0].code` | [D19. case](../database/D19-case.md) `urgency` | `stat`, `asap` Emergency; `urgent` Urgent; else Elective |
| `patient` (followed) | the handles ([F2. CoverageEligibilityRequest](F2-coverage-eligibility-request.md)); [D19. case](../database/D19-case.md) `patient_gender` fallback | the case's `patient_name`, `patient_gender` come from the member ([D5. member](../database/D5-member.md)) first |
| `provider` (followed) `name`, `identifier[0].value` | [D19. case](../database/D19-case.md) `hospital_name`, `hospital_hfr_id` | |
| `insurance[0].coverage` (followed) `identifier[0].value` | the policy code the hospital quotes; the subscriber fallback handle | `UNDEFINED` ignored |
| `insurance[0].coverage` (followed) `period.start`, `.end` | [D19. case](../database/D19-case.md) `admitted_on`, `expected_discharge` | overridden by `billablePeriod` and the scalars |
| `billablePeriod.start`, `.end` | [D19. case](../database/D19-case.md) `admitted_on`; `discharge_date` (claim only) | |
| `supportingInfo[]` dated scalars (table above) | [D19. case](../database/D19-case.md) `admitted_on`, `discharge_date`; the surgery date in the trail | |
| `supportingInfo[]` category `DIS` code | [D19. case](../database/D19-case.md) `discharge_type` | `Normal Discharge`, `LAMA`, `Deceased`, `Transfer` |
| `diagnosis[].diagnosisCodeableConcept.coding[0]` code, display | [D20. case_diagnosis](../database/D20-case-diagnosis.md) `code`, `description`, `type` | first primary, rest secondary |
| `careTeam[].provider` (followed Practitioner), `careTeam[].role.coding[0].display` | [D22. case_doctor](../database/D22-case-doctor.md) `name`, `hfr_id`, `qualification`, `role` | first is the doctor of record |
| `procedure[].procedureReference` (followed), `.display` | [D21. case_procedure](../database/D21-case-procedure.md) `code`, `name`, `category` | code from the billing item's `productOrService` |
| `item[].productOrService.coding[0]` code, display | [D25. case_line_item](../database/D25-case-line-item.md) `code`, `description` | description falls back to the code |
| `item[].quantity.value`, `unitPrice.value`, `net.value` | [D25. case_line_item](../database/D25-case-line-item.md) `quantity`, `unit_cost`, `claimed_amount` | defaults as above |
| `item[].modifier[0]` code, display | [D25. case_line_item](../database/D25-case-line-item.md) `modifier_code`, `modifier_display` | the ward or ICU tier |
| `item[].procedureSequence[]` | names the procedure the item bills | |
| `supportingInfo[].valueAttachment` (`title`, `contentType`, `url`, `data`), `code`, `category` | [D23. case_document](../database/D23-case-document.md) `title`, `type_code`, `phase`, `url`, `doc_type`, `file_size`; [D24. case_document_file](../database/D24-case-document-file.md) `content_type`, `body` | unknown codes filed as `ODN` |
| `supportingInfo[]` code `CQD` `valueString` | the reply filed by [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md) on the queried lines; [D26. case_timeline](../database/D26-case-timeline.md) | a resubmission answering a query |
| `supportingInfo[].valueReference` to a QuestionnaireResponse | read as [F7. QuestionnaireResponse](F7-questionnaireresponse.md) | |
| the whole bundle | [D27. case_exchange_message](../database/D27-case-exchange-message.md) `payload` (kind `preauth` or `claim`, direction `in`) | also the source the forms are read from later |

#### F8U. USED BY
- APIs: [A10. Predetermination Quote](../apis/A10-predetermination-quote.md)
- Callbacks: [C1. Callback Door](../callbacks/C1-callback-door.md), [C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md), [C5. Claim Submit](../callbacks/C5-claim-submit.md), [C6. Predetermination](../callbacks/C6-predetermination.md)
- FHIR: [F1. Bundle](F1-bundle.md), [F7. QuestionnaireResponse](F7-questionnaireresponse.md), [F15. Patient](F15-patient.md), [F16. Practitioner](F16-practitioner.md), [F18. Coverage](F18-coverage.md), [F19. Other resources](F19-other-resources.md)
- Database: [D3. document_type](../database/D3-document-type.md), [D19. case](../database/D19-case.md), [D20. case_diagnosis](../database/D20-case-diagnosis.md), [D21. case_procedure](../database/D21-case-procedure.md), [D23. case_document](../database/D23-case-document.md), [D25. case_line_item](../database/D25-case-line-item.md), [D29. predetermination_quote](../database/D29-predetermination-quote.md)
- Tests: [T13. LAMA and Death Claims](../tests/T13-claim-lama-death.md)
