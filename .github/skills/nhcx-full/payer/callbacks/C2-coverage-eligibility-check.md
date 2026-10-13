# C2. Coverage Eligibility Check

#### C2E. ENDPOINT
Delivered in-process by [G8. Receive](../gateway/G8-receive.md) for NHCX route `v1/coverageeligibility/check`, passed to `C1.receive`, classified `eligibility` because the bundle holds a `CoverageEligibilityRequest` ([F2. CoverageEligibilityRequest](../fhir/F2-coverage-eligibility-request.md)). Answered inside the same delivery by [A1. Eligibility Answer](../apis/A1-eligibility-answer.md) on `v1/coverageeligibility/on_check`, on the request's own correlation id.

#### C2D. DESCRIPTION
The first question a hospital asks about a patient, and the only one it may ask several ways at once: `purpose` carries `validation` (is the cover in force), `benefits` (what does it allow), `discovery` (which cover does this person have, sent with no policy code) and `auth-requirements` (what does this payer want with these packages). One reply answers all the purposes sent.

**The beneficiary's user token.** A hospital that has authenticated the beneficiary against their ABHA (ABDM's biometric service, not an NHCX exchange) may carry the user token on the request's protected headers, under the header its onboarding names, with `x-hcx-ben-abha-id` beside it; any hospital may send it to any payer. This payer reads it when present and records it on the delivery (the header name is a module setting, default `x-hcx-user-token`); it never refuses an eligibility check for lacking one. Under the `pmjay` profile the token, or the scheme's consent questionnaire on the later legs, is what proves presence ([PAYERS.md](../references/PAYERS.md)); the live scheme validates the token itself.

**Who it is about.** Every handle the request carries is read the same way, and the enrolment is found by any of them: the ABHA number (14 digits, on the member or on the enrolment the link was made against), the mobile number (compared on its last ten digits, separators stripped), the member id (any identifier on the Patient that is neither ABHA nor mobile), and `Coverage.subscriberId` as the fallback when the typed identifiers said nothing (read as an ABHA when it is 14 digits, a mobile when it is ten, else a member id). The policy code on the Coverage is not a handle: a discovery sends `NONE`, and a hospital's spelling of a product is checked by [A2. Insurance Plan Answer](../apis/A2-insurance-plan-answer.md), not here.

**Three answers.** The lookup goes for cover in force today first (active, today inside the period), then for the most recently ended cover the same person had, so the answer can say "lapsed on" rather than "never heard of you":

| Found | Answer (A1) | Delivery outcome |
|---|---|---|
| an enrolment in force | in force, with the wallet as the benefit; for `auth-requirements`, the ruling per item | `answered` |
| an enrolment, not in force today | `inforce` false with the period that ended, so the hospital reads a lapse, not an unknown person | `lapsed` |
| nothing | the no-cover bundle: `inforce` false, the handles echoed, no Coverage | `no_cover` |

A payer that has never heard of the person is still an answer: the hospital's poll is waiting on the thread, and silence would leave it to time out.

**The ruling.** With `auth-requirements`, each `item` names a package the hospital intends to claim. A1 answers per item with the package rate and the documents and forms wanted at each stage, from the procedure registry ([D10. procedure_rule](../database/D10-procedure-rule.md), [D11. procedure_rule_doc](../database/D11-procedure-rule-doc.md)) and the enrolment's product ([D12. policy](../database/D12-policy.md), [D13. policy_procedure](../database/D13-policy-procedure.md)); an item this payer does not price is answered as not priced. The dialect of the ruling (how a document's stage and a form's url are written into `authorizationSupporting`) is the scheme's [PAYER](../references/PAYERS.md#markers), see [F3. CoverageEligibilityResponse](../fhir/F3-coverage-eligibility-response.md).

**Nothing is stored.** No case, no row: an enquiry is answered from the registry and forgotten, except for the audit line ([D31. audit_log](../database/D31-audit-log.md)) and the answer in [G9. Ledger](../gateway/G9-ledger.md). Two enquiries about one person are two answers.

**Redelivery.** C1 drops a repeated delivery by api call id. A repeat that slips through is answered again, which is harmless: the reply is the same and the hospital's poll takes the first.

#### C2Q. REQUEST
`fhir` is an [F1. Bundle](../fhir/F1-bundle.md) Bundle carrying [F2. CoverageEligibilityRequest](../fhir/F2-coverage-eligibility-request.md) CoverageEligibilityRequest with [F15. Patient](../fhir/F15-patient.md) Patient, [F18. Coverage](../fhir/F18-coverage.md) Coverage (subscriber id, policy code or `NONE`), the provider [F17. Organization](../fhir/F17-organization.md) Organization typed `prov` (the asker, echoed back as the requestor) and the payer Organization. Headers read: `x-hcx-sender_code` (the hospital), `x-hcx-recipient_code` (this payer), `x-hcx-correlation_id`, `x-hcx-workflow_id` (echoed on the answer; NHA publishes no eligibility workflow code, hospitals send 11 or their case number).

#### C2P. PSEUDOCODE

```
C2(in, ask):                                         # ask = F2 parse: purposes, handles, items, provider
    handles = {abha: ask.abha_no, mobile: ask.mobile, member_id: ask.member_id}
              with ask.subscriber_id filling whichever of the three is empty and fits it
    subscription = find_enrolment(handles)           # C1 shared rule: in force, else lapsed, else none
    if subscription:
        member = D5[subscription.member_id]
        policy = D12[subscription.policy_id]
        bundle = A1.eligibility_response({payer: in.payer, payer_code: in.recipient,
                     member, subscription, policy,
                     provider: {id: ask.provider_id, name: ask.provider_name},
                     purposes: ask.purposes, items: ask.items, request: payload(in.envelope)})
        status = "answered"
        action = "eligibility.answered"
        detail = "<sender> asked, correlation <corr>, subscription <id>"
        if "auth-requirements" in ask.purposes:
            action = "eligibility.auth_requirements"
            detail = "<sender> asked about <n> items, correlation <corr>, subscription <id>"
        if subscription not in force today:          # active, pstart <= today <= pend
            status = "lapsed"; action = "eligibility.lapsed"
    else:
        bundle = A1.no_cover_response({payer: in.payer, payer_code: in.recipient,
                     provider: {id: ask.provider_id, name: ask.provider_name},
                     request: payload(in.envelope), purposes: ask.purposes,
                     patient_name: ask.patient_name, abha: ask.abha_no, mobile: ask.mobile,
                     searched_id: ask.member_id or ask.subscriber_id})
        status = "no_cover"; action = "eligibility.no_cover"
        detail = "<sender> asked, correlation <corr>, no enrolment matched"

    ack = answer(in, bundle, "v1/coverageeligibility/on_check",
                 workflow = in.workflow_id, status = "response.complete", what = action)
    return "settled"                                 # delivery outcome {status, subscription_id, txn_id}
```

The answer is built and sent by [A1. Eligibility Answer](../apis/A1-eligibility-answer.md); the refusal paths (`rejected` when the gateway refuses the envelope, `error` when it is unreachable) are C1's shared `answer` rule.

#### C2S. RESPONSE
`settled` in all three cases (in force, lapsed, no cover); `rejected` when the bundle cannot be read or the gateway refuses the answer; `error` when the gateway is not configured or not reachable, so NHCX redelivers the enquiry.

State changes: none on the registry. One [D31. audit_log](../database/D31-audit-log.md) audit row (`eligibility.answered`, `eligibility.auth_requirements`, `eligibility.lapsed` or `eligibility.no_cover`, entity `nhcx_txn`, the delivery's ledger id, with the answer's transaction id). The answer itself is on the ledger ([G9. Ledger](../gateway/G9-ledger.md)). In the sandbox the enquiry ticks the integration checklist for the addressed participant, one step per purpose [SANDBOX](../references/PAYERS.md#markers).

#### C2U. USED BY
- Screens: [S4. Members](../screens/S4-members.md), [S5. Subscriptions](../screens/S5-subscriptions.md)
- APIs: [A1. Eligibility Answer](../apis/A1-eligibility-answer.md), [A11. Transaction Related](../apis/A11-txn-related.md), [A15. Case Exchange Log](../apis/A15-case-exchange.md), [A16. ABHA Policy Link](../apis/A16-abha-policy-link.md), [A18. Provider Driver](../apis/A18-provider-driver.md), [A20. ABHA Create and Verify (ABDM M1)](../apis/A20-abha-m1.md)
- Callbacks: [C1. Callback Door](C1-callback-door.md), [C4. Pre-auth Submit](C4-preauth-submit.md)
- FHIR: [F1. Bundle](../fhir/F1-bundle.md), [F2. CoverageEligibilityRequest](../fhir/F2-coverage-eligibility-request.md), [F3. CoverageEligibilityResponse](../fhir/F3-coverage-eligibility-response.md)
- Database: [D5. member](../database/D5-member.md), [D6. subscription](../database/D6-subscription.md), [D7. subscription_family_member](../database/D7-subscription-family-member.md)
- Tests: [T3. Eligibility Validation and Discovery Answered](../tests/T3-eligibility-answered.md), [T4. Auth-requirements Ruling Answered](../tests/T4-auth-requirements-ruled.md)
