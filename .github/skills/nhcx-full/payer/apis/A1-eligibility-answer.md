# A1. Eligibility Answer

#### A1E. ENDPOINT
In-process: `gateway.send("v1/coverageeligibility/on_check", envelope)`, [G7. Send](../gateway/G7-send.md), which encrypts it and posts it to NHCX for the hospital, on the thread the hospital's check arrived on: `POST {nhcx}/v1/coverageeligibility/on_check`. No answer to it is awaited: NHCX's acceptance, returned by G7, settles it.

It answers [C2. Coverage Eligibility Check](../callbacks/C2-coverage-eligibility-check.md) in every purpose. On the hospital's side the same route carries two things, told apart by the correlation id: the eligibility verdict (`validation`, `benefits`, `discovery`) and the authorisation-requirements ruling (`auth-requirements`). Both are this one send.

#### A1D. DESCRIPTION
Sent at once, inside the callback that took the check in, by the application itself; no person is involved. A check that cannot be answered is not filed and waited on: an eligibility question has an answer the moment it is asked, and a hospital's desk polls its thread until one comes.

**What is answered**, from the enrolment C2 found ([D6. subscription](../database/D6-subscription.md) through the handles of [F2. CoverageEligibilityRequest](../fhir/F2-coverage-eligibility-request.md)):

| Found | Answer | `inforce` | Disposition (verbatim) |
|---|---|---|---|
| An enrolment in force today (active, today inside its period) | the cover, with the wallet as the benefit | true | "Policy is in force until `<pend>`. `<INR balance>` of cover remains." or, with nothing left, "Policy is in force until `<pend>`. The sum insured is exhausted; no balance remains." |
| Only a lapsed or paused enrolment (the most recently ended one the person had) | the cover, marked not in force | false | "Cover lapsed on `<pend>`.", "Cover does not begin until `<pstart>`." or "Cover is `<status>`. No benefit is payable while the subscription is not active." |
| Nothing | no cover | no `insurance` entry at all | "No active cover was found for the details provided." |

A lapsed enrolment is answered with its reason rather than as "no such person", because the hospital's desk shows the disposition to the operator [REF](../references/PAYERS.md#markers).

**Per purpose** (the `purpose[]` of the request; none means `validation`):

- `validation` and `benefits` without items: one item for the admission with the sum insured (`allowedMoney` of the plan, `usedMoney` what has gone) and the wallet balance as the `benefit` typed benefit; `authorizationRequired` true. Used is the product's sum assured minus the wallet balance ([D12. policy](../database/D12-policy.md) `total_assured`, [D6. subscription](../database/D6-subscription.md) `wallet_balance`).
- `discovery`: the cover alone, no items.
- `benefits` or `auth-requirements` with items: one item per package the hospital quoted. A package on the policy's schedule ([D13. policy_procedure](../database/D13-policy-procedure.md), matched by the registry code first, then the SNOMED or ICD-10-PCS code) answers with the registry's own name and category, the package rate as a `Procedure` benefit when priced ([D10. procedure_rule](../database/D10-procedure-rule.md) `package_rate`) and, as `authorizationSupporting`, the documents due at pre-authorisation ([D11. procedure_rule_doc](../database/D11-procedure-rule-doc.md), phase `preauth`). An `auth-requirements` ask also lists the discharge and claim documents as stage `post` and the treatment-guideline form by its url ([F6. Questionnaire](../fhir/F6-questionnaire.md)) [PAYER](../references/PAYERS.md#markers). A package not on the schedule is answered `excluded` true, so the hospital learns it before the pre-authorisation rather than from a rejection. The disposition gains a sentence: "All `<n>` requested items are covered; pre-authorisation is required and the documents listed must accompany it.", "None of the `<n>` requested items is covered by this policy." or "`<c>` of `<n>` requested items are covered; the rest are not on this policy's schedule."

The text convention on each supporting requirement (`Type: pre`, `Procedure Code:<code>`, `fullUrl: <url>`) is the PMJAY dialect the hospital's reader parses [PAYER](../references/PAYERS.md#markers); see [F3. CoverageEligibilityResponse](../fhir/F3-coverage-eligibility-response.md).

**Headers set by the application.** The answer travels back the way the question came.

| Header | Value |
|---|---|
| `x-hcx-sender_code` | The check's `x-hcx-recipient_code`: the code the hospital addressed, which is this payer's participant code (or the processing code when a TPA processes for the insurer, [D1. payer](../database/D1-payer.md)) |
| `x-hcx-recipient_code` | The check's `x-hcx-sender_code`: the hospital |
| `x-hcx-correlation_id` | The check's own, verbatim. It is what the hospital's poll matches the answer on |
| `x-hcx-workflow_id` | The check's own `x-hcx-workflow_id`, echoed; left off when the check carried none |
| `x-hcx-status` | `response.complete` |

No scheme table applies: an answer echoes the question's workflow id, whatever adapter the hospital used (see [PAYERS.md](../references/PAYERS.md)). G7 completes the rest ([G5. Protocol Headers](../gateway/G5-protocol-headers.md)).

**Checks before sending.** The callback door ([C1. Callback Door](../callbacks/C1-callback-door.md)) has already refused an envelope without sender, recipient or correlation id. This send refuses nothing of its own: every check is answered, with cover or without. A gateway that is not configured is a deployment fault, reported to the exchange as a retryable failure: "No gateway is configured, so the enquiry cannot be answered" [REF](../references/PAYERS.md#markers).

#### A1Q. REQUEST

The arguments passed to G7 Send:

| Field | Type | Notes |
|---|---|---|
| `jwe_headers` | object | The five headers above |
| `fhir` | Bundle | The eligibility response bundle |

The bundle echoes the request's entries first, then appends this payer's `CoverageEligibilityResponse`, its `Patient` (the member as this payer knows them, with member id and ABHA), its `Coverage` (the enrolment) and its `Organization`, plus the hospital's Organization when the request named one. A hospital's reader takes the **last** of each resource type as the payer's ([F3. CoverageEligibilityResponse](../fhir/F3-coverage-eligibility-response.md)).

FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F3. CoverageEligibilityResponse](../fhir/F3-coverage-eligibility-response.md), [F15. Patient](../fhir/F15-patient.md), [F18. Coverage](../fhir/F18-coverage.md), [F17. Organization](../fhir/F17-organization.md); for the no-cover answer the Patient carries only what the request said (member number, ABHA, name, mobile).

Envelope, a validation answered in force:

```json
{
  "jwe_headers": {"x-hcx-sender_code": "<payer code>",
                  "x-hcx-recipient_code": "<facility code>",
                  "x-hcx-correlation_id": "50c822b5-6923-4765-8bb0-65615e019e00",
                  "x-hcx-workflow_id": "11",
                  "x-hcx-status": "response.complete"},
  "fhir": <F1 Bundle: the request's entries echoed, then F3 CoverageEligibilityResponse (outcome complete, inforce true, one admission item with the sum insured and the wallet), F15 Patient, F18 Coverage, F17 payer and provider Organizations>
}
```

An `auth-requirements` answer differs only in `purpose` and in the items: one per quoted package, each with `authorizationRequired`, `excluded`, the rate and its `authorizationSupporting` list.

#### A1S. RESPONSE

**Acknowledgement** (the G7 result, NHCX status 202):

```json
{"ok": true, "gateway_status": 202,
 "txn_id": "7UPG003U", "ledger_id": "7UPG003U",
 "correlation_id": "50c822b5-6923-4765-8bb0-65615e019e00",
 "request_id": "...", "headers": {"...": "..."}, "response": "<NHCX's acceptance>"}
```

What is recorded, in this order:
- [D31. audit_log](../database/D31-audit-log.md) audit: action `eligibility.answered`, `eligibility.lapsed`, `eligibility.auth_requirements` or `eligibility.no_cover`, entity `nhcx_txn` with the inbound transaction id, detail "`<hospital>` asked, correlation `<id>`, subscription `<id>`, answer txn `<txn_id>`". This row is also the receipt the door reads to drop a retried delivery ([C1. Callback Door](../callbacks/C1-callback-door.md)).
- Nothing on a case: an eligibility check opens none. The enrolment is not written.
- The callback answers the gateway `{"status": "answered" | "lapsed" | "no_cover", "subscription_id", "txn_id"}`, and G8 answers NHCX 202.

**Failed send.** Per the shared conventions ([API index](INDEX.md)):
- A G7 `SendError` or a result with `ok` false whose NHCX status is 4xx is a refusal of the envelope: sending the same one again would be refused the same way. The callback answers `rejected` ("The gateway refused the answer: `<message>`"), nothing is recorded, and NHCX does not redeliver.
- Unreachable, or 5xx: the callback answers `error` ("The gateway could not queue the answer"), so NHCX redelivers the check and the answer is tried again. A redelivery that arrives after the audit row was written is a duplicate and is dropped by the door.

Data: [D6. subscription](../database/D6-subscription.md), [D5. member](../database/D5-member.md), [D12. policy](../database/D12-policy.md), [D13. policy_procedure](../database/D13-policy-procedure.md), [D10. procedure_rule](../database/D10-procedure-rule.md), [D11. procedure_rule_doc](../database/D11-procedure-rule-doc.md), [D1. payer](../database/D1-payer.md), [D31. audit_log](../database/D31-audit-log.md)

Reply: none. Nothing comes back on this thread; a hospital that wants the ruling again sends a fresh check.

#### A1P. PSEUDOCODE

```
// shared send convention (every outbound bundle), in-process through G7
function SEND(path, envelope, case):
    archive envelope with the case (outbound), or under "unmatched" when there is none
    try:
        result = gateway.send(path, envelope)       // G7 Send, posts to {nhcx}/<path>
    catch send_error:                               // G7 SendError {code, message, retryable, ...}
        if send_error.retryable: raise Unreachable(send_error.message)
        raise Refused(send_error.message)           // the envelope itself is wrong
    if not result.ok:                               // NHCX did not accept it
        if result.gateway_status >= 500: raise Unreachable("GATEWAY_HTTP_" + status)
        raise Refused(NHCX's response.error.code + ": " + message, or "GATEWAY_HTTP_<status>: NHCX did not accept the message")
    return ack = {txn_id: result.txn_id, correlation_id: result.correlation_id,
                  request_id: result.request_id}

// an answer travels back the way the question came
function ANSWER_HEADERS(in):                        // in: the inbound delivery C1 built
    h = {x-hcx-sender_code:    in.recipient,         // the code the hospital addressed
         x-hcx-recipient_code: in.sender,
         x-hcx-correlation_id: in.correlation_id,
         x-hcx-status:         "response.complete"}
    if in.workflow_id: h[x-hcx-workflow_id] = in.workflow_id
    return h

function answer_eligibility(in, ask):               // called by C2; ask is the parsed F2
    payer = D1 payer row
    sub = find enrolment in force today by ask.handles   // D6 join D5: ABHA (member or enrolment),
                                                          // mobile (last 10 digits), member id
    if none: sub = most recently ended enrolment by the same handles
    if sub:
        member = D5[sub.member_id]; policy = D12[sub.policy_id] with D13, D10, D11 loaded
        bundle = F3 answer bundle(payer, in.recipient, member, sub, policy,
                                  requestor = ask.provider, purposes = ask.purposes,
                                  items = ask.items, request = in.fhir)
        status = "answered"; action = "eligibility.answered"
        if ask asks auth-requirements: action = "eligibility.auth_requirements"
        if not in force today(sub): status = "lapsed"; action = "eligibility.lapsed"
    else:
        bundle = F3 no-cover bundle(payer, in.recipient, requestor = ask.provider,
                                    request = in.fhir, purposes = ask.purposes,
                                    patient name, ABHA, mobile, searched id = ask.member_id or ask.subscriber_id)
        status = "no_cover"; action = "eligibility.no_cover"

    ack = SEND("v1/coverageeligibility/on_check",
               {jwe_headers: ANSWER_HEADERS(in), fhir: bundle}, none)
        on Refused r:     return rejected("The gateway refused the answer: " + r.message)
        on Unreachable u: return error("The gateway could not queue the answer")
    INSERT D31 audit {action, entity_type: "nhcx_txn", entity_id: in.txn_id,
                      detail: "<sender> asked, correlation <corr>, subscription <sub.id>, answer txn " + ack.txn_id}
    return settled {status, subscription_id: sub.id or "", txn_id: ack.txn_id}

function in force today(sub):
    return sub.status == active and (sub.pstart empty or sub.pstart <= today)
                                and (sub.pend empty or sub.pend >= today)
```

#### A1U. USED BY
- Screens: [S4. Members](../screens/S4-members.md), [S5. Subscriptions](../screens/S5-subscriptions.md), [S8. Procedures](../screens/S8-procedures.md), [S9. Procedure Configurator](../screens/S9-procedure-configurator.md), [S11. FHIR Preview](../screens/S11-fhir-preview.md)
- APIs: [A2. Insurance Plan Answer](A2-insurance-plan-answer.md), [A3. Pre-auth Answer](A3-preauth-answer.md), [A5. Query Request](A5-query-request.md), [A6. Payment Notice](A6-payment-notice.md), [A7. Payment Enquiry Answer](A7-payment-enquiry-answer.md), [A8. Status Answer](A8-status-answer.md), [A9. Task Answer](A9-task-answer.md), [A10. Predetermination Quote](A10-predetermination-quote.md), [A15. Case Exchange Log](A15-case-exchange.md)
- Callbacks: [C1. Callback Door](../callbacks/C1-callback-door.md), [C2. Coverage Eligibility Check](../callbacks/C2-coverage-eligibility-check.md), [C3. Insurance Plan Request](../callbacks/C3-insurance-plan-request.md)
- FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F2. CoverageEligibilityRequest](../fhir/F2-coverage-eligibility-request.md), [F3. CoverageEligibilityResponse](../fhir/F3-coverage-eligibility-response.md)
- Database: [D1. payer](../database/D1-payer.md), [D6. subscription](../database/D6-subscription.md), [D7. subscription_family_member](../database/D7-subscription-family-member.md), [D10. procedure_rule](../database/D10-procedure-rule.md), [D11. procedure_rule_doc](../database/D11-procedure-rule-doc.md), [D13. policy_procedure](../database/D13-policy-procedure.md), [D31. audit_log](../database/D31-audit-log.md)
- Gateway: [G1. Embedding](../gateway/G1-embedding.md), [G5. Protocol Headers](../gateway/G5-protocol-headers.md), [G7. Send](../gateway/G7-send.md)
- Tests: [T3. Eligibility Validation and Discovery Answered](../tests/T3-eligibility-answered.md), [T4. Auth-requirements Ruling Answered](../tests/T4-auth-requirements-ruled.md)
