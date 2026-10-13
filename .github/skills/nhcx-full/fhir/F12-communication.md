# F12. Communication

#### F12R. RESOURCE
- `resourceType`: `Communication` (the reply), inside a `Bundle` `type: collection` with profile `https://nrces.in/ndhm/fhir/r4/StructureDefinition/TaskBundle`, wrapped by a `Task`.
- Profiles in `meta.profile`: Communication `https://nrces.in/ndhm/fhir/r4/StructureDefinition/Communication`; Task `https://nrces.in/ndhm/fhir/r4/StructureDefinition/Task`.
- Direction: **sent**, on NHCX route `v1/communication/on_request`, sent by A7 through [G7. Send](../gateway/G7-send.md), on the thread of the payer's CommunicationRequest (F11). Also **received**: a bare Communication from the payer is a note (last section).

#### F12D. DESCRIPTION
One route carries two different bundles:

| Variant | Answers | Sent | Carries a Communication? |
|---|---|---|---|
| Reply | a query (`D23 claim_query.kind = query`) | when the desk sends the reply form | yes: a new Communication with the text and files |
| Acknowledgement | a notification (`kind = notification`) | automatically on arrival; by hand again after a failure | no: the payer's own bundle sent back with its Task `completed` |

A note (`kind = note`) gets neither.

**Reply bundle.** Entries in this order:
1. Task (new): `deliver`, `completed`, its one `include` input pointing at the Communication.
2. Communication (new).
3. The payer's CommunicationRequest, exactly as it arrived, under its own fullUrl. When the stored request has none, a minimal `{"resourceType": "CommunicationRequest", "id": <request_id or new uuid>, "status": "active"}` at `urn:uuid:<id>`.
4. The case, as the payer already holds it: Claim, Patient, provider Organization, payer Organization, every Practitioner, Coverage, **and every entry those resources reference, transitively** (Procedure, QuestionnaireResponse, ...), plus every entry the echoed CommunicationRequest references, so that no reference in the bundle dangles (the knowledge source's `nhcx.fhir.collection-bundle`: a collection bundle resolves every reference inside itself). Lifted, deep-copied, from the queried leg's own sent bundle (A5 for leg `claim`, else A4; if the first has no Claim the other leg's is tried). Organizations: the one typed `prov` is the provider (else the one at `https://nhcx.abdm.gov.in/provider`, else the first); the next one is the payer. When no leg ever went out, they are built from the case: a stub Claim at `https://nhcx.abdm.gov.in/<preauth|claim>/request` (F8), Patient (F15, from the claim row only), the two Organizations (F17), Coverage (F18). No Practitioner then.

**Refusals before building** (reply): "Query not found."; "That message is not a question: a notification is acknowledged and a note is read, neither takes an answer."; "Set the facility's HFR ID and NHCX participant code under Settings before answering a query."; "Write a reply or attach a document, an empty answer tells the payer nothing."; "One of the chosen documents is not on this claim."

**Acknowledgement bundle.** The request bundle as stored (`D23 claim_query.request_json`), sent back with:
- the payer's Task first, deep-copied, `status` set to `completed`; intent, code and reason as sent;
- when the request came without a Task, a new one: `status: completed`, `intent: proposal`, `code` `poll` under `http://terminology.hl7.org/CodeSystem/financialtaskcode`, `authoredOn` now, `requester` the payer Organization, `owner` the provider Organization, `reasonCode` from `D23 claim_query.reason_code` under `ndhm-reason-code` with its words, and an `include` input pointing at the CommunicationRequest; fullUrl `urn:uuid:<new>`;
- the Organizations grouped where the first one stood (at the end when there were none), the facility's first. The facility's is the one the Task `owner` or a request `recipient[]` points at; else the one typed `prov`; else, when the payer named nobody, the facility's own Organization is built (F17) and put first, followed by whatever the payer sent (or a built payer Organization when it sent none);
- every other entry in place, deep-copied; entries without fullUrl get `urn:uuid:<id or new uuid>`.

Refusals: "Query not found."; "Only a notification is acknowledged; a query is answered from the communication tab."; "Set the facility's HFR ID and NHCX participant code under Settings first."

#### F12F. FIELDS
**Reply bundle envelope**

| Element path | Value or source | Notes |
|---|---|---|
| `Bundle.id` | new uuid | |
| `Bundle.meta.lastUpdated` | now | |
| `Bundle.meta.profile` | `.../StructureDefinition/TaskBundle` | |
| `Bundle.identifier` | `{system: <adapter payer_system>, value: "<D9 claim.claim_no>-Q<D23 claim_query.id>"}` | value format [REF](../references/PAYERS.md#markers) |
| `Bundle.type` | `collection` | |
| `Bundle.timestamp` | now | |

**Task (reply)**

| Element path | Value or source | Notes |
|---|---|---|
| `id` | new uuid; fullUrl `urn:uuid:<id>` | |
| `meta.profile` | `.../StructureDefinition/Task` | |
| `status` | `completed` | |
| `intent` | `order` | |
| `code` | `deliver` under `https://nrces.in/ndhm/fhir/r4/CodeSystem/ndhm-task-codes` | no display |
| `authoredOn` | now | |
| `requester` | provider Organization fullUrl, display `Organization` | |
| `owner` | payer Organization fullUrl, display `Organization` | |
| `input[0].type` | `include` under `http://terminology.hl7.org/CodeSystem/financialtaskinputtype` | |
| `input[0].valueReference` | the Communication's fullUrl, display `Communication` | |
| `reasonCode` | copied from the request's Task; else `D23 claim_query.reason_code` under `ndhm-reason-code` with its words (F11) | left out when neither |

**Communication (reply)**

| Element path | Value or source | Notes |
|---|---|---|
| `id` | new uuid; fullUrl `urn:uuid:<id>` | |
| `meta.profile` | `.../StructureDefinition/Communication` | |
| `identifier` | the request's identifiers that carry a value, copied | else `{system: "<adapter payer_system>/communication", value: "<claim_no>-Q<query id>"}` [REF](../references/PAYERS.md#markers) |
| `basedOn[0]` | the request's fullUrl, display `CommunicationRequest` | |
| `inResponseTo` | not set | FHIR allows only a Communication there |
| `about[0].reference` | the Claim entry's fullUrl | |
| `about[0].display` | `Claim <claim_ref>`: `D23 claim_query.claim_ref`, else `D9 claim.claim_no` | |
| `status` | `completed` | |
| `category[0]` | `notification` under `http://terminology.hl7.org/CodeSystem/communication-category` | |
| `priority` | `routine` | |
| `recipient[0]` | payer Organization fullUrl, display `Organization` | |
| `sender` | provider Organization fullUrl, display `Organization` | |
| `payload[]` text | `{contentString: <reply text, trimmed>}` | first, only when text was written |
| `payload[]` file | `contentAttachment`: `contentType` D28 claim_document.content_type, `title` label else filename, `creation` uploaded_at, `data` base64 of the file | one per ticked or uploaded document, in order |
| `payload[].extension[0]` | `{url: "<adapter payer_system>/StructureDefinition/document-type", valueString: D28 claim_document.code}` | only when the document has a code [REF](../references/PAYERS.md#markers) |

**Acknowledgement (changed elements only)**

| Element path | Value or source |
|---|---|
| `Bundle.id` | new uuid |
| `Bundle.meta` | `lastUpdated` now, profile TaskBundle |
| `Bundle.identifier` | the request bundle's own identifier, else `{system: <adapter payer_system>, value: "<claim_no>-N<query id>"}` [REF](../references/PAYERS.md#markers) |
| `Bundle.type`, `timestamp` | `collection`, now |
| `Task.status` | `completed` |

After a send, `D23 claim_query` gets `status` `answered` (reply) or `acknowledged`, `reply_txn_id`, `reply_correlation_id`, `answered_at` / `acknowledged_at`, `reply_json` (the bundle); a reply also keeps `reply_text` and `reply_documents` (JSON list of D28 ids).

#### F12U. USED BY
- APIs: [A7. Communication Reply](../apis/A7-communication-on-request.md)
- FHIR: [F1. Bundle](F1-bundle.md), [F11. CommunicationRequest](F11-communicationrequest.md), [F15. Patient](F15-patient.md), [F16. Practitioner and PractitionerRole](F16-practitioner.md), [F17. Organization](F17-organization.md), [F18. Coverage](F18-coverage.md), [F19. Other bundle resources](F19-other-resources.md)
