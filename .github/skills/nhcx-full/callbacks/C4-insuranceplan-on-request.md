# C4. Insurance Plan Reply

#### C4E. ENDPOINT
Delivered in-process by [G8. Receive](../gateway/G8-receive.md) for NHCX route `v1/insuranceplan/on_request`, passed to `C1.receive` with `delivery.type` `insurance`. Answers A3.

#### C4D. DESCRIPTION
The payer's package master for the policy, a few seconds after A3 went out. Matched by `x-hcx-correlation_id` against the plan row (D10 `correlation_id`, newest row). Nothing matching answers `unmatched`.

Only a plan still `fetching` takes it; a settled plan answers `ignored`. The payer redelivers the same master several times on one thread [SANDBOX](../references/PAYERS.md#markers). A plan on record as a failed send (`error`) is reopened and the reply applied.

A bundle with no InsurancePlan at all (only the payer's Organization) is the payer saying it has nothing filed under this policy [SANDBOX](../references/PAYERS.md#markers). It is settled as an empty plan with a message, not rejected, so the plan does not sit in `fetching`. Polling looks only for replies that carry an InsurancePlan, so this outcome is reached through the callback only.

#### C4Q. REQUEST
`fhir` is an F1 Bundle carrying one F5 InsurancePlan, usually beside the payer's F17 Organization and its F6 Questionnaires.

A reply that carries no InsurancePlan is settled as `empty`. A refusal arrives as a `ProtocolResponse` (for example PAYR-1008 or PAYR-1401 [PAYER](../references/PAYERS.md#markers)).

#### C4P. PSEUDOCODE

```
C4(envelope, corr):
    row = newest D10 where correlation_id == corr
    if none: return "unmatched"
    if row.status != "fetching" and not failed_send(row):
        return "ignored"
    body = payload(envelope)
    if body.type == "ProtocolResponse":
        write D10: status = "error", error_message = rejection(body)
        return "settled"
    revive(D10, row, "fetching")
    try:
        parsed = read_plan(body)       # A3S "How the reply is read"
    except no InsurancePlan in body:
        apply_plan(row, no benefits, no values, body)                  # status "empty"
        write D10: error_message = "The payer reply carries no InsurancePlan. " +
                                   "The payer has no package master filed under this policy."
        return "settled"
    apply_plan(row, parsed, body)
    return "settled"

read_plan(body):
    plan = first InsurancePlan                       # none -> the except branch above
    values = {plan_identifier (identifier[0].value, else id), plan_title (name),
              plan_type (type[0] display), sum_insured (first plan[].generalCost[].cost.value),
              policy_documents (requirements on the InsurancePlan itself)}
    benefits = packages from plan[].specificCost[].benefit[] (package master shape)
               merged on package code with coverage[].benefit[] (indemnity shape),
               specificCost winning; each with category, code, display, kind, rate,
               currency, cost_type, conditions, extras (tiers), supporting_info
    forms = each Questionnaire once per url
    return {values, benefits, forms}

apply_plan(row, parsed, body):
    in one transaction:
        write D10: parsed.values, status = "ready" if benefits else "empty",
                   fetched_at = now, error_message = null, response_json = body
        delete D11 and D12 rows of this plan
        insert D11 per benefit with seq 1..n
        insert D12 per form
```

#### C4S. RESPONSE
`settled`, `unmatched`, or `ignored` for a plan no longer `fetching`. No InsurancePlan in the bundle is not `rejected`; only a missing `fhir` is.

State changes:

| Table | Change |
|---|---|
| D10 claim_plan | `status` `ready` (at least one package), `empty` (none, including the no-InsurancePlan case, which also sets `error_message`), or `error` with `<code>: <message>`; plan identifier, title, type, sum insured, policy documents; `fetched_at`; `response_json` |
| D11 claim_plan_benefit | replaced: one row per package |
| D12 claim_plan_form | replaced: one row per Questionnaire |

#### C4U. USED BY
- Screens: [S7. Insurance Plan](../screens/S7-insurance-plan.md)
- APIs: [A3. Insurance Plan Request](../apis/A3-insurance-plan-request.md), [A10. Transaction Related](../apis/A10-txn-related.md), [A12. Transaction FHIR](../apis/A12-txn-fhir.md), [A17. Claim State](../apis/A17-claim-state.md)
- Callbacks: [C1. Callback Door](C1-callback-door.md), [C3. Authorisation Requirements Ruling](C3-auth-requirements-on-check.md)
- Database: [D10. claim_plan](../database/D10-claim-plan.md)
- Tests: [T1. Test Configuration](../tests/T1-test-configuration.md), [T4. IRDAI Insurance Plan and Authorisation Requirements](../tests/T4-irdai-plan-and-auth-requirements.md), [T13. PMJAY Eligibility, Package Master and Ruling](../tests/T13-pmjay-eligibility-and-package-master.md)
