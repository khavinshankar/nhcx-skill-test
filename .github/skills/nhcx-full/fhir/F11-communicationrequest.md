# F11. CommunicationRequest

#### F11R. RESOURCE
- `resourceType`: `CommunicationRequest`, riding in a `Bundle` of `type: collection`, usually beside a `Task` that wraps it.
- Profiles seen on arrival: `https://nrces.in/ndhm/fhir/r4/StructureDefinition/CommunicationRequest`, `.../StructureDefinition/Task`, bundle `.../StructureDefinition/TaskBundle`. The application does not check `meta.profile` on what it receives.
- Direction: **received**, payer to provider, on NHCX route `v1/communication/request`, received by [G8. Receive](../gateway/G8-receive.md) and handled by C9. It is echoed back unchanged inside the reply and the acknowledgement (F12, A7).

#### F11D. DESCRIPTION
The payer opens a communication thread of its own to ask for something (a **query**) or to tell the facility something (a **notification**). The bundle arrives through the callback door (C1) as message type `communication`.

**Which handler.** The door looks at the resource types in the bundle:
- a bundle whose `type` is `ProtocolResponse` is ignored;
- any `CommunicationRequest` in it: filed as a query or notification (this file);
- otherwise any `Communication`: filed as a payer **note** (see F12, "Received: payer note");
- neither: ignored.

**Shapes that arrive.** All are accepted; the shapes are those seen from sandbox payers [SANDBOX](../references/PAYERS.md#markers):

| Shape | Entries |
|---|---|
| NRCeS TaskBundle for a communication request (Sandbox Payer, IRDAI payers) | Task (`poll`, `include` input pointing at the request), CommunicationRequest, Claim, Patient, payer Organization, provider Organization, Practitioner, Coverage |
| Task plus request | Task, CommunicationRequest, one or two Organizations |
| Bare request | CommunicationRequest, Organization (no Task) |

Only the **first** CommunicationRequest and the **first** Task are read. The Claim, Patient, Practitioner and Coverage the payer sends are not read; they are kept in the stored bundle.

**Query or notification.** Decided by the sender's payer adapter (the one for `x-hcx-sender_code`, else the claim's payer) and the Task:
1. Adapter `query_mode` is `resubmit` (PMJAY, see [PAYERS.md](../references/PAYERS.md)): always a **notification**. PMJAY asks inside the ClaimResponse instead (F9) [PAYER](../references/PAYERS.md#markers).
2. Otherwise (`communication` mode: Sandbox Payer, Generic): `Task.intent` `proposal` is a **notification**, `order` is a **query** [PAYER](../references/PAYERS.md#markers).
3. No intent: the Task's reason code (normalised, below) of empty, `additionalinfo`, `questionnaire` or `query` is a **query**; any other reason (`tatquery`, `grievance`, `walletupdate`, `policychange`, `claimarbitration`, ...) is a **notification** [REF](../references/PAYERS.md#markers).

A query is filed `open` and puts the case into `queried`. A notification is filed and acknowledged at once (A7, acknowledgement variant); a failed acknowledgement is recorded on the row, never raised.

**Which claim.** The references the request names are tried in this order:
1. each value from `about[]`, `basedOn[]`, `identifier[]` (below) as a claim number: the current `D9 claim.claim_no`, else a historical `claim_ref` on `D20 claim_submission` or `D18 claim_preauth`;
2. each value as a `request_id` of a message already held in `D23 claim_query` (this also gives the leg);
3. the envelope's correlation id as the thread of one of the application's own sends;
4. the envelope's `x-hcx-workflow_id` as the correlation id of a claim submission (leg `claim`) or pre-auth (leg `preauth`). This also fixes the leg even when an earlier step found the claim.

No match: the callback outcome is `unmatched` and nothing is stored. When no step named the leg, it is `claim` if a claim submission exists and is past `draft`, else `preauth`.

**Redelivery.** A second message on a correlation id already held in `D23 claim_query.correlation_id` is `ignored`.

#### F11F. FIELDS
Elements read, and where they go (`D23 claim_query` unless stated):

| Element path | Read as / stored in | Notes |
|---|---|---|
| `CommunicationRequest.id` | `request_id` | Also used to build the echo fullUrl `urn:uuid:<id>` when the entry has no fullUrl |
| `CommunicationRequest.about[]`, `.basedOn[]`, `.identifier[]` | the reference list for matching; `claim_ref` | From each item: `reference`, its last path segment when it has a `/`, `display`, `identifier.value`, and `value` when there is no `reference`. Duplicates dropped. `claim_ref` is the first value that has no `/` in it |
| `CommunicationRequest.payload[].contentString` | `questions` (JSON list), `remarks` (joined with newlines) | One question per payload line |
| `CommunicationRequest.reasonCode[].text` | `questions`, `remarks` | Read only when no payload line had text |
| `Task.description` | `questions`, `remarks` | Read only when neither of the above had text |
| `CommunicationRequest.authoredOn` | parsed, not stored | |
| `Task.id` | parsed, not stored | |
| `Task.reasonCode` | `reason_code` | One CodeableConcept or a list (first taken); first coding's `code`, else `text`. Stored lower case; `claimArbitartion` is stored as `claimarbitration` [PAYER](../references/PAYERS.md#markers) |
| `Task.intent` | classification only | `proposal` / `order` (lower-cased) |
| `Organization` entries | not read on arrival | Used when the acknowledgement is built (F12): the one `Task.owner` or `CommunicationRequest.recipient[]` points at is taken as the facility's, else the one typed `prov` |
| whole bundle | `request_json` | Echoed later in F12 |
| header `x-hcx-correlation_id` | `correlation_id` | The reply goes back on it |
| header `x-hcx-sender_code` | `sender_code` | Recipient of the reply |
| header `x-hcx-workflow_id` | `workflow_id` | Echoed on the reply |
| (derived) | `kind` `query` or `notification`; `status` `open`; `stage`; `received_at` now | |

Reason codes and the words shown for them: `tatquery` Turnaround time query, `grievance` Grievance, `walletupdate` Wallet or benefit update, `policychange` Policy change, `additionalinfo` Additional information request, `claimarbitration` Claim arbitration intimation, `questionnaire` Questionnaire, `query` Query. Any other code is shown as the payer spelled it. Code system: `https://nrces.in/ndhm/fhir/r4/CodeSystem/ndhm-reason-code`.

#### F11U. USED BY
- APIs: [A7. Communication Reply](../apis/A7-communication-on-request.md)
- Callbacks: [C9. Payer Communication](../callbacks/C9-communication-request.md)
- FHIR: [F12. Communication](F12-communication.md), [F17. Organization](F17-organization.md)
