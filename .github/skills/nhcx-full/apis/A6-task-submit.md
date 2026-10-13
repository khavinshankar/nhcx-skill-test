# A6. Task Submit (cancel, status, reprocess, release)

#### A6E. ENDPOINT
In-process: `gateway.send("v1/task/submit", envelope)`, [G7. Send](../gateway/G7-send.md), which encrypts it and posts it to NHCX for the payer: `POST {nhcx}/v1/task/submit`. The payer answers with a Task bundle on `task/on_submit` (taken in by [G8. Receive](../gateway/G8-receive.md), callbacks C7 and C8 through the callback door C1, type `task` or `status`, or found by polling the [G9. Ledger](../gateway/G9-ledger.md), A10 / A11 / A12 / A13).

#### A6D. DESCRIPTION
Every follow-up request that is not a Claim goes on this route as a Task bundle. Four kinds:

| Kind | What it asks | Leg |
|---|---|---|
| cancel | Withdraw the pre-authorisation | pre-auth |
| status | Where does this leg stand? | pre-auth or claim |
| reprocess | Look at a decided claim again | claim |
| release | Pay the unpaid balance of a partly paid claim | claim |

FHIR: [F1. Bundle](../fhir/F1-bundle.md) (the bundle id and Task anchor of each kind), [F10. Task (claim actions)](../fhir/F10-task-claim-actions.md)

**The intimation input.** Beside `claimNumber`, a cancel and a reprocess name the case once more in an input whose type code comes from the payer adapter, per kind (see [PAYERS.md](../references/PAYERS.md)) [PAYER](../references/PAYERS.md#markers): `intimationNumber` everywhere, except `initimationNumber` (the payer's own misspelling) on a `pmjay` cancel, which the PMJAY sandbox refuses otherwise with ERR-PYR-CLM-007 [SANDBOX](../references/PAYERS.md#markers).

The status Task goes on `task/submit`, not on the NHCX status route, because the NHCX sandbox refuses `v1/status` with NHCX-1012 whatever correlation id it carries [SANDBOX](../references/PAYERS.md#markers).

**Workflow ids (`x-hcx-workflow_id`).** From the payer adapter (see [PAYERS.md](../references/PAYERS.md)) [PAYER](../references/PAYERS.md#markers).

| Kind | `pmjay` | `kyrocare` (Sandbox Payer) | `generic` |
|---|---|---|---|
| cancel | PC01 | PC01 | PC01 |
| status | the leg's correlation id, else `13` [REF](../references/PAYERS.md#markers) | same | same |
| reprocess | 36 | 36 | 36 |
| release | 36 | 36 | 36 |

Cancel, reprocess and release are read from the adapter and can be overridden per environment (a JSON object of kind to workflow id), for example to send cancel as `122`, which one NHA source gives in place of PC01. The status Task's workflow id is not read from the adapter [REF](../references/PAYERS.md#markers).

**Headers set by the application** (G7 generates the rest, [G5. Protocol Headers](../gateway/G5-protocol-headers.md)): `x-hcx-sender_code` = facility participant code; `x-hcx-recipient_code` = the case's processing id (D9 `processing_id`), else the case's processing id, else the claim's payer id, else the configured default payer code; `x-hcx-workflow_id` as above.

**Status enquiry and the adapter.** PMJAY answers no status Task (it refuses it with PAYR-1018 without a reason code and PAYR-1008 with one) [PAYER](../references/PAYERS.md#markers) (see [PAYERS.md](../references/PAYERS.md)), so its adapter turns the enquiry off and a request is refused before sending: "`<adapter name>` answers no status enquiry over NHCX; read where the case stands on its own desk, and the verdict arrives on this thread." The Sandbox Payer and Generic adapters allow it.

**Checks before sending.**

| Kind | Errors, in order |
|---|---|
| cancel | "There is no pre-authorisation to cancel."; "A pre-authorisation that is `<status label, lower case>` cannot be cancelled." (only `submitting`, `approved`, `partial`, `queried` can be); "Choose why the pre-authorisation is being cancelled."; with reason `other` and no note: "Describe the reason, with “Other reason” the note is the only thing the payer can read."; "Set the facility's HFR ID and NHCX participant code under Settings first." |
| status | "Ask about the pre-authorisation or the claim."; the adapter refusal above; "No pre-authorisation has been sent yet." (pre-auth) or "The claim has not been submitted yet." (claim); the Settings error |
| reprocess | "Only a claim the payer has decided can be sent back for reprocessing." (claim must be `rejected`, `partial` or `approved`); "A claim that has been paid in full cannot be reprocessed."; "Say why the claim should be looked at again."; the Settings error; "Choose why the claim is being sent back." (a reason code the adapter does not allow); "That document is not on this claim." |
| release | "Only a decided claim can have its balance asked for." (`approved` or `partial`); "A claim that has been paid in full has no balance."; "Say how much of the claim is still owed." (blank, zero or negative); the Settings error |

"Paid in full" means the paid total from payment notices (A8) is at least the claimed amount.

**Cancel reasons:**

| Code | Display |
|---|---|
| `treatmentplanchanged` | Treatment plan changed during hospitalization |
| `patientrequest` | Patient requested cancellation |
| `financialconstraints` | Financial constraints |
| `alternativetreatment` | Alternative treatment chosen |
| `duplicateclaim` | Duplicate claim / preauth |
| `administrativeerror` | Administrative error |
| `other` | Other reason (the note is then required) |

**Reprocess reasons** (all three allowed by every adapter):

| Code | Display |
|---|---|
| `claimrejected` | Reprocess request due to claim rejected by payer |
| `partialpayment` | Reprocess request due to partial payment by payer |
| `rejectiondisputed` | Rejection disputed, additional evidence provided |

#### A6Q. REQUEST

The arguments passed to G7 Send:

| Field | Type | Notes |
|---|---|---|
| `jwe_headers` | object | The three headers above |
| `fhir` | Bundle | The Task, then the provider and payer Organizations |

FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F10. Task (claim actions)](../fhir/F10-task-claim-actions.md), [F17. Organization](../fhir/F17-organization.md)

Envelope, cancel (PMJAY):

```json
{
  "jwe_headers": {"x-hcx-sender_code": "<facility code>",
                  "x-hcx-recipient_code": "<payer code>",
                  "x-hcx-workflow_id": "PC01"},
  "fhir": <F1 Bundle carrying F10 Task (code cancel, reason administrativeerror, claimNumber and the intimation input, spelt initimationNumber under pmjay [PAYER](../references/PAYERS.md#markers), both NM-26-0SH000006), F17 provider and payer Organizations>
}
```

Envelope, status (Sandbox Payer; the workflow id is the pre-auth's correlation id):

```json
{"jwe_headers": {"x-hcx-sender_code": "<facility code>",
                 "x-hcx-recipient_code": "<payer code>",
                 "x-hcx-workflow_id": "623780ae-bf5e-4f47-82fc-790e1644a642"},
 "fhir": <F1 Bundle carrying F10 Task (code status, claimNumber NM-26-0SH00002B), F17 Organizations>}
```

A reprocess (PMJAY, workflow `36` [PAYER](../references/PAYERS.md#markers)) and a release carry their own F10 Task in the same envelope.

#### A6S. RESPONSE

**Acknowledgement:** the G7 result, `{"ok": true, "gateway_status": 202, "txn_id", "correlation_id", "request_id", "headers", "response", ...}`.
- Cancel: the pre-auth leg goes to `cancelling` under the cancel's own ids, with the reason and the note. A `ProtocolResponse` on that thread (C7) puts the leg back to its earlier status with the refusal text, so a corrected cancel can be sent again.
- Status, reprocess, release: an enquiry row in `asking` under its own ids.

**Failed send.** When the failure names ids: the cancel leaves the pre-auth in `error` with the message under the cancel ids; an enquiry row is stored as `error`. A payer answer that later arrives on those ids reopens the row and is applied.

Data: [D18. claim_preauth](../database/D18-claim-preauth.md), [D29. claim_enquiry](../database/D29-claim-enquiry.md)

Reply: [C7. Cancel Reply](../callbacks/C7-cancel-on-submit.md) (cancel), [C8. Enquiry Reply](../callbacks/C8-enquiry-on-submit.md) (status, reprocess, release)

**Polling.**
- Cancel (while `cancelling`, or within 15 minutes of a refusal): A10 (G9 related) with `cancel_txn_id`; every entry not sent by this facility is fetched with A12, and every bundle carrying a Task is read; an acceptance is applied first, else the newest answer. With none, a ProtocolResponse found through A13 (type `task`) and A12 turns it to `error`. When G9 no longer holds it (A10 not found): "The gateway no longer has the cancel transaction, its ledger was reset after it was sent. Cancel again." (ignored during the grace period).
- Enquiries (while `asking`): A10, newest inbound Task via A12. With none: a refused payer answer when one G hosts both participants, a ProtocolResponse through A13 (type `task`), or the enquiry's own A11 status (`dispatch_failed`, shown as the ledger's `errorMessage` / `errorCode` / "Dispatch to NHCX failed.") makes it `error`. When G9 no longer holds it (A10 not found): "The gateway no longer has this transaction. Ask again."

#### A6P. PSEUDOCODE

```
// shared send convention (every outbound bundle), in-process through G7
function SEND(path, envelope, case):
    archive envelope with the case (outbound)
    try:
        result = gateway.send(path, envelope)       // G7 Send, posts to {nhcx}/<path>
    catch send_error:                               // G7 SendError {code, message, retryable, ...}
        if send_error names ids (txn_id, correlation_id):
            return ack = those ids, failed = send_error
        raise send_error                            // nothing went out; nothing written
    ack = {txn_id: result.txn_id, correlation_id: result.correlation_id,
           request_id: result.request_id}
    if not result.ok:                               // NHCX did not accept it; ledger row "rejected"
        return ack, failed = NHCX's refusal (APIs conventions)
    return ack, failed = none

function task_parties(case_id):
    case = claim[case_id]                  or refuse "Claim not found."
    org  = default organization
    if org missing or HFR ID or participant code empty:
        refuse "Set the facility's HFR ID and NHCX participant code under Settings first."
    provider = {id: org HFR ID, name: org.name}
    payer    = {code: case.payer_id or default payer code, name: case.payer_name or registry_name(code) or code}   // the registry's name, never a configured one
    return case, org, provider, payer

function leg_reference(case_id, stage):          // the number the payer knows the leg by, and its thread
    if stage == claim:
        state = claim_submission for the case
        if state missing or state.status == draft: refuse "The claim has not been submitted yet."
        return state.claim_ref or case.claim_no, state.correlation_id
    sent = claim_preauth for the case
    if sent missing: refuse "No pre-authorisation has been sent yet."
    return sent.claim_ref or case.claim_no, sent.correlation_id

// ---- cancel
function cancel_preauth(case_id, reason, note):
    sent = claim_preauth for the case
    if sent missing: refuse "There is no pre-authorisation to cancel."
    if sent.status not in {submitting, approved, partial, queried}:
        refuse "A pre-authorisation that is <status label, lower case> cannot be cancelled."
    if reason not in cancel reasons: refuse "Choose why the pre-authorisation is being cancelled."
    note = trim(note)
    if reason == other and note empty:
        refuse "Describe the reason, with “Other reason” the note is the only thing the payer can read."
    case, org, provider, payer = task_parties(case_id)
    bundle = F1 Bundle carrying F10 Task (cancel, reason code and display, note,
             claimNumber = case.claim_no, intimation input typed adapter.intimation_input(cancel)
             = case.claim_no   // [PAYER](../references/PAYERS.md#markers) pmjay: initimationNumber; others: intimationNumber), F17 Organizations
    ack, failed = SEND("v1/task/submit", {
        jwe_headers: {x-hcx-sender_code: org.participant_code,
                      x-hcx-recipient_code: case.processing_id or case.payer_id or default payer code,
                      x-hcx-workflow_id: workflow_id(adapter, cancel)},
        fhir: bundle}, case)
    UPDATE claim_preauth[sent.id] SET pre_cancel_status = sent.status, status = cancelling, cancel_txn_id = ack.txn_id,
        cancel_correlation_id = ack.correlation_id, cancel_requested_at = now,
        cancel_reason = reason, cancel_note = note or null, error_message = null
        (status = error, error_message = failed.message when failed); recompute case stage
    if failed: raise failed

// ---- enquiries (status, reprocess, release) share one sender
function send_enquiry(case_id, kind, stage, path, bundle, case, org, workflow, reason):
    ack, failed = SEND(path, {
        jwe_headers: {x-hcx-sender_code: org.participant_code,
                      x-hcx-recipient_code: case.processing_id or case.payer_id or default payer code,
                      x-hcx-workflow_id: workflow},
        fhir: bundle}, case)
    id = INSERT claim_enquiry {claim_id, kind, stage, txn_id: ack.txn_id,
         correlation_id: ack.correlation_id, requested_at: now, status: asking,
         reason: reason or null, request_json: bundle}
         with status = error, error_message = failed.message when failed
    if failed: raise failed
    return id

function ask_status(case_id, stage):
    if stage not in {preauth, claim}: refuse "Ask about the pre-authorisation or the claim."
    adapter = payer adapter for the case
    if adapter turns the status enquiry off:
        refuse "<adapter name> answers no status enquiry over NHCX; read where the case stands on its own desk, and the verdict arrives on this thread."
    claim_ref, thread = leg_reference(case_id, stage)
    case, org, provider, payer = task_parties(case_id)
    bundle = F1 Bundle carrying F10 Task (status, claimNumber = claim_ref) for the stage, F17 Organizations
    return send_enquiry(case_id, status, stage, "v1/task/submit", bundle,
                        case, org, workflow = thread or "13", reason = "")   // [REF](../references/PAYERS.md#markers)

function ask_reprocess(case_id, reason, reason_code, document_ids):
    state = claim_submission for the case
    if state missing or state.status not in {rejected, partial, approved}:
        refuse "Only a claim the payer has decided can be sent back for reprocessing."
    paid = paid total from claim_payment (settled notices, once per UTR, newest wins)
    if paid and paid >= state.requested_amount:
        refuse "A claim that has been paid in full cannot be reprocessed."
    reason = trim(reason)
    if reason empty: refuse "Say why the claim should be looked at again."
    case, org, provider, payer = task_parties(case_id)
    if reason_code not in reprocess reasons or not allowed by the adapter:
        refuse "Choose why the claim is being sent back."
    claim_ref, _ = leg_reference(case_id, claim)
    documents = for each id: claim_document[id], must belong to the case, else
                refuse "That document is not on this claim."   (base64 data, title)
    member = (PMJAY if adapter is PMJAY else MB, case.member_id)     // [PAYER](../references/PAYERS.md#markers)
    bundle = F1 Bundle carrying F10 Task (reprocess, reason code and display, reason text,
             claim_ref, documents, member), F17 Organizations
    id = send_enquiry(case_id, reprocess, claim, "v1/task/submit", bundle,
                      case, org, workflow_id(adapter, reprocess), reason)
    UPDATE claim_enquiry[id] SET reason_code = reason_code, document_ids = document_ids
    return id

function ask_release(case_id, amount, note):
    state = claim_submission for the case
    if state missing or state.status not in {approved, partial}:
        refuse "Only a decided claim can have its balance asked for."
    paid = paid total from claim_payment (settled notices, once per UTR, newest wins)
    if paid and paid >= state.requested_amount:
        refuse "A claim that has been paid in full has no balance."
    if amount blank or amount <= 0: refuse "Say how much of the claim is still owed."
    case, org, provider, payer = task_parties(case_id)
    claim_ref, _ = leg_reference(case_id, claim)
    bundle = F1 Bundle carrying F10 Task (release, claim_ref, amount, note), F17 Organizations
    return send_enquiry(case_id, release, claim, "v1/task/submit", bundle,
                        case, org, workflow_id(adapter, release), trim(note))
```

#### A6U. USED BY
- Screens: [S9. Pre-authorisation](../screens/S9-preauthorisation.md), [S11. Claim Submission](../screens/S11-claim-submission.md)
- APIs: [A5. Claim Submit](A5-claim-submit.md), [A10. Transaction Related](A10-txn-related.md), [A11. Transaction Dispatch](A11-txn-dispatch.md), [A13. Transaction List](A13-txn-list.md)
- Callbacks: [C1. Callback Door](../callbacks/C1-callback-door.md), [C7. Cancel Reply](../callbacks/C7-cancel-on-submit.md), [C8. Enquiry Reply](../callbacks/C8-enquiry-on-submit.md)
- FHIR: [F10. Task (claim actions)](../fhir/F10-task-claim-actions.md)
- Tests: [T2. Test Runners](../tests/T2-test-runners.md), [T9. IRDAI Status Enquiry and Cancel](../tests/T9-irdai-cancel-and-status.md), [T12. IRDAI Reprocess and Balance Release](../tests/T12-irdai-reprocess-and-release.md), [T18. PMJAY Payment Notice, Status Refusal and Cancel](../tests/T18-pmjay-payment-status-cancel.md)
