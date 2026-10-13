# F11. CommunicationRequest

#### F11R. RESOURCE
`CommunicationRequest`, `meta.profile` `https://nrces.in/ndhm/fhir/r4/StructureDefinition/CommunicationRequest`, inside a bundle profiled `.../TaskBundle` with `security` `V` (F1). Direction: sent on `v1/communication/request` by [A5. Query Request](../apis/A5-query-request.md) when a case is queried on the desk ([A13. Adjudicate](../apis/A13-adjudicate.md)). It opens a thread of its own: no correlation id goes in, [G7. Send](../gateway/G7-send.md) mints one, and the hospital's Communication (F12) comes back under it ([C9. Communication](../callbacks/C9-communication.md)).

Entries, all at `urn:uuid:` addresses: the Task (profile `.../Task`), the CommunicationRequest, the Claim as this payer holds it (profile `.../Claim`), the Patient (F15), the payer Organization and the hospital Organization (F17), one Practitioner per doctor on the case (profile `.../Practitioner`), and the Coverage (F18). This is the IG's TaskBundle for a communication request, the shape a hospital's communication handler already reads [PAYER](../references/PAYERS.md#markers).

#### F11D. DESCRIPTION
The scheme payer asks inside its ClaimResponse and takes the answer as a fresh submission; this payer asks on the communication API instead, in `communication` query mode ([PAYERS.md](../references/PAYERS.md)) [PAYER](../references/PAYERS.md#markers). The hospital tells the two apart by the adapter it holds for this payer's code, so nothing in the message says which mode it is.

**The Task.** `status` `requested`, `intent` `order`, `code` `poll` (`http://terminology.hl7.org/CodeSystem/financialtaskcode`), `reasonCode` `additionalinfo` "Additional Information Request" (`https://nrces.in/ndhm/fhir/r4/CodeSystem/ndhm-reason-code`), `description` every payload line joined by spaces, `requester` the payer, `owner` the hospital, and one `input` typed `include` (`http://terminology.hl7.org/CodeSystem/financialtaskinputtype`) pointing at the CommunicationRequest. A hospital reads `intent` `order` as a query and `proposal` as a notification, and switches on the reason code [PAYER](../references/PAYERS.md#markers): this payer sends notifications through no other shape, so every request it sends is a query.

**The payload.** The case-level remarks first (`D19.adjudication_remarks`), then one `contentString` per queried line ([D25. case_line_item](../database/D25-case-line-item.md) with `status` `queried`): the line's code and description, and its query remarks after a colon. Each queried line also becomes one `reasonCode` (`additionalinfo`, `text` the same line). A case queried with no remarks and no queried line gets the one line "Additional information is required to decide this claim." and the render notes it. Attachments are never asked for by payload; the words say which document.

**What it is about.** `basedOn[0]` points at the Claim entry with display `Claim-preauth` or `Claim-claim` by the leg the case is on, and `identifier[0].value` is the hospital's own claim number, so the hospital finds the case by either. The restated Claim carries the hospital's number and this payer's case number as identifiers, `use` by leg, `status` `active`, the inpatient claim type, `priority` from the case urgency (`stat` for Emergency, `urgent` for Urgent, else `normal`), `billablePeriod` from admission to discharge or expected discharge, the diagnoses as ICD-10 (`http://hl7.org/fhir/sid/icd-10`), the procedures by SNOMED else this payer's procedure system, the care team, one insurance entry pointing at the Coverage, every line as an item with `unitPrice` and `net`, and `total` the claimed total. It is what this payer holds, not the hospital's bundle echoed [REF](../references/PAYERS.md#markers).

**The parties.** The payer Organization is the insurer Organization of F5 without its address; the hospital Organization is typed `prov` with a `PRN` identifier on `https://facility.ndhm.gov.in` holding the HFR id; each Practitioner is named, with an `MD` "Medical License number" identifier on `https://doctor.ndhm.gov.in` when the case holds the HPR id, and its care-team entry carries the SNOMED role `223366009` and qualification `394658006` with the specialty as text.

**Ids.** Every resource id is a deterministic UUID v5 keyed on the case and the decision time (the Task and the request), the case and leg (the Claim), the member (Patient), the payer (Organization), the HFR id (hospital Organization and Practitioners) and the enrolment (Coverage), so re-sending the same query gives the same bundle [REF](../references/PAYERS.md#markers). The minted correlation id and transaction are written on the case (`D19.nhcx_query_correlation_id`, `D19.nhcx_query_txn_id`) by [A5. Query Request](../apis/A5-query-request.md).

#### F11F. FIELDS
| Element written | From | Notes |
|---|---|---|
| Task `status`, `intent`, `code` | `requested`, `order`, `poll` | |
| Task `reasonCode` | `additionalinfo` | ndhm-reason-code |
| Task `description` | the payload lines joined | |
| Task `authoredOn` | now, IST | |
| Task `requester`, `owner` | payer and hospital Organization urns, display `Organization` | |
| Task `input[0]` | type `include`, `valueReference` the request urn, display `CommunicationRequest` | |
| `id` | UUID v5 of `CommunicationRequest/<D19.id>/<D19.adjudicated_at>` | |
| `identifier[0].value` | the hospital's claim number: `D19.nhcx_claim_submission_ref`, else `D19.nhcx_claim_ref` | |
| `basedOn[0]` | the Claim urn, display `Claim-preauth` or `Claim-claim` | |
| `status` | `active` | |
| `category[0]` | `alert` (`http://terminology.hl7.org/CodeSystem/communication-category`) | |
| `priority` | `routine` | |
| `payload[].contentString` | `D19.adjudication_remarks`; then `<D25.code> <D25.description>: <D25.query_remarks>` per queried line | |
| `authoredOn` | now, IST | |
| `requester`, `sender` | the payer Organization urn | |
| `recipient[0]` | the hospital Organization urn | |
| `reasonCode[]` | `additionalinfo` with `text` per queried line, else one with the remarks | |
| Claim | `D19` (numbers, urgency, dates, hospital), `D20` diagnoses, `D21` procedures, `D22` doctors, `D25` lines, `D19.total_claimed` | restated |
| Coverage `identifier[0]` | `system` `<payer base>/policynumber/`, `value` `D12.uin` else `D12.id` | `period.end` `D6.pend` |

#### F11U. USED BY
- APIs: [A5. Query Request](../apis/A5-query-request.md), [A13. Adjudicate](../apis/A13-adjudicate.md), [A15. Case Exchange Log](../apis/A15-case-exchange.md)
- FHIR: [F1. Bundle](F1-bundle.md), [F9. ClaimResponse](F9-claimresponse.md), [F12. Communication](F12-communication.md), [F15. Patient](F15-patient.md), [F17. Organization](F17-organization.md), [F18. Coverage](F18-coverage.md)
- Database: [D25. case_line_item](../database/D25-case-line-item.md)
- Tests: [T8. Pre-auth Queried and Answered](../tests/T8-preauth-queried.md)
