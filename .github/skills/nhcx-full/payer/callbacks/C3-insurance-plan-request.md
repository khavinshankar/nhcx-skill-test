# C3. Insurance Plan Request

#### C3E. ENDPOINT
Delivered in-process by [G8. Receive](../gateway/G8-receive.md) for NHCX route `v1/insuranceplan/request`, passed to `C1.receive`, classified `insuranceplan` because the bundle holds a `Task` asking for a plan ([F4. Task (InsurancePlan request)](../fhir/F4-task-insuranceplan.md): coded `poll`, or with no code and intent `plan` or none). Answered inside the same delivery by [A2. Insurance Plan Answer](../apis/A2-insurance-plan-answer.md) on `v1/insuranceplan/on_request`, on the request's own correlation id.

#### C3D. DESCRIPTION
The hospital wants the package master: which procedures a product covers, at what rate, with which documents and forms. The request is a Task rather than a plan ("send me the plan", not "here is a plan"), and it carries what it wants in two typed inputs: `policyNumber` and `providerId`. A Task coded anything else is somebody else's errand and goes to C7 or C8.

**What the policy number may be.** The hospital names the product as it knows it, and four spellings are honoured, in this order:

1. The product's own id, UIN or an alias ([D12. policy](../database/D12-policy.md), [D16. policy_alias](../database/D16-policy-alias.md)).
2. An enrolment id ([D6. subscription](../database/D6-subscription.md)): the handle this payer's own eligibility answer ([A1. Eligibility Answer](../apis/A1-eligibility-answer.md)) gave the hospital as the coverage identifier. A handle this payer taught the hospital has to resolve here too. The plan is then rendered as that person's cover rather than the product on offer.
3. A retired product's code ([D12. policy](../database/D12-policy.md) with `deleted_at` set): everyone who held it was moved onto the default product when it went, and a registry a hospital reads may still quote the old code, so the cover on offer under it is the default product's [REF](../references/PAYERS.md#markers).
4. Nothing: the empty plan.

**A product nobody has filed is answered, not refused.** The empty InsurancePlan bundle still carries this payer's Organization, so the answer says who could not find it. NHA's implementation guide allows an empty plan when no cover matches the policy and provider, and silence would leave the hospital's poll running until it timed out with nothing to show for it.

**Nothing is stored** beyond the audit line ([D31. audit_log](../database/D31-audit-log.md)). The plan is rendered from [D10. procedure_rule](../database/D10-procedure-rule.md) to [D18. policy_sub_limit](../database/D18-policy-sub-limit.md) on every request, so a change to a product or a procedure is served on the next ask.

**Redelivery.** C1 drops a repeat by api call id; a repeat that slips through is answered again with the same plan.

#### C3Q. REQUEST
`fhir` is an [F1. Bundle](../fhir/F1-bundle.md) Bundle carrying [F4. Task (InsurancePlan request)](../fhir/F4-task-insuranceplan.md) Task with inputs typed `policyNumber` and `providerId` (the NDHM task-input-type system), and usually the asking hospital's [F17. Organization](../fhir/F17-organization.md) Organization, whose name is read for the audit line. Headers read: `x-hcx-sender_code`, `x-hcx-recipient_code`, `x-hcx-correlation_id`, `x-hcx-workflow_id` (echoed).

#### C3P. PSEUDOCODE

```
C3(in, ask):                                         # ask = F4 parse: policy_number, provider_id, provider_name
    asked = ask.provider_name or ask.provider_id or in.sender
    enrolment = none
    policy = D12 by code (id, uin or D16 alias), live
    if none:
        sub = D6[ask.policy_number]
        if sub: policy = D12[sub.policy_id]; enrolment = sub
    if none and a retired D12 row has that code:
        policy = D12 by code (the default product)   # [REF](../references/PAYERS.md#markers)
    if none:
        bundle = A2.empty_plan({payer: in.payer})
        ack = answer(in, bundle, "v1/insuranceplan/on_request",
                     workflow = in.workflow_id, status = "response.complete",
                     what = "insuranceplan.no_plan")
        D31 detail: "<asked> asked, correlation <corr>, no product matched <policy_number>"
        return "settled"                             # outcome {status: no_plan, txn_id}

    bundle = A2.insurance_plan({payer: in.payer, policy, enrolment})
    ack = answer(in, bundle, "v1/insuranceplan/on_request",
                 workflow = in.workflow_id, status = "response.complete",
                 what = "insuranceplan.answered")
    D31 detail: "<asked> asked, correlation <corr>, policy <policy.id>"
    return "settled"                                 # outcome {status: answered, policy_id, txn_id}
```

#### C3S. RESPONSE
`settled` whether a plan or the empty plan went back; `rejected` when the bundle cannot be read or the gateway refuses the answer; `error` when the gateway is not configured or not reachable, so NHCX redelivers.

State changes: none on the products. One [D31. audit_log](../database/D31-audit-log.md) audit row (`insuranceplan.answered` or `insuranceplan.no_plan`, entity `nhcx_txn`, the delivery's ledger id, with the answer's transaction id). In the sandbox a served plan ticks the checklist for the addressed participant [SANDBOX](../references/PAYERS.md#markers).

#### C3U. USED BY
- Screens: [S6. Policies](../screens/S6-policies.md)
- APIs: [A2. Insurance Plan Answer](../apis/A2-insurance-plan-answer.md), [A18. Provider Driver](../apis/A18-provider-driver.md)
- Callbacks: [C1. Callback Door](C1-callback-door.md), [C7. Task Submit](C7-task-submit.md)
- FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F4. Task (InsurancePlan request)](../fhir/F4-task-insuranceplan.md), [F5. InsurancePlan](../fhir/F5-insuranceplan.md)
- Database: [D6. subscription](../database/D6-subscription.md), [D12. policy](../database/D12-policy.md), [D16. policy_alias](../database/D16-policy-alias.md)
- Tests: [T5. Insurance Plan Served](../tests/T5-insurance-plan-served.md)
