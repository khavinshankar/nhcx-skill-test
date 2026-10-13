# C3. Authorisation Requirements Ruling

#### C3E. ENDPOINT
Delivered in-process by [G8. Receive](../gateway/G8-receive.md) for NHCX route `v1/coverageeligibility/on_check`, passed to `C1.receive` with `delivery.type` `coverage`. Answers A2 sent with purpose `auth-requirements`. Reached only when no case (D9) waits on the correlation id; otherwise the message is C2.

#### C3D. DESCRIPTION
The payer's ruling on the procedure set: for each quoted line, whether it needs authorisation, whether it is excluded, what it would allow, and which documents and forms have to accompany it. Matched by `x-hcx-correlation_id` against the ruling (D13 `correlation_id`, newest row). Nothing matching answers `unmatched`.

Only a ruling still `checking` takes it; a settled ruling answers `ignored` (redelivery). A ruling on record as a failed send (`error`) is reopened and the reply applied.

#### C3Q. REQUEST
The same F1 Bundle shape as C2: the request's resources (F2 with the procedure set in `item[]`) followed by the payer's F3 CoverageEligibilityResponse (purpose `auth-requirements`), F15 Patient, F18 Coverage and F17 Organizations. Each `insurance[0].item[]` rules on one line; its `authorizationSupporting[]` names what must accompany it, with the kind, stage and form url in free text [PAYER](../references/PAYERS.md#markers).

#### C3P. PSEUDOCODE

```
C3(envelope, corr):
    row = newest D13 where correlation_id == corr
    if none: return "unmatched"
    if row.status != "checking" and not failed_send(row):
        return "ignored"
    body = payload(envelope)
    if body.type == "ProtocolResponse":
        write D13: status = "error", error_message = rejection(body)
        return "settled"
    revive(D13, row, "checking")
    adapter = payer adapter of the case's payer (D9.payer_id)
    verdict = LAST CoverageEligibilityResponse in body.entry
    if none: raise Rejected("The payer reply carries no CoverageEligibilityResponse.")
    ins = verdict.insurance[0]
    items = []; requirements = []; seen = {}
    for each item in ins.item:
        items += {code, display (productOrService), category_code, auth_required (1/0/null),
                  excluded (1/0/null), benefit_type (benefit[0].type code),
                  allowed_amount (benefit[0].allowedMoney.value)}
        for each support in item.authorizationSupporting:
            s = adapter.read_supporting(support)
                # "fullUrl: <url>" in text -> kind form, else document
                # "Type: <stage>" -> stage (a document with none is "pre"; a form with none is "") [REF](../references/PAYERS.md#markers)
                # "Procedure Code:<code>" -> for_code
                # at_preauth = kind is form, or stage in adapter.preauth_stages
            key = (s.kind, s.code, s.form_url)
            if key in seen: continue
            seen += key
            requirements += {kind, code, display, form_url, stage,
                             for_code (else the item's code), at_preauth (1/0)}
    in one transaction:
        write D13: outcome, disposition, inforce, status = "ready", settled_at = now,
                   error_message = null, response_json = body
        delete D14 and D15 rows of this ruling
        insert D14 per item with seq 1..n
        insert D15 per requirement with seq 1..n
    return "settled"
```

#### C3S. RESPONSE
`settled`, `unmatched` when no ruling waits on the thread, `ignored` for a ruling no longer `checking`, or `rejected` when no CoverageEligibilityResponse is carried.

State changes:

| Table | Change |
|---|---|
| D13 claim_auth | `status` `ready` (or `error` with `error_message` `<code>: <message>` for a `ProtocolResponse`), `outcome`, `disposition`, `inforce`, `settled_at`, `response_json` |
| D14 claim_auth_item | replaced: one row per ruled line |
| D15 claim_auth_requirement | replaced: one row per distinct document or form |

A reply with no `authorizationSupporting` is valid: the ruling is `ready` with no requirement rows, and the package master's own list (C4) is what applies.

#### C3U. USED BY
- Screens: [S8. Line Items](../screens/S8-line-items.md)
- APIs: [A2. Coverage Eligibility Check](../apis/A2-coverage-eligibility-check.md), [A10. Transaction Related](../apis/A10-txn-related.md), [A12. Transaction FHIR](../apis/A12-txn-fhir.md), [A17. Claim State](../apis/A17-claim-state.md)
- Callbacks: [C1. Callback Door](C1-callback-door.md), [C2. Coverage Eligibility Verdict](C2-coverage-eligibility-on-check.md)
- FHIR: [F3. CoverageEligibilityResponse](../fhir/F3-coverage-eligibility-response.md)
- Database: [D12. claim_plan_form](../database/D12-claim-plan-form.md), [D13. claim_auth](../database/D13-claim-auth.md)
- Tests: [T4. IRDAI Insurance Plan and Authorisation Requirements](../tests/T4-irdai-plan-and-auth-requirements.md), [T13. PMJAY Eligibility, Package Master and Ruling](../tests/T13-pmjay-eligibility-and-package-master.md)
