# A2. Coverage Eligibility Check

#### A2E. ENDPOINT
In-process: `gateway.send("v1/coverageeligibility/check", envelope)`, [G7. Send](../gateway/G7-send.md). G7 encrypts and posts it to NHCX: `POST {nhcx}/v1/coverageeligibility/check`. The payer answers asynchronously with `v1/coverageeligibility/on_check`, taken in by [G8. Receive](../gateway/G8-receive.md) and handed to the callback door C1 (type `coverage`), or found by polling the [G9. Ledger](../gateway/G9-ledger.md) (A10 to A13).

#### A2D. DESCRIPTION
Sends a `CoverageEligibilityRequest` bundle to the payer. The app builds the bundle itself; G7 only completes the headers, encrypts and dispatches it. The call returns NHCX's acceptance only; the verdict arrives later on the same correlation id.

One bundle shape serves four purposes:

| Purpose | Asked when | Policy code | `item[]` | Stored on |
|---|---|---|---|---|
| `validation` | at registration: is the policy in force? | required | none | the case |
| `benefits` | before a pre-authorisation or an enhancement: what does the policy cover for this package? | required | the lines quoted so far, when there are any | the case |
| `discovery` | an indemnity payer, when the policy is not yet known: find active coverage | optional (`NONE` in the bundle) | none | the case |
| `auth-requirements` | on the chosen procedure set, before a pre-authorisation and again before an enhancement | the case's, `NONE` if it has none | the quoted procedure set, required | the ruling (`claim_auth`), not the case |

The first three are the eligibility check, sent from the check form with the operator's purpose, policy code and member ID. `auth-requirements` is the procedure-set ruling, sent two ways:
- by the operator ("Validate procedure set"), to any payer: the check is optional and is not tied to an adapter;
- automatically, and never waited on, just before a pre-authorisation or enhancement is submitted (A4), when the case is eligible, has lines, the payer's adapter sends this check unasked ([PAYERS.md](../references/PAYERS.md)), and the set has not already been asked about (a ruling not in error whose fingerprint equals the current set). A failure of this automatic send is swallowed and the pre-authorisation goes anyway.

JWE headers: the app sets only these three, plus the beneficiary's user token when the desk holds a current stage-Preauth authentication for the patient and this payer ([A18. Biometric Authentication](A18-biometric-authentication.md), any payer, every purpose), and `x-hcx-ben-abha-id` whenever an ABHA number is known: the token's ABHA when a token is held, else the case's ABHA number (from the policy search or the payer's earlier reply), else the header is **left out**. The beneficiary's ABHA is never mandatory for a check, whatever the transport notes say: a beneficiary found by Member id with no ABHA is checked without the header, and the search option is labelled "Member id"; G7 generates ([G5. Protocol Headers](../gateway/G5-protocol-headers.md)) `x-hcx-api_call_id`, `x-hcx-request_id`, `x-hcx-correlation_id`, `x-hcx-timestamp` and `x-hcx-status`.
- `x-hcx-sender_code`: the facility's NHCX participant code (Settings).
- `x-hcx-recipient_code`: the policy's `processing_id` from the policy search (A1), else its `payer_id`, else the configured default payer code. NHA's documentation is explicit that the recipient is the processing id, not the payer id (NHCX-1003 otherwise) (in the reference implementation the PMJAY payer, see [PAYERS.md](../references/PAYERS.md)) [REF](../references/PAYERS.md#markers).
- `x-hcx-workflow_id`: `11` (Patient Admitted, NHA's own sample) for every purpose, the one default; a module setting (`eligibility_workflow_id`, `11` or `case`) sends the case number instead for a payer that wants it. Both are accepted by the sandbox payers [SANDBOX](../references/PAYERS.md#markers). (The adapter's workflow-id table is not used for this call; see [PAYERS.md](../references/PAYERS.md).)

Refused before any call, eligibility check (in this order):
- "Claim not found."
- purpose not validation, benefits or discovery: "Choose whether this check is a validation, a benefits check or a discovery."
- "Member ID is required for an eligibility check."
- "Policy code is required for a validation check." / "Policy code is required for a benefits check."
- "Set the facility's HFR ID under Settings before raising claims."
- "Set the facility's NHCX participant code under Settings before raising claims."

Refused before any call, auth-requirements:
- "Claim not found."
- case not `eligible`: "Check the policy's eligibility before validating a procedure set against it."
- no lines: "Choose the line items first, this checks the procedure set, so there has to be one."
- "Set the facility's HFR ID and NHCX participant code under Settings before checking requirements."

**Additional information on a discovery.** A discovery sent from the discovery page ([S17. Beneficiary Discovery](../screens/S17-beneficiary-discovery.md)) may carry what else the desk knows about the person, so the payer has more than one handle to match on. Each is optional and is left out of the bundle when empty ([F15. Patient](../fhir/F15-patient.md)):

| Field | Rule | In the bundle |
|---|---|---|
| Aadhaar number | 12 digits once spaces and hyphens are removed, else "An Aadhaar number has 12 digits" | Patient identifier typed `ADN` |
| Mobile number | 10 digits, else "A mobile number has 10 digits" | Patient `telecom`, system `phone` |
| Member ID | free text | becomes the member the bundle names (the `PMJAY` and `MB` identifiers and `Coverage.subscriberId`); the identifier searched on then rides beside it: an ABHA number as an identifier typed `ABHA`, a mobile as the phone |

The Aadhaar number is sent to the payer and kept in the stored bundle; screens that list a check show its last four digits only.

**A discovery needs a case to land on.** C2 matches the verdict by correlation id against a D9 row, and a discovery started from [S17. Beneficiary Discovery](../screens/S17-beneficiary-discovery.md) has none yet. So `discover()` opens a draft case for the patient and the chosen payer first (D9: `status` `draft`, `purpose` `discovery`, `patient_id`, `payer_id`, `processing_id` = the payer code, `member_id` the identifier given, no policy yet), then sends on it; the cover the desk picks from the answer is applied to that same case (policy code, member id, product). The facility guard (HFR id and participant code set) is checked **before** the case is created, so a refusal leaves no orphan case.

The bundle builder itself refuses a bundle without a member id ("A coverage check needs the member id to ask about."), without the facility registry id ("A coverage check needs the facility's registry id.") or without a payer code ("A coverage check needs the payer's participant code.").

#### A2Q. REQUEST

The envelope's fields are the arguments passed to G7 Send.

| Field | Type | Required | Value |
|---|---|---|---|
| `jwe_headers.x-hcx-sender_code` | string | yes | facility participant code |
| `jwe_headers.x-hcx-recipient_code` | string | yes | payer participant code |
| `jwe_headers.x-hcx-workflow_id` | string | yes | `11`, or the case number under the setting |
| `fhir` | object | yes | the `CoverageEligibilityRequest` bundle |

FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F2. CoverageEligibilityRequest](../fhir/F2-coverage-eligibility-request.md), [F15. Patient](../fhir/F15-patient.md), [F17. Organization](../fhir/F17-organization.md), [F18. Coverage](../fhir/F18-coverage.md), [F16. Practitioner and PractitionerRole](../fhir/F16-practitioner.md), [F19. Other bundle resources](../fhir/F19-other-resources.md) (Location)

Envelope, an auth-requirements check from a case file:

```json
{
 "jwe_headers": {
  "x-hcx-sender_code": "<facility code>",
  "x-hcx-recipient_code": "<payer code>",
  "x-hcx-workflow_id": "11"
 },
 "fhir": <F1 Bundle carrying F2 CoverageEligibilityRequest (purpose auth-requirements), F15 Patient, F17 provider and payer Organizations, F19 Location, F18 Coverage, F16 PractitionerRole>
}
```

A validation or discovery check is the same envelope with its own purpose and no `item`.

#### A2S. RESPONSE
Acknowledgement, the G7 result:

```
{"ok": true, "gateway_status": 202, "txn_id": "01M07CJ...", "ledger_id": "01M07CJ...",
 "correlation_id": "<uuid>", "request_id": "<uuid>",
 "headers": {"x-hcx-correlation_id": "<uuid>", ...}, "response": <NHCX's acceptance>, ...}
```

The ids (`txn_id`, `correlation_id`) are stored on the leg (the case for the first three purposes, the ruling for auth-requirements), the leg goes to `checking` and any earlier error is cleared. A re-asked ruling drops the previous ruling's items and requirements. NHCX itself answers G7 `202 request.queued`.

A failed send that names its ids keeps them on the leg, sets it to `error` with the G7 error's message (or NHCX's refusal when `ok` is false), and raises the error (shared convention). A failed send naming no ids leaves the leg as it was.

Data: [D9. claim](../database/D9-claim.md), [D13. claim_auth](../database/D13-claim-auth.md), [D14. claim_auth_item](../database/D14-claim-auth-item.md), [D15. claim_auth_requirement](../database/D15-claim-auth-requirement.md)

Reply: [C2. Coverage Eligibility Verdict](../callbacks/C2-coverage-eligibility-on-check.md) (validation, benefits, discovery), [C3. Authorisation Requirements Ruling](../callbacks/C3-auth-requirements-on-check.md) (auth-requirements)

- A dispatch that failed (for example `CERT_NOT_FOUND` for an unregistered recipient) comes back from G7 at once as a failed send under its ids; A11 reads the same outcome from the G9 ledger.

#### A2P. PSEUDOCODE

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

// validation, benefits, discovery
function run_check(case_id, purpose, policy_code, member_id):
    case = claim[case_id]                  or refuse "Claim not found."
    if purpose not in {validation, benefits, discovery}:
        refuse "Choose whether this check is a validation, a benefits check or a discovery."
    policy_code = trim(policy_code); member_id = trim(member_id)
    if member_id empty:                    refuse "Member ID is required for an eligibility check."
    if purpose in {validation, benefits} and policy_code empty:
        refuse "Policy code is required for a <purpose> check."
    org = default organization
    if org missing or org.identifier_value empty:
        refuse "Set the facility's HFR ID under Settings before raising claims."
    if org.participant_code empty:
        refuse "Set the facility's NHCX participant code under Settings before raising claims."

    // gather
    adapter = payer adapter for case.payer_id
    // no patient row is read: the eligibility Patient (F15) carries identifiers only, no demographics
    items   = (purpose == benefits) ? eligibility items from claim_line (one per package
              or implant, ward tiers as modifiers) : []

    // build (builder refuses missing member id, registry id or payer code)
    bundle = build F2 CoverageEligibilityRequest bundle (F1) with purpose, member id,
             policy code (else NONE), F15 Patient, F17 provider (org HFR ID, name) and
             payer (case.payer_id else default payer code, case.payer_name),
             F18 Coverage, F19 Location, F16 PractitionerRole, items

    // call
    ack, failed = SEND("v1/coverageeligibility/check", {
        jwe_headers: {x-hcx-sender_code: org.participant_code,
                      x-hcx-recipient_code: case.processing_id or case.payer_id or default payer code,
                      x-hcx-workflow_id: case.claim_no if settings.eligibility_workflow_id == "case" else "11"},
        fhir: bundle}, case)

    // write
    UPDATE claim[case_id] SET status = checking, purpose, policy_code = policy_code or
        the stored one, member_id, txn_id = ack.txn_id, correlation_id = ack.correlation_id,
        checked_at = now, error_message = null
    if failed:
        same update with status = error, error_message = failed.message
        raise failed

// discovery from the discovery page (S17): no case yet
function discover(patient_id, payer_code, id_type, id_value, extra):
    org = default organization
    if org missing or org.identifier_value empty or org.participant_code empty:
        refuse the Settings message above                    // checked BEFORE any case is created
    case_id = INSERT claim {status: draft, purpose: discovery, patient_id, payer_id: payer_code,
                            processing_id: payer_code, member_id: id_value if id_type == member id,
                            abha_number: id_value if id_type == ABHA, mobile_number: id_value if mobile,
                            search_id_type: id_type, search_id_value: id_value, claim_no: next number}
    run_check(case_id, discovery, policy_code = "", member_id = extra.member_id or id_value)
        with the additional information (Aadhaar, mobile, the searched identifier) on the F15 Patient
    return case_id                                           // the chosen cover is applied to this case

// auth-requirements, by the operator
function request_auth(case_id):
    case = claim[case_id]                  or refuse "Claim not found."
    if case.status != eligible:
        refuse "Check the policy's eligibility before validating a procedure set against it."
    // any payer may be asked: the adapter decides only the automatic send below
    lines = claim_line rows of the case
    if lines empty:
        refuse "Choose the line items first, this checks the procedure set, so there has to be one."
    org = default organization
    if org missing or HFR ID or participant code empty:
        refuse "Set the facility's HFR ID and NHCX participant code under Settings before checking requirements."

    bundle = build F2 bundle with purpose auth-requirements, case.member_id,
             case.policy_code, org HFR ID and name, payer code and name,
             items = eligibility items from lines

    ack, failed = SEND("v1/coverageeligibility/check", envelope as above, case)

    values = {status: checking, txn_id: ack.txn_id, correlation_id: ack.correlation_id,
              requested_at: now, settled_at: null, error_message: null,
              outcome: null, disposition: null, inforce: null, response_json: null,
              asked_codes: fingerprint of the quoted procedure set}
    if failed: values.status = error; values.error_message = failed.message
    in one transaction:
        if no claim_auth row for the case: INSERT claim_auth (values, claim_id)
        else:
            DELETE claim_auth_item        WHERE auth_id = ruling.id
            DELETE claim_auth_requirement WHERE auth_id = ruling.id
            UPDATE claim_auth[ruling.id] SET values
    if failed: raise failed

// auth-requirements, automatic (called by A4 before each pre-auth or enhancement send)
function ensure_auth_requirements(case_id):
    case = claim[case_id]
    if case missing or case.status != eligible or no claim_line rows: return false
    if not adapter.auth_requirements:                                  return false
    ruling = claim_auth for the case
    if ruling exists and ruling.status != error
       and ruling.asked_codes == fingerprint of current set:           return false
    try: request_auth(case_id)
    catch any refusal or G7 error: return false                        // swallowed; the send goes on
    return true
```

#### A2U. USED BY
- Screens: [S3. Policy Discovery](../screens/S3-policy-discovery.md), [S8. Line Items](../screens/S8-line-items.md), [S9. Pre-authorisation](../screens/S9-preauthorisation.md), [S17. Beneficiary Discovery](../screens/S17-beneficiary-discovery.md), [S18. Beneficiary Verification](../screens/S18-beneficiary-verification.md)
- APIs: [A1. Policy Search](A1-policy-search.md), [A4. Pre-auth Submit](A4-preauth-submit.md), [A10. Transaction Related](A10-txn-related.md), [A11. Transaction Dispatch](A11-txn-dispatch.md), [A13. Transaction List](A13-txn-list.md), [A18. Biometric Authentication](A18-biometric-authentication.md)
- Callbacks: [C1. Callback Door](../callbacks/C1-callback-door.md), [C2. Coverage Eligibility Verdict](../callbacks/C2-coverage-eligibility-on-check.md), [C3. Authorisation Requirements Ruling](../callbacks/C3-auth-requirements-on-check.md)
- FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F15. Patient](../fhir/F15-patient.md), [F18. Coverage](../fhir/F18-coverage.md)
- Database: [D9. claim](../database/D9-claim.md), [D13. claim_auth](../database/D13-claim-auth.md), [D31. biometric_auth](../database/D31-biometric-auth.md)
- Gateway: [G1. Embedding](../gateway/G1-embedding.md), [G7. Send](../gateway/G7-send.md)
- Tests: [T3. IRDAI Policy Search and Eligibility](../tests/T3-irdai-policy-and-eligibility.md), [T4. IRDAI Insurance Plan and Authorisation Requirements](../tests/T4-irdai-plan-and-auth-requirements.md), [T13. PMJAY Eligibility, Package Master and Ruling](../tests/T13-pmjay-eligibility-and-package-master.md), [T19. PMJAY Beneficiary Verification and ABHA](../tests/T19-pmjay-biometric-and-abha.md)
