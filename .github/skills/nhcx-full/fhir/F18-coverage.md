# F18. Coverage

#### F18R. RESOURCE
- `resourceType`: `Coverage`
- Profile in `meta.profile`: `https://nrces.in/ndhm/fhir/r4/StructureDefinition/Coverage`
- Direction: **sent** at `https://nhcx.abdm.gov.in/coverage` in the eligibility bundle and every claim-side bundle. **Received**: the payer's own Coverage in the eligibility reply, read back onto the claim.

#### F18D. DESCRIPTION
The policy the claim is made against. The same content in every sent bundle; what differs is where the policy code and member id come from, and the `id`:

| Bundle | `id` | Policy code | Member id |
|---|---|---|---|
| Eligibility check (F2 via A2), purposes validation, benefits, discovery | none | the policy code entered on the check form, else `NONE` | the member id entered on the check form |
| Auth-requirements check (F2 via A2) | none | `D9 claim.policy_code`, else `NONE` | `D9 claim.member_id` |
| Claim bundles (F8 via A4, A5) | `1` | `D9 claim.policy_code`, else `NONE` | `D9 claim.member_id` |
| Communication reply (F12 via A7) | as the sent leg had it | lifted from the sent leg; when none went out, built as the claim-bundle Coverage | |

`NONE` is the discovery value: "which plan is the question". A validation or benefits check refuses without a policy code ("Policy code is required for a validation check."), so only a discovery (or a claim with no policy code) sends `NONE`. After an eligibility check, `D9 claim.policy_code` becomes the code the check was sent with (or keeps its old value when the form was empty) and `D9 claim.member_id` the member id.

The policy code on the claim row comes from the policy search (A1): the BIS's policy-number field when present, else its `productid` [REF](../references/PAYERS.md#markers).

Relationship is always `self`: the beneficiary is the subscriber [REF](../references/PAYERS.md#markers). The payer's reply may state another relationship (for example `child`); that is stored for display but never sent back.

#### F18F. FIELDS
**Sent**

| Element path | Value or source | Cardinality / notes |
|---|---|---|
| `id` | `1` in claim bundles, else absent | |
| `meta.profile[0]` | `.../StructureDefinition/Coverage` | |
| `identifier[0].type.coding[0]` | `http://terminology.hl7.org/CodeSystem/v2-0203` `NH` "National Health Plan Identifier" | |
| `identifier[0].value` | the policy code (table above), else `NONE` | no `system` |
| `status` | `active` | constant |
| `type.coding[0]` | `http://terminology.hl7.org/CodeSystem/v3-ActCode` `HIP` "health insurance plan policy" | constant |
| `subscriber` | `{reference: "https://nhcx.abdm.gov.in/patient"}` | F15 |
| `subscriberId` | the member id (table above) | |
| `beneficiary` | `{reference: "https://nhcx.abdm.gov.in/patient"}` | F15 |
| `relationship.coding[0]` | `http://terminology.hl7.org/CodeSystem/subscriber-relationship` `self` | no display |
| `payor[0]` | `{reference: "https://nhcx.abdm.gov.in/payer"}` | F17 |

Not sent: `period`, `class`, `network`, `order`, `dependent`.

The eligibility builder writes `status` and `type` before `identifier`; the claim builder writes `identifier` first [REF](../references/PAYERS.md#markers). The content is the same.

**Received (eligibility reply).** The reply repeats the request's Coverage and appends the payer's; the **last** Coverage is read onto `D9 claim`:

| Element path | Stored in |
|---|---|
| `class[0].name` | `plan_name` |
| `period.start` | `plan_period_start` |
| `period.end` | `plan_period_end` |
| `relationship.coding[0].display`, else `.code` | `relationship` |

Empty values are not written. Coverages in ClaimResponse, Task and communication bundles are not read.

#### F18U. USED BY
- APIs: [A2. Coverage Eligibility Check](../apis/A2-coverage-eligibility-check.md), [A4. Pre-auth Submit](../apis/A4-preauth-submit.md), [A5. Claim Submit](../apis/A5-claim-submit.md), [A7. Communication Reply](../apis/A7-communication-on-request.md)
- Callbacks: [C2. Coverage Eligibility Verdict](../callbacks/C2-coverage-eligibility-on-check.md), [C3. Authorisation Requirements Ruling](../callbacks/C3-auth-requirements-on-check.md), [C5. Pre-auth Reply](../callbacks/C5-preauth-on-submit.md), [C6. Claim Reply](../callbacks/C6-claim-on-submit.md), [C7. Cancel Reply](../callbacks/C7-cancel-on-submit.md), [C9. Payer Communication](../callbacks/C9-communication-request.md)
- FHIR: [F2. CoverageEligibilityRequest](F2-coverage-eligibility-request.md), [F8. Claim](F8-claim.md), [F12. Communication](F12-communication.md)
