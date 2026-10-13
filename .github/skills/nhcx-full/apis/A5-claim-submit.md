# A5. Claim Submit

#### A5E. ENDPOINT
In-process: `gateway.send("v1/claim/submit", envelope)`, [G7. Send](../gateway/G7-send.md), which encrypts it and posts it to NHCX for the payer: `POST {nhcx}/v1/claim/submit`. The verdict comes back asynchronously on `claim/on_submit` (taken in by [G8. Receive](../gateway/G8-receive.md), callback C6 through the callback door C1, type `claim`, or found by polling the [G9. Ledger](../gateway/G9-ledger.md), A10 / A11 / A12 / A13).

#### A5D. DESCRIPTION
Files the claim once the patient has left: the pre-authorisation's bundle with `use: claim`, the payer's pre-auth reference on the insurance line, the Procedure marked completed, the claim-stage documents and forms, and the discharge on `supportingInfo`. It is also the route for answering a claim query in `resubmit` mode, and for resubmitting a decided claim where the payer takes that.

**Send kinds.**

| Where the claim stands | Kind |
|---|---|
| No claim record, or `draft` | `claim` |
| `queried` | `claim_query_response` |
| `approved`, `partial` or `rejected`, when the adapter has a resubmit workflow | `claim_resubmit` |
| `approved`, `partial` or `rejected`, adapter has none | refused: "The payer has decided this claim; it goes back for another look as a reprocess request, not as a claim sent again." |
| `error` | the kind that failed is sent again (`claim_query_response` or `claim_resubmit`), else `claim` |
| `submitting` | refused: "The claim is with the payer; wait for its answer before sending again." |

FHIR: [F1. Bundle](../fhir/F1-bundle.md) (the bundle id and Claim anchor of each kind), [F8. Claim](../fhir/F8-claim.md)

**Status (`x-hcx-status`).** Set by the send, not left to the gateway's path default: `response.complete` for a claim query answer (`claim_query_response`), `request.initiated` for everything else, as NHA's workflow sheet pairs them (see [PAYERS.md](../references/PAYERS.md)). The reference implementation left it to the default, `request.initiated`, on every send [REF](../references/PAYERS.md#markers).

**Workflow ids (`x-hcx-workflow_id`)**, from the payer adapter (see [PAYERS.md](../references/PAYERS.md)) [PAYER](../references/PAYERS.md#markers), overridable per environment (a JSON object of kind to workflow id):

| Kind | `pmjay` | `kyrocare` (Sandbox Payer) | `generic` |
|---|---|---|---|
| `claim` | 15 | 15 | 15 |
| `claim_query_response` | 151 (adapter default; 161 as a sandbox configuration override [SANDBOX](../references/PAYERS.md#markers)) | 151 | 151 |
| `claim_resubmit` | none (not offered) | 16 [REF](../references/PAYERS.md#markers) | 16 [REF](../references/PAYERS.md#markers) |

16 (claim resubmitted) is not in NHA's published workflow list; the reference implementation used it for the non-PMJAY adapters [REF](../references/PAYERS.md#markers). Confirm with the payer before offering a resubmission.

The SHA sandbox refuses 16, 151 and 19 on a claim with PAYR-1321 "Invalid workflow id" and takes 161 for a query answer [SANDBOX](../references/PAYERS.md#markers). The adapter's value stays the published 151; a sandbox run sets 161 through the per-environment override, so the sandbox quirk never becomes the adapter's default. A decided PMJAY claim goes back only as a reprocess Task (A6) [PAYER](../references/PAYERS.md#markers).

**Use case (`x-hcx-use_case`).** Every claim send carries it, to every payer, whether or not the payer reads it: `New` for `claim`, `Resubmit` for `claim_query_response` and `claim_resubmit` (see [PAYERS.md](../references/PAYERS.md)).

**Headers set by the application** (G7 generates the rest, [G5. Protocol Headers](../gateway/G5-protocol-headers.md)): `x-hcx-sender_code` = facility participant code; `x-hcx-recipient_code` = the case's processing id (D9 `processing_id`), else the case's processing id, else the claim's payer id, else the configured default payer code; `x-hcx-workflow_id` as above.

**Checks before sending**, in order:
1. The send-kind refusals above.
2. On `claim_query_response` with no reply text: "Write the reply to the payer's query before answering it."
3. "Record how the patient was discharged before claiming."
4. "A claim goes in against an approved pre-authorisation." (the pre-auth must be `approved` or `queried`)
5. "Set the facility's HFR ID and NHCX participant code under Settings before submitting."
6. "Link the admitted patient before submitting."
7. "Enter the admission date on the preauth draft."
8. "Quote at least one ICD-10 diagnosis."
9. "Add at least one doctor to the care team."
10. "Add at least one line, the procedure being done."

#### A5Q. REQUEST

The arguments passed to G7 Send:

| Field | Type | Notes |
|---|---|---|
| `jwe_headers` | object | The three headers above, plus the beneficiary's discharge user token under the configured header and `x-hcx-ben-abha-id` when [A18. Biometric Authentication](A18-biometric-authentication.md) holds a current stage-Discharge authentication (then the Discharge Consent form is left out of the bundle) |
| `fhir` | Bundle | The Claim bundle |

The resources are those of the pre-authorisation bundle (A4 REQUEST), with the claim leg's differences: `use` claim, the pre-auth reference, the discharge, the claim lines (a LAMA or DAMA discharge before or during surgery collapses them to the single procedure `LM100` [PAYER](../references/PAYERS.md#markers)), the Procedure completed, and only the claim-stage documents and forms.

FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F8. Claim](../fhir/F8-claim.md), [F15. Patient](../fhir/F15-patient.md), [F17. Organization](../fhir/F17-organization.md), [F18. Coverage](../fhir/F18-coverage.md), [F16. Practitioner and PractitionerRole](../fhir/F16-practitioner.md), [F19. Other bundle resources](../fhir/F19-other-resources.md) (Procedure), [F7. QuestionnaireResponse](../fhir/F7-questionnaireresponse.md)

Envelope (PMJAY first claim):

```json
{
  "jwe_headers": {"x-hcx-sender_code": "<facility code>",
                  "x-hcx-recipient_code": "<payer code>",
                  "x-hcx-workflow_id": "15"},
  "fhir": <F1 Bundle carrying F8 Claim (use claim, preAuthRef, discharge), F15 Patient, F17 provider and payer Organizations, F18 Coverage, F16 Practitioner, F19 Procedure (completed), F7 QuestionnaireResponse per answered claim-leg form>
}
```

A PMJAY query answer goes under the adapter's claim query-response workflow id (151; 161 under the sandbox override [SANDBOX](../references/PAYERS.md#markers)) [PAYER](../references/PAYERS.md#markers) with the reply text riding on the Claim as the "Claim query detail" entry (F8), for example "Final bill and discharge summary attached again; the ward stay was two days as billed.".

#### A5S. RESPONSE

**Acknowledgement:** the G7 result, `{"ok": true, "gateway_status": 202, "txn_id", "correlation_id", "request_id", "headers", "response", ...}`. The claim leg becomes `submitting` under its ids (`txn_id`, `correlation_id`); the previous verdict fields are cleared. On a query answer the question being answered is kept so it can still be shown.

**Failed send.** When the failure names ids, the leg is kept under them as refused at the door: a query answer goes back to `queried` with the question restored and the message recorded; any other kind becomes `error`. A later answer on the failed send's correlation reopens the leg.

Data: [D20. claim_submission](../database/D20-claim-submission.md)

Reply: [C6. Claim Reply](../callbacks/C6-claim-on-submit.md)

**Polling** (claim `submitting`, on each load of S6): A10 (G9 related) with the claim's `txn_id`, newest inbound ClaimResponse via A12. With none, a refused payer answer when one G hosts both participants, or a ProtocolResponse for this correlation found through A13 (type `claim`) and A12, is applied as a refusal at the door; then A11 (G9 dispatch), where `dispatch_failed` is also a refusal at the door with the ledger's `errorMessage` / `errorCode` / "Dispatch to NHCX failed.". When G9 no longer holds the transaction (A10 not found), the claim turns to `error`: "The gateway no longer has this transaction, its ledger was reset after the claim was sent. Submit again."

#### A5P. PSEUDOCODE

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

function submit_claim(case_id, reply):
    case  = claim[case_id]
    kind  = claim_send_kind(case_id)                       // may refuse
    state = claim_submission for the case
    answering = (kind == claim_query_response)
    question  = (state.query_note or state.disposition) if answering and state exists
    answer = null
    if answering:
        answer = trim(reply)
        if answer empty: refuse "Write the reply to the payer's query before answering it."

    // gather (each refusal in this order)
    case = claim[case_id]                  or refuse "Claim not found."
    discharge = claim_submission row
    if discharge missing or discharge.discharge_mode empty:
        refuse "Record how the patient was discharged before claiming."
    granted = claim_preauth for the case
    if granted missing or granted.status not in {approved, queried}:
        refuse "A claim goes in against an approved pre-authorisation."
    lines = claim lines: the claim_line rows, or, for a LAMA / DAMA discharge before or
            during surgery, the single procedure LM100 at its claim_plan_benefit rate, quantity =
            days admitted (admission to discharge, at least 1) [PAYER](../references/PAYERS.md#markers)
            (display "LAMA / DAMA procedure", rate 0 when the plan has no such package [REF](../references/PAYERS.md#markers))
    same organization, encounter, admission date, claim_diagnosis, claim_care_team and
        line refusals as A4 (checks 5 to 10), reading organization, patient, practitioner,
        claim_plan_benefit (procedure type)
    summary   = the claim-stage claim_document whose code the ruling (claim_auth_requirement)
                or plan names for a "discharge summary", else the claim_document coded HDS [PAYER](../references/PAYERS.md#markers)
    documents = claim-stage claim_document rows (minus form-answer files), excluding
                HDS and the summary
    forms     = claim-stage forms (D12 rule: the ruling's claim forms, plus the quoted packages'
                own STG forms, plus the policy-wide forms, plus the Discharge Consent when no
                stage-Discharge token is held) with answers from claim_form_answer
    total     = sum of the claim lines

    // build
    bundle = F1 Bundle for leg claim, flow queryupdate if answering else request,
             carrying F8 Claim (use claim, billable period admission to discharge date
             else admission, preAuthRef = granted.preauth_ref, discharge mode, stage,
             surgery, discharge and death instants, summary, documents, reply text
             as the query detail when answering, total), F15 Patient, F17 Organizations,
             F18 Coverage, F16 Practitioners, F19 Procedures (completed), F7 QuestionnaireResponses
    workflow = workflow_id(adapter, kind)

    // call
    ack, failed = SEND("v1/claim/submit", {
        jwe_headers: {x-hcx-sender_code: org.participant_code,
                      x-hcx-recipient_code: case.processing_id or case.payer_id or default payer code,
                      x-hcx-workflow_id: workflow,
                      x-hcx-use_case: use_case_for(kind),      // New, or Resubmit for a query answer or a resubmission
                      x-hcx-status: status_for(adapter, kind)},   // response.complete for a query answer (151; 161 under the sandbox override), else request.initiated
        fhir: bundle}, case)

    // write
    values = {status: submitting, txn_id: ack.txn_id, correlation_id: ack.correlation_id,
              submitted_at: now, settled_at: null, error_message: null,
              claim_ref: case.claim_no, outcome: null, disposition: null,
              approved_amount: null, eligible_amount: null, submitted_amount: null,
              items_json: null, requested_amount: total, submission_kind: kind,
              workflow_id: workflow, request_json: bundle, response_json: null,
              reply_text: answer}
    if question: values.query_note = question
    if failed:                                              // refused at the door
        values.status = error; values.error_message = failed.message
        if kind == claim_query_response:
            values.status = queried; values.disposition = question
    UPDATE claim_submission (created as draft first when missing) SET values;
        recompute case stage
    if failed: raise failed

function claim_send_kind(case_id):
    state = claim_submission for the case
    if state is none or state.status == draft: return claim
    if state.status == error:
        return state.submission_kind if in {claim_query_response, claim_resubmit} else claim
    if state.status == queried: return claim_query_response
    if state.status in {rejected, partial, approved}:
        if adapter has no claim_resubmit workflow id:
            refuse "The payer has decided this claim; it goes back for another look as a reprocess request, not as a claim sent again."
        return claim_resubmit
    if state.status == submitting:
        refuse "The claim is with the payer; wait for its answer before sending again."
    return claim
```

#### A5U. USED BY
- Screens: [S11. Claim Submission](../screens/S11-claim-submission.md), [S14. Patient Registration Form](../screens/S14-patient-registration-form.md), [S15. Patient Detail](../screens/S15-patient-detail.md), [S16. Practitioner Master](../screens/S16-practitioner-master.md), [S18. Beneficiary Verification](../screens/S18-beneficiary-verification.md)
- APIs: [A7. Communication Reply](A7-communication-on-request.md), [A10. Transaction Related](A10-txn-related.md), [A11. Transaction Dispatch](A11-txn-dispatch.md), [A13. Transaction List](A13-txn-list.md), [A17. Claim State](A17-claim-state.md), [A18. Biometric Authentication](A18-biometric-authentication.md)
- Callbacks: [C6. Claim Reply](../callbacks/C6-claim-on-submit.md)
- FHIR: [F8. Claim](../fhir/F8-claim.md), [F9. ClaimResponse](../fhir/F9-claimresponse.md), [F12. Communication](../fhir/F12-communication.md), [F15. Patient](../fhir/F15-patient.md), [F17. Organization](../fhir/F17-organization.md), [F18. Coverage](../fhir/F18-coverage.md)
- Database: [D12. claim_plan_form](../database/D12-claim-plan-form.md), [D31. biometric_auth](../database/D31-biometric-auth.md)
- Gateway: [G5. Protocol Headers](../gateway/G5-protocol-headers.md)
- Tests: [T10. IRDAI Claim Approved, Part-approved and Rejected](../tests/T10-irdai-claim.md), [T17. PMJAY Claim Through the Role Walk](../tests/T17-pmjay-claim-adjudicated.md), [T19. PMJAY Beneficiary Verification and ABHA](../tests/T19-pmjay-biometric-and-abha.md)
