# A2. Insurance Plan Answer

#### A2E. ENDPOINT
In-process: `gateway.send("v1/insuranceplan/on_request", envelope)`, [G7. Send](../gateway/G7-send.md), which encrypts it and posts it to NHCX for the hospital, on the thread the hospital's request arrived on: `POST {nhcx}/v1/insuranceplan/on_request`. No answer to it is awaited.

It answers [C3. Insurance Plan Request](../callbacks/C3-insurance-plan-request.md). The hospital reads the bundle as its package master: every package with its rate, tier conditions, documents and forms ([F5. InsurancePlan](../fhir/F5-insuranceplan.md), [F6. Questionnaire](../fhir/F6-questionnaire.md)).

#### A2D. DESCRIPTION
Sent at once, inside the callback that took the request in. The hospital's request is a Task ([F4. Task (InsurancePlan request)](../fhir/F4-task-insuranceplan.md)) naming a policy number and the asking provider; what comes back is the product as this payer publishes it.

**Which product.** The policy number the Task carries is resolved in this order, and the first hit wins:

1. A product by its id, UIN or an alias ([D12. policy](../database/D12-policy.md), [D16. policy_alias](../database/D16-policy-alias.md)).
2. An enrolment by its id ([D6. subscription](../database/D6-subscription.md)): the eligibility answer ([A1. Eligibility Answer](A1-eligibility-answer.md)) hands the hospital the enrolment id as the Coverage, and a hospital may ask for the plan by that handle. The product is the enrolment's, and the plan is rendered as that person's cover (its period and plan type from the enrolment) rather than as the product on offer.
3. A retired product by the same code ([D12. policy](../database/D12-policy.md) `deleted_at` set): everyone who held it was moved onto the default product when it went, and the registry a hospital reads still quotes the old code, so the cover on offer under that code is the default product's [REF](../references/PAYERS.md#markers) [SANDBOX](../references/PAYERS.md#markers).

Nothing found is answered, not refused: an **empty plan**, a bundle carrying this payer's Organization and no InsurancePlan. The specification allows an empty plan when no product matches the policy and provider, and silence would leave the hospital's poll running until it timed out.

**What the plan says** ([F5. InsurancePlan](../fhir/F5-insuranceplan.md)): the product's name, UIN, type and plan type, its period (the enrolment's, else the calendar year of today, noted as assumed), the SNOMED coverage clauses with their benefits and limits ([D14. policy_coverage_clause](../database/D14-policy-coverage-clause.md), [D15. policy_clause_benefit](../database/D15-policy-clause-benefit.md)), each covered procedure as a benefit carrying its package rate, its document requirements per phase and its treatment-guideline questionnaire ([D13. policy_procedure](../database/D13-policy-procedure.md), [D10. procedure_rule](../database/D10-procedure-rule.md), [D11. procedure_rule_doc](../database/D11-procedure-rule-doc.md), [F6. Questionnaire](../fhir/F6-questionnaire.md)), the exclusions and sub-limits as extensions ([D17. policy_exclusion](../database/D17-policy-exclusion.md), [D18. policy_sub_limit](../database/D18-policy-sub-limit.md)), and the priced procedures again as specific costs on the plan. A product with neither a clause nor a covered procedure still goes out, with an issue logged: the profile wants at least one coverage.

**Headers set by the application.** As every answer: sender and recipient swapped, the request's correlation id verbatim, the request's own workflow id echoed, `x-hcx-status` `response.complete` (see [A1. Eligibility Answer](A1-eligibility-answer.md)). No scheme table applies [PAYER](../references/PAYERS.md#markers).

**Checks before sending.** None of its own beyond the door's ([C1. Callback Door](../callbacks/C1-callback-door.md)). A missing gateway is reported as a retryable failure, "No gateway is configured, so the enquiry cannot be answered" [REF](../references/PAYERS.md#markers).

#### A2Q. REQUEST

The arguments passed to G7 Send:

| Field | Type | Notes |
|---|---|---|
| `jwe_headers` | object | Sender, recipient, correlation id, workflow id, status |
| `fhir` | Bundle | The InsurancePlan bundle, or the empty plan |

FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F5. InsurancePlan](../fhir/F5-insuranceplan.md), [F6. Questionnaire](../fhir/F6-questionnaire.md) (one per procedure with questions or required documents), [F17. Organization](../fhir/F17-organization.md) (this payer, as `ownedBy` and `administeredBy`; a TPA deployment points `administeredBy` at a second Organization [REF](../references/PAYERS.md#markers))

Envelope, a product found:

```json
{
  "jwe_headers": {"x-hcx-sender_code": "<payer code>",
                  "x-hcx-recipient_code": "<facility code>",
                  "x-hcx-correlation_id": "0b398fdf-0516-4935-9ebb-a0dc90a06bb6",
                  "x-hcx-workflow_id": "NM-26-0SE000001",
                  "x-hcx-status": "response.complete"},
  "fhir": <F1 Bundle (InsurancePlanBundle profile, security V): F5 InsurancePlan, F17 Organization, then one F6 Questionnaire per package, addressed by the url the plan's benefits point at>
}
```

The empty plan is the same envelope with a bundle holding the Organization alone.

#### A2S. RESPONSE

**Acknowledgement:** the G7 result (`ok`, `gateway_status` 202, `txn_id`, `correlation_id`, `request_id`, `headers`, `response`).

Recorded:
- [D31. audit_log](../database/D31-audit-log.md) audit: `insuranceplan.answered` with "`<hospital>` asked, correlation `<id>`, policy `<id>`, answer txn `<txn_id>`", or `insuranceplan.no_plan` with "no product matched `<code>`". The row is the door's receipt against a retried delivery.
- Nothing else: a plan request touches no case.
- The callback answers the gateway `{"status": "answered", "policy_id", "txn_id"}` or `{"status": "no_plan", "txn_id"}`.

**Failed send.** As [A1. Eligibility Answer](A1-eligibility-answer.md): a refusal (4xx, or a `SendError` that is not retryable) answers `rejected` with "The gateway refused the answer: `<message>`"; unreachable or 5xx answers `error` so NHCX redelivers the request.

Data: [D12. policy](../database/D12-policy.md), [D16. policy_alias](../database/D16-policy-alias.md), [D6. subscription](../database/D6-subscription.md), [D13. policy_procedure](../database/D13-policy-procedure.md), [D10. procedure_rule](../database/D10-procedure-rule.md), [D11. procedure_rule_doc](../database/D11-procedure-rule-doc.md), [D14. policy_coverage_clause](../database/D14-policy-coverage-clause.md), [D15. policy_clause_benefit](../database/D15-policy-clause-benefit.md), [D17. policy_exclusion](../database/D17-policy-exclusion.md), [D18. policy_sub_limit](../database/D18-policy-sub-limit.md), [D1. payer](../database/D1-payer.md), [D31. audit_log](../database/D31-audit-log.md)

Reply: none. The hospital does not answer a plan. PMJAY's own sandbox answers a plan request in 15 to 60 minutes and refuses a second request meanwhile [SANDBOX](../references/PAYERS.md#markers); this payer answers within the callback, which is what a hospital built against the provider skill waits for first.

#### A2P. PSEUDOCODE

```
function answer_insurance_plan(in, ask):            // called by C3; ask is the parsed F4
    payer = D1 payer row
    asked_by = ask.provider_name or ask.provider_id or in.sender
    enrolment = none
    policy = D12 by id, UIN or D16 alias == ask.policy_number (live rows only)
    if none:
        sub = D6[ask.policy_number]
        if sub: policy = D12[sub.policy_id]; enrolment = sub
    if none:
        if a retired D12 row has id, UIN or alias == ask.policy_number:
            policy = D12 by UIN == the default product's UIN            // [REF](../references/PAYERS.md#markers) [SANDBOX](../references/PAYERS.md#markers)
    if none:
        bundle = F5 empty plan bundle(payer)         // Organization only
        ack = SEND("v1/insuranceplan/on_request",
                   {jwe_headers: ANSWER_HEADERS(in), fhir: bundle}, none)   // A1: SEND, ANSWER_HEADERS
            on Refused r:     return rejected("The gateway refused the answer: " + r.message)
            on Unreachable u: return error("The gateway could not queue the answer")
        INSERT D31 audit {action: "insuranceplan.no_plan", entity_type: "nhcx_txn", entity_id: in.txn_id,
                          detail: asked_by + " asked, correlation <corr>, no product matched \"" + ask.policy_number + "\", answer txn " + ack.txn_id}
        return settled {status: "no_plan", txn_id: ack.txn_id}

    load policy children: D13 procedures (with D10 and D11), D14 clauses with D15,
                          D16 aliases, D17 exclusions, D18 sub-limits
    bundle = F5 plan bundle(payer, policy, enrolment)   // enrolment gives period and plan type; else the year of today, issue noted
    ack = SEND("v1/insuranceplan/on_request",
               {jwe_headers: ANSWER_HEADERS(in), fhir: bundle}, none)
        on Refused r:     return rejected("The gateway refused the answer: " + r.message)
        on Unreachable u: return error("The gateway could not queue the answer")
    INSERT D31 audit {action: "insuranceplan.answered", entity_type: "nhcx_txn", entity_id: in.txn_id,
                      detail: asked_by + " asked, correlation <corr>, policy " + policy.id + ", answer txn " + ack.txn_id}
    return settled {status: "answered", policy_id: policy.id, txn_id: ack.txn_id}
```

#### A2U. USED BY
- Screens: [S6. Policies](../screens/S6-policies.md), [S7. Policy Configurator](../screens/S7-policy-configurator.md), [S8. Procedures](../screens/S8-procedures.md), [S9. Procedure Configurator](../screens/S9-procedure-configurator.md), [S11. FHIR Preview](../screens/S11-fhir-preview.md)
- Callbacks: [C2. Coverage Eligibility Check](../callbacks/C2-coverage-eligibility-check.md), [C3. Insurance Plan Request](../callbacks/C3-insurance-plan-request.md)
- FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F4. Task (InsurancePlan request)](../fhir/F4-task-insuranceplan.md), [F5. InsurancePlan](../fhir/F5-insuranceplan.md), [F6. Questionnaire](../fhir/F6-questionnaire.md)
- Database: [D12. policy](../database/D12-policy.md), [D16. policy_alias](../database/D16-policy-alias.md), [D31. audit_log](../database/D31-audit-log.md)
- Tests: [T5. Insurance Plan Served](../tests/T5-insurance-plan-served.md)
