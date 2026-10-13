# F12. Communication

#### F12R. RESOURCE
`Communication`, received on `v1/communication/on_request` as the hospital's answer to this payer's query ([F11. CommunicationRequest](F11-communicationrequest.md)). It comes bare or behind the handbook's Task (coded `deliver`, or `poll`, which is also how a plan request is coded), and the Communication decides before any Task: a bundle holding one is a reply, whatever else it carries. No profile is checked. Read by [C9. Communication](../callbacks/C9-communication.md). A `CommunicationRequest` from a hospital is somebody asking, not answering; it is classified apart and logged, never answered [REF](../references/PAYERS.md#markers).

#### F12D. DESCRIPTION
The reply to a query: what the hospital says, what it attaches, and which case it is about. It is filed the way the desk's own query response is ([A13. Adjudicate](../apis/A13-adjudicate.md)): the documents attached to the case, the text on the timeline, the queried lines back in front of an adjudicator.

**Which case.** Matching is forgiving, because a reply that reaches the wrong case is bad and a reply that reaches no case is worse. [C9. Communication](../callbacks/C9-communication.md) tries, in order: the query thread's correlation id ([D19. case](../database/D19-case.md) `nhcx_query_correlation_id`), the claim thread's, the pre-authorisation thread's; then every reference the reply hangs on, each tried as a claim number from this sender; then the workflow id the reply travels under, as a query correlation id. Every reference is collected from: the Communication's own first identifier; the first identifier and the `CLN` identifier of every Task in the bundle; and for each of `basedOn`, `about`, `inResponseTo` and `partOf`, the `reference`, the `display` and the `identifier.value`. Each collected value also yields what follows `Claim/`, `CommunicationRequest/` or `ClaimResponse/` (a claim number may itself carry slashes, as this payer's do [REF](../references/PAYERS.md#markers)) and its last path segment after `/` or `:`, so `Claim/CASE-1001`, `.../Claim/CL/26/0SE0000V9` and `urn:uuid:<request id>` all find the case.

**Texts.** Every `payload[].contentString`, in order, joined with newlines for the timeline. When there is none, the `reasonCode` text or first display is used, else "N document(s) received over NHCX".

**Attachments.** Every `payload[].contentAttachment` is one document ([D23. case_document](../database/D23-case-document.md)): `title` (else "Attachment"); `contentType` starting `image/` is an image, anything else a PDF; inline `data` decoded and kept ([D24. case_document_file](../database/D24-case-document-file.md)) with its size, the url defaulting to `urn:nhcx:communication/<identifier or "reply">/payload/<n>`; an attachment with neither url nor data is dropped. The document code rides in the payload's `extension[]` (a `valueCodeableConcept` code, else a `valueString`, upper-cased); a code this payer's taxonomy does not carry ([D3. document_type](../database/D3-document-type.md)) is filed as `ODN` and the timeline says so. The phase is `preauth` unless the case is at stage `claim`.

**A reply to nothing.** When the case is not waiting on a query, the documents are still filed and the text goes on the timeline, nothing else changes: a hospital sending more is never wrong. A case past adjudication refuses the reply.

**What is not read.** `status`, `category`, `priority`, `sender`, `recipient`, `subject`, `encounter` and the Task's own fields beyond its identifiers. The `sent` timestamp is kept for the trail only.

#### F12F. FIELDS

| Element read | Stored in | Notes |
|---|---|---|
| `Communication.identifier[0].value` | a reference for matching; the attachment url fallback | |
| `Task.identifier[0].value`, `Task.identifier[]` typed `CLN` (every Task in the bundle) | references for matching | the handbook's reply names the claim on the Task in front |
| `basedOn[]`, `about[]`, `inResponseTo[]`, `partOf[]`: `reference`, `display`, `identifier.value` | references for matching, each also split as described | `basedOn` names the CommunicationRequest, `about` the Claim |
| `payload[].contentString` | the reply text: [D26. case_timeline](../database/D26-case-timeline.md) (a timeline event by the sender), [D25. case_line_item](../database/D25-case-line-item.md) `query_remarks` cleared and the lines back to `pending` through the query response | joined with newlines |
| `reasonCode[0]` text or display, else code | the reply text when no `contentString` came | |
| `payload[].contentAttachment.title`, `.contentType`, `.url`, `.data` | [D23. case_document](../database/D23-case-document.md) `title`, `doc_type`, `url`, `file_size`, `phase`; [D24. case_document_file](../database/D24-case-document-file.md) `content_type`, `body` | one document per attachment |
| `payload[].extension[].valueCodeableConcept.coding[0].code`, else `.valueString` | [D23. case_document](../database/D23-case-document.md) `type_code` | upper-cased; unknown codes filed as `ODN` |
| `sent` | the trail only | as sent |
| envelope `x-hcx-correlation_id`, `x-hcx-workflow_id` | the matching keys; [D27. case_exchange_message](../database/D27-case-exchange-message.md) `correlation_id` | the query thread is cleared on [D19. case](../database/D19-case.md) once matched |
| the whole bundle | [D27. case_exchange_message](../database/D27-case-exchange-message.md) `payload`, kind `communication`, direction `in` | the summary names the text and the document count |

#### F12U. USED BY
- Callbacks: [C1. Callback Door](../callbacks/C1-callback-door.md), [C9. Communication](../callbacks/C9-communication.md)
- FHIR: [F1. Bundle](F1-bundle.md), [F11. CommunicationRequest](F11-communicationrequest.md), [F19. Other resources](F19-other-resources.md)
- Database: [D3. document_type](../database/D3-document-type.md), [D23. case_document](../database/D23-case-document.md)
