# F9. ClaimResponse

#### F9R. RESOURCE
`ClaimResponse`. Direction: received. No profile is required or checked (PMJAY and the Sandbox Payer send none [PAYER](../references/PAYERS.md#markers)). It arrives on `preauth/on_submit` (pre-authorisation, enhancement, query answers, predetermination), on `claim/on_submit` (claim), and inside the Task replies of `task/on_submit` (F10).

#### F9D. DESCRIPTION
The payer's verdict on a Claim (F8). The **first** ClaimResponse in the bundle is read (in a Task reply, the one the Task's output points at, F10). The rest of the payer's bundle (its Patient, Organizations) is not read.

**`outcome` alone never gives the decision.** `complete` comes back for an approval and for a rejection alike [PAYER](../references/PAYERS.md#markers). The claim-level `adjudication[].reason` is read beside it, and the pair decides:

| `outcome` | Claim-level adjudication reason | Leg status |
|---|---|---|
| `queued` or `acknowledged` (any reason), or any outcome with reason `submitted` or `acknowledged` | | stays `submitting`: an acknowledgement, not a decision |
| any | `cancelled` | `rejected` (but see cancelling, below) |
| any | `rejected` or `denied` | `rejected` |
| any | `queried` | `queried` |
| `error` | any other | `error`: the payer could not process it. Not a decision |
| `partial` | `approved` | `partial` |
| `partial` | anything else | `queried` |
| `complete` | `approved` or none | `approved` |
| `complete` | anything else | `queried` |
| anything else | | `queried` |

**Errors are shown, never obeyed.** A reply is an error when its envelope travels as `x-hcx-status` `response.error`, when the ClaimResponse carries `error[]`, or when its outcome is `error` with no rejecting reason. An error decides nothing and stops nothing: the leg goes to `error` with the payer's words as its message, the screen shows them, and the same send is offered again. A rejection that a payer writes as `outcome: error` with reason `rejected` is still a rejection (the row above it).

**The workflow id comes first.** When the reply's `x-hcx-workflow_id` is one of the payer-side codes in [PAYERS.md](../references/PAYERS.md) (20 received, 21 approved, 23 rejected, 24 queried, and their claim and enhancement counterparts), that code gives the status and the table above is not consulted, except that an error still wins and an approval the bundle marks `partial` stays `partial`. With any other workflow id, or none, the table decides.

The `rejected` row is a correction. The reference implementation had no `rejected` row, so a rejection sent as `outcome: complete` with reason `rejected` was read as `queried`. Check the reason codes each payer uses in the knowledge source [PAYER](../references/PAYERS.md#markers).

The rows are tried top to bottom. The claim-level reason is the first `adjudication[]` entry with a reason code whose `category` code is `status`, else the first with any reason code, lower-cased.

Rules:
- **One thread, several replies.** A leg is answered more than once on one correlation id: an acknowledgement, maybe a query, then the decision, each under the payer's own workflow id (for PMJAY see [PAYERS.md](../references/PAYERS.md)) [PAYER](../references/PAYERS.md#markers). Every reply is applied. A redelivery is ignored: same `x-hcx-api_call_id` as the last applied reply or, when the payer sends none, the same outcome and adjudication on a leg no longer `submitting`.
- **Totals by category, never by position.** `total[]` is a list keyed by `category.coding[0].code`, lower-cased. `benefit` is what this reply grants, `eligible` what the case now stands at (an enhancement's reply grants the addition under `benefit` and restates the whole under `eligible`), `submitted` echoes what was asked. Others (`tax`, `incentive`) are ignored.
- **`preAuthRef`.** On a pre-authorisation, a reply without one keeps the stored reference. The claim leg stores whatever the reply carries. PMJAY's acknowledgement writes the reference with the plan prefix (`PMJAY/HP/S/2024/R2/2026091310000103`) and the decision without it (`2026091310000103`) [PAYER](../references/PAYERS.md#markers).
- **Per item.** Each `item[]` becomes one row keyed by `itemSequence`, read from its `adjudication[]` by category.
- **Query trail.** [PAYER](../references/PAYERS.md#markers) PMJAY writes its remarks on the `reason`-category item adjudication as free text, sometimes a pipe-delimited `USER~datetime~type~comment~trust` string, and sends `" : null"` or `" : ."` when it has none. Each piece between pipes is kept when it says something (a leading colon stripped; empty, `.`, `null`, `none`, `nil` and `-` dropped). The kept pieces of every item, then each `processNote[].text`, de-duplicated, form the query note.
- **Cancelling.** While a cancel Task is out (F10), a reply on the pre-authorisation thread adjudicated `cancelled` confirms the withdrawal (leg `cancelled`). Anything else on that thread is ignored until the Task is answered. A leg already `cancelled` ignores every reply.
- **Predetermination.** The reply is an answer whatever it says: the quote row becomes `answered` and keeps the outcome, adjudication, disposition and the `benefit` total as the amount the policy would allow.
- A ProtocolResponse instead of the bundle is a refusal at the door (A4, A5).

#### F9F. FIELDS
Read into the pre-authorisation leg (D18 `claim_preauth`) or the claim leg (D20 `claim_submission`):

| Element read | Stored in | Notes |
|---|---|---|
| `outcome` | `outcome` | |
| claim-level `adjudication[].reason.coding[0].code` (prefer `category` `status`) | `adjudication` (lower case) | |
| `outcome` + `adjudication` | `status` | table above; `settled_at` set unless `submitting` |
| `disposition` | `disposition` | the payer's words, shown on the leg |
| `preAuthRef` | `preauth_ref` | D18: only when present; D20: as received |
| `total[]` category `benefit`, `amount.value` | `approved_amount` | |
| `total[]` category `eligible`, `amount.value` | `eligible_amount` | |
| `total[]` category `submitted`, `amount.value` | `submitted_amount` | |
| `item[]` | `items_json` (JSON list, one object per item) | below |
| `item[].adjudication[]` category `reason` (display) and `processNote[].text` | `query_note` | newline-joined |
| `error[].code` (coding code and display, else text) | `error_message` on an error reply, one line per entry, followed by the disposition and the process notes | shown on the leg in the danger colour |
| `form` (an Attachment: `contentType`, `data` or `url`, `title`) | read from `response_json` when shown | the screen offers "Open <title> (PDF)" on the reply; nothing is stored apart from the bundle |
| envelope `x-hcx-api_call_id` | `api_call_id` | redelivery check |
| the whole bundle | `response_json` | |

`items_json`, per `item[]`, from `adjudication[]` by `category.coding[0].code` (lower-cased):

| Category | Key | From |
|---|---|---|
| (item) | `sequence` | `itemSequence` |
| `eligible` | `eligible` | `amount.value` |
| `status` | `status` | `reason.coding[0].code`, else display (for example `Approved`, `Queried`, `Requested`, `Rejected`) |
| `reason` | `reason` | `reason.coding[0].display`, else code, cleaned as described |
| `eligpercent` | `percent` | `value` |
| `eligquant` | `quantity` | `value` |
| `deductible` | `deductible`, `deduction_reason` | `amount.value`; `reason` code and display joined with ", " |
| `benefit` | `benefit` | `amount.value` |
| `submitted` | `submitted` | `amount.value` |

Predetermination, into D19 `claim_predetermination`: `outcome`, `adjudication`, `disposition`, `allowed_amount` (the `benefit` total), `response_json`, `status` `answered`, `answered_at`.

In a Task reply (F10) the same fields are read, then used by the Task's rules there.

#### F9U. USED BY
- APIs: [A17. Claim State](../apis/A17-claim-state.md)
- Callbacks: [C5. Pre-auth Reply](../callbacks/C5-preauth-on-submit.md), [C6. Claim Reply](../callbacks/C6-claim-on-submit.md), [C7. Cancel Reply](../callbacks/C7-cancel-on-submit.md), [C8. Enquiry Reply](../callbacks/C8-enquiry-on-submit.md)
- FHIR: [F1. Bundle](F1-bundle.md), [F10. Task (claim actions)](F10-task-claim-actions.md), [F11. CommunicationRequest](F11-communicationrequest.md)
