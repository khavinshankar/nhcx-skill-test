# C2. Coverage Eligibility Verdict

#### C2E. ENDPOINT
Delivered in-process by [G8. Receive](../gateway/G8-receive.md) for NHCX route `v1/coverageeligibility/on_check`, passed to `C1.receive` with `delivery.type` `coverage`. Answers A2 sent with purpose `validation`, `benefits` or `discovery`. The auth-requirements ruling arrives on the same route and type and is C3.

#### C2D. DESCRIPTION
The payer's verdict on an eligibility check, seconds after A2 went out. Matched by `x-hcx-correlation_id` against the case itself (D9 `correlation_id`, newest row). When no case waits on that id, the same message is tried as a ruling (C3), because two coverage exchanges run per case.

Only a case still `checking` takes the verdict. A case that has settled answers `ignored`, which is what makes a redelivery harmless. A case on record as a failed send (C1 `failed_send`: status `error`) is reopened and the verdict applied, so a verdict that follows a `ProtocolResponse` still lands.

#### C2Q. REQUEST
`fhir` is an F1 Bundle that repeats the request's resources (F2 CoverageEligibilityRequest, F15 Patient, F17 Organizations, F19 Location, F18 Coverage, F16 PractitionerRole) and appends the payer's F3 CoverageEligibilityResponse with its own F15 Patient, F18 Coverage and F17 Organizations. Where a type repeats, the last copy is the payer's. Some payers send the CoverageEligibilityResponse alone or with only Patient and Coverage.

A refusal arrives as a `ProtocolResponse` (for example PAYR-1008 when the bundle's HFR ID does not match the id NHCX holds for the sender [PAYER](../references/PAYERS.md#markers)).

#### C2P. PSEUDOCODE

```
C2(envelope, corr):
    row = newest D9 where correlation_id == corr            # found by C1, else C3 runs instead
    if row.status != "checking" and not failed_send(row):
        return "ignored"
    body = payload(envelope)
    if body.type == "ProtocolResponse":
        write D9: status = "error", error_message = rejection(body)   # stage not restamped
        return "settled"
    verdict = first CoverageEligibilityResponse in body.entry     # read and validate before any write
    if none: raise Rejected("The payer reply carries no CoverageEligibilityResponse.")
    revive(D9, row, "checking")              # a rejected reply leaves the case exactly as it was
    ins = verdict.insurance[0]
    auth_required = last item.authorizationRequired that is present (1/0)
    wallets = every item.benefit with allowedMoney.value, as (type codes, allowed, used)
    wallet = the one typed "benefit", else typed "30", else the first   # [PAYER](../references/PAYERS.md#markers)
    allowed_amount = wallet.allowed + (wallet.used or 0)        # allowed is what is left [PAYER](../references/PAYERS.md#markers)
    used_amount = wallet.used
    patient = last Patient in the bundle; coverage = last Coverage
    values = {inforce, outcome, disposition, auth_required, allowed_amount, used_amount,
              beneficiary_name, patient_gender, patient_dob, patient_address, abha_number,
              patient_photo, plan_name, plan_period_start, plan_period_end, relationship}
             without empty values                              # empty never overwrites
    status = "error" if outcome == "error"
             else "eligible" if inforce
             else "not-eligible"
    write D9: values, status, response_json = body
    restamp the case stage
    return "settled"
```

Column sources: `beneficiary_name` from `name[0].text`, else the given names, else `family`; `patient_address` joins `line`, `district`, `state`, `postalCode`; `abha_number` from the identifier typed `ABHA`; `patient_photo` from `photo[0].data` or `url`; `plan_name` from `Coverage.class[0].name`; `plan_period_*` from `Coverage.period`; `relationship` from `Coverage.relationship` display, else code.

#### C2S. RESPONSE
`settled`, `ignored` for a case no longer `checking`, or `rejected` when the bundle carries no CoverageEligibilityResponse (the case is left exactly as it was: the verdict is read and validated before the failed-send revive, so a rejected reply never reopens a case; C1 may also run the handler in a savepoint, which rolls a revive back on `rejected` anyway).

State changes, D9 claim:

| Reply | `status` | Other columns |
|---|---|---|
| verdict, `outcome` `error` | `error` | the verdict columns above, `response_json` |
| verdict, `inforce` true | `eligible` | as above; `stage` / `sub_stage` restamped |
| verdict, otherwise | `not-eligible` | as above |
| `ProtocolResponse` | `error` | `error_message` = `<code>: <message>` |

#### C2U. USED BY
- Screens: [S3. Policy Discovery](../screens/S3-policy-discovery.md), [S17. Beneficiary Discovery](../screens/S17-beneficiary-discovery.md)
- APIs: [A2. Coverage Eligibility Check](../apis/A2-coverage-eligibility-check.md), [A10. Transaction Related](../apis/A10-txn-related.md), [A11. Transaction Dispatch](../apis/A11-txn-dispatch.md), [A12. Transaction FHIR](../apis/A12-txn-fhir.md), [A17. Claim State](../apis/A17-claim-state.md)
- Callbacks: [C1. Callback Door](C1-callback-door.md), [C3. Authorisation Requirements Ruling](C3-auth-requirements-on-check.md)
- FHIR: [F3. CoverageEligibilityResponse](../fhir/F3-coverage-eligibility-response.md), [F15. Patient](../fhir/F15-patient.md)
- Database: [D9. claim](../database/D9-claim.md)
- Gateway: [G7. Send](../gateway/G7-send.md)
- Tests: [T3. IRDAI Policy Search and Eligibility](../tests/T3-irdai-policy-and-eligibility.md), [T13. PMJAY Eligibility, Package Master and Ruling](../tests/T13-pmjay-eligibility-and-package-master.md)
