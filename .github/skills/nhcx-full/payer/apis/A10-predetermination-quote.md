# A10. Predetermination Quote

#### A10E. ENDPOINT
In-process: `gateway.send("v1/preauth/on_submit", envelope)`, [G7. Send](../gateway/G7-send.md), which encrypts it and posts it to NHCX for the hospital, on the thread the predetermination arrived on: `POST {nhcx}/v1/preauth/on_submit`. No answer to it is awaited.

It answers [C6. Predetermination](../callbacks/C6-predetermination.md). The route is the pre-authorisation's, because that is the NHCX route there is for it; `use: predetermination` on the ClaimResponse says what it is. On the hospital's side the reply is matched to its quote row and stored as answered whatever it says.

#### A10D. DESCRIPTION
"What would you pay for this?": a Claim with `use` `predetermination` ([F8. Claim](../fhir/F8-claim.md)), the same shape as a pre-authorisation, asked before anybody is admitted. It is the **one** answer this payer decides by rules rather than by a person: a quote binds nobody, so nobody needs to sign it. The hospital learns what the policy would allow and what it would cut; no case is opened; the only thing recorded is the quote ([D29. predetermination_quote](../database/D29-predetermination-quote.md)).

**Pricing.** The submission is shaped into a transient case (never stored): the enrolment found by the Claim's handles, in force first, else the most recently ended ([D6. subscription](../database/D6-subscription.md) as [A1. Eligibility Answer](A1-eligibility-answer.md) finds it; a patient this payer does not cover is still answered, the quote saying no enrolment matched); the member; the hospital, admission, diagnoses, procedures, doctors, documents and lines as sent, every line `pending`. The rules engine reads it against the filing: the enrolment and its product, the member, and the member's other cases. Each rule type reads one part and says, for each thing it does not like, what was sent and what was required, with a path into the Claim:

| Rule type | Reads |
|---|---|
| `policy_validity` | the enrolment is active, on sale, and the admission falls inside its period |
| `waiting_period` | the admission against the enrolment's start, per procedure category |
| `sum_insured_cap` | the lines against what is left of the wallet |
| `sub_limit` | the lines against the product's sub-limits ([D18. policy_sub_limit](../database/D18-policy-sub-limit.md)) |
| `exclusion` | the procedures against the product's exclusions ([D17. policy_exclusion](../database/D17-policy-exclusion.md)) |
| `required_docs` | the documents sent against the procedure's rules for the phase ([D11. procedure_rule_doc](../database/D11-procedure-rule-doc.md)) |
| `package_mismatch` | the lines against the package rate ([D10. procedure_rule](../database/D10-procedure-rule.md)) |
| `duplicate_window` | the member's other cases in a window |
| `clinical_mismatch` | the diagnoses against the procedures |

The findings decide the verdict: any finding at severity `reject` rejects every line; else any at `query` queries; else the reductions are applied line by line and the verdict is `approve` or `partial`. The rule set comes from a file (`rules_file`), else the built-in defaults [REF](../references/PAYERS.md#markers).

**What is answered** ([F9. ClaimResponse](../fhir/F9-claimresponse.md) with `use: predetermination`): the transient case with the pricing applied, rendered as a verdict would be: `outcome` `complete` or `partial` with status `approved`, `error` with `rejected`, `partial` with `queried`; per line the claimed and eligible amounts and the reason; and every finding written into the disposition after the words, as "`<rule id>` [`<severity>`] `<path>`: sent `<sent>`; required `<required>`. `<remedy>`", because PMJAY carries no `error[]` and no `processNote` and the disposition is where a finding lives [PAYER](../references/PAYERS.md#markers). `adjudicatedBy` reads "Predetermination pricing". `preAuthRef` is left off: there is no case.

**Headers set by the application.** As every answer ([A1. Eligibility Answer](A1-eligibility-answer.md)): sender and recipient swapped, the ask's correlation id verbatim, its workflow id echoed (the hospital sends 12 [PAYER](../references/PAYERS.md#markers)), `x-hcx-status` `response.complete`. No scheme table of its own.

**Checks before sending.** A quote already on record for the correlation id is a retried delivery: answered `duplicate`, nothing sent again. A pricing failure ("The predetermination could not be priced", "no pricing rules are loaded") is a retryable error to the exchange. Sandbox faults apply as to a verdict [SANDBOX](../references/PAYERS.md#markers) ([A19. Sandbox Scenarios](A19-sandbox-scenarios.md)).

#### A10Q. REQUEST

The arguments passed to G7 Send:

| Field | Type | Notes |
|---|---|---|
| `jwe_headers` | object | Sender, recipient, correlation id, workflow id, status |
| `fhir` | Bundle | The ClaimResponse bundle |

FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F9. ClaimResponse](../fhir/F9-claimresponse.md) (`use: predetermination`), [F15. Patient](../fhir/F15-patient.md), [F17. Organization](../fhir/F17-organization.md), [F18. Coverage](../fhir/F18-coverage.md) (when an enrolment matched)

Envelope, a quote with one sub-limit finding:

```json
{
  "jwe_headers": {"x-hcx-sender_code": "<payer code>",
                  "x-hcx-recipient_code": "<facility code>",
                  "x-hcx-correlation_id": "d2c4e6f8-1a3b-4c5d-9e7f-8b6a4c2d0e1f",
                  "x-hcx-workflow_id": "12",
                  "x-hcx-status": "response.complete"},
  "fhir": <F1 Bundle: F9 ClaimResponse (use predetermination, outcome partial, status approved, disposition "Predetermination approved for INR 60000 of INR 69000 claimed. SUB-LIMIT-ROOM [reduce] Claim.item[0]: sent INR 9000; required INR 5000 per day. Bill the room at the policy's rate.", items with eligible amounts), F15 Patient, F17 Organizations, F18 Coverage>
}
```

#### A10S. RESPONSE

**Acknowledgement:** the G7 result.

Recorded:
- [D29. predetermination_quote](../database/D29-predetermination-quote.md) one quote: the correlation id (unique: the receipt against a retried delivery), the sender, the hospital's claim number, member and enrolment ids when matched, patient name, `total_claimed`, `total_quoted`, the verdict (`approve`, `partial`, `reject`, `query`), the findings, `answer_txn_id`, the scenario in play, and both bundles as request and response.
- [D31. audit_log](../database/D31-audit-log.md) audit `predetermination.answered`, entity `nhcx_txn`: "`<hospital>` asked, correlation `<id>`, `<verdict>` quoted `<INR quoted>` of `<INR claimed>`, answer txn `<txn_id>`".
- Nothing on any case.

The callback answers the gateway `{"status": "quoted", "quote_id", "verdict", "total_quoted", "findings", "txn_id"}`. Quotes are listed on the desk (`GET quotes`, `GET quotes/:id`, [S3. Case Desk](../screens/S3-case-desk.md)).

**Failed send.** As [A1. Eligibility Answer](A1-eligibility-answer.md): a refusal answers `rejected` ("The gateway refused the answer: `<message>`"), nothing recorded; unreachable or 5xx answers `error` so NHCX redelivers the ask and it is priced again.

Data: [D29. predetermination_quote](../database/D29-predetermination-quote.md), [D6. subscription](../database/D6-subscription.md), [D5. member](../database/D5-member.md), [D12. policy](../database/D12-policy.md), [D10. procedure_rule](../database/D10-procedure-rule.md), [D11. procedure_rule_doc](../database/D11-procedure-rule-doc.md), [D17. policy_exclusion](../database/D17-policy-exclusion.md), [D18. policy_sub_limit](../database/D18-policy-sub-limit.md), [D19. case](../database/D19-case.md) (the member's other cases, read only), [D31. audit_log](../database/D31-audit-log.md)

Reply: none. A hospital that goes ahead sends the pre-authorisation ([C4. Pre-auth Submit](../callbacks/C4-preauth-submit.md)), which opens the case.

#### A10P. PSEUDOCODE

```
function file_predetermination(in, submission):     // called by C6; submission is the parsed F8
    if a D29 row has correlation_id == in.correlation_id:
        return settled {status: "duplicate", quote_id, verdict}
    sub = find enrolment(submission.handles)          // A1: in force, else most recently ended; may be none
    member = D5[sub.member_id] if sub
    case = transient case from submission, sub, member   // as C4 shapes one; stage preauth, lines pending, not stored
    case.documents = resolve document codes(submission.documents)   // unknown codes filed as ODN
    if case.member_id empty: case.member_id = submission.member_id or submission.subscriber_id

    filing = {case, stage: "predetermination", now, sub, policy = D12[sub.policy_id] with children,
              member, prior cases = D19 rows for the member}
    evaluation = rules.evaluate(filing)               // findings, verdict, remarks, per-line outcomes
        on failure: log; return error("The predetermination could not be priced")
    apply(evaluation, case)                           // line statuses and approved amounts, total_approved,
                                                       // adjudication_status approved | rejected | queried,
                                                       // remarks, adjudicated_by "Predetermination pricing"
    cover = {member, sub, policy}
    render(current) = F9 bundle(in.payer, in.recipient, current, cover, use = "predetermination",
                                claim_ref = submission.claim_ref, recipient = in.sender,
                                findings = evaluation.findings)
    headers = ANSWER_HEADERS(in)                       // A1; the ask's workflow id echoed
    result = dispatch(case, render, headers, "v1/preauth/on_submit")   // A19 faults, else one SEND
    if result failed:
        on Refused r:     return rejected("The gateway refused the answer: " + r.message)
        on Unreachable u: return error("The gateway could not queue the answer")
    INSERT D29 {correlation_id: in.correlation_id, sender_code: in.sender, claim_ref: submission.claim_ref,
                member_id: sub.member_id, subscription_id: sub.id, patient_name: case.patient_name,
                total_claimed: case.total_claimed, total_quoted: case.total_approved,
                verdict: evaluation.verdict, findings: evaluation.findings, answer_txn_id: result.txn_id,
                scenario, request: in.fhir, response: the bundle sent}
    INSERT D31 audit {action: "predetermination.answered", entity_type: "nhcx_txn", entity_id: in.txn_id,
                      detail: "<sender> asked, correlation <corr>, <verdict> quoted <INR quoted> of <INR claimed>, answer txn " + result.txn_id}
    return settled {status: "quoted", quote_id, verdict, total_quoted, findings: count, txn_id: result.txn_id}

function decide(findings):                            // the engine's verdict from its findings
    if any finding.severity == reject: verdict reject; every line rejected, remarks "Not payable: " + reasons
    else if any finding.severity == query: verdict query; lines left pending
    else: apply each reduce finding to its line (eligible = required amount), the rest approved in full;
          verdict partial when any line was cut, else approve
```

#### A10U. USED BY
- Screens: [S8. Procedures](../screens/S8-procedures.md)
- APIs: [A3. Pre-auth Answer](A3-preauth-answer.md), [A15. Case Exchange Log](A15-case-exchange.md), [A19. Sandbox Scenarios](A19-sandbox-scenarios.md)
- Callbacks: [C1. Callback Door](../callbacks/C1-callback-door.md), [C6. Predetermination](../callbacks/C6-predetermination.md)
- FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F9. ClaimResponse](../fhir/F9-claimresponse.md)
- Database: [D1. payer](../database/D1-payer.md), [D18. policy_sub_limit](../database/D18-policy-sub-limit.md), [D21. case_procedure](../database/D21-case-procedure.md), [D29. predetermination_quote](../database/D29-predetermination-quote.md), [D31. audit_log](../database/D31-audit-log.md)
- Gateway: [G1. Embedding](../gateway/G1-embedding.md), [G5. Protocol Headers](../gateway/G5-protocol-headers.md), [G7. Send](../gateway/G7-send.md)
- Tests: [T11. Predetermination Quoted](../tests/T11-predetermination-quoted.md)
