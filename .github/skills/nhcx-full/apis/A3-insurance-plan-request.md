# A3. Insurance Plan Request

#### A3E. ENDPOINT
In-process: `gateway.send("v1/insuranceplan/request", envelope)`, [G7. Send](../gateway/G7-send.md). G7 encrypts and posts it to NHCX: `POST {nhcx}/v1/insuranceplan/request`. The payer answers asynchronously with `v1/insuranceplan/on_request`, taken in by [G8. Receive](../gateway/G8-receive.md) and handed to the callback door C1 (type `insurance`), or found by polling the [G9. Ledger](../gateway/G9-ledger.md) (A10 to A13).

#### A3D. DESCRIPTION
Asks the payer for its package master (the InsurancePlan) for this policy and this facility: every empanelled speciality, the packages under it, their rates, ward and implant tiers, claim conditions, the documents each package needs and the questionnaires those documents point at. It is the only exchange whose request carries no clinical content: a discovery `Task` naming a policy number and the facility's HFR ID.

A master belongs to a facility and a policy, not to one case. So on a first fetch the app first looks for a `ready` master already held on another case with the same payer, the same policy code and the same facility HFR ID. When there is one, the newest is copied onto this case with its packages and forms and no request goes out. "Fetch again" (refresh) always asks the payer. A full scheme master runs to tens of megabytes [PAYER](../references/PAYERS.md#markers).

JWE headers: the app sets only these three; G7 generates the rest ([G5. Protocol Headers](../gateway/G5-protocol-headers.md)).
- `x-hcx-sender_code`: the facility's NHCX participant code.
- `x-hcx-recipient_code`: the case's `processing_id`, else its `payer_id`, else the configured default payer code.
- `x-hcx-workflow_id`: the case number [REF](../references/PAYERS.md#markers). It is also how the case finds the exchange again, since the Task itself names no case. Confirm the value against the knowledge source (see [PAYERS.md](../references/PAYERS.md)).

Refused before any call:
- "Claim not found."
- "Set the facility's HFR ID under Settings before fetching a package master."
- "Set the facility's NHCX participant code under Settings before fetching a package master."
- with neither a policy code nor an HFR ID: "A plan request needs a policy code or the facility's HFR ID."

#### A3Q. REQUEST

The envelope's fields are the arguments passed to G7 Send.

| Field | Type | Required | Value |
|---|---|---|---|
| `jwe_headers.x-hcx-sender_code` | string | yes | facility participant code |
| `jwe_headers.x-hcx-recipient_code` | string | yes | payer participant code |
| `jwe_headers.x-hcx-workflow_id` | string | yes | case number [REF](../references/PAYERS.md#markers) |
| `fhir` | object | yes | a Task bundle naming the policy number (when the case has one) and the facility HFR ID |

FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F4. Task (InsurancePlan discovery)](../fhir/F4-task-insuranceplan.md)

Envelope, from a case file:

```json
{
 "jwe_headers": {
  "x-hcx-sender_code": "<facility code>",
  "x-hcx-recipient_code": "<payer code>",
  "x-hcx-workflow_id": "NM-26-0SH000004"
 },
 "fhir": <F1 Bundle carrying one F4 Task (policyNumber POL7UMU001, providerId IN1910000151)>
}
```

#### A3S. RESPONSE
Acknowledgement: the G7 result, `{"ok": true, "gateway_status": 202, "txn_id": "...", "correlation_id": "...", "request_id": "...", "headers": {...}, "response": ...}`. The plan goes to `fetching` under its ids (`txn_id`, `correlation_id`) and every earlier result is cleared. A refetch deletes the case's stored packages before the answer lands, so a stale package cannot survive. A failed send that names its ids keeps them and sets the plan to `error` (shared convention).

Plan statuses: `fetching` (Awaiting payer), `ready`, `empty` (No plan returned), `error`.

Data: [D10. claim_plan](../database/D10-claim-plan.md), [D11. claim_plan_benefit](../database/D11-claim-plan-benefit.md), [D12. claim_plan_form](../database/D12-claim-plan-form.md)

Reply: [C4. Insurance Plan Reply](../callbacks/C4-insuranceplan-on-request.md)

- A failed dispatch comes back from G7 at once as a failed send. While polling, a failed dispatch read from the G9 ledger (A11) or a transaction G9 no longer holds (A10) sets the plan to `error`.

#### A3P. PSEUDOCODE

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

function request_plan(case_id, refresh = false):
    case = claim[case_id]                  or refuse "Claim not found."
    if not refresh and reuse_plan(case_id): return          // no request goes out

    org = default organization
    if org missing or org.identifier_value empty:
        refuse "Set the facility's HFR ID under Settings before fetching a package master."
    if org.participant_code empty:
        refuse "Set the facility's NHCX participant code under Settings before fetching a package master."

    provider_id = org.identifier_value
    policy_code = trim(case.policy_code)
    if policy_code empty and provider_id empty:
        refuse "A plan request needs a policy code or the facility's HFR ID."
    bundle = F1 Bundle carrying F4 Task with input policyNumber (when policy_code)
             and input providerId (provider_id)

    ack, failed = SEND("v1/insuranceplan/request", {
        jwe_headers: {x-hcx-sender_code: org.participant_code,
                      x-hcx-recipient_code: case.processing_id or case.payer_id or default payer code,
                      x-hcx-workflow_id: case.claim_no},     // [REF](../references/PAYERS.md#markers) case number
        fhir: bundle}, case)

    values = {status: fetching, txn_id: ack.txn_id, correlation_id: ack.correlation_id,
              requested_at: now, fetched_at: null, error_message: null,
              policy_code: policy_code or null, provider_id,
              plan_identifier: null, plan_title: null, plan_type: null,
              sum_insured: null, policy_documents: null, response_json: null}   // every earlier result, D10
    if failed: values.status = error; values.error_message = failed.message
    in one transaction:
        if no claim_plan row for the case: INSERT claim_plan (values, claim_id)
        else:
            DELETE claim_plan_benefit WHERE plan_id = plan.id
            UPDATE claim_plan[plan.id] SET values
    if failed: raise failed

function reuse_plan(case_id):
    source = newest claim_plan (by fetched_at, then id) WHERE status = ready
             AND claim_id != case_id AND policy_code = case.policy_code
             AND provider_id = org HFR ID AND its case's payer_id = case.payer_id
    if none: return false
    in one transaction:
        copy every source column except id and claim_id onto this case's claim_plan
            (INSERT, or DELETE its claim_plan_benefit and claim_plan_form rows and UPDATE)
        copy every claim_plan_benefit and claim_plan_form row of source onto this plan
    return true
```

#### A3U. USED BY
- Screens: [S7. Insurance Plan](../screens/S7-insurance-plan.md)
- APIs: [A10. Transaction Related](A10-txn-related.md), [A11. Transaction Dispatch](A11-txn-dispatch.md), [A13. Transaction List](A13-txn-list.md)
- Callbacks: [C4. Insurance Plan Reply](../callbacks/C4-insuranceplan-on-request.md)
- FHIR: [F4. Task (InsurancePlan discovery)](../fhir/F4-task-insuranceplan.md)
- Database: [D10. claim_plan](../database/D10-claim-plan.md)
- Tests: [T4. IRDAI Insurance Plan and Authorisation Requirements](../tests/T4-irdai-plan-and-auth-requirements.md), [T13. PMJAY Eligibility, Package Master and Ruling](../tests/T13-pmjay-eligibility-and-package-master.md)
